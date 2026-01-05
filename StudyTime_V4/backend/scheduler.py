"""
StudyTime - Personalized Priority Scheduler
============================================

Respects user preferences while maintaining intelligent scheduling.
Supports three modes: Relaxed, Balanced, and Urgent.
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
# User Preferences Helper
# ============================================

def get_user_preferences(payload: Dict) -> Dict:
    """Extract and validate user preferences"""
    prefs = payload.get("preferences", {})
    
    defaults = {
        "wake": DEFAULT_WAKE,
        "sleep": DEFAULT_SLEEP,
        "timezone": "America/New_York",
        "maxStudyHours": 6,
        "sessionLength": 60,
        "breakDuration": 15,
        "betweenClasses": 30,
        "afterSchool": 120,
        "urgencyMode": "balanced",  # relaxed, balanced, urgent
        "studyTime": "afternoon",  # morning, afternoon, evening, any
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
    
    # Merge with defaults
    for key, default_value in defaults.items():
        if key not in prefs:
            prefs[key] = default_value
    
    return prefs


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
# Schedule Analysis with Auto-Meals
# ============================================

def get_day_schedule(date: datetime, payload: Dict, prefs: Dict) -> List[Tuple[datetime, datetime, str]]:
    """Get ALL busy blocks for a day, including auto-meals"""
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
    
    # Auto-add meal times if enabled
    if prefs.get("autoMeals", True):
        lunch_start = parse_time(date, prefs.get("lunchStart", "12:00"))
        lunch_end = parse_time(date, prefs.get("lunchEnd", "13:00"))
        dinner_start = parse_time(date, prefs.get("dinnerStart", "18:00"))
        dinner_end = parse_time(date, prefs.get("dinnerEnd", "19:00"))
        
        busy_blocks.append((lunch_start, lunch_end, "Lunch"))
        busy_blocks.append((dinner_start, dinner_end, "Dinner"))
    
    busy_blocks.sort(key=lambda x: x[0])
    return busy_blocks


# ============================================
# Gap Finding with User Preferences
# ============================================

def find_gaps(date: datetime, payload: Dict, prefs: Dict, now: datetime) -> List[Dict]:
    """Find ALL free gaps in a day with user preferences applied"""
    wake = prefs.get("wake", DEFAULT_WAKE)
    sleep = prefs.get("sleep", DEFAULT_SLEEP)
    
    day_start = parse_time(date, wake)
    day_end = parse_time(date, sleep)
    
    # Skip past days
    if date.date() < now.date():
        return []
    
    # Check if weekend
    is_weekend = date.weekday() >= 5
    if is_weekend and not prefs.get("weekendStudy", True):
        return []
    
    is_today = date.date() == now.date()
    
    if is_today:
        # TODAY: Start from NOW
        day_start = max(day_start, now)
        
        if day_start >= day_end:
            return []
        
        logger.info(f"🕐 NOW: {now.strftime('%I:%M %p')} → Finding gaps until {day_end.strftime('%I:%M %p')}")
    
    busy_blocks = get_day_schedule(date, payload, prefs)
    
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
                
                # Determine gap type
                is_between_classes = "Class" in after and i > 0 and "Class" in busy_blocks[i-1][2]
                is_after_school = i > 0 and "Class" in busy_blocks[i-1][2] and "Class" not in after
                
                gaps.append({
                    "date": date,
                    "start": current_time,
                    "end": busy_start,
                    "duration": gap_duration,
                    "before": before,
                    "after": after,
                    "is_today": is_today,
                    "is_weekend": is_weekend,
                    "is_between_classes": is_between_classes,
                    "is_after_school": is_after_school,
                    "hours_from_now": (current_time - now).total_seconds() / 3600,
                })
        
        current_time = max(current_time, busy_end)
    
    # Gap after last activity
    if current_time < day_end:
        gap_duration = minutes_between(current_time, day_end)
        if gap_duration >= MIN_USABLE_BLOCK:
            before = busy_blocks[-1][2] if busy_blocks else ("now" if is_today else "start")
            
            is_after_school = busy_blocks and any("Class" in b[2] for b in busy_blocks)
            
            gaps.append({
                "date": date,
                "start": current_time,
                "end": day_end,
                "duration": gap_duration,
                "before": before,
                "after": "sleep",
                "is_today": is_today,
                "is_weekend": is_weekend,
                "is_between_classes": False,
                "is_after_school": is_after_school,
                "hours_from_now": (current_time - now).total_seconds() / 3600,
            })
    
    return gaps


def build_gap_inventory(start_date: datetime, end_date: datetime, payload: Dict, prefs: Dict) -> List[Dict]:
    """Build complete inventory of gaps with preferences"""
    all_gaps = []
    current = start_date.date()
    end = end_date.date()
    
    while current <= end:
        date_obj = datetime.combine(current, datetime.min.time())
        if hasattr(start_date, 'tzinfo') and start_date.tzinfo:
            date_obj = date_obj.replace(tzinfo=start_date.tzinfo)
        
        day_gaps = find_gaps(date_obj, payload, prefs, start_date)
        all_gaps.extend(day_gaps)
        current += timedelta(days=1)
    
    # Sort by start time
    all_gaps.sort(key=lambda g: g["start"])
    
    return all_gaps


# ============================================
# Task Priority with Deadline Buffer
# ============================================

def calculate_task_priority(task: Dict, now: datetime, prefs: Dict) -> Dict:
    """Calculate task urgency with deadline buffer"""
    try:
        deadline = parse_datetime_aware(task["due"], now)
    except:
        deadline = now + timedelta(days=7)
    
    # Apply deadline buffer
    buffer_hours = prefs.get("deadlineBuffer", 12)
    adjusted_deadline = deadline - timedelta(hours=buffer_hours)
    
    hours_until_due = (adjusted_deadline - now).total_seconds() / 3600
    days_until_due = hours_until_due / 24
    is_due_today = adjusted_deadline.date() == now.date()
    is_due_tomorrow = adjusted_deadline.date() == (now + timedelta(days=1)).date()
    is_overdue = hours_until_due < 0
    
    # Priority scoring based on urgency mode
    urgency_mode = prefs.get("urgencyMode", "balanced")
    
    if is_overdue:
        priority = -1000
    elif is_due_today:
        if urgency_mode == "urgent":
            priority = hours_until_due * 0.5  # Very aggressive
        elif urgency_mode == "balanced":
            priority = hours_until_due  # Moderate
        else:  # relaxed
            priority = hours_until_due * 2  # Less aggressive
    elif is_due_tomorrow:
        priority = 100 + hours_until_due
    else:
        priority = 1000 + (days_until_due * 10)
    
    # Adjust for difficulty
    difficulty = task.get("difficulty", "Medium")
    if difficulty == "Hard" and prefs.get("prioritizeHard", True):
        priority *= 0.9
    
    return {
        "deadline": deadline,
        "adjusted_deadline": adjusted_deadline,
        "hours_until_due": hours_until_due,
        "days_until_due": days_until_due,
        "is_due_today": is_due_today,
        "is_due_tomorrow": is_due_tomorrow,
        "is_overdue": is_overdue,
        "priority": priority,
    }


# ============================================
# Gap Scoring with Preferences
# ============================================

def score_gap_for_task(gap: Dict, task: Dict, urgency: Dict, prefs: Dict) -> float:
    """Score gaps based on user preferences and urgency mode"""
    score = 0.0
    urgency_mode = prefs.get("urgencyMode", "balanced")
    study_time_pref = prefs.get("studyTime", "any")
    
    # FACTOR 1: TIME - Varies by urgency mode
    hours_away = gap["hours_from_now"]
    
    if urgency_mode == "urgent":
        # Urgent mode: Chronological is KING
        score += hours_away * 5
        if gap["is_today"]:
            score -= 500
    elif urgency_mode == "balanced":
        # Balanced: Mix of early and distributed
        if urgency["is_due_today"] or urgency["is_due_tomorrow"]:
            score += hours_away * 10
            if gap["is_today"]:
                score -= 200
        else:
            score += hours_away * 5
    else:  # relaxed
        # Relaxed: Spread evenly
        days_until_due = urgency["days_until_due"]
        if days_until_due > 3:
            score += abs(hours_away - (days_until_due * 24 / 2)) * 2
        else:
            score += hours_away * 3
    
    # FACTOR 2: Preferred study time
    if study_time_pref != "any":
        hour = gap["start"].hour
        
        if study_time_pref == "morning" and 6 <= hour < 12:
            score -= 50
        elif study_time_pref == "afternoon" and 12 <= hour < 18:
            score -= 50
        elif study_time_pref == "evening" and 18 <= hour < 24:
            score -= 50
        else:
            score += 30  # Penalty for non-preferred time
    
    # FACTOR 3: Between classes preference
    if gap["is_between_classes"]:
        between_classes_time = prefs.get("betweenClasses", 30)
        if gap["duration"] >= between_classes_time:
            score -= 30  # Bonus for using between-class time
        else:
            score += 50  # Penalty if gap too small
    
    # FACTOR 4: After school preference
    if gap["is_after_school"]:
        after_school_time = prefs.get("afterSchool", 120)
        if gap["duration"] >= after_school_time:
            score -= 40  # Bonus for after-school study
    
    # FACTOR 5: Can fit task?
    task_duration = task.get("duration", 60)
    if gap["duration"] >= task_duration:
        score -= 100
    
    # FACTOR 6: Appropriate gap size
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    session_length = prefs.get("sessionLength", 60)
    
    if gap["duration"] >= min(session_length, rules["max"]):
        score -= 20
    elif gap["duration"] >= rules["min"]:
        score += 10
    else:
        score += 100
    
    # FACTOR 7: Hard tasks in morning (if preference enabled)
    if prefs.get("prioritizeHard", True) and difficulty == "Hard":
        if gap["start"].hour < 12:
            score -= 40
    
    return score


# ============================================
# Task Scheduling with Preferences
# ============================================

def schedule_task_with_preferences(task: Dict, gaps: List[Dict], scheduled_blocks: List[Dict], 
                                   now: datetime, prefs: Dict) -> List[Dict]:
    """Schedule task respecting user preferences"""
    difficulty = task.get("difficulty", "Medium")
    rules = DIFFICULTY_RULES[difficulty]
    total_duration = task.get("duration", 60)
    remaining = total_duration
    
    urgency = calculate_task_priority(task, now, prefs)
    
    blocks = []
    session_num = 1
    
    logger.info(f"\n📝 {task['name']}")
    logger.info(f"   {total_duration}min | {difficulty} | Due: {urgency['adjusted_deadline'].strftime('%m/%d %I:%M%p')}")
    
    if urgency["is_due_today"]:
        logger.info(f"   ⚠️ URGENT: Due in {urgency['hours_until_due']:.1f}h")
    
    # Determine max session length
    max_session = min(prefs.get("sessionLength", 60), rules["max"])
    
    # Helper: Check if gap is usable
    def is_gap_usable(gap):
        if gap["start"] < now:
            return False
        if gap["start"] >= urgency["adjusted_deadline"]:
            return False
        usable_end = min(gap["end"], urgency["adjusted_deadline"])
        return minutes_between(gap["start"], usable_end) >= MIN_USABLE_BLOCK
    
    # Check daily study limit
    daily_study = defaultdict(int)
    for block in scheduled_blocks:
        date_key = block.get("date", "")
        daily_study[date_key] += block.get("duration", 0)
    
    max_daily_minutes = prefs.get("maxStudyHours", 6) * 60
    
    # PHASE 1: Try complete fit if auto-split is disabled
    if not prefs.get("autoSplit", True):
        for gap in gaps[:]:
            if not is_gap_usable(gap):
                continue
            
            usable_end = min(gap["end"], urgency["adjusted_deadline"])
            usable_duration = minutes_between(gap["start"], usable_end)
            
            if usable_duration >= remaining:
                date_key = gap["start"].strftime("%m/%d/%Y")
                if daily_study[date_key] + remaining <= max_daily_minutes:
                    session_start = gap["start"]
                    session_end = session_start + timedelta(minutes=remaining)
                    
                    blocks.append({
                        "title": task["name"],
                        "day": WEEKDAY_NAMES[session_start.weekday()],
                        "start": session_start.strftime("%H:%M"),
                        "end": session_end.strftime("%H:%M"),
                        "date": date_key,
                        "duration": remaining,
                        "difficulty": difficulty,
                        "color": "#4CAF50",
                        "status": "scheduled",
                    })
                    
                    logger.info(f"   ✓ Complete: {session_start.strftime('%a %m/%d %I:%M%p')}-{session_end.strftime('%I:%M%p')} ({remaining}min)")
                    
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
    
    # PHASE 2: Split into sessions
    logger.info(f"   → Splitting into sessions (max {max_session}min each)")
    
    # Score all usable gaps
    scored_gaps = []
    for gap in gaps:
        if is_gap_usable(gap):
            score = score_gap_for_task(gap, task, urgency, prefs)
            scored_gaps.append((score, gap))
    
    scored_gaps.sort(key=lambda x: x[0])
    
    for score, gap in scored_gaps:
        if remaining <= 0:
            break
        
        if not is_gap_usable(gap) or gap not in gaps:
            continue
        
        date_key = gap["start"].strftime("%m/%d/%Y")
        if daily_study[date_key] >= max_daily_minutes:
            continue
        
        usable_end = min(gap["end"], urgency["adjusted_deadline"])
        available = minutes_between(gap["start"], usable_end)
        
        if available < MIN_USABLE_BLOCK:
            continue
        
        # Determine chunk size
        remaining_daily = max_daily_minutes - daily_study[date_key]
        chunk = min(remaining, available, max_session, remaining_daily)
        
        if chunk < rules["min"] and remaining > rules["min"]:
            if chunk < MIN_USABLE_BLOCK:
                continue
        
        session_start = gap["start"]
        session_end = session_start + timedelta(minutes=chunk)
        
        blocks.append({
            "title": f"{task['name']} (Part {session_num})",
            "day": WEEKDAY_NAMES[session_start.weekday()],
            "start": session_start.strftime("%H:%M"),
            "end": session_end.strftime("%H:%M"),
            "date": date_key,
            "duration": chunk,
            "difficulty": difficulty,
            "color": "#4CAF50",
            "status": "scheduled",
        })
        
        logger.info(f"   ✓ Part {session_num}: {session_start.strftime('%a %m/%d %I:%M%p')}-{session_end.strftime('%I:%M%p')} ({chunk}min)")
        
        remaining -= chunk
        session_num += 1
        daily_study[date_key] += chunk
        
        # Update gap
        if session_end >= gap["end"]:
            gaps.remove(gap)
        else:
            gap["start"] = session_end + timedelta(minutes=prefs.get("breakDuration", 15))
            gap["duration"] = minutes_between(gap["start"], gap["end"])
            gap["hours_from_now"] = (gap["start"] - now).total_seconds() / 3600
            if gap["duration"] < MIN_USABLE_BLOCK:
                gaps.remove(gap)
    
    if remaining > 0:
        logger.warning(f"   ⚠️ Could not schedule {remaining}min")
        blocks.append({
            "title": f"⚠️ {task['name']} (INCOMPLETE: {remaining}min)",
            "day": WEEKDAY_NAMES[urgency["adjusted_deadline"].weekday()],
            "start": urgency["adjusted_deadline"].strftime("%H:%M"),
            "end": urgency["adjusted_deadline"].strftime("%H:%M"),
            "date": urgency["adjusted_deadline"].strftime("%m/%d/%Y"),
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
    """Main scheduling engine with full personalization support"""
    prefs = get_user_preferences(payload)
    now = get_aware_now(prefs.get("timezone", "America/New_York"))
    
    logger.info("=" * 70)
    logger.info(f"🎓 StudyTime Personalized Scheduler")
    logger.info(f"📅 {now.strftime('%A, %B %d, %Y')}")
    logger.info(f"🕐 Current Time: {now.strftime('%I:%M %p')}")
    logger.info(f"⚙️ Mode: {prefs.get('urgencyMode', 'balanced').upper()}")
    logger.info(f"📚 Max Study: {prefs.get('maxStudyHours', 6)}h/day")
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
    
    # Sort tasks by priority
    for task in study_tasks:
        task["_urgency"] = calculate_task_priority(task, now, prefs)
    
    study_tasks.sort(key=lambda t: t["_urgency"]["priority"])
    
    # Find latest deadline
    max_deadline = max(t["_urgency"]["adjusted_deadline"] for t in study_tasks)
    
    # Build gap inventory
    logger.info(f"\n🔍 Finding available time until {max_deadline.strftime('%m/%d')}...")
    all_gaps = build_gap_inventory(now, max_deadline, payload, prefs)
    
    logger.info(f"\n📊 Found {len(all_gaps)} available time slots")
    
    # Schedule each task
    logger.info(f"\n" + "="*70)
    logger.info("SCHEDULING TASKS:")
    logger.info("="*70)
    
    all_blocks = []
    for task in study_tasks:
        task_blocks = schedule_task_with_preferences(task, all_gaps, all_blocks, now, prefs)
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