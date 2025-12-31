"""
StudyTime Reality-Based Scheduler - Real-Time Priority Version
===============================================================

This scheduler works like a real student would:
1. PRIORITIZES TODAY AND RIGHT NOW (if free time available)
2. Looks at your ACTUAL daily schedule (classes, work, commute)
3. Finds REAL gaps (between classes, after work, evenings, weekends)
4. Fills those gaps with appropriate study chunks
5. Spreads work naturally across ALL available days (INCLUDING SUNDAYS)
6. Never clusters everything on one day
7. NEVER schedules anything after deadlines
8. Handles in-class exams properly

Strategy: Real-Time First + Gap-First Scheduling with Natural Distribution
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import OrderedDict, defaultdict
import logging
import math

logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Difficulty rules - relaxed maximums to prefer complete assignments
DIFFICULTY_RULES = {
    "Easy":   {"min": 20, "max": 90, "priority": 1.0},    # Can do up to 90min
    "Medium": {"min": 30, "max": 120, "priority": 1.5},   # Can do up to 2 hours
    "Hard":   {"min": 45, "max": 180, "priority": 2.0},   # Can do up to 3 hours
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


# ============================================
# Task Session Preference Classification
# ============================================

def classify_task_session_preference(task: Dict) -> str:
    """
    Classify tasks by their ideal study session type:
    - between_classes: Short/easy tasks that fit well in class breaks
    - after_school: Long/hard tasks that need extended focus time
    - flexible: Can work in either context
    """
    duration = task.get("duration", 60)
    difficulty = task.get("difficulty", "Medium")

    if duration >= 120 or (difficulty == "Hard" and duration >= 90):
        return "after_school"
    if duration <= 70 and difficulty in ("Easy", "Medium"):
        return "between_classes"
    return "flexible"


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
    Works for ALL days including weekends (Sunday fix applied).
    """
    day_start = parse_time(date, wake)
    day_end = parse_time(date, sleep)
    
    # CRITICAL: Don't schedule in the past
    if date.date() < now.date():
        logger.debug(f"Skipping past date: {date.date()}")
        return []  # Don't schedule on past days
    
    if date.date() == now.date():
        # For today, start from current time (with 15min buffer)
        current_time_with_buffer = now + timedelta(minutes=15)
        day_start = max(day_start, current_time_with_buffer)
        
        # If we've passed the sleep time for today, no gaps available
        if day_start >= day_end:
            logger.debug(f"Today's schedule already ended")
            return []
        
        logger.info(f"Today's schedule starts at {day_start.strftime('%H:%M')} (current time: {now.strftime('%H:%M')})")
    
    # Get all busy blocks for the day
    busy_blocks = get_day_schedule(date, payload, wake, sleep)
    
    gaps = []
    current_time = day_start
    
    for i, (busy_start, busy_end, busy_type) in enumerate(busy_blocks):
        # Is there a gap before this busy block?
        if current_time < busy_start:
            gap_duration = minutes_between(current_time, busy_start)
            
            if gap_duration >= MIN_USABLE_BLOCK:
                # Determine what comes before and after
                before = busy_blocks[i-1][2] if i > 0 else "wake up"
                after = busy_type
                
                # Check if this is a gap between classes
                is_between_classes = (
                    i > 0 and
                    before.startswith("Class:") and
                    after.startswith("Class:")
                )
                
                gaps.append({
                    "date": date,
                    "start": current_time,
                    "end": busy_start,
                    "duration": gap_duration,
                    "before": before,
                    "after": after,
                    "is_between_activities": i > 0,
                    "is_between_classes": is_between_classes,
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
                "before": busy_blocks[-1][2] if busy_blocks else "wake up",
                "after": "sleep",
                "is_between_activities": False,
                "is_between_classes": False,
            })
    
    return gaps


def build_gap_inventory(start_date: datetime, end_date: datetime, payload: Dict) -> List[Dict]:
    """
    Build a complete inventory of all available gaps across all days.
    Returns sorted list of all gaps.
    INCLUDES ALL DAYS OF THE WEEK (Monday through Sunday).
    """
    wake = payload.get("preferences", {}).get("wake", DEFAULT_WAKE)
    sleep = payload.get("preferences", {}).get("sleep", DEFAULT_SLEEP)
    
    all_gaps = []
    current = start_date.date()
    end = end_date.date()
    
    # Loop through EVERY day from start to end
    while current <= end:
        date_obj = datetime.combine(current, datetime.min.time())
        day_gaps = find_gaps(date_obj, payload, wake, sleep, start_date)
        all_gaps.extend(day_gaps)
        current += timedelta(days=1)  # This will naturally include Sunday
    
    # Sort gaps chronologically
    all_gaps.sort(key=lambda g: g["start"])
    
    return all_gaps


