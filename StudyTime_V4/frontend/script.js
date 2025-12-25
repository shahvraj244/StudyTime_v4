/*
Smart Study Scheduler - Frontend
Coordinates with backend API to generate intelligent schedules
*/

/*const API_URL = ""; // Same origin, uses /generate endpoint

let courses = [];
let tasks = [];
let breaks = [];
let jobs = [];
let commutes = [];
let calendar;

const DAY_MAP = { 
  Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", 
  Thu: "Thursday", Fri: "Friday", Sat: "Saturday", Sun: "Sunday" 
};

const DAY_INDEX = { 
  Sunday: 0, Monday: 1, Tuesday: 2, Wednesday: 3, 
  Thursday: 4, Friday: 5, Saturday: 6 
};

// Initialize calendar on page load
document.addEventListener("DOMContentLoaded", () => {
  const el = document.getElementById("calendar");
  if (el && typeof FullCalendar !== "undefined") {
    calendar = new FullCalendar.Calendar(el, {
      initialView: "timeGridWeek",
      allDaySlot: false,
      slotMinTime: "06:00:00",
      slotMaxTime: "24:00:00",
      height: "auto",
      editable: true,
      selectable: true,
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'timeGridWeek,timeGridDay'
      },
      events: [],
      eventClick: function(info) {
        // Show event details on click
        const details = `${info.event.title}\n${info.event.startStr} - ${info.event.endStr}`;
        alert(details);
      }
    });
    calendar.render();
  } else {
    // Fallback if FullCalendar not available
    calendar = { 
      addEvent: () => {}, 
      removeAllEvents: () => {},
      render: () => {}
    };
    console.warn("FullCalendar not initialized or #calendar missing.");
  }
});

// Utility functions
function popup(msg) { 
  alert(msg); 
}

function getChecked(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)]
    .map(e => e.value);
}

function dayToIndex(day) {
  if (!day) return 0;
  if (DAY_INDEX[day] !== undefined) return DAY_INDEX[day];
  return DAY_INDEX[DAY_MAP[day]] ?? 0;
}

function normalizeTimeInput(val) {
  if (!val) return null;
  val = val.trim();
  
  // Handle 24-hour format (HH:MM)
  const m24 = val.match(/^(\d{1,2}):(\d{2})$/);
  if (m24) {
    let hh = parseInt(m24[1], 10);
    const mm = parseInt(m24[2], 10);
    if (hh >= 0 && hh <= 23 && mm >= 0 && mm <= 59) {
      return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
    }
    return null;
  }
  
  // Handle 12-hour format (HH:MM AM/PM)
  const m12 = val.match(/^(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)$/);
  if (m12) {
    let hh = parseInt(m12[1], 10);
    const mm = parseInt(m12[2], 10);
    const ampm = m12[3].toLowerCase();
    
    if (ampm === "pm" && hh < 12) hh += 12;
    if (ampm === "am" && hh === 12) hh = 0;
    
    if (hh >= 0 && hh <= 23 && mm >= 0 && mm <= 59) {
      return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
    }
    return null;
  }
  
  return null;
}

function formatDateTime(dateStr, timeStr) {
  // Convert MM/DD/YYYY and HH:MM to ISO format
  if (!dateStr || !timeStr) return null;
  
  const [month, day, year] = dateStr.split('/');
  if (!month || !day || !year) return null;
  
  return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T${timeStr}:00`;
}

// Add Course
function addCourse() {
  const code = document.getElementById("course-code")?.value.trim() ?? "";
  const startRaw = document.getElementById("course-start")?.value.trim() ?? "";
  const endRaw = document.getElementById("course-end")?.value.trim() ?? "";
  const days = getChecked("course-days");

  const start = normalizeTimeInput(startRaw);
  const end = normalizeTimeInput(endRaw);

  if (!code || !start || !end || days.length === 0) { 
    popup("Fill all course fields with valid times (e.g., 09:00 or 9:00 AM)"); 
    return; 
  }

  const color = "#1565c0";
  courses.push({ code, start, end, days, color });

  const li = document.createElement("li");
  li.innerHTML = `<strong>${code}</strong> (${days.join(", ")}) ${start}-${end}`;
  document.getElementById("course-list")?.appendChild(li);

  // Add to calendar
  days.forEach(d => {
    calendar.addEvent({ 
      title: code, 
      daysOfWeek: [dayToIndex(d)], 
      startTime: start, 
      endTime: end, 
      backgroundColor: color,
      borderColor: color
    });
  });

  popup("Course added successfully!");
  
  // Clear form
  document.getElementById("course-code").value = "";
  document.getElementById("course-start").value = "";
  document.getElementById("course-end").value = "";
  document.querySelectorAll('input[name="course-days"]').forEach(cb => cb.checked = false);
}

// Add Task
function addTask() {
  const name = document.getElementById("task-name")?.value.trim() ?? "";
  const duration = parseInt(document.getElementById("task-duration")?.value ?? "0", 10);
  const dueDate = document.getElementById("task-due-date")?.value ?? "";
  const dueTime = document.getElementById("task-due-time")?.value ?? "23:59";
  const difficulty = document.getElementById("task-difficulty")?.value || "Medium";
  const isExam = document.getElementById("task-exam")?.checked || false;

  if (!name || !duration || !dueDate) { 
    popup("Fill all task fields (name, duration, due date)"); 
    return; 
  }

  // Format due date to ISO format
  const due = formatDateTime(dueDate, dueTime);
  if (!due) {
    popup("Invalid date format. Use MM/DD/YYYY");
    return;
  }

  const color = isExam ? "#E91E63" : "#4CAF50";
  tasks.push({ name, duration, due, difficulty, is_exam: isExam, color });

  const li = document.createElement("li");
  const examLabel = isExam ? " 📝 EXAM" : "";
  li.innerHTML = `<strong>${name}</strong>${examLabel} (${duration} min, ${difficulty}) - Due: ${dueDate} ${dueTime}`;
  document.getElementById("task-list")?.appendChild(li);

  popup("Task added successfully!");
  
  // Clear form
  document.getElementById("task-name").value = "";
  document.getElementById("task-duration").value = "";
  document.getElementById("task-due-date").value = "";
  document.getElementById("task-due-time").value = "23:59";
  document.getElementById("task-difficulty").value = "Medium";
  document.getElementById("task-exam").checked = false;
}

// Add Break
function addBreak() {
  const name = document.getElementById("break-name")?.value.trim() ?? "";
  const startRaw = document.getElementById("break-start")?.value.trim() ?? "";
  const endRaw = document.getElementById("break-end")?.value.trim() ?? "";
  const days = getChecked("break-days");

  const start = normalizeTimeInput(startRaw);
  const end = normalizeTimeInput(endRaw);

  if (!name || !start || !end || days.length === 0) { 
    popup("Fill all break fields with valid times"); 
    return; 
  }

  const color = "#FF9800";
  days.forEach(d => {
    breaks.push({ name, day: d, start, end, color });
    
    calendar.addEvent({ 
      title: name, 
      daysOfWeek: [dayToIndex(d)], 
      startTime: start, 
      endTime: end, 
      backgroundColor: color,
      borderColor: color
    });
  });

  const li = document.createElement("li");
  li.innerHTML = `<strong>${name}</strong> (${days.join(", ")}) ${start}-${end}`;
  document.getElementById("break-list")?.appendChild(li);

  popup("Break added successfully!");
  
  // Clear form
  document.getElementById("break-name").value = "";
  document.getElementById("break-start").value = "";
  document.getElementById("break-end").value = "";
  document.querySelectorAll('input[name="break-days"]').forEach(cb => cb.checked = false);
}

// Add Job (optional)
function addJob() {
  const name = document.getElementById("job-name")?.value.trim() ?? "";
  const startRaw = document.getElementById("job-start")?.value.trim() ?? "";
  const endRaw = document.getElementById("job-end")?.value.trim() ?? "";
  const days = getChecked("job-days");

  const start = normalizeTimeInput(startRaw);
  const end = normalizeTimeInput(endRaw);

  if (!name || !start || !end || days.length === 0) { 
    popup("Fill all job fields with valid times"); 
    return; 
  }

  const color = "#9C27B0";
  jobs.push({ name, days, start, end, color });

  days.forEach(d => {
    calendar.addEvent({ 
      title: `Work: ${name}`, 
      daysOfWeek: [dayToIndex(d)], 
      startTime: start, 
      endTime: end, 
      backgroundColor: color,
      borderColor: color
    });
  });

  const li = document.createElement("li");
  li.innerHTML = `<strong>${name}</strong> (${days.join(", ")}) ${start}-${end}`;
  document.getElementById("job-list")?.appendChild(li);

  popup("Job added successfully!");
  
  // Clear form
  document.getElementById("job-name").value = "";
  document.getElementById("job-start").value = "";
  document.getElementById("job-end").value = "";
  document.querySelectorAll('input[name="job-days"]').forEach(cb => cb.checked = false);
}

// Generate Schedule
async function generate() {
  if (tasks.length === 0) {
    popup("Add at least one task to generate a schedule");
    return;
  }

  // Normalize data for backend
  const normalizedCourses = courses.map(c => ({ 
    name: c.code,
    days: c.days.map(d => DAY_MAP[d] ?? d),
    start: c.start,
    end: c.end
  }));

  const normalizedBreaks = breaks.map(b => ({ 
    name: b.name,
    day: DAY_MAP[b.day] ?? b.day,
    start: b.start,
    end: b.end
  }));

  const normalizedJobs = jobs.map(j => ({
    name: j.name,
    days: j.days.map(d => DAY_MAP[d] ?? d),
    start: j.start,
    end: j.end
  }));

  const payload = { 
    courses: normalizedCourses, 
    tasks: tasks,
    breaks: normalizedBreaks,
    jobs: normalizedJobs,
    commutes: commutes,
    preferences: { 
      wake: "08:00", 
      sleep: "23:00" 
    } 
  };

  console.log("Sending payload:", payload);

  try {
    const res = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Backend error: ${errorText}`);
    }

    const result = await res.json();
    console.log("Received result:", result);

    // Clear calendar and redraw everything
    calendar.removeAllEvents();

    // Add courses back
    normalizedCourses.forEach(c => {
      c.days.forEach(d => {
        calendar.addEvent({ 
          title: c.name, 
          daysOfWeek: [dayToIndex(d)], 
          startTime: c.start, 
          endTime: c.end, 
          backgroundColor: "#1565c0",
          borderColor: "#1565c0"
        });
      });
    });

    // Add breaks back
    normalizedBreaks.forEach(b => {
      calendar.addEvent({ 
        title: b.name, 
        daysOfWeek: [dayToIndex(b.day)], 
        startTime: b.start, 
        endTime: b.end, 
        backgroundColor: "#FF9800",
        borderColor: "#FF9800"
      });
    });

    // Add jobs back
    normalizedJobs.forEach(j => {
      j.days.forEach(d => {
        calendar.addEvent({ 
          title: `Work: ${j.name}`, 
          daysOfWeek: [dayToIndex(d)], 
          startTime: j.start, 
          endTime: j.end, 
          backgroundColor: "#9C27B0",
          borderColor: "#9C27B0"
        });
      });
    });

    // Add scheduled study blocks
    const events = result.events || [];
    events.forEach(e => {
      // Parse the date from the event
      let eventDate = null;
      if (e.date) {
        const [month, day, year] = e.date.split('/');
        eventDate = new Date(year, month - 1, day);
      }

      const color = e.status === 'overdue' ? '#E53935' : 
                   e.status === 'incomplete' ? '#FF9800' : 
                   e.color || '#4CAF50';

      if (eventDate) {
        // Use specific date for one-time events
        const startDateTime = new Date(eventDate);
        const [startHour, startMin] = e.start.split(':');
        startDateTime.setHours(parseInt(startHour), parseInt(startMin));

        const endDateTime = new Date(eventDate);
        const [endHour, endMin] = e.end.split(':');
        endDateTime.setHours(parseInt(endHour), parseInt(endMin));

        calendar.addEvent({
          title: e.title,
          start: startDateTime,
          end: endDateTime,
          backgroundColor: color,
          borderColor: color
        });
      } else {
        // Fallback to recurring events
        calendar.addEvent({
          title: e.title,
          daysOfWeek: [dayToIndex(e.day)],
          startTime: e.start,
          endTime: e.end,
          backgroundColor: color,
          borderColor: color
        });
      }
    });

    // Show summary
    const summary = result.summary || {};
    const summaryMsg = `Schedule Generated!\n\n` +
      `Total Tasks: ${summary.total_tasks || 0}\n` +
      `Successfully Scheduled: ${summary.scheduled || 0}\n` +
      `Incomplete: ${summary.incomplete || 0}\n` +
      `Overdue: ${summary.overdue || 0}`;
    
    popup(summaryMsg);

  } catch (err) {
    console.error("Generation error:", err);
    popup(`Error: ${err.message}\n\nMake sure backend is running:\ncd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000`);
  }
}

// Clear All Data
function clearAll() {
  if (!confirm("Are you sure you want to clear all data? This cannot be undone.")) {
    return;
  }

  courses = [];
  tasks = [];
  breaks = [];
  jobs = [];
  commutes = [];
  
  calendar.removeAllEvents();
  
  document.getElementById("course-list") && (document.getElementById("course-list").innerHTML = "");
  document.getElementById("task-list") && (document.getElementById("task-list").innerHTML = "");
  document.getElementById("break-list") && (document.getElementById("break-list").innerHTML = "");
  document.getElementById("job-list") && (document.getElementById("job-list").innerHTML = "");
  
  popup("All data cleared successfully!");
}

// Expose functions to window for HTML onclick attributes
window.addCourse = addCourse;
window.addTask = addTask;
window.addBreak = addBreak;
window.addJob = addJob;
window.generate = generate;
window.clearAll = clearAll;*/


