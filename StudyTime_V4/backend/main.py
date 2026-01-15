from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Request, Cookie
from typing import Optional
import auth  # Import your new auth module

# Import database and models
from database import get_db, init_db, check_db_connection, DatabaseManager
from models import Course, Task, Break, Job, Commute, User, UserPreferences, ScheduledEvent

# Import updated scheduler
import scheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="StudyTime API",
    description="Smart study scheduling API with personalization",
    version="3.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates directory
frontend_dir = Path(__file__).parent.parent / "frontend"
templates = Jinja2Templates(directory=str(frontend_dir))


# ============================================
# PAGE ROUTES - Login comes first
# ============================================

@app.get("/")
def root_redirect():
    """Redirect root to login page"""
    return RedirectResponse(url="/login")


@app.get("/login")
def login_page(request: Request):
    """Login page - Entry point of the app"""
    return FileResponse(str(frontend_dir / "login.html"))


@app.get("/dashboard")
def dashboard_page(request: Request):
    """Dashboard overview page"""
    return FileResponse(str(frontend_dir / "dashboard.html"))


@app.get("/calendar")
def calendar_page(request: Request):
    """Calendar view page"""
    return FileResponse(str(frontend_dir / "calendar.html"))


@app.get("/schedule")
def schedule_page(request: Request):
    """Schedule input page"""
    return FileResponse(str(frontend_dir / "index.html"))


@app.get("/preferences")
def preferences_page(request: Request):
    """User preferences page"""
    return FileResponse(str(frontend_dir / "preferences.html"))


# ============================================
# AUTH ENDPOINTS
# ============================================

# Add this helper function to get current user from session
def get_current_user(session_token: Optional[str] = Cookie(None, alias="session_token")):
    """Dependency to get current authenticated user"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_data = auth.validate_session(session_token)
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return session_data

# Add optional authentication (doesn't raise error if not authenticated)
def get_current_user_optional(session_token: Optional[str] = Cookie(None, alias="session_token")):
    """Optional authentication - returns None if not authenticated"""
    if not session_token:
        return None
    return auth.validate_session(session_token)


# ============================================
# REPLACE YOUR AUTH ENDPOINTS WITH THESE:
# ============================================

@app.post("/api/auth/signup")
def signup(credentials: dict, db: Session = Depends(get_db)):
    """User registration"""
    email = credentials.get("email", "").strip().lower()
    username = credentials.get("username", "").strip().lower()
    password = credentials.get("password", "")
    full_name = credentials.get("fullName", "").strip()
    
    # Validation
    if not email or not username or not password:
        raise HTTPException(status_code=400, detail="Email, username, and password are required")
    
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Check if user already exists
    if auth.get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if auth.get_user_by_username(db, username):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    try:
        # Create new user
        user = auth.create_user(
            db=db,
            email=email,
            username=username,
            password=password,
            full_name=full_name if full_name else None
        )
        
        logger.info(f"New user registered: {email}")
        
        return {
            "success": True,
            "message": "Account created successfully!",
            "user": user.to_dict()
        }
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create account")


@app.post("/api/auth/login")
def login(credentials: dict, response: Response, db: Session = Depends(get_db)):
    """User login with session creation"""
    login_input = credentials.get("login", "").strip().lower()  # email or username
    password = credentials.get("password", "")
    
    if not login_input or not password:
        raise HTTPException(status_code=400, detail="Login and password are required")
    
    # Authenticate user
    user = auth.authenticate_user(db, login_input, password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email/username or password")
    
    # Create session
    session_token = auth.create_session(
        user_id=user.id,
        email=user.email,
        username=user.username,
        is_admin=user.is_admin
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Set session cookie (HttpOnly for security)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=60*60*24*7,  # 7 days
        samesite="lax"
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return {
        "success": True,
        "user": user.to_dict()
    }


@app.post("/api/auth/logout")
def logout(response: Response, current_user: dict = Depends(get_current_user)):
    """Logout and destroy session"""
    # Get session token from cookie
    session_token = current_user.get("session_token")
    
    if session_token:
        auth.destroy_session(session_token)
    
    # Clear session cookie
    response.delete_cookie(key="session_token")
    
    return {"success": True, "message": "Logged out successfully"}


@app.get("/api/auth/me")
def get_current_user_info(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current authenticated user information"""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user.to_dict()


