from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import logging
from pathlib import Path
import sys
from sqlalchemy import text 

# Import your models
from models import Base

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
        "check_same_thread": False,
        "timeout": 30
    },
    poolclass=StaticPool,
    echo=False,  # Set to True for debugging
    future=True
)


# Enable foreign key support for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints and WAL mode for SQLite"""
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    except Exception as e:
        logger.error(f"Error setting SQLite pragmas: {e}")
        cursor.close()


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def init_db():
    """
    Initialize the database by creating all tables.
    Safe to call multiple times.
    """
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Error creating database tables: {e}", exc_info=True)
        return False


def drop_all_tables():
    """
    Drop all tables. USE WITH CAUTION - This deletes all data!
    """
    try:
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("✓ All tables dropped")
        return True
    except Exception as e:
        logger.error(f"✗ Error dropping tables: {e}", exc_info=True)
        return False


def reset_db():
    """
    Reset the database by dropping and recreating all tables.
    USE WITH CAUTION - This deletes all data!
    """
    logger.warning("Resetting database...")
    if drop_all_tables():
        if init_db():
            logger.info("✓ Database reset complete")
            return True
    logger.error("✗ Database reset failed")
    return False


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
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database context error: {e}", exc_info=True)
        raise
    finally:
        db.close()


class DatabaseManager:
    """
    Helper class for common database operations with error handling
    """
    
    @staticmethod
    def create(db: Session, model_instance):
        """Create a new record"""
        try:
            db.add(model_instance)
            db.commit()
            db.refresh(model_instance)
            logger.debug(f"Created {type(model_instance).__name__}: {model_instance.id}")
            return model_instance
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating record: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_by_id(db: Session, model, record_id: str):
        """Get a record by ID"""
        try:
            return db.query(model).filter(model.id == record_id).first()
        except Exception as e:
            logger.error(f"Error getting record by ID: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_all(db: Session, model, skip: int = 0, limit: int = 100):
        """Get all records with pagination"""
        try:
            return db.query(model).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting all records: {e}", exc_info=True)
            raise
    
    @staticmethod
    def update(db: Session, model_instance, **kwargs):
        """Update a record"""
        try:
            for key, value in kwargs.items():
                if hasattr(model_instance, key):
                    setattr(model_instance, key, value)
            db.commit()
            db.refresh(model_instance)
            logger.debug(f"Updated {type(model_instance).__name__}: {model_instance.id}")
            return model_instance
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating record: {e}", exc_info=True)
            raise
    
    @staticmethod
    def delete(db: Session, model_instance):
        """Delete a record"""
        try:
            record_type = type(model_instance).__name__
            record_id = model_instance.id
            db.delete(model_instance)
            db.commit()
            logger.debug(f"Deleted {record_type}: {record_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting record: {e}", exc_info=True)
            raise
    
    @staticmethod
    def bulk_create(db: Session, model_instances: list):
        """Create multiple records at once"""
        try:
            db.add_all(model_instances)
            db.commit()
            logger.debug(f"Bulk created {len(model_instances)} records")
            return model_instances
        except Exception as e:
            db.rollback()
            logger.error(f"Error bulk creating records: {e}", exc_info=True)
            raise


# Utility functions
def get_active_tasks(db: Session):
    """Get all incomplete tasks"""
    from models import Task
    try:
        return db.query(Task).filter(Task.completed == False).all()
    except Exception as e:
        logger.error(f"Error getting active tasks: {e}")
        return []


def mark_task_complete(db: Session, task_id: str):
    """Mark a task as completed"""
    from models import Task
    from datetime import datetime
    
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.completed = True
            task.completion_date = datetime.utcnow()
            db.commit()
            db.refresh(task)
            logger.info(f"Task completed: {task.name}")
            return task
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking task complete: {e}")
        raise


def get_upcoming_tasks(db: Session, limit: int = 10):
    """Get upcoming tasks sorted by due date"""
    from models import Task
    try:
        return db.query(Task).filter(
            Task.completed == False
        ).order_by(Task.due).limit(limit).all()
    except Exception as e:
        logger.error(f"Error getting upcoming tasks: {e}")
        return []


def check_db_connection():
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_db_info():
    """Get database information"""
    from models import Course, Task, Break, Job, Commute
    
    try:
        with get_db_context() as db:
            return {
                "database_url": DATABASE_URL,
                "connected": True,
                "tables": {
                    "courses": db.query(Course).count(),
                    "tasks": db.query(Task).count(),
                    "breaks": db.query(Break).count(),
                    "jobs": db.query(Job).count(),
                    "commutes": db.query(Commute).count()
                }
            }
    except Exception as e:
        logger.error(f"Error getting DB info: {e}")
        return {
            "database_url": DATABASE_URL,
            "connected": False,
            "error": str(e)
        }


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
    'get_upcoming_tasks',
    'get_db_info'
]


if __name__ == "__main__":
    """
    Run this file directly to manage the database:
    python database.py [command]
    
    Commands:
        init    - Initialize database
        reset   - Reset database (deletes all data)
        check   - Check database connection
        info    - Show database information
    """
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            print("Initializing database...")
            if init_db():
                print("✓ Database initialized successfully")
            else:
                print("✗ Database initialization failed")
                
        elif command == "reset":
            confirm = input("⚠️  This will delete ALL data. Are you sure? (yes/no): ")
            if confirm.lower() == "yes":
                if reset_db():
                    print("✓ Database reset complete")
                else:
                    print("✗ Database reset failed")
            else:
                print("Reset cancelled")
                
        elif command == "check":
            print("Checking database connection...")
            if check_db_connection():
                print("✓ Database connection successful")
            else:
                print("✗ Database connection failed")
                
        elif command == "info":
            print("Database Information:")
            info = get_db_info()
            for key, value in info.items():
                print(f"  {key}: {value}")
                
        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  init   - Initialize database")
            print("  reset  - Reset database (deletes all data)")
            print("  check  - Check database connection")
            print("  info   - Show database information")
    else:
        # Default action: initialize and check
        print("StudyTime Database Manager")
        print("=" * 50)
        if init_db():
            if check_db_connection():
                print("✓ Database ready!")
                info = get_db_info()
                print("\nDatabase Info:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
            else:
                print("✗ Database initialized but connection failed")
        else:
            print("✗ Database initialization failed")