/*
Smart Study Scheduler - Frontend
Coordinates with backend API to generate intelligent schedules
*/

const API_URL = ""; // Same origin, uses /generate endpoint

let courses = [];
let tasks = [];
let breaks = [];
let jobs = [];
let commutes = [];
let calendar;

const DAY_MAP = { 
  Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", 
  Thu: "Thursday", Fri: "Friday", Sat: "Saturday", Sun: "Sunday" 
};

const DAY_INDEX = { 
  Sunday: 0, Monday: 1, Tuesday: 2, Wednesday: 3, 
  Thursday: 4, Friday: 5, Saturday: 6 
};

// Initialize calendar on page load
document.addEventListener("DOMContentLoaded", () => {
  const el = document.getElementById("calendar");
  if (el && typeof FullCalendar !== "undefined") {
    calendar = new FullCalendar.Calendar(el, {
      initialView: "timeGridWeek",
      allDaySlot: false,
      slotMinTime: "06:00:00",
      slotMaxTime: "24:00:00",
      height: "auto",
      editable: true,
      selectable: true,
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'timeGridWeek,timeGridDay'
      },
      events: [],
      eventClick: function(info) {
        // Show event details on click
        const details = `${info.event.title}\n${info.event.startStr} - ${info.event.endStr}`;
        alert(details);
      }
    });
    calendar.render();
  } else {
    // Fallback if FullCalendar not available
    calendar = { 
      addEvent: () => {}, 
      removeAllEvents: () => {},
      render: () => {}
    };
    console.warn("FullCalendar not initialized or #calendar missing.");
  }
});

