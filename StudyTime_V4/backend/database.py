from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import logging
from pathlib import Path

# Import your models
from models import Base

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "sqlite:///studytime.db"

# Ensure database directory exists
db_path = Path("studytime.db")
db_path.parent.mkdir(parents=True, exist_ok=True)

# Create engine with proper SQLite settings
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Allow multiple threads (for FastAPI)
        "timeout": 30  # Connection timeout in seconds
    },
    poolclass=StaticPool,  # Better for SQLite with FastAPI
    echo=False,  # Set to True for SQL query logging (useful for debugging)
    future=True  # Use SQLAlchemy 2.0 style
)


# Enable foreign key support for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints and other pragmas for SQLite"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
    cursor.close()


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent detached instance errors
)


def init_db():
    """
    Initialize the database by creating all tables.
    Call this once when the application starts.
    """
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return False


def drop_all_tables():
    """
    Drop all tables. USE WITH CAUTION - This deletes all data!
    Only use for testing or resetting the database.
    """
    try:
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully!")
        return True
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        return False


def reset_db():
    """
    Reset the database by dropping and recreating all tables.
    USE WITH CAUTION - This deletes all data!
    """
    logger.warning("Resetting database...")
    drop_all_tables()
    init_db()
    logger.info("Database reset complete!")


# Dependency for FastAPI
def get_db():
    """
    FastAPI dependency that provides a database session.
    
    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
            print(user.name)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


class DatabaseManager:
    """
    Helper class for common database operations
    """
    
    @staticmethod
    def create(db: Session, model_instance):
        """Create a new record"""
        try:
            db.add(model_instance)
            db.commit()
            db.refresh(model_instance)
            return model_instance
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating record: {e}")
            raise
    
    @staticmethod
    def get_by_id(db: Session, model, record_id: str):
        """Get a record by ID"""
        return db.query(model).filter(model.id == record_id).first()
    
    @staticmethod
    def get_all(db: Session, model, skip: int = 0, limit: int = 100):
        """Get all records with pagination"""
        return db.query(model).offset(skip).limit(limit).all()
    
    @staticmethod
    def update(db: Session, model_instance, **kwargs):
        """Update a record"""
        try:
            for key, value in kwargs.items():
                if hasattr(model_instance, key):
                    setattr(model_instance, key, value)
            db.commit()
            db.refresh(model_instance)
            return model_instance
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating record: {e}")
            raise
    
    @staticmethod
    def delete(db: Session, model_instance):
        """Delete a record"""
        try:
            db.delete(model_instance)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting record: {e}")
            raise
    
    @staticmethod
    def bulk_create(db: Session, model_instances: list):
        """Create multiple records at once"""
        try:
            db.add_all(model_instances)
            db.commit()
            return model_instances
        except Exception as e:
            db.rollback()
            logger.error(f"Error bulk creating records: {e}")
            raise


# Database utility functions for common queries
def get_active_tasks(db: Session):
    """Get all incomplete tasks"""
    from models import Task
    return db.query(Task).filter(Task.completed == False).all()


def get_courses_by_day(db: Session, day: str):
    """Get all courses for a specific day"""
    from models import Course
    from sqlalchemy import func
    return db.query(Course).filter(
        func.json_extract(Course.days, '$') != None
    ).all()  # Note: You'll need to filter in Python due to JSON array


def mark_task_complete(db: Session, task_id: str):
    """Mark a task as completed"""
    from models import Task
    from datetime import datetime
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.completed = True
        task.completion_date = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return task
    return None


def get_upcoming_tasks(db: Session, limit: int = 10):
    """Get upcoming tasks sorted by due date"""
    from models import Task
    return db.query(Task).filter(
        Task.completed == False
    ).order_by(Task.due).limit(limit).all()


# Health check function
def check_db_connection():
    """
    Check if database connection is working.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_context() as db:
            # Try a simple query
            db.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


# Export commonly used items
__all__ = [
    'engine',
    'SessionLocal',
    'get_db',
    'get_db_context',
    'init_db',
    'reset_db',
    'drop_all_tables',
    'DatabaseManager',
    'check_db_connection',
    'get_active_tasks',
    'mark_task_complete',
    'get_upcoming_tasks'
]


if __name__ == "__main__":
    """
    Run this file directly to initialize the database:
    python database.py
    """
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            init_db()
        elif command == "reset":
            confirm = input("This will delete all data. Are you sure? (yes/no): ")
            if confirm.lower() == "yes":
                reset_db()
            else:
                print("Reset cancelled.")
        elif command == "check":
            if check_db_connection():
                print("✓ Database connection successful!")
            else:
                print("✗ Database connection failed!")
        else:
            print(f"Unknown command: {command}")
            print("Available commands: init, reset, check")
    else:
        # Default action: initialize database
        print("Initializing database...")
        init_db()
        if check_db_connection():
            print("✓ Database initialized and connection verified!")
        else:
            print("✗ Database initialized but connection check failed!")