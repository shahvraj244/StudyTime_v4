"""
StudyTime Reality-Based Scheduler
==================================

This scheduler works like a real student would:
1. Looks at your ACTUAL daily schedule (classes, work, commute)
2. Finds REAL gaps (between classes, after work, evenings)
3. Fills those gaps with appropriate study chunks
4. Spreads work naturally across ALL available days
5. Never clusters everything on one day

Strategy: Gap-First Scheduling with Natural Distribution
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import OrderedDict, defaultdict
import logging

logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Difficulty rules
DIFFICULTY_RULES = {
    "Easy":   {"min": 20, "max": 45, "priority": 1.0},
    "Medium": {"min": 30, "max": 60, "priority": 1.5},
    "Hard":   {"min": 45, "max": 90, "priority": 2.0},
}

DEFAULT_WAKE = "08:00"
DEFAULT_SLEEP = "23:00"
MIN_USABLE_BLOCK = 20  # Smaller blocks are okay for short tasks


# ============================================
# Utility Functions
# ============================================

def parse_time(date: datetime, t: str) -> datetime:
    """Parse HH:MM time string into datetime on given date"""
    try:
        h, m = map(int, t.split(":"))
        return datetime(date.year, date.month, date.day, h, m)
    except:
        return datetime(date.year, date.month, date.day, 8, 0)


def minutes_between(a: datetime, b: datetime) -> int:
    """Calculate minutes between two datetimes"""
    return int((b - a).total_seconds() / 60)


def subtract_block(blocks: List[Tuple[datetime, datetime]], 
                  busy: Tuple[datetime, datetime]) -> List[Tuple[datetime, datetime]]:
    """Remove a busy block from list of free blocks"""
    result = []
    b_start, b_end = busy
    
    for start, end in blocks:
        if b_end <= start or b_start >= end:
            result.append((start, end))
        else:
            if start < b_start:
                result.append((start, b_start))
            if b_end < end:
                result.append((b_end, end))
    
    return result


# ============================================
# Schedule Analysis - Find Real Gaps
# ============================================

def get_day_schedule(date: datetime, payload: Dict, wake: str, sleep: str) -> List[Tuple[datetime, datetime, str]]:
    """
    Get a list of ALL busy blocks for a day (classes, work, commutes, breaks).
    Returns list of (start, end, type) tuples sorted by time.
    """
    day_name = WEEKDAY_NAMES[date.weekday()]
    busy_blocks = []
    
    # Add courses
    for c in payload.get("courses", []):
        if day_name in c.get("days", []):
            start = parse_time(date, c["start"])
            end = parse_time(date, c["end"])
            busy_blocks.append((start, end, f"Class: {c.get('name', 'Course')}"))
    
    # Add jobs
    for j in payload.get("jobs", []):
        if day_name in j.get("days", []):
            start = parse_time(date, j["start"])
            end = parse_time(date, j["end"])
            busy_blocks.append((start, end, f"Work: {j.get('name', 'Job')}"))
    
    # Add breaks (commutes, meals, etc.)
    for b in payload.get("breaks", []):
        if day_name == b.get("day"):
            start = parse_time(date, b["start"])
            end = parse_time(date, b["end"])
            busy_blocks.append((start, end, f"Break: {b.get('name', 'Break')}"))
    
    # Add commutes
    for ct in payload.get("commutes", []):
        if day_name in ct.get("days", []):
            start = parse_time(date, ct["start"])
            end = parse_time(date, ct["end"])
            busy_blocks.append((start, end, f"Commute: {ct.get('name', 'Commute')}"))
    
    # Sort by start time
    busy_blocks.sort(key=lambda x: x[0])
    
    return busy_blocks


def find_gaps(date: datetime, payload: Dict, wake: str, sleep: str, now: datetime) -> List[Dict]:
    """
    Find all free gaps in a day's schedule.
    Returns list of gap dictionaries with metadata about the gap.
    """
    day_start = parse_time(date, wake)
    day_end = parse_time(date, sleep)
    
    # Don't schedule in the past
    if date.date() == now.date():
        day_start = max(day_start, now)
    elif date.date() < now.date():
        return []  # Past day
    
    # Get all busy blocks for the day
    busy_blocks = get_day_schedule(date, payload, wake, sleep)
    
    gaps = []
    current_time = day_start
    
    for i, (busy_start, busy_end, busy_type) in enumerate(busy_blocks):
        # Is there a gap before this busy block?
        if current_time < busy_start:
            gap_duration = minutes_between(current_time, busy_start)
            
            if gap_duration >= MIN_USABLE_BLOCK:
                # Classify the gap type
                gap_type = "morning" if current_time.hour < 12 else \
                          "afternoon" if current_time.hour < 17 else "evening"
                
                # Determine what comes before and after
                before = busy_blocks[i-1][2] if i > 0 else "wake up"
                after = busy_type
                
                gaps.append({
                    "date": date,
                    "start": current_time,
                    "end": busy_start,
                    "duration": gap_duration,
                    "type": gap_type,
                    "before": before,
                    "after": after,
                    "is_between_activities": i > 0,  # True if between two activities
                })
        
        current_time = busy_end
    
    # Check for gap after last activity until sleep
    if current_time < day_end:
        gap_duration = minutes_between(current_time, day_end)
        if gap_duration >= MIN_USABLE_BLOCK:
            gaps.append({
                "date": date,
                "start": current_time,
                "end": day_end,
                "duration": gap_duration,
                "type": "evening",
                "before": busy_blocks[-1][2] if busy_blocks else "wake up",
                "after": "sleep",
                "is_between_activities": False,
            })
    
    return gaps


def build_gap_inventory(start_date: datetime, end_date: datetime, payload: Dict) -> List[Dict]:
    """
    Build a complete inventory of all available gaps across all days.
    Returns sorted list of all gaps.
    """
    wake = payload.get("preferences", {}).get("wake", DEFAULT_WAKE)
    sleep = payload.get("preferences", {}).get("sleep", DEFAULT_SLEEP)
    
    all_gaps = []
    current = start_date.date()
    end = end_date.date()
    
    while current <= end:
        date_obj = datetime.combine(current, datetime.min.time())
        day_gaps = find_gaps(date_obj, payload, wake, sleep, start_date)
        all_gaps.extend(day_gaps)
        current += timedelta(days=1)
    
    # Sort gaps chronologically
    all_gaps.sort(key=lambda g: g["start"])
    
    return all_gaps


# ============================================
# Gap Scoring - Which Gap is Best?
# ============================================

def score_gap_for_task(gap: Dict, task: Dict, scheduled_today: int) -> float:
    """
    Score how suitable a gap is for a task.
    Lower score = better fit.
    
    Scoring factors:
    1. Gap fits the task duration
    2. Spread work across days (penalize if too much scheduled today)
    3. Prefer gaps between activities (real breaks)
    4. Time of day preferences
    """
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    task_duration = task.get("duration", 60)
    gap_duration = gap["duration"]
    
    score = 0.0
    
    # Factor 1: How well does the gap fit?
    if gap_duration >= task_duration:
        # Gap is big enough for entire task - GOOD
        score += 10
        # But prefer not to waste large gaps
        waste = gap_duration - task_duration
        score += waste / 10
    elif gap_duration >= rules["min"]:
        # Gap fits a good chunk - OKAY
        score += 20
    else:
        # Gap is too small - AVOID unless it's the only option
        score += 100
    
    # Factor 2: Spread work across days (KEY FOR YOUR ISSUE)
    # Heavy penalty if too much already scheduled today
    if scheduled_today >= 120:  # More than 2 hours today
        score += 500  # STRONG penalty - force spreading
    elif scheduled_today >= 60:  # More than 1 hour today
        score += 200
    elif scheduled_today >= 30:
        score += 50
    
    # Factor 3: Prefer gaps between activities (natural study breaks)
    if gap["is_between_activities"]:
        score -= 30  # BONUS for between-class gaps
    else:
        score += 10  # Slight penalty for end-of-day
    
    # Factor 4: Time of day preferences
    # Most students prefer morning/afternoon over late evening
    gap_hour = gap["start"].hour
    if 8 <= gap_hour <= 16:  # Morning/afternoon
        score -= 10
    elif 17 <= gap_hour <= 20:  # Early evening
        score += 5
    else:  # Late evening
        score += 20
    
    # Factor 5: Earlier dates are slightly preferred (avoid procrastination)
    days_out = (gap["date"].date() - datetime.now().date()).days
    score += days_out * 2
    
    return score


# ============================================
# Task Scheduling with Gap-First Strategy
# ============================================

def schedule_task_in_gaps(task: Dict, gaps: List[Dict], scheduled_blocks: List[Dict]) -> List[Dict]:
    """
    Schedule a task by filling the best available gaps.
    Uses intelligent gap selection to spread work naturally.
    """
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    remaining = task.get("duration", 60)
    
    blocks = []
    
    # Track how much is scheduled each day (KEY for spreading)
    daily_scheduled = defaultdict(int)
    for block in scheduled_blocks:
        try:
            block_date = datetime.strptime(block["date"], "%m/%d/%Y").date()
            daily_scheduled[block_date] += block.get("duration", 0)
        except:
            pass
    
    # Try to schedule task
    attempts = 0
    max_attempts = len(gaps) * 2
    
    while remaining > 0 and attempts < max_attempts and gaps:
        attempts += 1
        
        # Find best gap for current state
        best_gap = None
        best_score = float('inf')
        
        for gap in gaps:
            gap_date = gap["date"].date()
            today_scheduled = daily_scheduled[gap_date]
            score = score_gap_for_task(gap, task, today_scheduled)
            
            if score < best_score:
                best_score = score
                best_gap = gap
        
        if best_gap is None:
            break
        
        # Determine how much to schedule in this gap
        gap_duration = best_gap["duration"]
        chunk_size = min(gap_duration, remaining, rules["max"])
        
        # Enforce minimum session length (unless it's the final chunk)
        if chunk_size < rules["min"] and remaining > rules["min"]:
            # Try smaller chunk if we're desperate
            if chunk_size >= MIN_USABLE_BLOCK:
                pass  # Allow it
            else:
                # Remove this gap and try next one
                gaps.remove(best_gap)
                continue
        
        # Schedule the chunk
        session_start = best_gap["start"]
        session_end = session_start + timedelta(minutes=chunk_size)
        
        block = {
            "title": task["name"],
            "day": WEEKDAY_NAMES[session_start.weekday()],
            "start": session_start.strftime("%H:%M"),
            "end": session_end.strftime("%H:%M"),
            "date": session_start.strftime("%m/%d/%Y"),
            "duration": chunk_size,
            "color": "#4CAF50",
            "difficulty": difficulty,
            "status": "scheduled",
            "gap_info": f"After {best_gap['before']}"
        }
        
        blocks.append(block)
        remaining -= chunk_size
        
        # Update daily tracking
        gap_date = best_gap["date"].date()
        daily_scheduled[gap_date] += chunk_size
        
        # Update the gap
        if chunk_size >= gap_duration:
            # Used entire gap
            gaps.remove(best_gap)
        else:
            # Partial use - shrink the gap
            best_gap["start"] = session_end
            best_gap["duration"] = minutes_between(session_end, best_gap["end"])
            
            if best_gap["duration"] < MIN_USABLE_BLOCK:
                gaps.remove(best_gap)
    
    # If still remaining, add warning
    if remaining > 0:
        blocks.append({
            "title": f"⚠️ Need {remaining} more minutes: {task['name']}",
            "day": "Multiple",
            "start": "00:00",
            "end": "00:00",
            "date": datetime.now().strftime("%m/%d/%Y"),
            "duration": 0,
            "color": "#FF9800",
            "status": "incomplete"
        })
    
    return blocks


# ============================================
# Priority Calculation
# ============================================

def calculate_priority(task: Dict, now: datetime) -> float:
    """
    Calculate task priority (lower = more urgent).
    Based on deadline and difficulty.
    """
    try:
        deadline = datetime.fromisoformat(task["due"])
    except:
        deadline = now + timedelta(days=7)
    
    hours_until_deadline = (deadline - now).total_seconds() / 3600
    
    difficulty = task.get("difficulty", "Medium")
    priority_weight = DIFFICULTY_RULES[difficulty]["priority"]
    
    # EDF with difficulty: harder tasks scheduled earlier
    priority = hours_until_deadline / priority_weight
    
    # Longer tasks get slight priority
    duration_factor = task.get("duration", 60) / 100.0
    priority -= duration_factor
    
    return priority


# ============================================
# In-Class Exam/Quiz Handler
# ============================================

def schedule_in_class_exam(task: Dict, payload: Dict) -> List[Dict]:
    """
    Schedule an in-class exam/quiz at the actual class time.
    Matches the task to its course and places it during class.
    """
    try:
        exam_date = datetime.fromisoformat(task["due"])
    except:
        exam_date = datetime.now()
    
    # Try to match task name to a course
    task_name = task.get("name", "").upper()
    courses = payload.get("courses", [])
    
    matched_course = None
    for course in courses:
        course_name = course.get("name", "").upper()
        # Check if course code is in task name (e.g., "COP3337" in "COP3337 Final Exam")
        if course_name in task_name or task_name.startswith(course_name[:3]):
            matched_course = course
            break
    
    if not matched_course:
        # No course match - place at exam date/time
        return [{
            "title": f"📝 EXAM: {task['name']}",
            "day": WEEKDAY_NAMES[exam_date.weekday()],
            "start": exam_date.strftime("%H:%M"),
            "end": (exam_date + timedelta(hours=1)).strftime("%H:%M"),
            "date": exam_date.strftime("%m/%d/%Y"),
            "duration": 60,
            "color": "#E91E63",
            "difficulty": "Exam",
            "status": "exam",
            "is_exam": True
        }]
    
    # Place at course's scheduled time on the exam date
    exam_day_name = WEEKDAY_NAMES[exam_date.weekday()]
    
    # Check if course meets on this day
    if exam_day_name not in matched_course.get("days", []):
        # Course doesn't meet this day - use course's normal time anyway
        pass
    
    course_start = matched_course.get("start", "09:00")
    course_end = matched_course.get("end", "10:00")
    
    return [{
        "title": f"📝 EXAM: {task['name']}",
        "day": exam_day_name,
        "start": course_start,
        "end": course_end,
        "date": exam_date.strftime("%m/%d/%Y"),
        "duration": minutes_between(
            parse_time(exam_date, course_start),
            parse_time(exam_date, course_end)
        ),
        "color": "#E91E63",
        "difficulty": "Exam",
        "status": "exam",
        "is_exam": True,
        "course": matched_course.get("name", "")
    }]


# ============================================
# Main Scheduler
# ============================================

def generate_schedule(payload: Dict) -> Dict:
    """
    Generate schedule using gap-first strategy.
    
    Algorithm:
    1. Find ALL gaps in schedule (between classes, after work, evenings)
    2. Sort tasks by priority (deadline + difficulty)
    3. For each task, fill the BEST gaps (using scoring)
    4. Scoring ensures work spreads across days naturally
    5. Handle in-class exams separately (place at class time)
    """
    now = datetime.now()
    
    tasks = payload.get("tasks", [])
    if not tasks:
        return {
            "events": [],
            "summary": {"total_tasks": 0, "scheduled": 0, "incomplete": 0, "overdue": 0, "exams": 0}
        }
    
    # Separate exams from regular tasks
    exam_tasks = [t for t in tasks if t.get("is_exam", False)]
    study_tasks = [t for t in tasks if not t.get("is_exam", False)]
    
    logger.info(f"Found {len(exam_tasks)} in-class exams and {len(study_tasks)} study tasks")
    
    # Handle in-class exams first
    exam_blocks = []
    for exam in exam_tasks:
        exam_events = schedule_in_class_exam(exam, payload)
        exam_blocks.extend(exam_events)
        logger.info(f"Scheduled exam: {exam['name']} on {exam_events[0]['date']} at {exam_events[0]['start']}")
    
    if not study_tasks:
        return {
            "events": exam_blocks,
            "summary": {
                "total_tasks": len(exam_tasks),
                "scheduled": 0,
                "incomplete": 0,
                "overdue": 0,
                "exams": len(exam_tasks),
                "message": "All tasks are in-class exams (no study time scheduled)"
            }
        }
    
    # Calculate priorities for study tasks
    for task in study_tasks:
        task["_priority"] = calculate_priority(task, now)
    
    # Sort by priority (most urgent first)
    study_tasks.sort(key=lambda t: t["_priority"])
    
    logger.info(f"Scheduling {len(study_tasks)} study tasks using gap-first strategy")
    for task in study_tasks:
        logger.info(f"  - {task['name']}: {task.get('duration')}min, "
                   f"{task.get('difficulty')}, priority={task['_priority']:.1f}")
    
    # Find latest deadline to know how far to look
    max_deadline = now + timedelta(days=14)
    for task in study_tasks:
        try:
            deadline = datetime.fromisoformat(task["due"])
            if deadline > max_deadline:
                max_deadline = deadline
        except:
            pass
    
    # Build complete inventory of gaps
    all_gaps = build_gap_inventory(now, max_deadline, payload)
    
    logger.info(f"Found {len(all_gaps)} available gaps across all days")
    
    # Log gap distribution
    gaps_by_day = defaultdict(list)
    for gap in all_gaps:
        day_str = gap["date"].strftime("%a %m/%d")
        gaps_by_day[day_str].append(gap["duration"])
    
    for day, durations in sorted(gaps_by_day.items()):
        total = sum(durations)
        logger.info(f"  {day}: {len(durations)} gaps, {total}min total")
    
    # Schedule each study task
    all_blocks = []
    stats = {
        "total_tasks": len(tasks),
        "scheduled": 0,
        "incomplete": 0,
        "overdue": 0,
        "exams": len(exam_tasks)
    }
    
    for task in study_tasks:
        logger.info(f"Scheduling: {task['name']}")
        
        # Schedule this task in available gaps
        task_blocks = schedule_task_in_gaps(task, all_gaps, all_blocks)
        
        # Update stats
        for block in task_blocks:
            status = block.get("status", "scheduled")
            if status == "scheduled":
                stats["scheduled"] += 1
                logger.info(f"  ✓ {block['date']} {block['start']}-{block['end']} "
                           f"({block['duration']}min) {block.get('gap_info', '')}")
            elif status == "incomplete":
                stats["incomplete"] += 1
            elif status == "overdue":
                stats["overdue"] += 1
        
        all_blocks.extend(task_blocks)
    
    # Combine exam blocks and study blocks
    all_events = exam_blocks + all_blocks
    
    logger.info(f"Scheduling complete: {stats}")
    
    return {"events": all_events, "summary": stats}