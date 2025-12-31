"""
PDF Generation Module for StudyTime
Generates professional PDF schedules using ReportLab with improved readability

Installation:
pip install reportlab
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Dict, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class PDFScheduleGenerator:
    """Generate professional PDF schedules with improved readability"""
    
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
        self.day_heading_style = ParagraphStyle(
            'DayHeading',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#1565c0'),
            spaceAfter=8,
            spaceBefore=16,
            leftIndent=0
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
        story.append(Spacer(1, 0.4*inch))
        
        # Organize all events by day
        daily_schedule = self._organize_by_day(schedule_data)
        
        # Check for overlaps
        overlaps = self._detect_overlaps(schedule_data)
        if overlaps:
            story.append(Paragraph("⚠️ Schedule Warnings", self.heading_style))
            story.append(self._create_overlap_warnings(overlaps))
            story.append(Spacer(1, 0.3*inch))
        
        # Create day-by-day schedule
        if daily_schedule:
            story.append(Paragraph("Weekly Schedule", self.heading_style))
            for date_str in sorted(daily_schedule.keys()):
                story.extend(self._create_day_section(date_str, daily_schedule[date_str]))

        
        # Summary sections (optional - can be removed if too verbose)
        story.append(PageBreak())
        story.append(Paragraph("Schedule Summary by Type", self.heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        if schedule_data.get('courses'):
            story.append(Paragraph("Courses Overview", self.day_heading_style))
            story.append(self._create_courses_summary(schedule_data['courses']))
            story.append(Spacer(1, 0.2*inch))
        
        if schedule_data.get('jobs'):
            story.append(Paragraph("Work Schedule Overview", self.day_heading_style))
            story.append(self._create_jobs_summary(schedule_data['jobs']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def _organize_by_day(self, schedule_data: Dict) -> Dict[str, List[Dict]]:
        """Organize all events by day and sort chronologically"""
        daily_events = defaultdict(list)
        
        # Process all event types
        for event_type, events in schedule_data.items():
            if not events:
                continue
                
            for event in events:
                event_copy = event.copy()
                event_copy['type'] = event_type
                
                # Parse datetime
                start_dt = self._parse_datetime(event.get('start'))
                if start_dt:
                    date_key = start_dt.strftime('%Y-%m-%d')
                    event_copy['start_dt'] = start_dt
                    
                    end_dt = self._parse_datetime(event.get('end'))
                    if end_dt:
                        event_copy['end_dt'] = end_dt
                    
                    daily_events[date_key].append(event_copy)
        
        # Sort events within each day
        for date_key in daily_events:
            daily_events[date_key].sort(key=lambda x: x.get('start_dt', datetime.max))
        
        return daily_events
    
    def _detect_overlaps(self, schedule_data: Dict) -> List[Dict]:
        """Detect overlapping events"""
        overlaps = []
        all_events = []
        
        # Collect all events with timestamps
        for event_type, events in schedule_data.items():
            if not events:
                continue
            for event in events:
                start_dt = self._parse_datetime(event.get('start'))
                end_dt = self._parse_datetime(event.get('end'))
                if start_dt and end_dt:
                    all_events.append({
                        'title': event.get('title', 'Untitled'),
                        'start': start_dt,
                        'end': end_dt,
                        'type': event_type
                    })
        
        # Sort by start time
        all_events.sort(key=lambda x: x['start'])
        
        # Check for overlaps
        for i in range(len(all_events)):
            for j in range(i + 1, len(all_events)):
                event_a = all_events[i]
                event_b = all_events[j]
                
                # If event B starts before event A ends, they overlap
                if event_b['start'] < event_a['end']:
                    overlaps.append({
                        'event1': event_a,
                        'event2': event_b
                    })
                else:
                    break  # No more overlaps possible for event_a
        
        return overlaps
    
    def _create_overlap_warnings(self, overlaps: List[Dict]):
        """Create warnings table for overlapping events"""
        data = [['Time Conflict', 'Details']]
        
        for overlap in overlaps[:10]:  # Limit to first 10
            e1 = overlap['event1']
            e2 = overlap['event2']
            
            time_str = f"{e1['start'].strftime('%a %b %d, %I:%M %p')}"
            details = f"{e1['title']} ({e1['type']}) overlaps with {e2['title']} ({e2['type']})"
            
            data.append([time_str, details])
        
        if len(overlaps) > 10:
            data.append(['...', f'And {len(overlaps) - 10} more conflicts'])
        
        table = Table(data, colWidths=[2*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E53935')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffebee'), colors.HexColor('#ffcdd2')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def _create_day_section(self, date_str: str, events: List[Dict]):
        """Create a section for one day's schedule"""
        elements = []
        
        # Day header
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_title = date_obj.strftime('%A, %B %d, %Y')
        except:
            day_title = date_str
        
        elements.append(Paragraph(day_title, self.day_heading_style))
        
        # Create table data
        data = [['Time', 'Event', 'Type', 'Duration']]
        
        for event in events:
            start_dt = event.get('start_dt')
            end_dt = event.get('end_dt')
            
            time_str = start_dt.strftime('%I:%M %p') if start_dt else 'TBD'
            if end_dt:
                time_str += f" - {end_dt.strftime('%I:%M %p')}"
            
            title = event.get('title', 'Untitled')
            event_type = self._format_type(event.get('type', ''))
            
            # Calculate duration
            duration = ''
            if start_dt and end_dt:
                delta = end_dt - start_dt
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                if hours > 0:
                    duration = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
                else:
                    duration = f"{minutes}m"
            
            # Get color for event type
            bg_color = self._get_type_color(event.get('type', ''))
            
            data.append([time_str, title, event_type, duration])
        
        # Create table
        table = Table(data, colWidths=[2*inch, 2.5*inch, 1*inch, 1*inch])
        
        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#424242')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Add row-specific coloring
        for i, event in enumerate(events, start=1):
            bg_color = self._get_type_color(event.get('type', ''))
            style_commands.append(('BACKGROUND', (0, i), (-1, i), bg_color))
        
        table.setStyle(TableStyle(style_commands))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_courses_summary(self, courses: List[Dict]):
        """Create summary table for courses"""
        # Group courses by title
        course_groups = defaultdict(list)
        for course in courses:
            title = course.get('title', 'Untitled')
            course_groups[title].append(course)
        
        data = [['Course', 'Schedule']]
        
        for title, instances in sorted(course_groups.items()):
            times = []
            for course in instances:
                start_dt = self._parse_datetime(course.get('start'))
                if start_dt:
                    day = start_dt.strftime('%a')
                    time = start_dt.strftime('%I:%M %p')
                    times.append(f"{day} {time}")
            
            schedule = ', '.join(sorted(set(times))[:5])  # Limit display
            if len(times) > 5:
                schedule += '...'
            
            data.append([title, schedule])
        
        return self._create_styled_table(data, '#1565c0', [2.5*inch, 4*inch])
    
    def _create_jobs_summary(self, jobs: List[Dict]):
        """Create summary table for jobs"""
        job_groups = defaultdict(list)
        for job in jobs:
            title = job.get('title', 'Untitled')
            job_groups[title].append(job)
        
        data = [['Job', 'Total Hours', 'Days']]
        
        for title, instances in sorted(job_groups.items()):
            total_hours = 0
            days = set()
            
            for job in instances:
                start_dt = self._parse_datetime(job.get('start'))
                end_dt = self._parse_datetime(job.get('end'))
                if start_dt and end_dt:
                    days.add(start_dt.strftime('%a'))
                    delta = end_dt - start_dt
                    total_hours += delta.seconds / 3600
            
            days_str = ', '.join(sorted(days))
            hours_str = f"{total_hours:.1f}h/week"
            
            data.append([title, hours_str, days_str])
        
        return self._create_styled_table(data, '#9C27B0', [2.5*inch, 1.5*inch, 2.5*inch])
    
    def _create_legend(self):
        """Create color legend table"""
        legend_data = [
            ['Type', 'Color'],
            ['Study Sessions', ''],
            ['Courses', ''],
            ['Breaks', ''],
            ['Work/Job', '']
        ]
        
        legend_table = Table(legend_data, colWidths=[2*inch, 4*inch])
        
        legend_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#424242')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#C8E6C9')),
            ('BACKGROUND', (1, 2), (1, 2), colors.HexColor('#BBDEFB')),
            ('BACKGROUND', (1, 3), (1, 3), colors.HexColor('#FFE0B2')),
            ('BACKGROUND', (1, 4), (1, 4), colors.HexColor('#E1BEE7')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return legend_table
    
    def _create_styled_table(self, data: List[List], color: str, col_widths: List):
        """Create a styled table with given data and header color"""
        table = Table(data, colWidths=col_widths)
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        return table
    
    def _parse_datetime(self, dt_str):
        """Parse datetime string flexibly"""
        if not dt_str:
            return None
        
        if isinstance(dt_str, datetime):
            return dt_str
        
        try:
            # Try ISO format
            dt = datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
            # Convert to local time (remove timezone info for display)
            return dt.replace(tzinfo=None)
        except:
            pass
        
        return None
    
    def _get_type_color(self, event_type: str):
        """Get background color for event type"""
        colors_map = {
            'tasks': colors.HexColor('#C8E6C9'),
            'courses': colors.HexColor('#BBDEFB'),
            'breaks': colors.HexColor('#FFE0B2'),
            'jobs': colors.HexColor('#E1BEE7')
        }
        return colors_map.get(event_type, colors.white)
    
    def _format_type(self, event_type: str) -> str:
        """Format event type for display"""
        type_map = {
            'tasks': 'Study',
            'courses': 'Class',
            'breaks': 'Break',
            'jobs': 'Work'
        }
        return type_map.get(event_type, event_type.title())


# FastAPI endpoint
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