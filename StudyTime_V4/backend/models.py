from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, Float
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    """Generate a unique UUID string"""
    return str(uuid.uuid4())


class Course(Base):
    """Represents a recurring course/class"""
    __tablename__ = "courses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    days = Column(JSON, nullable=False)
    start = Column(String, nullable=False)
    end = Column(String, nullable=False)
    color = Column(String, default="#1565c0")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
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
    """Represents an assignment or task to be scheduled"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    due = Column(String, nullable=False)
    difficulty = Column(String, default="Medium")
    is_exam = Column(Boolean, default=False)
    color = Column(String, default="#4CAF50")
    
    completed = Column(Boolean, default=False)
    completion_date = Column(DateTime, nullable=True)
    
    course_id = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
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
    """Represents recurring breaks, lunch, or blocked time"""
    __tablename__ = "breaks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    day = Column(String, nullable=False)
    start = Column(String, nullable=False)
    end = Column(String, nullable=False)
    color = Column(String, default="#FF9800")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
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
    """Represents work/job schedule"""
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    days = Column(JSON, nullable=False)
    start = Column(String, nullable=False)
    end = Column(String, nullable=False)
    color = Column(String, default="#9C27B0")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
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
    """Represents commute times"""
    __tablename__ = "commutes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    days = Column(JSON, nullable=False)
    start = Column(String, nullable=False)
    end = Column(String, nullable=False)
    color = Column(String, default="#607D8B")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
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
    """Stores comprehensive user preferences for scheduling"""
    __tablename__ = "user_preferences"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, unique=True, default="default")
    
    # Personal info
    name = Column(String, nullable=True)
    timezone = Column(String, default="America/New_York")
    
    # Daily schedule
    wake = Column(String, default="08:00")
    sleep = Column(String, default="23:00")
    
    # Study preferences
    max_study_hours = Column(Float, default=6.0)
    session_length = Column(Integer, default=60)
    break_duration = Column(Integer, default=15)
    between_classes = Column(Integer, default=30)
    after_school = Column(Integer, default=120)
    
    # Scheduling style
    urgency_mode = Column(String, default="balanced")  # relaxed, balanced, urgent
    study_time = Column(String, default="afternoon")  # morning, afternoon, evening, any
    
    # Advanced settings
    auto_split = Column(Boolean, default=True)
    prioritize_hard = Column(Boolean, default=True)
    weekend_study = Column(Boolean, default=True)
    deadline_buffer = Column(Integer, default=12)
    
    # Meal times
    lunch_start = Column(String, default="12:00")
    lunch_end = Column(String, default="13:00")
    dinner_start = Column(String, default="18:00")
    dinner_end = Column(String, default="19:00")
    auto_meals = Column(Boolean, default=True)
    
    # Notifications
    notifications_enabled = Column(Boolean, default=True)
    reminder_minutes_before = Column(Integer, default=30)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "timezone": self.timezone,
            "wake": self.wake,
            "sleep": self.sleep,
            "maxStudyHours": self.max_study_hours,
            "sessionLength": self.session_length,
            "breakDuration": self.break_duration,
            "betweenClasses": self.between_classes,
            "afterSchool": self.after_school,
            "urgencyMode": self.urgency_mode,
            "studyTime": self.study_time,
            "autoSplit": self.auto_split,
            "prioritizeHard": self.prioritize_hard,
            "weekendStudy": self.weekend_study,
            "deadlineBuffer": self.deadline_buffer,
            "lunchStart": self.lunch_start,
            "lunchEnd": self.lunch_end,
            "dinnerStart": self.dinner_start,
            "dinnerEnd": self.dinner_end,
            "autoMeals": self.auto_meals,
            "notifications_enabled": self.notifications_enabled,
            "reminder_minutes_before": self.reminder_minutes_before,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ScheduledEvent(Base):
    """Stores generated schedule events (study sessions)"""
    __tablename__ = "scheduled_events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    task_id = Column(String, nullable=False)
    
    title = Column(String, nullable=False)
    date = Column(String, nullable=False)
    start = Column(String, nullable=False)
    end = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    
    status = Column(String, default="scheduled")
    difficulty = Column(String, nullable=True)
    color = Column(String, default="#4CAF50")
    
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
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