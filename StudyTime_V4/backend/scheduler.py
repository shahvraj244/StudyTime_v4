"""
StudyTime - Intelligent Real-Time Scheduler (Merged Version)
==============================================================

Combines:
1. Aggressive "finish today" prioritization
2. Robust gap-finding with timezone awareness
3. Smart task classification (between-class vs after-school)
4. Complete assignment preference
5. Real-time awareness (never schedules in past)

Philosophy: Fill TODAY first for urgent tasks, spread non-urgent work naturally
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import logging
import math

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    ZoneInfo = None

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Difficulty rules
DIFFICULTY_RULES = {
    "Easy":   {"min": 20, "max": 90, "priority": 1.0},
    "Medium": {"min": 30, "max": 120, "priority": 1.5},
    "Hard":   {"min": 45, "max": 180, "priority": 2.0},
}

DEFAULT_WAKE = "08:00"
DEFAULT_SLEEP = "23:00"
MIN_USABLE_BLOCK = 20


# ============================================
# Utility Functions with Timezone Awareness
# ============================================

def get_aware_now(timezone_str: str = "America/New_York") -> datetime:
    """Get timezone-aware current datetime"""
    if ZoneInfo:
        try:
            tz = ZoneInfo(timezone_str)
            return datetime.now(tz)
        except:
            pass
    # Fallback to naive datetime
    return datetime.now()


def parse_time(date: datetime, t: str) -> datetime:
    """Parse HH:MM time string into datetime on given date"""
    try:
        h, m = map(int, t.split(":"))
        result = datetime(date.year, date.month, date.day, h, m)
        # Preserve timezone if date has one
        if hasattr(date, 'tzinfo') and date.tzinfo:
            result = result.replace(tzinfo=date.tzinfo)
        return result
    except:
        result = datetime(date.year, date.month, date.day, 8, 0)
        if hasattr(date, 'tzinfo') and date.tzinfo:
            result = result.replace(tzinfo=date.tzinfo)
        return result


def parse_datetime_aware(dt_str: str, reference_tz: datetime) -> datetime:
    """Parse ISO datetime string and make timezone-aware"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        if dt.tzinfo is None and hasattr(reference_tz, 'tzinfo') and reference_tz.tzinfo:
            dt = dt.replace(tzinfo=reference_tz.tzinfo)
        return dt
    except:
        return reference_tz + timedelta(days=7)


def minutes_between(a: datetime, b: datetime) -> int:
    """Calculate minutes between two datetimes"""
    return int((b - a).total_seconds() / 60)


# ============================================
# Task Classification
# ============================================

def classify_task_session_preference(task: Dict) -> str:
    """
    Classify tasks by ideal study session type:
    - between_classes: Short/easy tasks for class breaks
    - after_school: Long/hard tasks needing focus time
    - flexible: Can work in either context
    """
    duration = task.get("duration", 60)
    difficulty = task.get("difficulty", "Medium")

    if duration >= 120 or (difficulty == "Hard" and duration >= 90):
        return "after_school"
    if duration <= 70 and difficulty in ("Easy", "Medium"):
        return "between_classes"
    return "flexible"


def classify_gap_type(gap_start: datetime, gap_end: datetime, before: str, after: str) -> str:
    """Classify gap by time of day and context"""
    hour = gap_start.hour
    duration = minutes_between(gap_start, gap_end)
    
    # Check if between classes
    is_between_classes = (
        before.startswith("Class:") and 
        after.startswith("Class:")
    )
    
    if is_between_classes:
        return "between_classes"
    
    # Time-based classification
    if hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    elif hour < 21:
        return "evening"
    else:
        return "night"


# ============================================
# Schedule Analysis - Find Real Gaps
# ============================================

def get_day_schedule(date: datetime, payload: Dict, wake: str, sleep: str) -> List[Tuple[datetime, datetime, str]]:
    """
    Get ALL busy blocks for a day (classes, work, commutes, breaks).
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
    
    # Add breaks
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
    
    busy_blocks.sort(key=lambda x: x[0])
    return busy_blocks


def find_gaps(date: datetime, payload: Dict, wake: str, sleep: str, now: datetime) -> List[Dict]:
    """
    Find all free gaps in a day's schedule.
    For TODAY: only returns gaps from NOW onwards (never in the past).
    """
    day_start = parse_time(date, wake)
    day_end = parse_time(date, sleep)
    
    # CRITICAL: Don't schedule in the past
    if date.date() < now.date():
        return []
    
    if date.date() == now.date():
        # For TODAY, start from NOW (not wake time)
        day_start = max(day_start, now)
        
        if day_start >= day_end:
            return []  # Day is over
        
        logger.info(f"📍 Current time: {now.strftime('%H:%M')}, finding gaps from now until {day_end.strftime('%H:%M')}")
    
    busy_blocks = get_day_schedule(date, payload, wake, sleep)
    
    gaps = []
    current_time = day_start
    
    for i, (busy_start, busy_end, busy_type) in enumerate(busy_blocks):
        # Skip past busy blocks
        if busy_end <= current_time:
            continue
        
        # Gap before this busy block?
        if current_time < busy_start:
            gap_duration = minutes_between(current_time, busy_start)
            
            if gap_duration >= MIN_USABLE_BLOCK:
                before = busy_blocks[i-1][2] if i > 0 else "wake up"
                after = busy_type
                
                is_between_classes = (
                    i > 0 and
                    before.startswith("Class:") and
                    after.startswith("Class:")
                )
                
                gap_type = classify_gap_type(current_time, busy_start, before, after)
                
                gaps.append({
                    "date": date,
                    "start": current_time,
                    "end": busy_start,
                    "duration": gap_duration,
                    "before": before,
                    "after": after,
                    "is_between_activities": i > 0,
                    "is_between_classes": is_between_classes,
                    "gap_type": gap_type,
                    "is_today": date.date() == now.date(),
                })
        
        current_time = max(current_time, busy_end)
    
    # Gap after last activity until sleep
    if current_time < day_end:
        gap_duration = minutes_between(current_time, day_end)
        if gap_duration >= MIN_USABLE_BLOCK:
            before = busy_blocks[-1][2] if busy_blocks else "wake up"
            gap_type = classify_gap_type(current_time, day_end, before, "sleep")
            
            gaps.append({
                "date": date,
                "start": current_time,
                "end": day_end,
                "duration": gap_duration,
                "before": before,
                "after": "sleep",
                "is_between_activities": bool(busy_blocks),
                "is_between_classes": False,
                "gap_type": gap_type,
                "is_today": date.date() == now.date(),
            })
    
    return gaps


def build_gap_inventory(start_date: datetime, end_date: datetime, payload: Dict) -> List[Dict]:
    """
    Build complete inventory of ALL available gaps.
    Returns gaps sorted chronologically (earliest first).
    """
    wake = payload.get("preferences", {}).get("wake", DEFAULT_WAKE)
    sleep = payload.get("preferences", {}).get("sleep", DEFAULT_SLEEP)
    
    all_gaps = []
    current = start_date.date()
    end = end_date.date()
    
    while current <= end:
        date_obj = datetime.combine(current, datetime.min.time())
        # Preserve timezone
        if hasattr(start_date, 'tzinfo') and start_date.tzinfo:
            date_obj = date_obj.replace(tzinfo=start_date.tzinfo)
        
        day_gaps = find_gaps(date_obj, payload, wake, sleep, start_date)
        all_gaps.extend(day_gaps)
        current += timedelta(days=1)
    
    # Sort chronologically (earliest first) - THIS IS KEY for aggressive scheduling
    all_gaps.sort(key=lambda g: g["start"])
    
    return all_gaps


# ============================================
# Priority and Urgency Calculation
# ============================================

def calculate_task_urgency(task: Dict, now: datetime) -> Dict:
    """
    Calculate comprehensive urgency metrics for a task.
    Returns dict with urgency info.
    """
    try:
        deadline = parse_datetime_aware(task["due"], now)
    except:
        deadline = now + timedelta(days=7)
    
    hours_until_due = (deadline - now).total_seconds() / 3600
    is_due_today = deadline.date() == now.date()
    is_due_tomorrow = deadline.date() == (now + timedelta(days=1)).date()
    is_overdue = hours_until_due < 0
    
    # Calculate priority (lower = more urgent)
    if is_overdue:
        priority = -1000 - hours_until_due
    elif is_due_today:
        # Due today: prioritize by difficulty (Hard first)
        difficulty_weight = {"Hard": 0, "Medium": 10, "Easy": 20}
        difficulty = task.get("difficulty", "Medium")
        priority = difficulty_weight.get(difficulty, 10) + hours_until_due
    elif is_due_tomorrow:
        priority = 100 + hours_until_due
    else:
        # Normal priority based on time
        priority = 1000 + hours_until_due
    
    return {
        "deadline": deadline,
        "hours_until_due": hours_until_due,
        "is_due_today": is_due_today,
        "is_due_tomorrow": is_due_tomorrow,
        "is_overdue": is_overdue,
        "priority": priority,
        "urgency_level": (
            "OVERDUE" if is_overdue else
            "URGENT_TODAY" if is_due_today else
            "URGENT_TOMORROW" if is_due_tomorrow else
            "NORMAL"
        )
    }


# ============================================
# Gap Scoring
# ============================================

def score_gap_for_task(gap: Dict, task: Dict, urgency: Dict, daily_scheduled: Dict) -> float:
    """
    Score how suitable a gap is for a task (lower = better).
    
    For URGENT tasks (due today/tomorrow):
    - Heavily prioritize TODAY's gaps (chronological order)
    - Fill gaps as soon as possible
    
    For NORMAL tasks:
    - Prefer appropriate gap types (between-class vs evening)
    - Spread work across days
    - Prefer complete assignment in one session
    """
    score = 0.0
    
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    task_duration = task.get("duration", 60)
    gap_duration = gap["duration"]
    task_pref = classify_task_session_preference(task)
    
    # FACTOR 1: URGENCY - Most important for due-today tasks
    if urgency["urgency_level"] in ["URGENT_TODAY", "URGENT_TOMORROW", "OVERDUE"]:
        # For urgent tasks, STRONGLY prefer earlier gaps
        hours_away = (gap["start"] - urgency["deadline"]).total_seconds() / 3600
        
        if gap["is_today"]:
            score -= 500  # MASSIVE bonus for today
        else:
            # Penalize future days heavily for urgent tasks
            days_out = (gap["date"].date() - gap["start"].date()).days
            score += days_out * 200
    
    # FACTOR 2: Complete assignment preference
    if gap_duration >= task_duration:
        score -= 300  # Strong preference for fitting entire task
    
    # FACTOR 3: Gap type matching (only matters for non-urgent tasks)
    if urgency["urgency_level"] == "NORMAL":
        if task_pref == "between_classes" and gap["is_between_classes"]:
            score -= 50
        elif task_pref == "after_school" and gap["gap_type"] in ["evening", "night"]:
            score -= 50
        elif task_pref == "between_classes" and gap["gap_type"] in ["evening", "night"]:
            score += 30  # Slight penalty
    
    # FACTOR 4: Don't overload single days (for non-urgent tasks)
    if urgency["urgency_level"] == "NORMAL":
        gap_date = gap["date"].date()
        today_load = daily_scheduled.get(gap_date, 0)
        
        if today_load >= 180:
            score += 300  # Day is very full
        elif today_load >= 120:
            score += 150  # Day is getting full
    
    # FACTOR 5: Gap size fit
    if gap_duration >= rules["max"]:
        score -= 20
    elif gap_duration >= rules["min"]:
        score += 10
    else:
        score += 200  # Too small
    
    return score


# ============================================
# Task Scheduling
# ============================================

def schedule_task_in_gaps(task: Dict, gaps: List[Dict], scheduled_blocks: List[Dict], now: datetime) -> List[Dict]:
    """
    Schedule a task using aggressive "finish ASAP" strategy for urgent tasks,
    smart spreading for normal tasks.
    """
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    total_duration = task.get("duration", 60)
    remaining = total_duration
    
    # Calculate urgency
    urgency = calculate_task_urgency(task, now)
    
    blocks = []
    
    # Track daily scheduling
    daily_scheduled = defaultdict(int)
    for block in scheduled_blocks:
        try:
            block_date = datetime.strptime(block["date"], "%m/%d/%Y").date()
            daily_scheduled[block_date] += block.get("duration", 0)
        except:
            pass
    
    logger.info(f"  📋 {task['name']}: {remaining}min, {difficulty}, {urgency['urgency_level']}")
    if urgency['is_due_today']:
        logger.info(f"     ⚠️  Due TODAY in {urgency['hours_until_due']:.1f}h - FILLING EARLIEST GAPS")
    
    # Helper: check if gap is usable
    def is_gap_usable(gap):
        if gap["start"] >= urgency["deadline"]:
            return False
        usable_end = min(gap["end"], urgency["deadline"])
        return minutes_between(gap["start"], usable_end) >= MIN_USABLE_BLOCK
    
    # PHASE 1: Try to find ONE gap that fits ENTIRE task
    for gap in gaps[:]:
        if not is_gap_usable(gap):
            continue
        
        usable_end = min(gap["end"], urgency["deadline"])
        usable_duration = minutes_between(gap["start"], usable_end)
        
        if usable_duration >= remaining:
            logger.info(f"     ✓ Complete assignment fits in {gap['start'].strftime('%a %m/%d %H:%M')}")
            
            session_start = gap["start"]
            session_end = session_start + timedelta(minutes=remaining)
            
            color = (
                "#F44336" if urgency["urgency_level"] == "URGENT_TODAY" else
                "#FF9800" if urgency["urgency_level"] == "URGENT_TOMORROW" else
                "#4CAF50"
            )
            
            blocks.append({
                "title": task["name"],
                "day": WEEKDAY_NAMES[session_start.weekday()],
                "start": session_start.strftime("%H:%M"),
                "end": session_end.strftime("%H:%M"),
                "date": session_start.strftime("%m/%d/%Y"),
                "duration": remaining,
                "difficulty": difficulty,
                "color": color,
                "status": "scheduled",
                "urgency": urgency["urgency_level"]
            })
            
            # Update gap
            if session_end >= gap["end"] or session_end >= urgency["deadline"]:
                gaps.remove(gap)
            else:
                gap["start"] = session_end
                gap["duration"] = minutes_between(session_end, gap["end"])
                if gap["duration"] < MIN_USABLE_BLOCK:
                    gaps.remove(gap)
            
            return blocks
    
    # PHASE 2: Split into sessions
    logger.info(f"     → Splitting into sessions...")
    
    session_num = 1
    attempts = 0
    max_attempts = len(gaps) * 2
    
    while remaining > 0 and attempts < max_attempts and gaps:
        attempts += 1
        
        # Score all usable gaps
        scored_gaps = []
        for gap in gaps:
            if not is_gap_usable(gap):
                continue
            
            score = score_gap_for_task(gap, task, urgency, daily_scheduled)
            scored_gaps.append((score, gap))
        
        if not scored_gaps:
            break
        
        # Take best gap
        scored_gaps.sort(key=lambda x: x[0])
        best_score, best_gap = scored_gaps[0]
        
        # Calculate chunk size
        usable_end = min(best_gap["end"], urgency["deadline"])
        max_allowed = minutes_between(best_gap["start"], usable_end)
        
        if max_allowed < MIN_USABLE_BLOCK:
            gaps.remove(best_gap)
            continue
        
        chunk_size = min(remaining, max_allowed, rules["max"])
        
        # Enforce minimum (unless final chunk)
        if chunk_size < rules["min"] and remaining > rules["min"]:
            if chunk_size < MIN_USABLE_BLOCK:
                gaps.remove(best_gap)
                continue
        
        session_start = best_gap["start"]
        session_end = session_start + timedelta(minutes=chunk_size)
        
        color = (
            "#F44336" if urgency["urgency_level"] == "URGENT_TODAY" else
            "#FF9800" if urgency["urgency_level"] == "URGENT_TOMORROW" else
            "#4CAF50"
        )
        
        blocks.append({
            "title": f"{task['name']} (Session {session_num})",
            "day": WEEKDAY_NAMES[session_start.weekday()],
            "start": session_start.strftime("%H:%M"),
            "end": session_end.strftime("%H:%M"),
            "date": session_start.strftime("%m/%d/%Y"),
            "duration": chunk_size,
            "difficulty": difficulty,
            "color": color,
            "status": "scheduled",
            "urgency": urgency["urgency_level"]
        })
        
        logger.info(f"     ✓ Session {session_num}: {session_start.strftime('%a %m/%d %H:%M')}-{session_end.strftime('%H:%M')} ({chunk_size}min)")
        
        remaining -= chunk_size
        session_num += 1
        
        # Update gap and daily tracking
        gap_date = best_gap["date"].date()
        daily_scheduled[gap_date] += chunk_size
        
        if session_end >= best_gap["end"] or session_end >= urgency["deadline"]:
            gaps.remove(best_gap)
        else:
            best_gap["start"] = session_end
            best_gap["duration"] = minutes_between(session_end, best_gap["end"])
            if best_gap["duration"] < MIN_USABLE_BLOCK:
                gaps.remove(best_gap)
    
    # Handle incomplete scheduling
    if remaining > 0:
        logger.warning(f"     ⚠️  {remaining}min could NOT be scheduled!")
        blocks.append({
            "title": f"⚠️ INCOMPLETE: {task['name']} ({remaining}min missing)",
            "day": WEEKDAY_NAMES[urgency["deadline"].weekday()],
            "start": urgency["deadline"].strftime("%H:%M"),
            "end": urgency["deadline"].strftime("%H:%M"),
            "date": urgency["deadline"].strftime("%m/%d/%Y"),
            "duration": 0,
            "status": "incomplete",
            "color": "#FF5722"
        })
    
    return blocks


# ============================================
# Exam Handling
# ============================================

def schedule_in_class_exam(task: Dict, payload: Dict, now: datetime) -> List[Dict]:
    """Schedule in-class exam at course time"""
    try:
        exam_date = parse_datetime_aware(task["due"], now)
    except:
        exam_date = now
    
    task_name = task.get("name", "").upper()
    courses = payload.get("courses", [])
    
    matched_course = None
    for course in courses:
        course_name = course.get("name", "").upper()
        if course_name in task_name or task_name.startswith(course_name[:3]):
            matched_course = course
            break
    
    if matched_course:
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
            "status": "exam",
            "is_exam": True
        }]
    
    return [{
        "title": f"📝 EXAM: {task['name']}",
        "day": WEEKDAY_NAMES[exam_date.weekday()],
        "start": exam_date.strftime("%H:%M"),
        "end": (exam_date + timedelta(hours=1)).strftime("%H:%M"),
        "date": exam_date.strftime("%m/%d/%Y"),
        "duration": 60,
        "color": "#E91E63",
        "status": "exam",
        "is_exam": True
    }]


# ============================================
# Main Scheduler
# ============================================

def generate_schedule(payload: Dict) -> Dict:
    """
    Main scheduling algorithm with aggressive today-first logic.
    """
    # Get timezone-aware current time
    tz = payload.get("preferences", {}).get("timezone", "America/New_York")
    now = get_aware_now(tz)
    
    logger.info("=" * 70)
    logger.info(f"🎓 StudyTime Intelligent Scheduler")
    logger.info(f"📅 {now.strftime('%A, %B %d, %Y at %I:%M %p')}")
    logger.info("=" * 70)
    
    tasks = payload.get("tasks", [])
    if not tasks:
        return {
            "events": [],
            "summary": {"total_tasks": 0, "scheduled": 0, "incomplete": 0, "exams": 0}
        }
    
    # Separate exams from study tasks
    exam_tasks = [t for t in tasks if t.get("is_exam", False)]
    study_tasks = [t for t in tasks if not t.get("is_exam", False)]
    
    # Handle exams
    exam_blocks = []
    for exam in exam_tasks:
        exam_events = schedule_in_class_exam(exam, payload, now)
        exam_blocks.extend(exam_events)
    
    if not study_tasks:
        return {
            "events": exam_blocks,
            "summary": {"total_tasks": len(tasks), "scheduled": 0, "incomplete": 0, "exams": len(exam_tasks)}
        }
    
    # Calculate urgency and sort tasks
    for task in study_tasks:
        task["_urgency"] = calculate_task_urgency(task, now)
    
    study_tasks.sort(key=lambda t: t["_urgency"]["priority"])
    
    logger.info(f"\n📚 Tasks to Schedule (by urgency):\n")
    for i, task in enumerate(study_tasks, 1):
        urg = task["_urgency"]
        deadline_str = urg["deadline"].strftime("%m/%d %I:%M%p")
        logger.info(f"{i}. {task['name']} - {task['duration']}min, {task['difficulty']}")
        logger.info(f"   Due: {deadline_str} ({urg['urgency_level']})\n")
    
    # Find latest deadline
    max_deadline = max(t["_urgency"]["deadline"] for t in study_tasks)
    
    # Build gap inventory
    logger.info(f"🔍 Finding available time slots until {max_deadline.strftime('%m/%d')}...\n")
    all_gaps = build_gap_inventory(now, max_deadline, payload)
    
    # Show today's gaps
    today_gaps = [g for g in all_gaps if g["is_today"]]
    if today_gaps:
        logger.info("📅 TODAY's Free Time:")
        for gap in today_gaps:
            logger.info(f"   {gap['start'].strftime('%H:%M')}-{gap['end'].strftime('%H:%M')} "
                       f"({gap['duration']}min) - {gap['gap_type']}")
        logger.info("")
    
    # Schedule each task
    logger.info("📝 SCHEDULING:\n")
    all_blocks = []
    
    for task in study_tasks:
        task_blocks = schedule_task_in_gaps(task, all_gaps, all_blocks, now)
        all_blocks.extend(task_blocks)
        logger.info("")
    
    # Combine all events
    all_events = exam_blocks + all_blocks
    
    # Stats
    stats = {
        "total_tasks": len(tasks),
        "scheduled": len([b for b in all_blocks if b.get("status") == "scheduled"]),
        "incomplete": len([b for b in all_blocks if b.get("status") == "incomplete"]),
        "exams": len(exam_blocks)
    }
    
    logger.info("=" * 70)
    logger.info("✅ SCHEDULING COMPLETE!")
    logger.info(f"   Scheduled: {stats['scheduled']}/{len(study_tasks)} tasks")
    if stats['incomplete'] > 0:
        logger.info(f"   ⚠️  Incomplete: {stats['incomplete']}")
    logger.info("=" * 70)
    
    return {"events": all_events, "summary": stats}