# ============================================
# Gap Scoring - Which Gap is Best?
# ============================================

def score_gap_for_task(gap: Dict, task: Dict, scheduled_today: int, can_fit_whole_task: bool, now: datetime) -> float:
    """
    Score how suitable a gap is for a task.
    Lower score = better fit.
    
    Scoring factors:
    1. MASSIVELY prefer TODAY (especially if free time available NOW)
    2. Strongly prefer gaps that fit the ENTIRE task (complete assignment)
    3. Prefer correct gap type for task (between classes vs after school)
    4. Light spreading across days (but TODAY is king)
    5. Control weekend usage (save for urgent tasks)
    """
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    task_duration = task.get("duration", 60)
    gap_duration = gap["duration"]
    
    score = 0.0
    
    # Get task preference
    task_pref = classify_task_session_preference(task)
    is_between_classes = gap.get("is_between_classes", False)
    is_after_school = (gap.get("after") == "sleep")
    
    # Factor 1: Task placement preference
    if task_pref == "between_classes":
        if is_between_classes:
            score -= 50  # Perfect fit!
        elif is_after_school:
            score += 20  # Acceptable but not ideal
    elif task_pref == "after_school":
        if is_after_school:
            score -= 60  # Perfect fit!
        if is_between_classes:
            score += 80  # Really not ideal
    
    # Factor 2: STRONGLY prefer gaps that fit the whole task
    if can_fit_whole_task and gap_duration >= task_duration:
        score -= 300  # Massive preference for complete assignments
        logger.debug(f"  Gap {gap['start'].strftime('%m/%d %H:%M')} can fit entire task ({task_duration}min) - HUGE BONUS")
    elif gap_duration >= rules["max"]:
        score -= 20  # Gap fits a good long session
    elif gap_duration >= rules["min"]:
        score += 10  # Gap fits minimum session
    else:
        score += 200  # Gap too small
    
    # Factor 3: TIME URGENCY - STRONGLY prefer today and right now!
    days_out = (gap["date"].date() - now.date()).days
    hours_out = (gap["start"] - now).total_seconds() / 3600
    
    if days_out == 0:  # TODAY
        if hours_out <= 1:  # Available RIGHT NOW or very soon
            score -= 500  # MASSIVE bonus for immediate availability
            logger.debug(f"  Gap AVAILABLE NOW - huge priority boost")
        elif hours_out <= 4:  # Later today
            score -= 400  # Still huge bonus for today
        else:  # Tonight
            score -= 300  # Strong bonus for today
    elif days_out == 1:  # Tomorrow
        score += 50  # Small penalty
    else:  # Future days
        score += days_out * 20  # Increasing penalty for future days
    
    # Factor 4: Light spreading within a day (but don't prevent using today)
    if days_out == 0 and scheduled_today >= 180:
        score += 80  # Only penalize if already have 3+ hours today
    elif days_out == 0 and scheduled_today >= 120:
        score += 30  # Small penalty if already have 2+ hours today
    
    # Factor 5: Control weekend usage
    weekday = gap["date"].weekday()
    try:
        deadline = datetime.fromisoformat(task["due"])
    except:
        deadline = now + timedelta(days=7)
    
    days_to_deadline = (deadline.date() - now.date()).days
    
    # Avoid weekends unless deadline is close or it's actually the weekend now
    if weekday >= 5:  # Saturday (5) or Sunday (6)
        if days_out == 0:  # If today IS the weekend, use it!
            score -= 100  # Bonus for using available weekend time
        elif days_to_deadline > 2:
            score += 40  # Penalize future weekend use for non-urgent tasks
    
    return score


# ============================================
# Task Scheduling with Gap-First Strategy
# ============================================

