from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import logging
from pathlib import Path

# Import database and models
from database import get_db, init_db, check_db_connection, DatabaseManager
from models import Course, Task, Break, Job, Commute, UserPreferences

# Import scheduler
import scheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="StudyTime API",
    description="Smart study scheduling API with database persistence",
    version="2.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Pydantic Models for Request Validation
# ============================================

class CourseModel(BaseModel):
    name: str = Field(..., description="Course name or code")
    days: List[str] = Field(..., description="Days of the week")
    start: str = Field(..., description="Start time in HH:MM format")
    end: str = Field(..., description="End time in HH:MM format")
    color: Optional[str] = Field(default="#1565c0", description="Color hex code")
    
    @validator('days')
    def validate_days(cls, v):
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in v:
            if day not in valid_days:
                raise ValueError(f"Invalid day: {day}")
        return v
    
    @validator('start', 'end')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid time format: {v}. Must be HH:MM")
        return v


class TaskModel(BaseModel):
    name: str = Field(..., description="Task name")
    duration: int = Field(..., gt=0, description="Duration in minutes")
    due: str = Field(..., description="Due date in ISO format")
    difficulty: str = Field(default="Medium", description="Easy, Medium, or Hard")
    is_exam: bool = Field(default=False, description="Whether this is an in-class exam")
    color: Optional[str] = Field(default="#4CAF50", description="Color for calendar")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    
    @validator('difficulty')
    def validate_difficulty(cls, v):
        valid = ["Easy", "Medium", "Hard"]
        if v not in valid:
            raise ValueError(f"Invalid difficulty: {v}. Must be one of {valid}")
        return v
    
    @validator('due')
    def validate_due_date(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', ''))
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Must be ISO format")
        return v


class BreakModel(BaseModel):
    name: str = Field(..., description="Break name")
    day: str = Field(..., description="Day of the week")
    start: str = Field(..., description="Start time in HH:MM format")
    end: str = Field(..., description="End time in HH:MM format")
    color: Optional[str] = Field(default="#FF9800", description="Color hex code")
    
    @validator('day')
    def validate_day(cls, v):
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if v not in valid_days:
            raise ValueError(f"Invalid day: {v}")
        return v
    
    @validator('start', 'end')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid time format: {v}. Must be HH:MM")
        return v


class JobModel(BaseModel):
    name: str = Field(..., description="Job/work name")
    days: List[str] = Field(..., description="Days of the week")
    start: str = Field(..., description="Start time in HH:MM format")
    end: str = Field(..., description="End time in HH:MM format")
    color: Optional[str] = Field(default="#9C27B0", description="Color hex code")
    
    @validator('days')
    def validate_days(cls, v):
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in v:
            if day not in valid_days:
                raise ValueError(f"Invalid day: {day}")
        return v
    
    @validator('start', 'end')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid time format: {v}. Must be HH:MM")
        return v


class CommuteModel(BaseModel):
    name: str = Field(..., description="Commute description")
    days: List[str] = Field(..., description="Days of the week")
    start: str = Field(..., description="Start time in HH:MM format")
    end: str = Field(..., description="End time in HH:MM format")
    color: Optional[str] = Field(default="#607D8B", description="Color hex code")


class PreferencesModel(BaseModel):
    wake: str = Field(default="08:00", description="Wake time in HH:MM format")
    sleep: str = Field(default="23:00", description="Sleep time in HH:MM format")
    
    @validator('wake', 'sleep')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid time format: {v}. Must be HH:MM")
        return v


class SchedulePayload(BaseModel):
    courses: List[CourseModel] = Field(default=[], description="List of courses")
    tasks: List[TaskModel] = Field(default=[], description="List of tasks")
    breaks: List[BreakModel] = Field(default=[], description="List of breaks")
    jobs: List[JobModel] = Field(default=[], description="List of jobs")
    commutes: List[CommuteModel] = Field(default=[], description="List of commutes")
    preferences: PreferencesModel = Field(default_factory=PreferencesModel)


# ============================================
# Database CRUD Endpoints
# ============================================

# COURSES
@app.get("/api/courses", response_model=List[Dict])
def get_courses(db: Session = Depends(get_db)):
    """Get all courses"""
    courses = db.query(Course).all()
    return [course.to_dict() for course in courses]


@app.post("/api/courses", response_model=Dict)
def create_course(course: CourseModel, db: Session = Depends(get_db)):
    """Create a new course"""
    try:
        db_course = Course(
            name=course.name,
            days=course.days,
            start=course.start,
            end=course.end,
            color=course.color
        )
        return DatabaseManager.create(db, db_course).to_dict()
    except Exception as e:
        logger.error(f"Error creating course: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/courses/{course_id}", response_model=Dict)
def update_course(course_id: str, course: CourseModel, db: Session = Depends(get_db)):
    """Update a course"""
    db_course = DatabaseManager.get_by_id(db, Course, course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return DatabaseManager.update(
        db, db_course,
        name=course.name,
        days=course.days,
        start=course.start,
        end=course.end,
        color=course.color
    ).to_dict()


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
def create_task(task: TaskModel, db: Session = Depends(get_db)):
    """Create a new task"""
    try:
        db_task = Task(
            name=task.name,
            duration=task.duration,
            due=task.due,
            difficulty=task.difficulty,
            is_exam=task.is_exam,
            color=task.color,
            notes=task.notes
        )
        return DatabaseManager.create(db, db_task).to_dict()
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/tasks/{task_id}", response_model=Dict)
def update_task(task_id: str, task: TaskModel, db: Session = Depends(get_db)):
    """Update a task"""
    db_task = DatabaseManager.get_by_id(db, Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return DatabaseManager.update(
        db, db_task,
        name=task.name,
        duration=task.duration,
        due=task.due,
        difficulty=task.difficulty,
        is_exam=task.is_exam,
        color=task.color,
        notes=task.notes
    ).to_dict()


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
def create_break(break_item: BreakModel, db: Session = Depends(get_db)):
    """Create a new break"""
    try:
        db_break = Break(
            name=break_item.name,
            day=break_item.day,
            start=break_item.start,
            end=break_item.end,
            color=break_item.color
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
def create_job(job: JobModel, db: Session = Depends(get_db)):
    """Create a new job"""
    try:
        db_job = Job(
            name=job.name,
            days=job.days,
            start=job.start,
            end=job.end,
            color=job.color
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


# COMMUTES
@app.get("/api/commutes", response_model=List[Dict])
def get_commutes(db: Session = Depends(get_db)):
    """Get all commutes"""
    commutes = db.query(Commute).all()
    return [c.to_dict() for c in commutes]


@app.post("/api/commutes", response_model=Dict)
def create_commute(commute: CommuteModel, db: Session = Depends(get_db)):
    """Create a new commute"""
    try:
        db_commute = Commute(
            name=commute.name,
            days=commute.days,
            start=commute.start,
            end=commute.end,
            color=commute.color
        )
        return DatabaseManager.create(db, db_commute).to_dict()
    except Exception as e:
        logger.error(f"Error creating commute: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/commutes/{commute_id}")
def delete_commute(commute_id: str, db: Session = Depends(get_db)):
    """Delete a commute"""
    db_commute = DatabaseManager.get_by_id(db, Commute, commute_id)
    if not db_commute:
        raise HTTPException(status_code=404, detail="Commute not found")
    
    DatabaseManager.delete(db, db_commute)
    return {"message": "Commute deleted successfully"}


# ============================================
# Schedule Generation Endpoints
# ============================================

@app.post("/generate")
def generate_schedule_endpoint(payload: SchedulePayload):
    """
    Generate a study schedule based on courses, tasks, and availability
    
    Can work with:
    1. Raw payload data (no database persistence)
    2. Database-stored data (if IDs are provided instead of full objects)
    """
    try:
        logger.info(f"Received schedule request with {len(payload.tasks)} tasks")
        
        if not payload.tasks:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "No tasks provided",
                    "message": "Please add at least one task to generate a schedule"
                }
            )
        
        # Convert to dict format expected by scheduler
        payload_dict = {
            "courses": [course.dict() for course in payload.courses],
            "tasks": [task.dict() for task in payload.tasks],
            "breaks": [break_item.dict() for break_item in payload.breaks],
            "jobs": [job.dict() for job in payload.jobs],
            "commutes": [commute.dict() for commute in payload.commutes],
            "preferences": payload.preferences.dict()
        }
        
        # Generate schedule
        result = scheduler.generate_schedule(payload_dict)
        
        logger.info(f"Schedule generated: {len(result.get('events', []))} events")
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error generating schedule: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate schedule: {str(e)}")



@app.post("/api/schedule/save")
async def save_schedule(schedule_data: dict, db: Session = Depends(get_db)):
    """
    Save generated schedule sessions to database
    """
    try:
        from models import ScheduledEvent
        
        sessions = schedule_data.get("sessions", [])
        
        if not sessions:
            return {"message": "No sessions to save", "saved": 0}
        
        saved_events = []
        
        for session in sessions:
            # Extract task_id from title if possible (format: "Task Name" or "Task Name (Part N)")
            title = session.get("title", "")
            task_id = None  # You might want to include task_id in the session data
            
            # Parse datetime strings
            start_dt = datetime.fromisoformat(str(session["start"]))
            end_dt = datetime.fromisoformat(str(session["end"]))
            
            # Calculate duration
            duration = int((end_dt - start_dt).total_seconds() / 60)
            
            # Create scheduled event
            event = ScheduledEvent(
                task_id=task_id or "unknown",
                title=title,
                date=start_dt.strftime("%m/%d/%Y"),
                start=start_dt.strftime("%H:%M"),
                end=end_dt.strftime("%H:%M"),
                duration=duration,
                status="scheduled",
                color=session.get("color", "#4CAF50")
            )
            
            db.add(event)
            saved_events.append(event)
        
        db.commit()
        
        logger.info(f"Saved {len(saved_events)} scheduled events")
        
        return {
            "message": f"Successfully saved {len(saved_events)} study sessions",
            "saved": len(saved_events)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/schedule/from-database")
def generate_schedule_from_db(db: Session = Depends(get_db)):
    """
    Generate schedule using ALL data currently stored in database
    
    This endpoint reads all courses, tasks, breaks, jobs, and commutes
    from the database and generates a complete schedule.
    """
    try:
        # Fetch all data from database
        courses = db.query(Course).all()
        tasks = db.query(Task).filter(Task.completed == False).all()
        breaks = db.query(Break).all()
        jobs = db.query(Job).all()
        commutes = db.query(Commute).all()
        
        # Get user preferences (use default if none exist)
        prefs = db.query(UserPreferences).filter(
            UserPreferences.user_id == "default"
        ).first()
        
        if not prefs:
            preferences = {"wake": "08:00", "sleep": "23:00"}
        else:
            preferences = {"wake": prefs.wake, "sleep": prefs.sleep}
        
        logger.info(f"Generating schedule from DB: {len(courses)} courses, "
                   f"{len(tasks)} tasks, {len(breaks)} breaks, "
                   f"{len(jobs)} jobs, {len(commutes)} commutes")
        
        if not tasks:
            return {
                "events": [],
                "summary": {
                    "total_tasks": 0,
                    "scheduled": 0,
                    "message": "No incomplete tasks in database"
                }
            }
        
        # Convert to scheduler format
        payload_dict = {
            "courses": [c.to_dict() for c in courses],
            "tasks": [t.to_dict() for t in tasks],
            "breaks": [b.to_dict() for b in breaks],
            "jobs": [j.to_dict() for j in jobs],
            "commutes": [c.to_dict() for c in commutes],
            "preferences": preferences
        }
        
        # Generate schedule
        result = scheduler.generate_schedule(payload_dict)
        
        logger.info(f"Schedule generated from DB: {len(result.get('events', []))} events")
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating schedule from DB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate")
def validate_schedule(payload: SchedulePayload):
    """Validate schedule payload without generating"""
    try:
        return {
            "valid": True,
            "message": "Payload is valid",
            "summary": {
                "courses": len(payload.courses),
                "tasks": len(payload.tasks),
                "breaks": len(payload.breaks),
                "jobs": len(payload.jobs),
                "commutes": len(payload.commutes)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================
# PDF Generation
# ============================================

@app.post("/api/generate-pdf")
async def generate_pdf(schedule_data: dict):
    """Generate a PDF schedule from calendar data"""
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
    except ImportError:
        logger.warning("ReportLab not installed")
        raise HTTPException(
            status_code=501,
            detail="PDF generation requires 'reportlab' package. Install with: pip install reportlab"
        )
    except Exception as e:
        logger.error(f"PDF generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Health & Info Endpoints
# ============================================

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check with database connectivity"""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "service": "StudyTime API",
        "version": "2.0.0",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


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


@app.delete("/api/clear-all")
def clear_all_data(confirm: str = "", db: Session = Depends(get_db)):
    """
    Clear ALL data from database. USE WITH CAUTION!
    Requires confirm="yes" parameter.
    """
    if confirm != "yes":
        raise HTTPException(
            status_code=400,
            detail="Must provide confirm=yes to clear all data"
        )
    
    try:
        db.query(Course).delete()
        db.query(Task).delete()
        db.query(Break).delete()
        db.query(Job).delete()
        db.query(Commute).delete()
        db.commit()
        
        logger.warning("All data cleared from database")
        return {"message": "All data cleared successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Exception Handlers
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )


# ============================================
# Frontend Serving
# ============================================

frontend_dir = Path(__file__).parent.parent / "frontend"

if frontend_dir.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
        logger.info(f"Frontend mounted from: {frontend_dir}")
    except Exception as e:
        logger.warning(f"Could not mount frontend: {e}")


@app.get("/")
def serve_frontend():
    """Serve the frontend HTML"""
    index_path = frontend_dir / "index.html"
    
    if index_path.exists():
        return FileResponse(str(index_path))
    else:
        return JSONResponse(
            status_code=200,
            content={
                "message": "StudyTime API",
                "version": "2.0.0",
                "docs": "/docs",
                "health": "/health",
                "stats": "/api/stats"
            }
        )


# ============================================
# Startup/Shutdown Events
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("StudyTime API starting up...")
    
    # Initialize database
    if init_db():
        logger.info("✓ Database initialized successfully")
    else:
        logger.error("✗ Database initialization failed")
    
    # Check connection
    if check_db_connection():
        logger.info("✓ Database connection verified")
    else:
        logger.error("✗ Database connection check failed")
    
    logger.info(f"Frontend directory: {frontend_dir}")
    logger.info(f"Frontend exists: {frontend_dir.exists()}")


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