// Utility functions
function popup(msg) { 
  alert(msg); 
}

function getChecked(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)]
    .map(e => e.value);
}

function dayToIndex(day) {
  if (!day) return 0;
  if (DAY_INDEX[day] !== undefined) return DAY_INDEX[day];
  return DAY_INDEX[DAY_MAP[day]] ?? 0;
}

function normalizeTimeInput(val) {
  if (!val) return null;
  val = val.trim();
  
  // Handle 24-hour format (HH:MM)
  const m24 = val.match(/^(\d{1,2}):(\d{2})$/);
  if (m24) {
    let hh = parseInt(m24[1], 10);
    const mm = parseInt(m24[2], 10);
    if (hh >= 0 && hh <= 23 && mm >= 0 && mm <= 59) {
      return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
    }
    return null;
  }
  
  // Handle 12-hour format (HH:MM AM/PM)
  const m12 = val.match(/^(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)$/);
  if (m12) {
    let hh = parseInt(m12[1], 10);
    const mm = parseInt(m12[2], 10);
    const ampm = m12[3].toLowerCase();
    
    if (ampm === "pm" && hh < 12) hh += 12;
    if (ampm === "am" && hh === 12) hh = 0;
    
    if (hh >= 0 && hh <= 23 && mm >= 0 && mm <= 59) {
      return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
    }
    return null;
  }
  
  return null;
}

