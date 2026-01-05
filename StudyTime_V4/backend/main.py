from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import logging
from pathlib import Path
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

# Import database and models
from database import get_db, init_db, check_db_connection, DatabaseManager
from models import Course, Task, Break, Job, Commute, UserPreferences

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
# PAGE ROUTES
# ============================================

@app.get("/")
def home_page(request: Request):
    """Main schedule input page"""
    return FileResponse(str(frontend_dir / "index.html"))


@app.get("/dashboard")
def dashboard_page(request: Request):
    """Dashboard overview page"""
    return FileResponse(str(frontend_dir / "dashboard.html"))


@app.get("/calendar")
def calendar_page(request: Request):
    """Calendar view page"""
    return FileResponse(str(frontend_dir / "calendar.html"))


@app.get("/login")
def login_page(request: Request):
    """Login page"""
    return FileResponse(str(frontend_dir / "login.html"))


@app.get("/preferences")
def preferences_page(request: Request):
    """User preferences page"""
    return FileResponse(str(frontend_dir / "preferences.html"))


# ============================================
# USER PREFERENCES ENDPOINTS
# ============================================

@app.get("/api/preferences")
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
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# EXISTING ENDPOINTS (keeping your code)
# ============================================

# COURSES
@app.get("/api/courses", response_model=List[Dict])
def get_courses(db: Session = Depends(get_db)):
    """Get all courses"""
    courses = db.query(Course).all()
    return [course.to_dict() for course in courses]


