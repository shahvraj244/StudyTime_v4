# StudyTime_v4
StudyTime is a smart web based academic self-scheduling application designed to help students 
manage courses, assignments, breaks, and study time! 
Unlike a traditional calendar, StudyTime allows you to write down all the tasks and allow you to move 
task based on how much time you think it will take to do an assignment, this way you can 
prioritize level of assignment easy, medium, or hard, based on this you can choose 
which assigments you need to do first then do other task later based on your schedule. 

This project was built with students in mind who struggle with time management, overlapping deadlines, and burnout.

--Course Schedule--
* Add recurring class meetings (multiple days per week)
* Visualized on a weekly calendar
* Prevents scheduling conflicts with study tasks

--Task Management--
Add assignment with:
*Due Date
*Duration (minutes)
*Difficulty level (easy, medium, hard)
*In Class vs take-home indicator 

--Break & Availability Blocking-- 
* Add breaks (work, meals, gym, etc.,)
* Blocks these times so no tasks are scheduled during them

--Visual Weekly Calendar--
* Powered by 'FullCalendar'
* Clear, color-coded schedule
* Real-time updates after schedule generation


---Forntend---
* HTML5
* CSS3
* Vanilla Javascript
* FullCalendar.js (weekly calendar visualization)

---Backend---
* Python
* FastAPI
* Uvicorn (ASGI server)

---Data Format---
* JSON-based API communication
* RESTful endpoint ('POST/generate')


Enviornment Setup

* Requirements:
* FastAPI
* UVICORN
* FullCalendar
* SQLALCHEMNY

pip install -r requirements.txt

1. /backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000