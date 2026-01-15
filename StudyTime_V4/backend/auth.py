"""
Authentication and Security Module for StudyTime
Handles password hashing, session management, and user verification
"""

from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import secrets
from sqlalchemy.orm import Session
from models import User

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session store (in-memory for simplicity, use Redis for production)
active_sessions = {}

SESSION_DURATION = timedelta(days=7)  # Sessions last 7 days


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage"""
    return pwd_context.hash(password)


def create_session(user_id: str, email: str, username: str, is_admin: bool = False) -> str:
    """Create a new session token for a user"""
    session_token = secrets.token_urlsafe(32)
    
    active_sessions[session_token] = {
        "user_id": user_id,
        "email": email,
        "username": username,
        "is_admin": is_admin,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + SESSION_DURATION
    }
    
    return session_token


def validate_session(session_token: str) -> Optional[dict]:
    """Validate a session token and return user data if valid"""
    if not session_token:
        return None
    
    session_data = active_sessions.get(session_token)
    
    if not session_data:
        return None
    
    # Check if session expired
    if datetime.utcnow() > session_data["expires_at"]:
        del active_sessions[session_token]
        return None
    
    return session_data


def destroy_session(session_token: str) -> bool:
    """Destroy a session (logout)"""
    if session_token in active_sessions:
        del active_sessions[session_token]
        return True
    return False


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, email: str, username: str, password: str, 
                full_name: Optional[str] = None, is_admin: bool = False) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(password)
    
    user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        full_name=full_name,
        is_admin=is_admin
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def authenticate_user(db: Session, login: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email/username and password
    Returns user if valid, None otherwise
    """
    # Try to find user by email first, then username
    user = get_user_by_email(db, login)
    if not user:
        user = get_user_by_username(db, login)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if not user.is_active:
        return None
    
    return user