function formatDateTime(dateStr, timeStr) {
  // Convert MM/DD/YYYY and HH:MM to ISO format
  if (!dateStr || !timeStr) return null;
  
  const [month, day, year] = dateStr.split('/');
  if (!month || !day || !year) return null;
  
  return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T${timeStr}:00`;
}

// Add Course
function addCourse() {
  const code = document.getElementById("course-code")?.value.trim() ?? "";
  const startRaw = document.getElementById("course-start")?.value.trim() ?? "";
  const endRaw = document.getElementById("course-end")?.value.trim() ?? "";
  const days = getChecked("course-days");

  const start = normalizeTimeInput(startRaw);
  const end = normalizeTimeInput(endRaw);

  if (!code || !start || !end || days.length === 0) { 
    popup("Fill all course fields with valid times (e.g., 09:00 or 9:00 AM)"); 
    return; 
  }

  const color = "#1565c0";
  courses.push({ code, start, end, days, color });

  const li = document.createElement("li");
  li.innerHTML = `<strong>${code}</strong> (${days.join(", ")}) ${start}-${end}`;
  document.getElementById("course-list")?.appendChild(li);

  // Add to calendar
  days.forEach(d => {
    calendar.addEvent({ 
      title: code, 
      daysOfWeek: [dayToIndex(d)], 
      startTime: start, 
      endTime: end, 
      backgroundColor: color,
      borderColor: color
    });
  });

  popup("Course added successfully!");
  
  // Clear form
  document.getElementById("course-code").value = "";
  document.getElementById("course-start").value = "";
  document.getElementById("course-end").value = "";
  document.querySelectorAll('input[name="course-days"]').forEach(cb => cb.checked = false);
}

// Add Task
function addTask() {
  const name = document.getElementById("task-name")?.value.trim() ?? "";
  const duration = parseInt(document.getElementById("task-duration")?.value ?? "0", 10);
  const dueDate = document.getElementById("task-due-date")?.value ?? "";
  const dueTime = document.getElementById("task-due-time")?.value ?? "23:59";
  const difficulty = document.getElementById("task-difficulty")?.value || "Medium";
  const isExam = document.getElementById("task-exam")?.checked || false;

  if (!name || !duration || !dueDate) { 
    popup("Fill all task fields (name, duration, due date)"); 
    return; 
  }

  // Format due date to ISO format
  const due = formatDateTime(dueDate, dueTime);
  if (!due) {
    popup("Invalid date format. Use MM/DD/YYYY");
    return;
  }

  const color = isExam ? "#E91E63" : "#4CAF50";
  tasks.push({ name, duration, due, difficulty, is_exam: isExam, color });

  const li = document.createElement("li");
  const examLabel = isExam ? " 📝 EXAM" : "";
  li.innerHTML = `<strong>${name}</strong>${examLabel} (${duration} min, ${difficulty}) - Due: ${dueDate} ${dueTime}`;
  document.getElementById("task-list")?.appendChild(li);

  popup("Task added successfully!");
  
  // Clear form
  document.getElementById("task-name").value = "";
  document.getElementById("task-duration").value = "";
  document.getElementById("task-due-date").value = "";
  document.getElementById("task-due-time").value = "23:59";
  document.getElementById("task-difficulty").value = "Medium";
  document.getElementById("task-exam").checked = false;
}

// Add Break
function addBreak() {
  const name = document.getElementById("break-name")?.value.trim() ?? "";
  const startRaw = document.getElementById("break-start")?.value.trim() ?? "";
  const endRaw = document.getElementById("break-end")?.value.trim() ?? "";
  const days = getChecked("break-days");

  const start = normalizeTimeInput(startRaw);
  const end = normalizeTimeInput(endRaw);

  if (!name || !start || !end || days.length === 0) { 
    popup("Fill all break fields with valid times"); 
    return; 
  }

  const color = "#FF9800";
  days.forEach(d => {
    breaks.push({ name, day: d, start, end, color });
    
    calendar.addEvent({ 
      title: name, 
      daysOfWeek: [dayToIndex(d)], 
      startTime: start, 
      endTime: end, 
      backgroundColor: color,
      borderColor: color
    });
  });

  const li = document.createElement("li");
  li.innerHTML = `<strong>${name}</strong> (${days.join(", ")}) ${start}-${end}`;
  document.getElementById("break-list")?.appendChild(li);

  popup("Break added successfully!");
  
  // Clear form
  document.getElementById("break-name").value = "";
  document.getElementById("break-start").value = "";
  document.getElementById("break-end").value = "";
  document.querySelectorAll('input[name="break-days"]').forEach(cb => cb.checked = false);
}

// Add Job (optional)
function addJob() {
  const name = document.getElementById("job-name")?.value.trim() ?? "";
  const startRaw = document.getElementById("job-start")?.value.trim() ?? "";
  const endRaw = document.getElementById("job-end")?.value.trim() ?? "";
  const days = getChecked("job-days");

  const start = normalizeTimeInput(startRaw);
  const end = normalizeTimeInput(endRaw);

  if (!name || !start || !end || days.length === 0) { 
    popup("Fill all job fields with valid times"); 
    return; 
  }

  const color = "#9C27B0";
  jobs.push({ name, days, start, end, color });

  days.forEach(d => {
    calendar.addEvent({ 
      title: `Work: ${name}`, 
      daysOfWeek: [dayToIndex(d)], 
      startTime: start, 
      endTime: end, 
      backgroundColor: color,
      borderColor: color
    });
  });

  const li = document.createElement("li");
  li.innerHTML = `<strong>${name}</strong> (${days.join(", ")}) ${start}-${end}`;
  document.getElementById("job-list")?.appendChild(li);

  popup("Job added successfully!");
  
  // Clear form
  document.getElementById("job-name").value = "";
  document.getElementById("job-start").value = "";
  document.getElementById("job-end").value = "";
  document.querySelectorAll('input[name="job-days"]').forEach(cb => cb.checked = false);
}

// Generate Schedule
async function generate() {
  if (tasks.length === 0) {
    popup("Add at least one task to generate a schedule");
    return;
  }

  // Normalize data for backend
  const normalizedCourses = courses.map(c => ({ 
    name: c.code,
    days: c.days.map(d => DAY_MAP[d] ?? d),
    start: c.start,
    end: c.end
  }));

  const normalizedBreaks = breaks.map(b => ({ 
    name: b.name,
    day: DAY_MAP[b.day] ?? b.day,
    start: b.start,
    end: b.end
  }));

  const normalizedJobs = jobs.map(j => ({
    name: j.name,
    days: j.days.map(d => DAY_MAP[d] ?? d),
    start: j.start,
    end: j.end
  }));

  const payload = { 
    courses: normalizedCourses, 
    tasks: tasks,
    breaks: normalizedBreaks,
    jobs: normalizedJobs,
    commutes: commutes,
    preferences: { 
      wake: "08:00", 
      sleep: "23:00" 
    } 
  };

  console.log("Sending payload:", payload);

  try {
    const res = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Backend error: ${errorText}`);
    }

    const result = await res.json();
    console.log("Received result:", result);

    // Clear calendar and redraw everything
    calendar.removeAllEvents();

    // Add courses back
    normalizedCourses.forEach(c => {
      c.days.forEach(d => {
        calendar.addEvent({ 
          title: c.name, 
          daysOfWeek: [dayToIndex(d)], 
          startTime: c.start, 
          endTime: c.end, 
          backgroundColor: "#1565c0",
          borderColor: "#1565c0"
        });
      });
    });

    // Add breaks back
    normalizedBreaks.forEach(b => {
      calendar.addEvent({ 
        title: b.name, 
        daysOfWeek: [dayToIndex(b.day)], 
        startTime: b.start, 
        endTime: b.end, 
        backgroundColor: "#FF9800",
        borderColor: "#FF9800"
      });
    });

    // Add jobs back
    normalizedJobs.forEach(j => {
      j.days.forEach(d => {
        calendar.addEvent({ 
          title: `Work: ${j.name}`, 
          daysOfWeek: [dayToIndex(d)], 
          startTime: j.start, 
          endTime: j.end, 
          backgroundColor: "#9C27B0",
          borderColor: "#9C27B0"
        });
      });
    });

    // Add scheduled study blocks
    const events = result.events || [];
    events.forEach(e => {
      // Parse the date from the event
      let eventDate = null;
      if (e.date) {
        const [month, day, year] = e.date.split('/');
        eventDate = new Date(year, month - 1, day);
      }

      const color = e.status === 'overdue' ? '#E53935' : 
                   e.status === 'incomplete' ? '#FF9800' : 
                   e.color || '#4CAF50';

      if (eventDate) {
        // Use specific date for one-time events
        const startDateTime = new Date(eventDate);
        const [startHour, startMin] = e.start.split(':');
        startDateTime.setHours(parseInt(startHour), parseInt(startMin));

        const endDateTime = new Date(eventDate);
        const [endHour, endMin] = e.end.split(':');
        endDateTime.setHours(parseInt(endHour), parseInt(endMin));

        calendar.addEvent({
          title: e.title,
          start: startDateTime,
          end: endDateTime,
          backgroundColor: color,
          borderColor: color
        });
      } else {
        // Fallback to recurring events
        calendar.addEvent({
          title: e.title,
          daysOfWeek: [dayToIndex(e.day)],
          startTime: e.start,
          endTime: e.end,
          backgroundColor: color,
          borderColor: color
        });
      }
    });

    // Show summary
    const summary = result.summary || {};
    const summaryMsg = `Schedule Generated!\n\n` +
      `Total Tasks: ${summary.total_tasks || 0}\n` +
      `Successfully Scheduled: ${summary.scheduled || 0}\n` +
      `Incomplete: ${summary.incomplete || 0}\n` +
      `Overdue: ${summary.overdue || 0}`;
    
    popup(summaryMsg);

  } catch (err) {
    console.error("Generation error:", err);
    popup(`Error: ${err.message}\n\nMake sure backend is running:\ncd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000`);
  }
}

