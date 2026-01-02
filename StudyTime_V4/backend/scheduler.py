"""
StudyTime - Real-Time Priority Scheduler
=========================================

REAL-TIME LOGIC:
1. Check if you're free RIGHT NOW
2. Schedule IMMEDIATELY if urgent
3. Fill EARLIEST gaps first (4pm before 9pm, today before tomorrow)
4. Chronological ordering is KING
5. Never skip earlier time for later time

Core principle: If time exists TODAY, use it TODAY!
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import logging
import math

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

DIFFICULTY_RULES = {
    "Easy":   {"min": 20, "max": 90, "priority": 1.0},
    "Medium": {"min": 30, "max": 120, "priority": 1.5},
    "Hard":   {"min": 45, "max": 180, "priority": 2.0},
}

DEFAULT_WAKE = "08:00"
DEFAULT_SLEEP = "23:00"
MIN_USABLE_BLOCK = 20


# ============================================
# Timezone-Aware Time Functions
# ============================================

def get_aware_now(timezone_str: str = "America/New_York") -> datetime:
    """Get timezone-aware current datetime"""
    if ZoneInfo:
        try:
            tz = ZoneInfo(timezone_str)
            return datetime.now(tz)
        except:
            pass
    return datetime.now()


def parse_time(date: datetime, t: str) -> datetime:
    """Parse HH:MM time string into datetime on given date"""
    try:
        h, m = map(int, t.split(":"))
        result = datetime(date.year, date.month, date.day, h, m)
        if hasattr(date, 'tzinfo') and date.tzinfo:
            result = result.replace(tzinfo=date.tzinfo)
        return result
    except:
        result = datetime(date.year, date.month, date.day, 8, 0)
        if hasattr(date, 'tzinfo') and date.tzinfo:
            result = result.replace(tzinfo=date.tzinfo)
        return result


def parse_datetime_aware(dt_str: str, reference_tz: datetime) -> datetime:
    """Parse ISO datetime string"""
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
# Schedule Analysis
# ============================================

def get_day_schedule(date: datetime, payload: Dict, wake: str, sleep: str) -> List[Tuple[datetime, datetime, str]]:
    """Get ALL busy blocks for a day"""
    day_name = WEEKDAY_NAMES[date.weekday()]
    busy_blocks = []
    
    for c in payload.get("courses", []):
        if day_name in c.get("days", []):
            start = parse_time(date, c["start"])
            end = parse_time(date, c["end"])
            busy_blocks.append((start, end, f"Class: {c.get('name', 'Course')}"))
    
    for j in payload.get("jobs", []):
        if day_name in j.get("days", []):
            start = parse_time(date, j["start"])
            end = parse_time(date, j["end"])
            busy_blocks.append((start, end, f"Work: {j.get('name', 'Job')}"))
    
    for b in payload.get("breaks", []):
        if day_name == b.get("day"):
            start = parse_time(date, b["start"])
            end = parse_time(date, b["end"])
            busy_blocks.append((start, end, f"Break: {b.get('name', 'Break')}"))
    
    for ct in payload.get("commutes", []):
        if day_name in ct.get("days", []):
            start = parse_time(date, ct["start"])
            end = parse_time(date, ct["end"])
            busy_blocks.append((start, end, f"Commute: {ct.get('name', 'Commute')}"))
    
    busy_blocks.sort(key=lambda x: x[0])
    return busy_blocks


def find_gaps(date: datetime, payload: Dict, wake: str, sleep: str, now: datetime) -> List[Dict]:
    """
    Find ALL free gaps in a day.
    For TODAY: starts from NOW (not wake time).
    Returns gaps in chronological order.
    """
    day_start = parse_time(date, wake)
    day_end = parse_time(date, sleep)
    
    # Skip past days
    if date.date() < now.date():
        return []
    
    is_today = date.date() == now.date()
    
    if is_today:
        # TODAY: Start from NOW
        day_start = max(day_start, now)
        
        if day_start >= day_end:
            return []  # Day is over
        
        logger.info(f"🕐 NOW: {now.strftime('%I:%M %p')} → Finding gaps until {day_end.strftime('%I:%M %p')}")
    
    busy_blocks = get_day_schedule(date, payload, wake, sleep)
    
    gaps = []
    current_time = day_start
    
    for i, (busy_start, busy_end, busy_type) in enumerate(busy_blocks):
        # Skip past activities
        if busy_end <= current_time:
            continue
        
        # Gap before this busy block?
        if current_time < busy_start:
            gap_duration = minutes_between(current_time, busy_start)
            
            if gap_duration >= MIN_USABLE_BLOCK:
                before = busy_blocks[i-1][2] if i > 0 else ("now" if is_today else "start")
                after = busy_type
                
                gaps.append({
                    "date": date,
                    "start": current_time,
                    "end": busy_start,
                    "duration": gap_duration,
                    "before": before,
                    "after": after,
                    "is_today": is_today,
                    "hours_from_now": (current_time - now).total_seconds() / 3600,
                })
        
        current_time = max(current_time, busy_end)
    
    # Gap after last activity
    if current_time < day_end:
        gap_duration = minutes_between(current_time, day_end)
        if gap_duration >= MIN_USABLE_BLOCK:
            before = busy_blocks[-1][2] if busy_blocks else ("now" if is_today else "start")
            
            gaps.append({
                "date": date,
                "start": current_time,
                "end": day_end,
                "duration": gap_duration,
                "before": before,
                "after": "sleep",
                "is_today": is_today,
                "hours_from_now": (current_time - now).total_seconds() / 3600,
            })
    
    return gaps


def build_gap_inventory(start_date: datetime, end_date: datetime, payload: Dict) -> List[Dict]:
    """
    Build complete inventory of gaps.
    CRITICAL: Returns gaps in STRICT CHRONOLOGICAL ORDER (earliest first).
    """
    wake = payload.get("preferences", {}).get("wake", DEFAULT_WAKE)
    sleep = payload.get("preferences", {}).get("sleep", DEFAULT_SLEEP)
    
    all_gaps = []
    current = start_date.date()
    end = end_date.date()
    
    while current <= end:
        date_obj = datetime.combine(current, datetime.min.time())
        if hasattr(start_date, 'tzinfo') and start_date.tzinfo:
            date_obj = date_obj.replace(tzinfo=start_date.tzinfo)
        
        day_gaps = find_gaps(date_obj, payload, wake, sleep, start_date)
        all_gaps.extend(day_gaps)
        current += timedelta(days=1)
    
    # CRITICAL: Sort by start time (earliest first)
    all_gaps.sort(key=lambda g: g["start"])
    
    return all_gaps


# ============================================
# Task Priority Calculation
# ============================================

def calculate_task_priority(task: Dict, now: datetime) -> Dict:
    """Calculate task urgency and priority"""
    try:
        deadline = parse_datetime_aware(task["due"], now)
    except:
        deadline = now + timedelta(days=7)
    
    hours_until_due = (deadline - now).total_seconds() / 3600
    days_until_due = hours_until_due / 24
    is_due_today = deadline.date() == now.date()
    is_due_tomorrow = deadline.date() == (now + timedelta(days=1)).date()
    is_overdue = hours_until_due < 0
    
    # Priority scoring (lower = more urgent)
    if is_overdue:
        priority = -1000
    elif is_due_today:
        priority = hours_until_due  # 0-24
    elif is_due_tomorrow:
        priority = 100 + hours_until_due
    else:
        priority = 1000 + (days_until_due * 10)
    
    # Adjust for difficulty
    difficulty = task.get("difficulty", "Medium")
    if difficulty == "Hard":
        priority *= 0.9  # Slight boost for hard tasks
    
    return {
        "deadline": deadline,
        "hours_until_due": hours_until_due,
        "days_until_due": days_until_due,
        "is_due_today": is_due_today,
        "is_due_tomorrow": is_due_tomorrow,
        "is_overdue": is_overdue,
        "priority": priority,
    }


# ============================================
# SIMPLIFIED Gap Scoring - Chronological First
# ============================================

def score_gap_for_task(gap: Dict, task: Dict, urgency: Dict) -> float:
    """
    SIMPLIFIED scoring - prioritize EARLIEST gaps.
    
    Key principle: 
    - If due today/tomorrow → Use EARLIEST gap (chronological order)
    - Otherwise → Prefer appropriate timing
    
    Lower score = better.
    """
    score = 0.0
    
    # FACTOR 1: TIME - Earliest wins (this is the PRIMARY factor)
    hours_away = gap["hours_from_now"]
    
    if urgency["is_due_today"] or urgency["is_due_tomorrow"]:
        # URGENT: Chronological order is KING
        # Earlier gap = much better score
        score += hours_away * 10  # Small penalty per hour away
        
        # Massive bonus for TODAY
        if gap["is_today"]:
            score -= 1000  # Huge bonus for today
        else:
            score += 500   # Penalty for future days
    else:
        # NOT URGENT: Still prefer earlier, but less aggressive
        score += hours_away * 5
    
    # FACTOR 2: Can fit entire task?
    task_duration = task.get("duration", 60)
    if gap["duration"] >= task_duration:
        score -= 100  # Bonus for complete fit
    
    # FACTOR 3: Appropriate gap size
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    
    if gap["duration"] >= rules["max"]:
        score -= 20
    elif gap["duration"] >= rules["min"]:
        score += 10
    else:
        score += 100  # Too small
    
    return score


# ============================================
# Task Scheduling - Chronological First
# ============================================

def schedule_task_chronologically(task: Dict, gaps: List[Dict], scheduled_blocks: List[Dict], now: datetime) -> List[Dict]:
    """
    Schedule task using CHRONOLOGICAL-FIRST approach.
    Always fills EARLIEST available gaps first.
    """
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    total_duration = task.get("duration", 60)
    remaining = total_duration
    
    urgency = calculate_task_priority(task, now)
    
    blocks = []
    session_num = 1
    
    logger.info(f"\n📝 {task['name']}")
    logger.info(f"   {total_duration}min | {difficulty} | Due: {urgency['deadline'].strftime('%m/%d %I:%M%p')}")
    
    if urgency["is_due_today"]:
        logger.info(f"   ⚠️ URGENT: Due in {urgency['hours_until_due']:.1f}h - using EARLIEST gaps")
    
    # Helper: Check if gap is usable
    def is_gap_usable(gap):
        if gap["start"] < now:
            return False
        if gap["start"] >= urgency["deadline"]:
            return False
        usable_end = min(gap["end"], urgency["deadline"])
        return minutes_between(gap["start"], usable_end) >= MIN_USABLE_BLOCK
    
    # PHASE 1: Try to fit ENTIRE task in ONE gap
    for gap in gaps[:]:
        if not is_gap_usable(gap):
            continue
        
        usable_end = min(gap["end"], urgency["deadline"])
        usable_duration = minutes_between(gap["start"], usable_end)
        
        if usable_duration >= remaining:
            # CAN FIT ENTIRE TASK!
            session_start = gap["start"]
            session_end = session_start + timedelta(minutes=remaining)
            
            color = "#F44336" if urgency["is_due_today"] else "#4CAF50"
            
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
            })
            
            logger.info(f"   ✓ {session_start.strftime('%a %m/%d %I:%M%p')}-{session_end.strftime('%I:%M%p')} "
                       f"({remaining}min) - COMPLETE")
            
            # Update gap
            if session_end >= gap["end"]:
                gaps.remove(gap)
            else:
                gap["start"] = session_end
                gap["duration"] = minutes_between(session_end, gap["end"])
                gap["hours_from_now"] = (gap["start"] - now).total_seconds() / 3600
                if gap["duration"] < MIN_USABLE_BLOCK:
                    gaps.remove(gap)
            
            return blocks
    
    # PHASE 2: Split into sessions - use EARLIEST gaps first
    logger.info(f"   → Splitting into sessions (using earliest gaps first)")
    
    # Score all usable gaps
    scored_gaps = []
    for gap in gaps:
        if is_gap_usable(gap):
            score = score_gap_for_task(gap, task, urgency)
            scored_gaps.append((score, gap))
    
    # Sort by score (best first)
    scored_gaps.sort(key=lambda x: x[0])
    
    for score, gap in scored_gaps:
        if remaining <= 0:
            break
        
        # Check if gap is still valid
        if not is_gap_usable(gap) or gap not in gaps:
            continue
        
        usable_end = min(gap["end"], urgency["deadline"])
        available = minutes_between(gap["start"], usable_end)
        
        if available < MIN_USABLE_BLOCK:
            continue
        
        # Determine chunk size
        chunk = min(remaining, available, rules["max"])
        
        # Enforce minimum (unless last chunk)
        if chunk < rules["min"] and remaining > rules["min"]:
            if chunk < MIN_USABLE_BLOCK:
                continue
        
        session_start = gap["start"]
        session_end = session_start + timedelta(minutes=chunk)
        
        color = "#F44336" if urgency["is_due_today"] else "#4CAF50"
        
        blocks.append({
            "title": f"{task['name']} (Part {session_num})",
            "day": WEEKDAY_NAMES[session_start.weekday()],
            "start": session_start.strftime("%H:%M"),
            "end": session_end.strftime("%H:%M"),
            "date": session_start.strftime("%m/%d/%Y"),
            "duration": chunk,
            "difficulty": difficulty,
            "color": color,
            "status": "scheduled",
        })
        
        logger.info(f"   ✓ Part {session_num}: {session_start.strftime('%a %m/%d %I:%M%p')}-"
                   f"{session_end.strftime('%I:%M%p')} ({chunk}min)")
        
        remaining -= chunk
        session_num += 1
        
        # Update gap
        if session_end >= gap["end"]:
            gaps.remove(gap)
        else:
            gap["start"] = session_end
            gap["duration"] = minutes_between(session_end, gap["end"])
            gap["hours_from_now"] = (gap["start"] - now).total_seconds() / 3600
            if gap["duration"] < MIN_USABLE_BLOCK:
                gaps.remove(gap)
    
    # Handle incomplete
    if remaining > 0:
        logger.warning(f"   ⚠️ Could not schedule {remaining}min")
        blocks.append({
            "title": f"⚠️ {task['name']} (INCOMPLETE: {remaining}min)",
            "day": WEEKDAY_NAMES[urgency["deadline"].weekday()],
            "start": urgency["deadline"].strftime("%H:%M"),
            "end": urgency["deadline"].strftime("%H:%M"),
            "date": urgency["deadline"].strftime("%m/%d/%Y"),
            "duration": 0,
            "color": "#FF5722",
            "status": "incomplete",
        })
    
    return blocks


# ============================================
# Exam Handling
# ============================================

def schedule_in_class_exam(task: Dict, payload: Dict, now: datetime) -> List[Dict]:
    """Schedule in-class exam"""
    try:
        exam_date = parse_datetime_aware(task["due"], now)
    except:
        exam_date = now
    
    return [{
        "title": f"📝 {task['name']}",
        "day": WEEKDAY_NAMES[exam_date.weekday()],
        "start": exam_date.strftime("%H:%M"),
        "end": (exam_date + timedelta(hours=1)).strftime("%H:%M"),
        "date": exam_date.strftime("%m/%d/%Y"),
        "duration": 60,
        "color": "#E91E63",
        "status": "exam",
    }]


# ============================================
# Main Scheduler
# ============================================

def generate_schedule(payload: Dict) -> Dict:
    """
    Main scheduling engine with REAL-TIME chronological priority.
    """
    tz = payload.get("preferences", {}).get("timezone", "America/New_York")
    now = get_aware_now(tz)
    
    logger.info("=" * 70)
    logger.info(f"🎓 StudyTime Real-Time Scheduler")
    logger.info(f"📅 {now.strftime('%A, %B %d, %Y')}")
    logger.info(f"🕐 Current Time: {now.strftime('%I:%M %p')}")
    logger.info("=" * 70)
    
    tasks = payload.get("tasks", [])
    if not tasks:
        return {"events": [], "summary": {"total_tasks": 0}}
    
    # Separate exams and study tasks
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
            "summary": {"total_tasks": len(tasks), "scheduled": 0, "exams": len(exam_tasks)}
        }
    
    # Sort tasks by urgency
    for task in study_tasks:
        task["_urgency"] = calculate_task_priority(task, now)
    
    study_tasks.sort(key=lambda t: t["_urgency"]["priority"])
    
    # Find latest deadline
    max_deadline = max(t["_urgency"]["deadline"] for t in study_tasks)
    
    # Build gap inventory (CHRONOLOGICAL ORDER)
    logger.info(f"\n🔍 Finding available time until {max_deadline.strftime('%m/%d')}...")
    all_gaps = build_gap_inventory(now, max_deadline, payload)
    
    # Show TODAY's gaps
    today_gaps = [g for g in all_gaps if g["is_today"]]
    if today_gaps:
        logger.info(f"\n📅 TODAY's Available Time:")
        for gap in today_gaps:
            logger.info(f"   {gap['start'].strftime('%I:%M %p')}-{gap['end'].strftime('%I:%M %p')} "
                       f"({gap['duration']}min)")
    
    logger.info(f"\n📊 Total gaps found: {len(all_gaps)}")
    logger.info(f"   Today: {len(today_gaps)} gaps")
    logger.info(f"   Future: {len(all_gaps) - len(today_gaps)} gaps")
    
    # Schedule each task
    logger.info(f"\n" + "="*70)
    logger.info("SCHEDULING TASKS (by urgency):")
    logger.info("="*70)
    
    all_blocks = []
    for task in study_tasks:
        task_blocks = schedule_task_chronologically(task, all_gaps, all_blocks, now)
        all_blocks.extend(task_blocks)
    
    # Combine events
    all_events = exam_blocks + all_blocks
    
    # Stats
    stats = {
        "total_tasks": len(tasks),
        "scheduled": len([b for b in all_blocks if b.get("status") == "scheduled"]),
        "incomplete": len([b for b in all_blocks if b.get("status") == "incomplete"]),
        "exams": len(exam_blocks),
    }
    
    logger.info("\n" + "="*70)
    logger.info("✅ SCHEDULING COMPLETE")
    logger.info(f"   Scheduled: {stats['scheduled']}/{len(study_tasks)} tasks")
    if stats["incomplete"] > 0:
        logger.info(f"   ⚠️ Incomplete: {stats['incomplete']}")
    logger.info("="*70)
    
    return {"events": all_events, "summary": stats}