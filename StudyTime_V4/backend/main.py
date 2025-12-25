from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import logging
from pathlib import Path

# Import your scheduler module
import scheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="StudyTime API",
    description="Smart study scheduling API",
    version="1.0.0"
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
    
    @validator('days')
    def validate_days(cls, v):
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in v:
            if day not in valid_days:
                raise ValueError(f"Invalid day: {day}. Must be one of {valid_days}")
        return v
    
    @validator('start', 'end')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid time format: {v}. Must be HH:MM (e.g., 09:00)")
        return v


class TaskModel(BaseModel):
    name: str = Field(..., description="Task name")
    duration: int = Field(..., gt=0, description="Duration in minutes")
    due: str = Field(..., description="Due date in ISO format (YYYY-MM-DDTHH:MM:SS)")
    difficulty: str = Field(default="Medium", description="Easy, Medium, or Hard")
    is_exam: bool = Field(default=False, description="Whether this is an in-class exam/quiz")
    color: Optional[str] = Field(default="#4CAF50", description="Color for calendar display")
    
    @validator('difficulty')
    def validate_difficulty(cls, v):
        valid = ["Easy", "Medium", "Hard"]
        if v not in valid:
            raise ValueError(f"Invalid difficulty: {v}. Must be one of {valid}")
        return v
    
    @validator('due')
    def validate_due_date(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Must be ISO format (YYYY-MM-DDTHH:MM:SS)")
        return v


class BreakModel(BaseModel):
    name: str = Field(..., description="Break name")
    day: str = Field(..., description="Day of the week")
    start: str = Field(..., description="Start time in HH:MM format")
    end: str = Field(..., description="End time in HH:MM format")
    
    @validator('day')
    def validate_day(cls, v):
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if v not in valid_days:
            raise ValueError(f"Invalid day: {v}. Must be one of {valid_days}")
        return v
    
    @validator('start', 'end')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid time format: {v}. Must be HH:MM (e.g., 12:00)")
        return v


class JobModel(BaseModel):
    name: str = Field(..., description="Job/work name")
    days: List[str] = Field(..., description="Days of the week")
    start: str = Field(..., description="Start time in HH:MM format")
    end: str = Field(..., description="End time in HH:MM format")
    
    @validator('days')
    def validate_days(cls, v):
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in v:
            if day not in valid_days:
                raise ValueError(f"Invalid day: {day}. Must be one of {valid_days}")
        return v
    
    @validator('start', 'end')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid time format: {v}. Must be HH:MM (e.g., 14:00)")
        return v


class CommuteModel(BaseModel):
    name: str = Field(..., description="Commute description")
    days: List[str] = Field(..., description="Days of the week")
    start: str = Field(..., description="Start time in HH:MM format")
    end: str = Field(..., description="End time in HH:MM format")


class PreferencesModel(BaseModel):
    wake: str = Field(default="08:00", description="Wake time in HH:MM format")
    sleep: str = Field(default="23:00", description="Sleep time in HH:MM format")
    
    @validator('wake', 'sleep')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid time format: {v}. Must be HH:MM (e.g., 08:00)")
        return v


class SchedulePayload(BaseModel):
    courses: List[CourseModel] = Field(default=[], description="List of courses")
    tasks: List[TaskModel] = Field(default=[], description="List of tasks")
    breaks: List[BreakModel] = Field(default=[], description="List of breaks")
    jobs: List[JobModel] = Field(default=[], description="List of jobs/work")
    commutes: List[CommuteModel] = Field(default=[], description="List of commutes")
    preferences: PreferencesModel = Field(default_factory=PreferencesModel, description="User preferences")


# ============================================
# API Routes
# ============================================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "StudyTime API",
        "version": "1.0.0"
    }


@app.post("/generate")
def generate_schedule(payload: SchedulePayload):
    """
    Generate a study schedule based on courses, tasks, and availability
    
    Returns a schedule with study sessions optimally placed before task deadlines
    """
    try:
        logger.info(f"Received schedule request with {len(payload.tasks)} tasks")
        
        # Validate that there are tasks to schedule
        if not payload.tasks:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "No tasks provided",
                    "message": "Please add at least one task to generate a schedule"
                }
            )
        
        # Convert Pydantic models to dictionaries
        payload_dict = {
            "courses": [course.dict() for course in payload.courses],
            "tasks": [task.dict() for task in payload.tasks],
            "breaks": [break_item.dict() for break_item in payload.breaks],
            "jobs": [job.dict() for job in payload.jobs],
            "commutes": [commute.dict() for commute in payload.commutes],
            "preferences": payload.preferences.dict()
        }
        
        # Call the scheduler
        result = scheduler.generate_schedule(payload_dict)
        
        logger.info(f"Schedule generated successfully with {len(result.get('events', []))} events")
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error generating schedule: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate schedule: {str(e)}"
        )


@app.post("/validate")
def validate_schedule(payload: SchedulePayload):
    """
    Validate schedule payload without generating
    
    Useful for checking if data is properly formatted before scheduling
    """
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


@app.post("/api/generate-pdf")
async def generate_pdf(schedule_data: dict):
    """
    Generate a PDF schedule from calendar data
    
    Expects schedule_data with tasks, courses, breaks, jobs arrays
    """
    try:
        # Try to use ReportLab if available
        try:
            # Correct module name: pdfgeneration.py in this repo
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
            logger.warning("ReportLab not installed, returning error")
            raise HTTPException(
                status_code=501,
                detail="PDF generation requires 'reportlab' package. Install with: pip install reportlab"
            )
            
    except Exception as e:
        logger.error(f"PDF generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors"""
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

# Determine frontend directory
frontend_dir = Path(__file__).parent.parent / "frontend"

# Only mount static files if frontend directory exists
if frontend_dir.exists():
    try:
        # Mount static assets (JS/CSS)
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
        logger.info(f"Frontend static files mounted from: {frontend_dir}")
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
            status_code=404,
            content={
                "error": "Frontend not found",
                "message": "Ensure frontend/index.html exists",
                "api_docs": "/docs"
            }
        )


# ============================================
# Startup/Shutdown Events
# ============================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("StudyTime API starting up...")
    logger.info(f"Frontend directory: {frontend_dir}")
    logger.info(f"Frontend exists: {frontend_dir.exists()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
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