// Clear All Data
function clearAll() {
  if (!confirm("Are you sure you want to clear all data? This cannot be undone.")) {
    return;
  }

  courses = [];
  tasks = [];
  breaks = [];
  jobs = [];
  commutes = [];
  
  calendar.removeAllEvents();
  
  document.getElementById("course-list") && (document.getElementById("course-list").innerHTML = "");
  document.getElementById("task-list") && (document.getElementById("task-list").innerHTML = "");
  document.getElementById("break-list") && (document.getElementById("break-list").innerHTML = "");
  document.getElementById("job-list") && (document.getElementById("job-list").innerHTML = "");
  
  popup("All data cleared successfully!");
}

// PDF Generation
async function downloadPDF() {
  if (!calendar || calendar.getEvents().length === 0) {
    popup("Please generate a schedule first before downloading PDF");
    return;
  }

  try {
    // Get all calendar events
    const events = calendar.getEvents();
    
    // Group events by type
    const scheduledTasks = events.filter(e => 
      e.backgroundColor === '#4CAF50' || 
      e.backgroundColor === '#E53935' || 
      e.backgroundColor === '#FF9800'
    );
    const courseEvents = events.filter(e => e.backgroundColor === '#1565c0');
    const breakEvents = events.filter(e => e.backgroundColor === '#FF9800' && !scheduledTasks.includes(e));
    const jobEvents = events.filter(e => e.backgroundColor === '#9C27B0');

    // Create PDF content
    const pdf = await fetch('/api/generate-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tasks: scheduledTasks.map(e => ({
          title: e.title,
          start: e.start || e.startTime,
          end: e.end || e.endTime,
          color: e.backgroundColor
        })),
        courses: courseEvents.map(e => ({
          title: e.title,
          start: e.start || e.startTime,
          end: e.end || e.endTime
        })),
        breaks: breakEvents.map(e => ({
          title: e.title,
          start: e.start || e.startTime,
          end: e.end || e.endTime
        })),
        jobs: jobEvents.map(e => ({
          title: e.title,
          start: e.start || e.startTime,
          end: e.end || e.endTime
        }))
      })
    });

    if (!pdf.ok) {
      throw new Error('PDF generation failed');
    }

    // Download the PDF
    const blob = await pdf.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `StudyTime_Schedule_${new Date().toISOString().split('T')[0]}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    popup("Schedule PDF downloaded successfully!");
  } catch (err) {
    console.error("PDF generation error:", err);
    
    // Fallback: Create a simple text-based schedule
    generateSimplePDF();
  }
}

// Fallback: Client-side PDF generation using print
function generateSimplePDF() {
  // Create a printable view
  const printWindow = window.open('', '', 'width=800,height=600');
  
  if (!printWindow) {
    popup("Please allow pop-ups to download the PDF");
    return;
  }

  const events = calendar.getEvents();
  
  // Sort events by date/time
  const sortedEvents = events.sort((a, b) => {
    const aStart = a.start || new Date();
    const bStart = b.start || new Date();
    return aStart - bStart;
  });

  // Group by date
  const eventsByDate = {};
  sortedEvents.forEach(event => {
    const dateKey = event.start ? event.start.toDateString() : 'Recurring';
    if (!eventsByDate[dateKey]) {
      eventsByDate[dateKey] = [];
    }
    eventsByDate[dateKey].push(event);
  });

  // Build HTML for print
  let html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>StudyTime Schedule</title>
      <style>
        body {
          font-family: Arial, sans-serif;
          padding: 20px;
          max-width: 800px;
          margin: 0 auto;
        }
        h1 {
          color: #667eea;
          border-bottom: 3px solid #667eea;
          padding-bottom: 10px;
        }
        h2 {
          color: #333;
          margin-top: 25px;
          border-bottom: 2px solid #e0e0e0;
          padding-bottom: 8px;
        }
        .event {
          padding: 10px;
          margin: 8px 0;
          border-left: 4px solid;
          background: #f9f9f9;
          page-break-inside: avoid;
        }
        .event-title {
          font-weight: bold;
          font-size: 14px;
        }
        .event-time {
          color: #666;
          font-size: 13px;
        }
        .course { border-left-color: #1565c0; }
        .task { border-left-color: #4CAF50; }
        .break { border-left-color: #FF9800; }
        .job { border-left-color: #9C27B0; }
        .warning { border-left-color: #E53935; background: #ffebee; }
        .legend {
          margin: 20px 0;
          padding: 15px;
          background: #f5f5f5;
          border-radius: 8px;
        }
        .legend-item {
          display: inline-block;
          margin-right: 20px;
          margin-bottom: 5px;
        }
        .legend-color {
          display: inline-block;
          width: 15px;
          height: 15px;
          margin-right: 5px;
          vertical-align: middle;
        }
        @media print {
          body { padding: 10px; }
          .no-print { display: none; }
        }
      </style>
    </head>
    <body>
      <h1>📚 StudyTime Schedule</h1>
      <p>Generated on: ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}</p>
      
      <div class="legend">
        <strong>Legend:</strong><br>
        <div class="legend-item">
          <span class="legend-color" style="background: #4CAF50;"></span>
          Study Sessions
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #1565c0;"></span>
          Courses
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #FF9800;"></span>
          Breaks
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #9C27B0;"></span>
          Work/Job
        </div>
        <div class="legend-item">
          <span class="legend-color" style="background: #E53935;"></span>
          Issues/Warnings
        </div>
      </div>
  `;

  // Add events grouped by date
  Object.keys(eventsByDate).sort().forEach(dateKey => {
    html += `<h2>${dateKey}</h2>`;
    
    eventsByDate[dateKey].forEach(event => {
      const startTime = event.start ? event.start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 
                       (event.startTime || 'Recurring');
      const endTime = event.end ? event.end.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 
                     (event.endTime || '');
      
      let eventClass = 'event ';
      if (event.backgroundColor === '#1565c0') eventClass += 'course';
      else if (event.backgroundColor === '#4CAF50') eventClass += 'task';
      else if (event.backgroundColor === '#FF9800') eventClass += 'break';
      else if (event.backgroundColor === '#9C27B0') eventClass += 'job';
      else if (event.backgroundColor === '#E53935') eventClass += 'warning';
      
      html += `
        <div class="${eventClass}">
          <div class="event-title">${event.title}</div>
          <div class="event-time">${startTime}${endTime ? ' - ' + endTime : ''}</div>
        </div>
      `;
    });
  });

  html += `
      <div class="no-print" style="margin-top: 30px; text-align: center;">
        <button onclick="window.print()" style="padding: 10px 20px; font-size: 16px; cursor: pointer;">
          Print / Save as PDF
        </button>
      </div>
    </body>
    </html>
  `;

  printWindow.document.write(html);
  printWindow.document.close();
  
  // Auto-trigger print dialog after a short delay
  setTimeout(() => {
    printWindow.print();
  }, 500);
}

// Expose functions to window for HTML onclick attributes
window.addCourse = addCourse;
window.addTask = addTask;
window.addBreak = addBreak;
window.addJob = addJob;
window.generate = generate;
window.downloadPDF = downloadPDF;
window.clearAll = clearAll;