# ============================================
# USER PREFERENCES ENDPOINTS
# ============================================

'''@app.get("/api/preferences")
def get_preferences(user_id: str = "default", db: Session = Depends(get_db)):
    """Get user preferences"""
    try:
        prefs = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if not prefs:
            # Return defaults
            return {
                "name": None,
                "timezone": "America/New_York",
                "wake": "08:00",
                "sleep": "23:00",
                "maxStudyHours": 6,
                "sessionLength": 60,
                "breakDuration": 15,
                "betweenClasses": 30,
                "afterSchool": 120,
                "urgencyMode": "balanced",
                "studyTime": "afternoon",
                "autoSplit": True,
                "prioritizeHard": True,
                "weekendStudy": True,
                "deadlineBuffer": 12,
                "lunchStart": "12:00",
                "lunchEnd": "13:00",
                "dinnerStart": "18:00",
                "dinnerEnd": "19:00",
                "autoMeals": True,
            }
        
        return prefs.to_dict()
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/preferences")
def save_preferences(prefs_data: dict, user_id: str = "default", db: Session = Depends(get_db)):
    """Save or update user preferences"""
    try:
        # Check if preferences exist
        existing = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if existing:
            # Update existing
            for key, value in prefs_data.items():
                # Convert camelCase to snake_case
                snake_key = ''.join(['_'+c.lower() if c.isupper() else c for c in key]).lstrip('_')
                if hasattr(existing, snake_key):
                    setattr(existing, snake_key, value)
            
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing.to_dict()
        else:
            # Create new
            new_prefs = UserPreferences(
                user_id=user_id,
                name=prefs_data.get("name"),
                timezone=prefs_data.get("timezone", "America/New_York"),
                wake=prefs_data.get("wake", "08:00"),
                sleep=prefs_data.get("sleep", "23:00"),
                max_study_hours=prefs_data.get("maxStudyHours", 6.0),
                session_length=prefs_data.get("sessionLength", 60),
                break_duration=prefs_data.get("breakDuration", 15),
                between_classes=prefs_data.get("betweenClasses", 30),
                after_school=prefs_data.get("afterSchool", 120),
                urgency_mode=prefs_data.get("urgencyMode", "balanced"),
                study_time=prefs_data.get("studyTime", "afternoon"),
                auto_split=prefs_data.get("autoSplit", True),
                prioritize_hard=prefs_data.get("prioritizeHard", True),
                weekend_study=prefs_data.get("weekendStudy", True),
                deadline_buffer=prefs_data.get("deadlineBuffer", 12),
                lunch_start=prefs_data.get("lunchStart", "12:00"),
                lunch_end=prefs_data.get("lunchEnd", "13:00"),
                dinner_start=prefs_data.get("dinnerStart", "18:00"),
                dinner_end=prefs_data.get("dinnerEnd", "19:00"),
                auto_meals=prefs_data.get("autoMeals", True),
            )
            
            db.add(new_prefs)
            db.commit()
            db.refresh(new_prefs)
            return new_prefs.to_dict()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))'''