def schedule_task_in_gaps(task: Dict, gaps: List[Dict], scheduled_blocks: List[Dict], now: datetime) -> List[Dict]:
    """
    Schedule a task while respecting REAL deadlines.
    STRONGLY PREFERS to schedule entire task in one session.
    PRIORITIZES TODAY and RIGHT NOW.
    Only splits if absolutely necessary.
    """
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    total_duration = task.get("duration", 60)
    remaining = total_duration
    task_pref = classify_task_session_preference(task)
    buffered_now = now + timedelta(minutes=15)

    # Parse due datetime
    try:
        task_deadline = datetime.fromisoformat(task["due"])
    except:
        task_deadline = datetime.max

    blocks = []

    # Track how much is scheduled per day
    daily_scheduled = defaultdict(int)
    for block in scheduled_blocks:
        try:
            block_date = datetime.strptime(block["date"], "%m/%d/%Y").date()
            daily_scheduled[block_date] += block.get("duration", 0)
        except:
            pass

    logger.info(f"  Looking for {remaining}min slot (prefer complete assignment, type={task_pref})")

    # Helper function to check if gap is usable
    def is_gap_usable(gap):
        if gap["start"] >= task_deadline:
            return False
        if gap["date"].date() == now.date() and gap["start"] < buffered_now:
            return False
        usable_end = min(gap["end"], task_deadline)
        return minutes_between(gap["start"], usable_end) >= MIN_USABLE_BLOCK

    # Filter to preferred gap types if applicable
    preferred_gaps = gaps
    if task_pref == "between_classes":
        between_class_gaps = [g for g in gaps if g.get("is_between_classes") and is_gap_usable(g)]
        if between_class_gaps:
            preferred_gaps = between_class_gaps
            logger.info(f"  Found {len(between_class_gaps)} between-class gaps for this task")

    # PHASE 1: Try to find a single gap that fits the ENTIRE task
    for gap in preferred_gaps[:]:
        if not is_gap_usable(gap):
            continue
        
        usable_end = min(gap["end"], task_deadline)
        usable_duration = minutes_between(gap["start"], usable_end)
        
        # Check if this gap can fit the ENTIRE task
        if usable_duration >= remaining:
            logger.info(f"  ✓ Found gap that fits ENTIRE task: {gap['start'].strftime('%m/%d %H:%M')} ({usable_duration}min available)")
            
            session_start = gap["start"]
            session_end = session_start + timedelta(minutes=remaining)
            
            if session_end > task_deadline:
                session_end = task_deadline
                remaining = minutes_between(session_start, session_end)
            
            blocks.append({
                "title": task["name"],
                "day": WEEKDAY_NAMES[session_start.weekday()],
                "start": session_start.strftime("%H:%M"),
                "end": session_end.strftime("%H:%M"),
                "date": session_start.strftime("%m/%d/%Y"),
                "duration": remaining,
                "difficulty": difficulty,
                "color": "#4CAF50",
                "status": "scheduled",
                "gap_info": f"Complete assignment"
            })
            
            # Update gap
            if session_end >= gap["end"] or session_end >= task_deadline:
                gaps.remove(gap)
            else:
                gap["start"] = session_end
                gap["duration"] = minutes_between(session_end, gap["end"])
                if gap["duration"] < MIN_USABLE_BLOCK:
                    gaps.remove(gap)
            
            return blocks  # Done! Task scheduled completely

    # PHASE 2: If no single gap fits, split intelligently
    logger.info(f"  No single gap fits entire task, splitting into sessions...")
    
    attempts = 0
    max_attempts = len(gaps) * 2

    while remaining > 0 and attempts < max_attempts and gaps:
        attempts += 1

        best_gap = None
        best_score = float("inf")
        
        # Check if any gap can fit the remaining duration
        can_fit_remaining = any(
            minutes_between(g["start"], min(g["end"], task_deadline)) >= remaining
            for g in gaps
            if is_gap_usable(g)
        )

        for gap in gaps:
            if not is_gap_usable(gap):
                continue

            gap_date = gap["date"].date()
            today_scheduled = daily_scheduled[gap_date]
            score = score_gap_for_task(gap, task, today_scheduled, can_fit_remaining, now)

            if score < best_score:
                best_score = score
                best_gap = gap

        if not best_gap:
            logger.warning(f"  No suitable gap found, {remaining}min remaining")
            break

        # Calculate chunk size
        usable_end = min(best_gap["end"], task_deadline)
        max_allowed = minutes_between(best_gap["start"], usable_end)

        if max_allowed < MIN_USABLE_BLOCK:
            gaps.remove(best_gap)
            continue

        # Try to take as much as possible (prefer longer sessions)
        chunk_size = min(remaining, max_allowed, rules["max"])

        # Only enforce minimum if not final chunk
        if chunk_size < rules["min"] and remaining > rules["min"]:
            if chunk_size < MIN_USABLE_BLOCK:
                gaps.remove(best_gap)
                continue

        session_start = best_gap["start"]
        session_end = session_start + timedelta(minutes=chunk_size)
        
        if session_end > task_deadline:
            chunk_size = minutes_between(session_start, task_deadline)
            if chunk_size < MIN_USABLE_BLOCK:
                gaps.remove(best_gap)
                continue
            session_end = task_deadline

        blocks.append({
            "title": task["name"],
            "day": WEEKDAY_NAMES[session_start.weekday()],
            "start": session_start.strftime("%H:%M"),
            "end": session_end.strftime("%H:%M"),
            "date": session_start.strftime("%m/%d/%Y"),
            "duration": chunk_size,
            "difficulty": difficulty,
            "color": "#4CAF50",
            "status": "scheduled",
            "gap_info": f"Session {len(blocks)+1}/{math.ceil(total_duration/chunk_size)}"
        })

        remaining -= chunk_size

        # Update daily tracking
        gap_date = best_gap["date"].date()
        daily_scheduled[gap_date] += chunk_size

        # Update or remove gap
        if session_end >= best_gap["end"] or session_end >= task_deadline:
            gaps.remove(best_gap)
        else:
            best_gap["start"] = session_end
            best_gap["duration"] = minutes_between(session_end, best_gap["end"])

            if best_gap["duration"] < MIN_USABLE_BLOCK:
                gaps.remove(best_gap)

    # If still remaining → warning
    if remaining > 0:
        logger.warning(f"  Unable to schedule {remaining}min for {task['name']}")
        blocks.append({
            "title": f"⚠️ INCOMPLETE: {task['name']} ({remaining} min unscheduled)",
            "day": WEEKDAY_NAMES[task_deadline.weekday()],
            "start": (task_deadline - timedelta(minutes=1)).strftime("%H:%M"),
            "end": task_deadline.strftime("%H:%M"),
            "date": task_deadline.strftime("%m/%d/%Y"),
            "duration": 0,
            "status": "incomplete",
            "color": "#FF9800"
        })

    return blocks


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
# Priority Calculation
# ============================================

