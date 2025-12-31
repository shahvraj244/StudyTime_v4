# StudyTime Backend - Quick Command Reference

## 🚀 Setup Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python database.py init

# Check everything is working
python run_checks.py
```

---

## 🗄️ Database Commands

```bash
# Initialize/create tables
python database.py init

# Check connection
python database.py check

# View database info
python database.py info

# Reset database (⚠️ deletes all data)
python database.py reset
```

---

## 🏃 Running the Server

```bash
# Development mode (auto-reload)
uvicorn main:app --reload

# Specify host and port
uvicorn main:app --host 0.0.0.0 --port 8000

# Different port
uvicorn main:app --port 8080

# Production mode (with gunicorn)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 🧪 Testing Commands

```bash
# Quick SQLAlchemy fix verification
python verify_fix.py

# Complete system check
python run_checks.py

# Or bash version (Linux/Mac)
bash run_checks.sh

# Comprehensive API tests (server must be running)
python test_backend.py
```

---

## 🔍 API Endpoints - Quick Reference

### Health & Info
```bash
# Health check
curl http://localhost:8000/health

# Get statistics
curl http://localhost:8000/api/stats

# API documentation
open http://localhost:8000/docs
```

### Courses
```bash
# List all courses
curl http://localhost:8000/api/courses

# Create a course
curl -X POST http://localhost:8000/api/courses \
  -H "Content-Type: application/json" \
  -d '{"name":"MAC2311","days":["Monday","Wednesday"],"start":"09:00","end":"10:15"}'

# Update a course
curl -X PUT http://localhost:8000/api/courses/{id} \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Course","days":["Monday"],"start":"10:00","end":"11:00"}'

# Delete a course
curl -X DELETE http://localhost:8000/api/courses/{id}
```

### Tasks
```bash
# List all tasks
curl http://localhost:8000/api/tasks

# List only pending tasks
curl http://localhost:8000/api/tasks?completed=false

# Create a task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"name":"Homework","duration":120,"due":"2025-01-05T23:59:00","difficulty":"Medium"}'

# Update a task
curl -X PUT http://localhost:8000/api/tasks/{id} \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Task","duration":90,"due":"2025-01-10T23:59:00","difficulty":"Easy"}'

# Mark task complete
curl -X PATCH http://localhost:8000/api/tasks/{id}/complete

# Delete a task
curl -X DELETE http://localhost:8000/api/tasks/{id}
```

### Breaks
```bash
# List all breaks
curl http://localhost:8000/api/breaks

# Create a break
curl -X POST http://localhost:8000/api/breaks \
  -H "Content-Type: application/json" \
  -d '{"name":"Lunch","day":"Monday","start":"12:00","end":"13:00"}'

# Delete a break
curl -X DELETE http://localhost:8000/api/breaks/{id}
```

### Jobs
```bash
# List all jobs
curl http://localhost:8000/api/jobs

# Create a job
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"name":"Part-time Work","days":["Tuesday","Thursday"],"start":"16:00","end":"20:00"}'

# Delete a job
curl -X DELETE http://localhost:8000/api/jobs/{id}
```

### Commutes
```bash
# List all commutes
curl http://localhost:8000/api/commutes

# Create a commute
curl -X POST http://localhost:8000/api/commutes \
  -H "Content-Type: application/json" \
  -d '{"name":"Morning Commute","days":["Monday","Tuesday"],"start":"08:00","end":"08:30"}'

# Delete a commute
curl -X DELETE http://localhost:8000/api/commutes/{id}
```

### Schedule Generation
```bash
# Generate schedule from database
curl -X POST http://localhost:8000/api/schedule/from-database

# Generate schedule with payload
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"courses":[...],"tasks":[...],"preferences":{"wake":"08:00","sleep":"23:00"}}'

# Validate payload (without generating)
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"courses":[],"tasks":[]}'
```

### Data Management
```bash
# Clear all data (⚠️ dangerous!)
curl -X DELETE "http://localhost:8000/api/clear-all?confirm=yes"
```

---

## 🐍 Python API Usage

### Basic Setup
```python
import requests

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"
```

### Create Data
```python
# Create a course
course = {
    "name": "MAC2311",
    "days": ["Monday", "Wednesday", "Friday"],
    "start": "09:00",
    "end": "10:15"
}
response = requests.post(f"{API_URL}/courses", json=course)
course_id = response.json()["id"]

# Create a task
from datetime import datetime, timedelta
due_date = (datetime.now() + timedelta(days=5)).isoformat()

task = {
    "name": "Calculus Homework",
    "duration": 120,
    "due": due_date,
    "difficulty": "Medium"
}
response = requests.post(f"{API_URL}/tasks", json=task)
task_id = response.json()["id"]
```

