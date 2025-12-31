# StudyTime Backend - Quick Start Guide

## 🚀 Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python database.py init
```

Or simply run the database script:
```bash
python database.py
```

This will create `studytime.db` with all necessary tables.

### 3. Start the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## 📊 Database Management

### Check Database Status
```bash
python database.py check
```

### View Database Info
```bash
python database.py info
```

### Reset Database (⚠️ Deletes all data)
```bash
python database.py reset
```

---

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Make sure server is running first!
python test_backend.py
```

This will test:
- ✓ Database connectivity
- ✓ All CRUD operations
- ✓ Schedule generation
- ✓ Data validation
- ✓ Error handling

---

## 📝 API Usage Examples

### Health Check
```bash
curl http://localhost:8000/health
```

### Get Statistics
```bash
curl http://localhost:8000/api/stats
```

### Create a Course
```bash
curl -X POST http://localhost:8000/api/courses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MAC2311 - Calculus I",
    "days": ["Monday", "Wednesday", "Friday"],
    "start": "09:00",
    "end": "10:15",
    "color": "#1565c0"
  }'
```

### Create a Task
```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Calculus Homework",
    "duration": 120,
    "due": "2025-01-05T23:59:00",
    "difficulty": "Medium",
    "is_exam": false
  }'
```

### Get All Tasks
```bash
curl http://localhost:8000/api/tasks
```

### Get Only Pending Tasks
```bash
curl http://localhost:8000/api/tasks?completed=false
```

### Mark Task as Complete
```bash
curl -X PATCH http://localhost:8000/api/tasks/{task_id}/complete
```

### Generate Schedule (Direct Payload)
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "courses": [...],
    "tasks": [...],
    "preferences": {"wake": "08:00", "sleep": "23:00"}
  }'
```

### Generate Schedule from Database
```bash
curl -X POST http://localhost:8000/api/schedule/from-database
```

---

## 🗂️ Database Schema

### Tables Created

1. **courses** - Recurring class schedule
   - name, days (JSON array), start, end, color

2. **tasks** - Assignments and study items
   - name, duration, due, difficulty, is_exam, completed

3. **breaks** - Scheduled breaks and blocked time
   - name, day, start, end

4. **jobs** - Work schedule
   - name, days (JSON array), start, end

5. **commutes** - Travel time
   - name, days (JSON array), start, end

6. **user_preferences** - User settings
   - wake, sleep times, study preferences

7. **scheduled_events** - Generated study sessions
   - Links to tasks, includes scheduling status

---

## 🔧 Common Operations

### Clear All Data
```bash
curl -X DELETE "http://localhost:8000/api/clear-all?confirm=yes"
```

### Delete Specific Items
```bash
# Delete a course
curl -X DELETE http://localhost:8000/api/courses/{course_id}

# Delete a task
curl -X DELETE http://localhost:8000/api/tasks/{task_id}

# Delete a break
curl -X DELETE http://localhost:8000/api/breaks/{break_id}
```

---

## 📚 Complete Workflow Example

### 1. Set up your schedule
```python
import requests

BASE_URL = "http://localhost:8000/api"

# Add courses
course = {
    "name": "MAC2311",
    "days": ["Monday", "Wednesday", "Friday"],
    "start": "09:00",
    "end": "10:15"
}
requests.post(f"{BASE_URL}/courses", json=course)

# Add a job
job = {
    "name": "Part-time Work",
    "days": ["Tuesday", "Thursday"],
    "start": "16:00",
    "end": "20:00"
}
requests.post(f"{BASE_URL}/jobs", json=job)

# Add breaks
lunch = {
    "name": "Lunch",
    "day": "Monday",
    "start": "12:00",
    "end": "13:00"
}
requests.post(f"{BASE_URL}/breaks", json=lunch)
```

### 2. Add tasks
```python
from datetime import datetime, timedelta

due_date = (datetime.now() + timedelta(days=5)).isoformat()

task = {
    "name": "Calculus Homework - Chapter 5",
    "duration": 120,
    "due": due_date,
    "difficulty": "Medium",
    "is_exam": False
}
requests.post(f"{BASE_URL}/tasks", json=task)
```

### 3. Generate schedule
```python
response = requests.post(f"{BASE_URL}/schedule/from-database")
schedule = response.json()

print(f"Generated {len(schedule['events'])} events")
for event in schedule['events']:
    print(f"{event['date']} {event['start']}-{event['end']}: {event['title']}")
```

---

## ⚠️ Troubleshooting

### Database locked error
- Stop any running instances of the app
- Close any database browsers (SQLite Browser, etc.)
- Delete `studytime.db` and reinitialize

### Module not found errors
```bash
pip install -r requirements.txt
```

### Connection refused
- Make sure server is running
- Check if port 8000 is available
- Try a different port: `uvicorn main:app --port 8080`

### Foreign key constraint failed
- This usually means you're trying to link to a non-existent record
- Check that referenced IDs exist in the database

---

## 🎯 Features

✅ **Full CRUD Operations** - Create, Read, Update, Delete for all entities  
✅ **Smart Scheduling** - Intelligent gap-finding algorithm  
✅ **Real-time Priority** - Prioritizes TODAY and immediate availability  
✅ **Database Persistence** - SQLite with SQLAlchemy ORM  
✅ **Input Validation** - Pydantic models for type safety  
✅ **Comprehensive Testing** - Automated test suite  
✅ **RESTful API** - Standard HTTP methods  
✅ **Auto Documentation** - Interactive API docs at /docs  
✅ **Error Handling** - Graceful error messages  
✅ **Logging** - Detailed operation logs  

---

## 📖 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Stats Endpoint**: http://localhost:8000/api/stats

---

## 🐛 Known Issues & Limitations

1. **Single User**: Currently designed for single-user deployment
2. **No Authentication**: No auth layer (add JWT for production)
3. **SQLite**: Not suitable for high-concurrency (consider PostgreSQL)
4. **No Websockets**: Real-time updates require polling

---

## 🚀 Production Deployment

For production, consider:

1. **Use PostgreSQL** instead of SQLite
2. **Add authentication** (JWT tokens)
3. **Use gunicorn** with multiple workers
4. **Set up HTTPS** with SSL certificates
5. **Add rate limiting**
6. **Set specific CORS origins**
7. **Use environment variables** for configuration

Example production command:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 📝 License & Credits

Built with:
- FastAPI - Modern web framework
- SQLAlchemy - SQL toolkit and ORM
- Pydantic - Data validation
- Uvicorn - ASGI server

Created for smart study scheduling with real-world constraints.