@app.post("/api/courses", response_model=Dict)
def create_course(course: dict, db: Session = Depends(get_db)):
    """Create a new course"""
    try:
        db_course = Course(
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
def delete_course(course_id: str, db: Session = Depends(get_db)):
    """Delete a course"""
    db_course = DatabaseManager.get_by_id(db, Course, course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    DatabaseManager.delete(db, db_course)
    return {"message": "Course deleted successfully"}


# TASKS
@app.get("/api/tasks", response_model=List[Dict])
def get_tasks(completed: Optional[bool] = None, db: Session = Depends(get_db)):
    """Get all tasks, optionally filtered by completion status"""
    query = db.query(Task)
    if completed is not None:
        query = query.filter(Task.completed == completed)
    tasks = query.all()
    return [task.to_dict() for task in tasks]


@app.post("/api/tasks", response_model=Dict)
def create_task(task: dict, db: Session = Depends(get_db)):
    """Create a new task"""
    try:
        db_task = Task(
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
def mark_task_complete(task_id: str, db: Session = Depends(get_db)):
    """Mark a task as completed"""
    db_task = DatabaseManager.get_by_id(db, Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db_task.completed = True
    db_task.completion_date = datetime.utcnow()
    db.commit()
    return {"message": "Task marked as complete", "task": db_task.to_dict()}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """Delete a task"""
    db_task = DatabaseManager.get_by_id(db, Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    DatabaseManager.delete(db, db_task)
    return {"message": "Task deleted successfully"}


# BREAKS
@app.get("/api/breaks", response_model=List[Dict])
def get_breaks(db: Session = Depends(get_db)):
    """Get all breaks"""
    breaks = db.query(Break).all()
    return [b.to_dict() for b in breaks]


@app.post("/api/breaks", response_model=Dict)
def create_break(break_item: dict, db: Session = Depends(get_db)):
    """Create a new break"""
    try:
        db_break = Break(
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
def delete_break(break_id: str, db: Session = Depends(get_db)):
    """Delete a break"""
    db_break = DatabaseManager.get_by_id(db, Break, break_id)
    if not db_break:
        raise HTTPException(status_code=404, detail="Break not found")
    
    DatabaseManager.delete(db, db_break)
    return {"message": "Break deleted successfully"}


# JOBS
@app.get("/api/jobs", response_model=List[Dict])
def get_jobs(db: Session = Depends(get_db)):
    """Get all jobs"""
    jobs = db.query(Job).all()
    return [job.to_dict() for job in jobs]


@app.post("/api/jobs", response_model=Dict)
def create_job(job: dict, db: Session = Depends(get_db)):
    """Create a new job"""
    try:
        db_job = Job(
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
def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a job"""
    db_job = DatabaseManager.get_by_id(db, Job, job_id)
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    DatabaseManager.delete(db, db_job)
    return {"message": "Job deleted successfully"}


# ============================================
# SCHEDULE GENERATION WITH PREFERENCES
# ============================================

@app.post("/api/schedule/from-database")
def generate_schedule_from_db(user_id: str = "default", db: Session = Depends(get_db)):
    """Generate schedule using data from database with user preferences"""
    try:
        # Load user data
        courses = db.query(Course).all()
        tasks = db.query(Task).filter(Task.completed == False).all()
        breaks = db.query(Break).all()
        jobs = db.query(Job).all()
        commutes = db.query(Commute).all()
        
        # Load user preferences
        prefs = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if prefs:
            preferences = prefs.to_dict()
        else:
            # Use defaults
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
        
        logger.info(f"Generating schedule from DB with preferences: {preferences.get('urgencyMode')}")
        
        if not tasks:
            return {
                "events": [],
                "summary": {
                    "total_tasks": 0,
                    "scheduled": 0,
                    "message": "No incomplete tasks in database"
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
        logger.info(f"Schedule generated from DB: {len(result.get('events', []))} events")
        return result
        
    except Exception as e:
        logger.error(f"Error generating schedule from DB: {str(e)}", exc_info=True)
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

# ============================================
# SAVE SCHEDULE ENDPOINT
# ============================================

@app.post("/api/schedule/save")
def save_schedule(schedule_data: dict, db: Session = Depends(get_db)):
    """Save generated schedule sessions to database"""
    try:
        from models import ScheduledEvent
        
        sessions = schedule_data.get("sessions", [])
        
        if not sessions:
            raise HTTPException(status_code=400, detail="No sessions to save")
        
        # Clear existing scheduled events
        db.query(ScheduledEvent).delete()
        
        # Save new sessions
        saved_count = 0
        for session in sessions:
            # Parse datetime
            start_dt = session.get("start")
            if isinstance(start_dt, str):
                start_dt = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
            
            end_dt = session.get("end")
            if isinstance(end_dt, str):
                end_dt = datetime.fromisoformat(end_dt.replace('Z', '+00:00'))
            
            # Calculate duration
            duration = int((end_dt - start_dt).total_seconds() / 60) if start_dt and end_dt else 0
            
            event = ScheduledEvent(
                task_id="generated",  # You can enhance this to link to actual tasks
                title=session.get("title", "Study Session"),
                date=start_dt.strftime("%m/%d/%Y") if start_dt else "",
                start=start_dt.strftime("%H:%M") if start_dt else "",
                end=end_dt.strftime("%H:%M") if end_dt else "",
                duration=duration,
                status="scheduled",
                color=session.get("color", "#4CAF50")
            )
            
            db.add(event)
            saved_count += 1
        
        db.commit()
        
        logger.info(f"Saved {saved_count} scheduled events")
        
        return {
            "message": "Schedule saved successfully",
            "sessions_saved": saved_count
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# GET SAVED SCHEDULE ENDPOINT
# ============================================

@app.get("/api/schedule")
def get_saved_schedule(db: Session = Depends(get_db)):
    """Retrieve saved schedule"""
    try:
        from models import ScheduledEvent
        
        events = db.query(ScheduledEvent).all()
        
        return {
            "schedule": [event.to_dict() for event in events]
        }
        
    except Exception as e:
        logger.error(f"Error retrieving schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PDF GENERATION ENDPOINT
# ============================================

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


# ============================================
# CLEAR ALL DATA ENDPOINT
# ============================================

@app.delete("/api/clear-all")
def clear_all_data(confirm: str = None, db: Session = Depends(get_db)):
    """Clear all data from database"""
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="Must confirm with ?confirm=yes")
    
    try:
        from models import Course, Task, Break, Job, Commute, ScheduledEvent
        
        # Delete all records
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
# ============================================
# Static Files
# ============================================

if frontend_dir.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
        logger.info(f"Frontend mounted from: {frontend_dir}")
    except Exception as e:
        logger.warning(f"Could not mount frontend: {e}")


# ============================================
# Startup/Shutdown
# ============================================

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