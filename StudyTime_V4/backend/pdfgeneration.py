"""
PDF Generation Module for StudyTime
Generates professional PDF schedules using ReportLab

Installation:
pip install reportlab
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus.flowables import HRFlowable
from datetime import datetime
from io import BytesIO
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class PDFScheduleGenerator:
    """Generate professional PDF schedules"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=1  # Center
        )
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=12
        )
    
    def generate(self, schedule_data: Dict) -> BytesIO:
        """
        Generate a PDF schedule from calendar data
        
        Args:
            schedule_data: Dictionary containing tasks, courses, breaks, jobs
            
        Returns:
            BytesIO object containing the PDF
        """
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )
        
        # Build the PDF content
        story = []
        
        # Title
        title = Paragraph("📚 StudyTime Schedule", self.title_style)
        story.append(title)
        
        # Generated date
        date_text = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        date_para = Paragraph(date_text, self.styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 0.3*inch))
        
        # Add legend
        story.append(self._create_legend())
        story.append(Spacer(1, 0.3*inch))
        
        # Study Sessions Section
        if schedule_data.get('tasks'):
            story.append(Paragraph("Study Sessions", self.heading_style))
            story.append(self._create_tasks_table(schedule_data['tasks']))
            story.append(Spacer(1, 0.3*inch))
        
        # Courses Section
        if schedule_data.get('courses'):
            story.append(Paragraph("Courses", self.heading_style))
            story.append(self._create_courses_table(schedule_data['courses']))
            story.append(Spacer(1, 0.3*inch))
        
        # Breaks Section
        if schedule_data.get('breaks'):
            story.append(Paragraph("Breaks & Free Time", self.heading_style))
            story.append(self._create_breaks_table(schedule_data['breaks']))
            story.append(Spacer(1, 0.3*inch))
        
        # Work/Job Section
        if schedule_data.get('jobs'):
            story.append(Paragraph("Work Schedule", self.heading_style))
            story.append(self._create_jobs_table(schedule_data['jobs']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def _create_legend(self):
        """Create color legend table"""
        legend_data = [
            ['', 'Legend'],
            ['Study Sessions', ''],
            ['Courses', ''],
            ['Breaks', ''],
            ['Work/Job', ''],
            ['Issues/Warnings', '']
        ]
        
        legend_table = Table(legend_data, colWidths=[2*inch, 4*inch])
        
        legend_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#4CAF50')),
            ('BACKGROUND', (0, 2), (0, 2), colors.HexColor('#1565c0')),
            ('BACKGROUND', (0, 3), (0, 3), colors.HexColor('#FF9800')),
            ('BACKGROUND', (0, 4), (0, 4), colors.HexColor('#9C27B0')),
            ('BACKGROUND', (0, 5), (0, 5), colors.HexColor('#E53935')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return legend_table
    
    def _create_tasks_table(self, tasks: List[Dict]):
        """Create table for study sessions"""
        data = [['Task', 'Date & Time', 'Duration']]
        
        for task in tasks:
            title = task.get('title', 'Untitled')
            start = self._format_datetime(task.get('start'))
            end = self._format_datetime(task.get('end'))
            time_str = f"{start} - {end}" if start and end else "TBD"
            
            # Calculate duration if possible
            duration = "N/A"
            if task.get('start') and task.get('end'):
                try:
                    start_dt = datetime.fromisoformat(str(task['start']).replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(str(task['end']).replace('Z', '+00:00'))
                    duration_min = int((end_dt - start_dt).total_seconds() / 60)
                    duration = f"{duration_min} min"
                except:
                    pass
            
            data.append([title, time_str, duration])
        
        return self._create_styled_table(data, '#4CAF50')
    
    def _create_courses_table(self, courses: List[Dict]):
        """Create table for courses"""
        data = [['Course', 'Time', 'Days']]
        
        for course in courses:
            title = course.get('title', 'Untitled')
            start = self._format_time(course.get('start'))
            end = self._format_time(course.get('end'))
            time_str = f"{start} - {end}" if start and end else "TBD"
            days = "Various"  # Could be extracted from recurrence
            
            data.append([title, time_str, days])
        
        return self._create_styled_table(data, '#1565c0')
    
    def _create_breaks_table(self, breaks: List[Dict]):
        """Create table for breaks"""
        data = [['Break', 'Time', 'Type']]
        
        for break_item in breaks:
            title = break_item.get('title', 'Untitled')
            start = self._format_time(break_item.get('start'))
            end = self._format_time(break_item.get('end'))
            time_str = f"{start} - {end}" if start and end else "TBD"
            
            data.append([title, time_str, 'Break'])
        
        return self._create_styled_table(data, '#FF9800')
    
    def _create_jobs_table(self, jobs: List[Dict]):
        """Create table for work/jobs"""
        data = [['Job', 'Time', 'Type']]
        
        for job in jobs:
            title = job.get('title', 'Untitled')
            start = self._format_time(job.get('start'))
            end = self._format_time(job.get('end'))
            time_str = f"{start} - {end}" if start and end else "TBD"
            
            data.append([title, time_str, 'Work'])
        
        return self._create_styled_table(data, '#9C27B0')
    
    def _create_styled_table(self, data: List[List], color: str):
        """Create a styled table with given data and header color"""
        table = Table(data, colWidths=[3*inch, 2*inch, 1.5*inch])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def _format_datetime(self, dt):
        """Format datetime for display"""
        if not dt:
            return None
        try:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            return dt.strftime('%a, %b %d at %I:%M %p')
        except:
            return str(dt)
    
    def _format_time(self, time_str):
        """Format time string for display"""
        if not time_str:
            return None
        try:
            # Handle various time formats
            if isinstance(time_str, str) and ':' in time_str:
                h, m = time_str.split(':')[:2]
                h = int(h)
                m = int(m)
                period = 'AM' if h < 12 else 'PM'
                h = h if h <= 12 else h - 12
                h = 12 if h == 0 else h
                return f"{h}:{m:02d} {period}"
        except:
            pass
        return str(time_str)


# FastAPI endpoint to add to main.py
def get_pdf_endpoint_code():
    """
    Return code snippet to add to main.py for PDF generation endpoint
    """
    return '''
from fastapi.responses import StreamingResponse
from pdf_generator import PDFScheduleGenerator

@app.post("/api/generate-pdf")
async def generate_pdf(schedule_data: dict):
    """Generate PDF from schedule data"""
    try:
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
'''


if __name__ == "__main__":
    # Test PDF generation
    sample_data = {
        "tasks": [
            {"title": "Math Homework", "start": "2025-12-20T09:00:00", "end": "2025-12-20T11:00:00"},
            {"title": "Study for Physics", "start": "2025-12-21T14:00:00", "end": "2025-12-21T16:00:00"}
        ],
        "courses": [
            {"title": "MAC2311", "start": "09:00", "end": "10:30"}
        ],
        "breaks": [
            {"title": "Lunch", "start": "12:00", "end": "13:00"}
        ],
        "jobs": []
    }
    
    generator = PDFScheduleGenerator()
    pdf = generator.generate(sample_data)
    
    with open("test_schedule.pdf", "wb") as f:
        f.write(pdf.read())
    
    print("Test PDF generated: test_schedule.pdf")