### Read Data
```python
# Get all tasks
response = requests.get(f"{API_URL}/tasks")
tasks = response.json()

# Get pending tasks only
response = requests.get(f"{API_URL}/tasks?completed=false")
pending_tasks = response.json()

# Get statistics
response = requests.get(f"{API_URL}/stats")
stats = response.json()
print(f"Total tasks: {stats['tasks']['total']}")
```

### Update Data
```python
# Update a task
updated_task = {
    "name": "Updated Homework",
    "duration": 90,
    "due": "2025-01-10T23:59:00",
    "difficulty": "Easy"
}
response = requests.put(f"{API_URL}/tasks/{task_id}", json=updated_task)

# Mark task complete
response = requests.patch(f"{API_URL}/tasks/{task_id}/complete")
```

### Delete Data
```python
# Delete a task
response = requests.delete(f"{API_URL}/tasks/{task_id}")

# Delete a course
response = requests.delete(f"{API_URL}/courses/{course_id}")
```

### Generate Schedule
```python
# Generate from database
response = requests.post(f"{API_URL}/schedule/from-database")
schedule = response.json()

print(f"Generated {len(schedule['events'])} events")
for event in schedule['events']:
    print(f"{event['date']} {event['start']}-{event['end']}: {event['title']}")
```

---

## 🔧 Troubleshooting Commands

```bash
# Check Python version
python --version

# Check if packages are installed
pip list | grep fastapi
pip list | grep sqlalchemy

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check if port is in use (Linux/Mac)
lsof -i :8000

# Check if port is in use (Windows)
netstat -ano | findstr :8000

# View recent logs (if using systemd)
journalctl -u studytime-api -f

# Check database file exists
ls -lh studytime.db

# Verify database tables
sqlite3 studytime.db ".tables"

# Count records in database
sqlite3 studytime.db "SELECT COUNT(*) FROM tasks;"
```

---

## 📝 Environment Variables (Optional)

Create a `.env` file for configuration:

```bash
# .env file
DATABASE_URL=sqlite:///studytime.db
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
CORS_ORIGINS=["http://localhost:3000"]
```

Then load with:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## 🐳 Docker Commands (If Using Docker)

```bash
# Build image
docker build -t studytime-backend .

# Run container
docker run -p 8000:8000 studytime-backend

# Run with volume for database persistence
docker run -p 8000:8000 -v $(pwd)/data:/app/data studytime-backend

# View logs
docker logs studytime-backend

# Stop container
docker stop studytime-backend
```

---

## 📊 Monitoring Commands

```bash
# Watch server logs
tail -f /var/log/studytime/access.log

# Monitor CPU/memory usage
top | grep python

# Check disk usage
df -h

# Count API requests (if logging to file)
grep "POST /api" access.log | wc -l
```

---

## 🚨 Emergency Commands

```bash
# Kill server if it's stuck
pkill -f "uvicorn main:app"

# Remove database and start fresh
rm studytime.db
python database.py init

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Reinstall everything from scratch
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
python database.py reset
```

---

## ✅ Common Workflows

### Workflow 1: Fresh Start
```bash
pip install -r requirements.txt
python database.py init
python run_checks.py
uvicorn main:app --reload
```

### Workflow 2: Reset Everything
```bash
python database.py reset
rm -rf __pycache__
python run_checks.py
uvicorn main:app --reload
```

### Workflow 3: Deploy Update
```bash
git pull
pip install -r requirements.txt
python database.py check
python test_backend.py
sudo systemctl restart studytime-api
```

### Workflow 4: Development Loop
```bash
# Terminal 1: Run server
uvicorn main:app --reload

# Terminal 2: Watch logs
tail -f studytime.log

# Terminal 3: Test changes
python test_backend.py
```

---

## 📖 Documentation URLs

```
Interactive API Docs (Swagger):    http://localhost:8000/docs
Alternative Docs (ReDoc):          http://localhost:8000/redoc
OpenAPI JSON Schema:               http://localhost:8000/openapi.json
Health Check:                      http://localhost:8000/health
Statistics:                        http://localhost:8000/api/stats
```

---

**Print this as a cheat sheet! 📋**