def calculate_priority(task: Dict, now: datetime) -> float:
    """
    Calculate task priority (lower = more urgent).
    Based on deadline proximity and task characteristics.
    """
    base_priority = 0.0
    
    # Factor 1: Deadline urgency
    try:
        deadline = datetime.fromisoformat(task["due"])
        days_to_deadline = (deadline.date() - now.date()).days
        
        if days_to_deadline < 0:
            base_priority += 10000  # Overdue tasks first!
        else:
            base_priority += days_to_deadline * 10
    except:
        base_priority += 70  # No deadline = medium priority
    
    # Factor 2: Task difficulty and duration
    difficulty = task.get("difficulty", "Medium")
    duration = task.get("duration", 60)
    rules = DIFFICULTY_RULES.get(difficulty, DIFFICULTY_RULES["Medium"])
    
    # Harder/longer tasks get slight priority boost
    base_priority += rules["priority"] * (duration / 60)
    
    return base_priority


# ============================================
# Main Scheduler
# ============================================

def generate_schedule(payload: Dict) -> Dict:
    """
    Generate schedule using real-time first + gap-first strategy.
    
    Algorithm:
    1. Find ALL gaps in schedule (between classes, after work, evenings, WEEKENDS)
    2. Sort tasks by priority (deadline + difficulty)
    3. For each task, fill the BEST gaps (using scoring)
    4. Scoring PRIORITIZES TODAY and RIGHT NOW first
    5. Work spreads across days naturally only after today is reasonably full
    6. Handle in-class exams separately (place at class time)
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
                "message": "All tasks are in-class exams"
            }
        }
    
    # Calculate priorities for study tasks
    for task in study_tasks:
        task["_priority"] = calculate_priority(task, now)
    
    # Sort by priority (most urgent first)
    study_tasks.sort(key=lambda t: t["_priority"])
    
    logger.info(f"Scheduling {len(study_tasks)} study tasks using real-time + gap-first strategy")
    for task in study_tasks:
        logger.info(f"  - {task['name']}: {task.get('duration')}min, "
                   f"{task.get('difficulty')}, priority={task['_priority']:.1f}")
    
    # Find latest deadline
    max_deadline = now + timedelta(days=14)
    for task in study_tasks:
        try:
            deadline = datetime.fromisoformat(task["due"])
            if deadline > max_deadline:
                max_deadline = deadline
        except:
            pass
    
    # Build gap inventory (INCLUDING SUNDAYS)
    all_gaps = build_gap_inventory(now, max_deadline, payload)
    
    logger.info(f"Found {len(all_gaps)} available gaps across all days")
    
    # Log gap distribution by day
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
        
        task_blocks = schedule_task_in_gaps(task, all_gaps, all_blocks, now)
        
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