# ============================================
# COURSES - ADD AUTHENTICATION
# ============================================
@app.get("/api/courses", response_model=List[Dict])
def get_courses(
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Get all courses for current user"""
    user_id = current_user["user_id"]  # ✅ ADD THIS
    courses = db.query(Course).filter(Course.user_id == user_id).all()  # ✅ FILTER BY USER
    return [course.to_dict() for course in courses]


@app.post("/api/courses", response_model=Dict)
def create_course(
    course: dict,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Create a new course"""
    try:
        db_course = Course(
            user_id=current_user["user_id"],  # ✅ ADD THIS
            name=course.get("name"),
            days=course.get("days"),
            start=course.get("start"),
            end=course.get("end"),
            color=course.get("color", "#1565c0")
        )
        return DatabaseManager.create(db, db_course).to_dict()
    except Exception as e:
        logger.error(f"Error creating course: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/courses/{course_id}")
def delete_course(
    course_id: str,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Delete a course"""
    user_id = current_user["user_id"]  # ✅ ADD THIS
    db_course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == user_id  # ✅ ENSURE USER OWNS THIS
    ).first()
    
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    DatabaseManager.delete(db, db_course)
    return {"message": "Course deleted successfully"}


# ============================================
# TASKS - ADD AUTHENTICATION
# ============================================
@app.get("/api/tasks", response_model=List[Dict])
def get_tasks(
    completed: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Get all tasks for current user"""
    user_id = current_user["user_id"]  # ✅ ADD THIS
    query = db.query(Task).filter(Task.user_id == user_id)  # ✅ FILTER BY USER
    if completed is not None:
        query = query.filter(Task.completed == completed)
    tasks = query.all()
    return [task.to_dict() for task in tasks]


@app.post("/api/tasks", response_model=Dict)
def create_task(
    task: dict,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Create a new task"""
    try:
        db_task = Task(
            user_id=current_user["user_id"],  # ✅ ADD THIS
            name=task.get("name"),
            duration=task.get("duration"),
            due=task.get("due"),
            difficulty=task.get("difficulty", "Medium"),
            is_exam=task.get("is_exam", False),
            color=task.get("color", "#4CAF50"),
            notes=task.get("notes")
        )
        return DatabaseManager.create(db, db_task).to_dict()
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/api/tasks/{task_id}/complete")
def mark_task_complete(
    task_id: str,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Mark a task as completed"""
    user_id = current_user["user_id"]  # ✅ ADD THIS
    db_task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id  # ✅ ENSURE USER OWNS THIS
    ).first()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db_task.completed = True
    db_task.completion_date = datetime.utcnow()
    db.commit()
    return {"message": "Task marked as complete", "task": db_task.to_dict()}


@app.delete("/api/tasks/{task_id}")
def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Delete a task"""
    user_id = current_user["user_id"]  # ✅ ADD THIS
    db_task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id  # ✅ ENSURE USER OWNS THIS
    ).first()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    DatabaseManager.delete(db, db_task)
    return {"message": "Task deleted successfully"}


# ============================================
# BREAKS - ADD AUTHENTICATION
# ============================================
@app.get("/api/breaks", response_model=List[Dict])
def get_breaks(
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Get all breaks for current user"""
    user_id = current_user["user_id"]  # ✅ ADD THIS
    breaks = db.query(Break).filter(Break.user_id == user_id).all()  # ✅ FILTER
    return [b.to_dict() for b in breaks]


@app.post("/api/breaks", response_model=Dict)
def create_break(
    break_item: dict,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Create a new break"""
    try:
        db_break = Break(
            user_id=current_user["user_id"],  # ✅ ADD THIS
            name=break_item.get("name"),
            day=break_item.get("day"),
            start=break_item.get("start"),
            end=break_item.get("end"),
            color=break_item.get("color", "#FF9800")
        )
        return DatabaseManager.create(db, db_break).to_dict()
    except Exception as e:
        logger.error(f"Error creating break: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/breaks/{break_id}")
def delete_break(
    break_id: str,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Delete a break"""
    user_id = current_user["user_id"]  # ✅ ADD THIS
    db_break = db.query(Break).filter(
        Break.id == break_id,
        Break.user_id == user_id  # ✅ ENSURE USER OWNS THIS
    ).first()
    
    if not db_break:
        raise HTTPException(status_code=404, detail="Break not found")
    
    DatabaseManager.delete(db, db_break)
    return {"message": "Break deleted successfully"}


# ============================================
# JOBS - ADD AUTHENTICATION
# ============================================
@app.get("/api/jobs", response_model=List[Dict])
def get_jobs(
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Get all jobs for current user"""
    user_id = current_user["user_id"]  # ✅ ADD THIS
    jobs = db.query(Job).filter(Job.user_id == user_id).all()  # ✅ FILTER
    return [job.to_dict() for job in jobs]


@app.post("/api/jobs", response_model=Dict)
def create_job(
    job: dict,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Create a new job"""
    try:
        db_job = Job(
            user_id=current_user["user_id"],  # ✅ ADD THIS
            name=job.get("name"),
            days=job.get("days"),
            start=job.get("start"),
            end=job.get("end"),
            color=job.get("color", "#9C27B0")
        )
        return DatabaseManager.create(db, db_job).to_dict()
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/jobs/{job_id}")
def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Delete a job"""
    user_id = current_user["user_id"]  # ✅ ADD THIS
    db_job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user_id  # ✅ ENSURE USER OWNS THIS
    ).first()
    
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    DatabaseManager.delete(db, db_job)
    return {"message": "Job deleted successfully"}


# ============================================
# PREFERENCES - ADD AUTHENTICATION
# ============================================
@app.get("/api/preferences")
def get_preferences(
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    try:
        user_id = current_user["user_id"]  # ✅ USE REAL USER ID
        prefs = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if not prefs:
            # Return defaults
            return {
                "name": None,
                "timezone": "America/New_York",
                "wake": "08:00",
                "sleep": "23:00",
                "maxStudyHours": 6,
                "sessionLength": 60,
                "breakDuration": 15,
                "betweenClasses": 30,
                "afterSchool": 120,
                "urgencyMode": "balanced",
                "studyTime": "afternoon",
                "autoSplit": True,
                "prioritizeHard": True,
                "weekendStudy": True,
                "deadlineBuffer": 12,
                "lunchStart": "12:00",
                "lunchEnd": "13:00",
                "dinnerStart": "18:00",
                "dinnerEnd": "19:00",
                "autoMeals": True,
            }
        
        return prefs.to_dict()
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/preferences")
def save_preferences(
    prefs_data: dict,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Save or update user preferences"""
    try:
        user_id = current_user["user_id"]  # ✅ USE REAL USER ID
        
        # Check if preferences exist
        existing = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if existing:
            # Update existing
            for key, value in prefs_data.items():
                # Convert camelCase to snake_case
                snake_key = ''.join(['_'+c.lower() if c.isupper() else c for c in key]).lstrip('_')
                if hasattr(existing, snake_key):
                    setattr(existing, snake_key, value)
            
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing.to_dict()
        else:
            # Create new
            new_prefs = UserPreferences(
                user_id=user_id,  # ✅ USE REAL USER ID
                name=prefs_data.get("name"),
                timezone=prefs_data.get("timezone", "America/New_York"),
                wake=prefs_data.get("wake", "08:00"),
                sleep=prefs_data.get("sleep", "23:00"),
                max_study_hours=prefs_data.get("maxStudyHours", 6.0),
                session_length=prefs_data.get("sessionLength", 60),
                break_duration=prefs_data.get("breakDuration", 15),
                between_classes=prefs_data.get("betweenClasses", 30),
                after_school=prefs_data.get("afterSchool", 120),
                urgency_mode=prefs_data.get("urgencyMode", "balanced"),
                study_time=prefs_data.get("studyTime", "afternoon"),
                auto_split=prefs_data.get("autoSplit", True),
                prioritize_hard=prefs_data.get("prioritizeHard", True),
                weekend_study=prefs_data.get("weekendStudy", True),
                deadline_buffer=prefs_data.get("deadlineBuffer", 12),
                lunch_start=prefs_data.get("lunchStart", "12:00"),
                lunch_end=prefs_data.get("lunchEnd", "13:00"),
                dinner_start=prefs_data.get("dinnerStart", "18:00"),
                dinner_end=prefs_data.get("dinnerEnd", "19:00"),
                auto_meals=prefs_data.get("autoMeals", True),
            )
            
            db.add(new_prefs)
            db.commit()
            db.refresh(new_prefs)
            return new_prefs.to_dict()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SCHEDULE - ADD AUTHENTICATION
# ============================================
@app.post("/api/schedule/from-database")
def generate_schedule_from_db(
    force: bool = False,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Generate schedule - ONLY when explicitly requested"""
    user_id = current_user["user_id"]  # ✅ USE REAL USER ID
    
    existing_events = db.query(ScheduledEvent).filter(
        ScheduledEvent.user_id == user_id  # ✅ FILTER BY USER
    ).count()
    
    if existing_events > 0 and not force:
        events = db.query(ScheduledEvent).filter(
            ScheduledEvent.user_id == user_id  # ✅ FILTER BY USER
        ).all()
        return {
            "events": [e.to_dict() for e in events],
            "source": "database",
            "message": "Loaded existing schedule (no regeneration)"
        }

    try:
        # ✅ FILTER ALL QUERIES BY USER
        courses = db.query(Course).filter(Course.user_id == user_id).all()
        tasks = db.query(Task).filter(
            Task.user_id == user_id,
            Task.completed == False
        ).all()
        breaks = db.query(Break).filter(Break.user_id == user_id).all()
        jobs = db.query(Job).filter(Job.user_id == user_id).all()
        commutes = db.query(Commute).filter(Commute.user_id == user_id).all()
        
        prefs = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if prefs:
            preferences = prefs.to_dict()
        else:
            preferences = {
                "wake": "08:00",
                "sleep": "23:00",
                "timezone": "America/New_York",
                "maxStudyHours": 6,
                "sessionLength": 60,
                "breakDuration": 15,
                "betweenClasses": 30,
                "afterSchool": 120,
                "urgencyMode": "balanced",
                "studyTime": "afternoon",
                "autoSplit": True,
                "prioritizeHard": True,
                "weekendStudy": True,
                "deadlineBuffer": 12,
                "lunchStart": "12:00",
                "lunchEnd": "13:00",
                "dinnerStart": "18:00",
                "dinnerEnd": "19:00",
                "autoMeals": True,
            }
        
        logger.info(f"Generating NEW schedule from scratch for user {user_id}")
        
        if not tasks:
            return {
                "events": [],
                "summary": {
                    "total_tasks": 0,
                    "scheduled": 0,
                    "message": "No incomplete tasks to schedule"
                }
            }
        
        payload_dict = {
            "courses": [c.to_dict() for c in courses],
            "tasks": [t.to_dict() for t in tasks],
            "breaks": [b.to_dict() for b in breaks],
            "jobs": [j.to_dict() for j in jobs],
            "commutes": [c.to_dict() for c in commutes],
            "preferences": preferences
        }
        
        result = scheduler.generate_schedule(payload_dict)
        logger.info(f"Schedule generated: {len(result.get('events', []))} events")
        
        try:
            # ✅ DELETE ONLY USER'S EVENTS
            db.query(ScheduledEvent).filter(
                ScheduledEvent.user_id == user_id
            ).delete()
            
            saved_count = 0
            for event in result.get('events', []):
                if event.get('status') not in ['scheduled', 'incomplete', 'exam']:
                    continue
                
                date_str = event.get('date', '')
                start_str = event.get('start', '')
                end_str = event.get('end', '')
                
                scheduled_event = ScheduledEvent(
                    user_id=user_id,  # ✅ ADD THIS
                    task_id=event.get('task_id', 'generated'),
                    title=event.get('title', 'Study Session'),
                    date=date_str,
                    start=start_str,
                    end=end_str,
                    duration=event.get('duration', 0),
                    status=event.get('status', 'scheduled'),
                    difficulty=event.get('difficulty'),
                    color=event.get('color', '#4CAF50')
                )
                
                db.add(scheduled_event)
                saved_count += 1
            
            db.commit()
            logger.info(f"✓ Saved {saved_count} events to database")
            
        except Exception as save_error:
            logger.error(f"Error saving schedule: {save_error}")
            db.rollback()
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating schedule: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schedule")
def get_saved_schedule(
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Retrieve saved schedule"""
    try:
        user_id = current_user["user_id"]  # ✅ ADD THIS
        events = db.query(ScheduledEvent).filter(
            ScheduledEvent.user_id == user_id  # ✅ FILTER BY USER
        ).all()
        
        return {
            "schedule": [event.to_dict() for event in events]
        }
        
    except Exception as e:
        logger.error(f"Error retrieving schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/schedule/events/{event_id}")
def update_scheduled_event(
    event_id: str,
    event_data: dict,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Update a single scheduled event"""
    try:
        user_id = current_user["user_id"]  # ✅ ADD THIS
        event = db.query(ScheduledEvent).filter(
            ScheduledEvent.id == event_id,
            ScheduledEvent.user_id == user_id  # ✅ ENSURE USER OWNS THIS
        ).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        if "date" in event_data:
            event.date = event_data["date"]
        if "start" in event_data:
            event.start = event_data["start"]
        if "end" in event_data:
            event.end = event_data["end"]
        if "duration" in event_data:
            event.duration = event_data["duration"]
        if "title" in event_data:
            event.title = event_data["title"]
        
        event.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(event)
        
        logger.info(f"✓ Updated event {event_id}: {event.title} -> {event.date} {event.start}")
        
        return {
            "message": "Event updated successfully",
            "event": event.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_stats(
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Get database statistics"""
    try:
        user_id = current_user["user_id"]  # ✅ ADD THIS
        return {
            "courses": db.query(Course).filter(Course.user_id == user_id).count(),
            "tasks": {
                "total": db.query(Task).filter(Task.user_id == user_id).count(),
                "completed": db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.completed == True
                ).count(),
                "pending": db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.completed == False
                ).count()
            },
            "breaks": db.query(Break).filter(Break.user_id == user_id).count(),
            "jobs": db.query(Job).filter(Job.user_id == user_id).count(),
            "commutes": db.query(Commute).filter(Commute.user_id == user_id).count()
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/clear-all")
def clear_all_data(
    confirm: str = None,
    current_user: dict = Depends(get_current_user),  # ✅ ADD THIS
    db: Session = Depends(get_db)
):
    """Clear all data from database for current user"""
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="Must confirm with ?confirm=yes")
    
    try:
        user_id = current_user["user_id"]  # ✅ ADD THIS
        
        # ✅ DELETE ONLY USER'S DATA
        db.query(ScheduledEvent).filter(ScheduledEvent.user_id == user_id).delete()
        db.query(Task).filter(Task.user_id == user_id).delete()
        db.query(Course).filter(Course.user_id == user_id).delete()
        db.query(Break).filter(Break.user_id == user_id).delete()
        db.query(Job).filter(Job.user_id == user_id).delete()
        db.query(Commute).filter(Commute.user_id == user_id).delete()
        
        db.commit()
        
        logger.info(f"All data cleared for user {user_id}")
        
        return {"message": "All data cleared successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ============================================
# SCHEDULE GENERATION
# ============================================

@app.post("/api/schedule/from-database")
def generate_schedule_from_db(
    user_id: str = "default",
    force: bool = False,
    db: Session = Depends(get_db)
):
    """Generate schedule - ONLY when explicitly requested"""
    existing_events = db.query(ScheduledEvent).count()
    if existing_events > 0 and not force:
        events = db.query(ScheduledEvent).all()
        return {
            "events": [e.to_dict() for e in events],
            "source": "database",
            "message": "Loaded existing schedule (no regeneration)"
        }

    try:
        courses = db.query(Course).all()
        tasks = db.query(Task).filter(Task.completed == False).all()
        breaks = db.query(Break).all()
        jobs = db.query(Job).all()
        commutes = db.query(Commute).all()
        
        prefs = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if prefs:
            preferences = prefs.to_dict()
        else:
            preferences = {
                "wake": "08:00",
                "sleep": "23:00",
                "timezone": "America/New_York",
                "maxStudyHours": 6,
                "sessionLength": 60,
                "breakDuration": 15,
                "betweenClasses": 30,
                "afterSchool": 120,
                "urgencyMode": "balanced",
                "studyTime": "afternoon",
                "autoSplit": True,
                "prioritizeHard": True,
                "weekendStudy": True,
                "deadlineBuffer": 12,
                "lunchStart": "12:00",
                "lunchEnd": "13:00",
                "dinnerStart": "18:00",
                "dinnerEnd": "19:00",
                "autoMeals": True,
            }
        
        logger.info(f"Generating NEW schedule from scratch")
        
        if not tasks:
            return {
                "events": [],
                "summary": {
                    "total_tasks": 0,
                    "scheduled": 0,
                    "message": "No incomplete tasks to schedule"
                }
            }
        
        payload_dict = {
            "courses": [c.to_dict() for c in courses],
            "tasks": [t.to_dict() for t in tasks],
            "breaks": [b.to_dict() for b in breaks],
            "jobs": [j.to_dict() for j in jobs],
            "commutes": [c.to_dict() for c in commutes],
            "preferences": preferences
        }
        
        result = scheduler.generate_schedule(payload_dict)
        logger.info(f"Schedule generated: {len(result.get('events', []))} events")
        
        try:
            db.query(ScheduledEvent).delete()
            
            saved_count = 0
            for event in result.get('events', []):
                if event.get('status') not in ['scheduled', 'incomplete', 'exam']:
                    continue
                
                date_str = event.get('date', '')
                start_str = event.get('start', '')
                end_str = event.get('end', '')
                
                scheduled_event = ScheduledEvent(
                    task_id=event.get('task_id', 'generated'),
                    title=event.get('title', 'Study Session'),
                    date=date_str,
                    start=start_str,
                    end=end_str,
                    duration=event.get('duration', 0),
                    status=event.get('status', 'scheduled'),
                    difficulty=event.get('difficulty'),
                    color=event.get('color', '#4CAF50')
                )
                
                db.add(scheduled_event)
                saved_count += 1
            
            db.commit()
            logger.info(f"✓ Saved {saved_count} events to database")
            
        except Exception as save_error:
            logger.error(f"Error saving schedule: {save_error}")
            db.rollback()
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating schedule: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/schedule/events/{event_id}")
def update_scheduled_event(event_id: str, event_data: dict, db: Session = Depends(get_db)):
    """Update a single scheduled event"""
    try:
        event = db.query(ScheduledEvent).filter(ScheduledEvent.id == event_id).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        if "date" in event_data:
            event.date = event_data["date"]
        if "start" in event_data:
            event.start = event_data["start"]
        if "end" in event_data:
            event.end = event_data["end"]
        if "duration" in event_data:
            event.duration = event_data["duration"]
        if "title" in event_data:
            event.title = event_data["title"]
        
        event.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(event)
        
        logger.info(f"✓ Updated event {event_id}: {event.title} -> {event.date} {event.start}")
        
        return {
            "message": "Event updated successfully",
            "event": event.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get database statistics"""
    try:
        return {
            "courses": db.query(Course).count(),
            "tasks": {
                "total": db.query(Task).count(),
                "completed": db.query(Task).filter(Task.completed == True).count(),
                "pending": db.query(Task).filter(Task.completed == False).count()
            },
            "breaks": db.query(Break).count(),
            "jobs": db.query(Job).count(),
            "commutes": db.query(Commute).count()
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check"""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "service": "StudyTime API",
        "version": "3.0.0",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/schedule")
def get_saved_schedule(db: Session = Depends(get_db)):
    """Retrieve saved schedule"""
    try:
        events = db.query(ScheduledEvent).all()
        
        return {
            "schedule": [event.to_dict() for event in events]
        }
        
    except Exception as e:
        logger.error(f"Error retrieving schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-pdf")
async def generate_pdf(schedule_data: dict):
    """Generate PDF from schedule data"""
    try:
        from pdfgeneration import PDFScheduleGenerator
        
        generator = PDFScheduleGenerator()
        pdf_buffer = generator.generate(schedule_data)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=StudyTime_Schedule_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/clear-all")
def clear_all_data(confirm: str = None, db: Session = Depends(get_db)):
    """Clear all data from database"""
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="Must confirm with ?confirm=yes")
    
    try:
        db.query(ScheduledEvent).delete()
        db.query(Task).delete()
        db.query(Course).delete()
        db.query(Break).delete()
        db.query(Job).delete()
        db.query(Commute).delete()
        
        db.commit()
        
        logger.info("All data cleared from database")
        
        return {"message": "All data cleared successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Static Files
if frontend_dir.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
        logger.info(f"Frontend mounted from: {frontend_dir}")
    except Exception as e:
        logger.warning(f"Could not mount frontend: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("StudyTime API starting...")
    
    if init_db():
        logger.info("✓ Database initialized")
    else:
        logger.error("✗ Database initialization failed")
    
    if check_db_connection():
        logger.info("✓ Database connected")
    else:
        logger.error("✗ Database connection failed")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("StudyTime API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )