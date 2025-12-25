from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text
from datetime import datetime
import uuid

Base = declarative_base()


def generate_uuid():
    """Generate a unique UUID string"""
    return str(uuid.uuid4())


class Course(Base):
    """
    Represents a recurring course/class
    """
    __tablename__ = "courses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # Changed from 'code' to 'name' to match algorithm
    days = Column(JSON, nullable=False)  # Store as JSON array: ["Monday", "Wednesday", "Friday"]
    start = Column(String, nullable=False)  # HH:MM format (e.g., "09:00")
    end = Column(String, nullable=False)  # HH:MM format (e.g., "10:30")
    color = Column(String, default="#1565c0")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "days": self.days,
            "start": self.start,
            "end": self.end,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Task(Base):
    """
    Represents an assignment or task to be scheduled
    """
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)  # Total duration in minutes
    due = Column(String, nullable=False)  # ISO format: "2025-12-21T23:59:00"
    difficulty = Column(String, default="Medium")  # Easy, Medium, Hard
    is_exam = Column(Boolean, default=False)  # If true, don't schedule study time
    color = Column(String, default="#4CAF50")
    
    # Status tracking
    completed = Column(Boolean, default=False)
    completion_date = Column(DateTime, nullable=True)
    
    # Optional course association
    course_id = Column(String, nullable=True)
    
    # Notes/description
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "duration": self.duration,
            "due": self.due,
            "difficulty": self.difficulty,
            "is_exam": self.is_exam,
            "color": self.color,
            "completed": self.completed,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "course_id": self.course_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Break(Base):
    """
    Represents recurring breaks, lunch, or blocked time
    """
    __tablename__ = "breaks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # "Lunch", "Gym", etc.
    day = Column(String, nullable=False)  # "Monday", "Tuesday", etc.
    start = Column(String, nullable=False)  # HH:MM format
    end = Column(String, nullable=False)  # HH:MM format
    color = Column(String, default="#FF9800")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "day": self.day,
            "start": self.start,
            "end": self.end,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Job(Base):
    """
    Represents work/job schedule
    """
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # Job/work name
    days = Column(JSON, nullable=False)  # Store as JSON array: ["Monday", "Tuesday"]
    start = Column(String, nullable=False)  # HH:MM format
    end = Column(String, nullable=False)  # HH:MM format
    color = Column(String, default="#9C27B0")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "days": self.days,
            "start": self.start,
            "end": self.end,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Commute(Base):
    """
    Represents commute times
    """
    __tablename__ = "commutes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # "Morning Commute", "To Work", etc.
    days = Column(JSON, nullable=False)  # Store as JSON array
    start = Column(String, nullable=False)  # HH:MM format
    end = Column(String, nullable=False)  # HH:MM format
    color = Column(String, default="#607D8B")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "days": self.days,
            "start": self.start,
            "end": self.end,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UserPreferences(Base):
    """
    Stores user preferences for scheduling
    """
    __tablename__ = "user_preferences"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, unique=True)  # For multi-user support
    
    # Wake/sleep times
    wake = Column(String, default="08:00")  # HH:MM format
    sleep = Column(String, default="23:00")  # HH:MM format
    
    # Study preferences
    preferred_study_time = Column(String, nullable=True)  # "morning", "afternoon", "evening"
    max_daily_study_hours = Column(Integer, default=8)
    min_break_between_sessions = Column(Integer, default=15)  # minutes
    
    # Notifications
    notifications_enabled = Column(Boolean, default=True)
    reminder_minutes_before = Column(Integer, default=30)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "wake": self.wake,
            "sleep": self.sleep,
            "preferred_study_time": self.preferred_study_time,
            "max_daily_study_hours": self.max_daily_study_hours,
            "min_break_between_sessions": self.min_break_between_sessions,
            "notifications_enabled": self.notifications_enabled,
            "reminder_minutes_before": self.reminder_minutes_before,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ScheduledEvent(Base):
    """
    Stores generated schedule events (study sessions)
    """
    __tablename__ = "scheduled_events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    task_id = Column(String, nullable=False)  # Reference to Task
    
    # Event details
    title = Column(String, nullable=False)
    date = Column(String, nullable=False)  # MM/DD/YYYY format
    start = Column(String, nullable=False)  # HH:MM format
    end = Column(String, nullable=False)  # HH:MM format
    duration = Column(Integer, nullable=False)  # minutes
    
    # Status
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled, incomplete, overdue
    difficulty = Column(String, nullable=True)
    color = Column(String, default="#4CAF50")
    
    # Completion tracking
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "date": self.date,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "status": self.status,
            "difficulty": self.difficulty,
            "color": self.color,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }