const API_URL = ""; // Same origin

let calendar;

const DAY_MAP = { 
  Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", 
  Thu: "Thursday", Fri: "Friday", Sat: "Saturday", Sun: "Sunday" 
};

const DAY_INDEX = { 
  Sunday: 0, Monday: 1, Tuesday: 2, Wednesday: 3, 
  Thursday: 4, Friday: 5, Saturday: 6 
};

// ============================================
// Initialize App
// ============================================
document.addEventListener("DOMContentLoaded", async () => {
  initCalendar();
  await loadAllData();
});

function initCalendar() {
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
        const details = `${info.event.title}\n${info.event.startStr} - ${info.event.endStr}`;
        alert(details);
      }
    });
    calendar.render();
  }
}

// ============================================
// Load All Data from Database
// ============================================
async function loadAllData() {
  try {
    showLoading(true);
    
    // Load all data from database
    const [courses, tasks, breaks, jobs] = await Promise.all([
      fetch('/api/courses').then(r => r.json()),
      fetch('/api/tasks?completed=false').then(r => r.json()),
      fetch('/api/breaks').then(r => r.json()),
      fetch('/api/jobs').then(r => r.json())
    ]);

    console.log("Loaded from database:", { courses, tasks, breaks, jobs });

    // Clear lists before repopulating
    document.getElementById("course-list").innerHTML = "";
    document.getElementById("task-list").innerHTML = "";
    document.getElementById("break-list").innerHTML = "";
    document.getElementById("job-list").innerHTML = "";

    // Display in UI
    courses.forEach(c => displayCourseInList(c));
    tasks.forEach(t => displayTaskInList(t));
    breaks.forEach(b => displayBreakInList(b));
    jobs.forEach(j => displayJobInList(j));

    // Add to calendar
    courses.forEach(c => addCourseToCalendar(c));
    breaks.forEach(b => addBreakToCalendar(b));
    jobs.forEach(j => addJobToCalendar(j));

    showToast('Data loaded successfully', 'success');
  } catch (error) {
    console.error('Error loading data:', error);
    showToast('Error loading data: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// Helper Functions
// ============================================
function showLoading(show) {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) {
    overlay.classList.toggle('hidden', !show);
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ'}</div>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  
  setTimeout(() => toast.classList.add('show'), 10);
  
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

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
  if (!dateStr || !timeStr) return null;
  
  const [month, day, year] = dateStr.split('/');
  if (!month || !day || !year) return null;
  
  return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T${timeStr}:00`;
}

function createDeleteButton(onClick) {
  const span = document.createElement("span");
  span.textContent = "❌";
  span.className = "delete-btn";
  span.onclick = onClick;
  return span;
}

function createCompleteButton(taskId, taskName) {
  const span = document.createElement("span");
  span.textContent = "✅";
  span.className = "complete-btn";
  span.title = "Mark as complete";
  span.onclick = () => completeTask(taskId, taskName);
  return span;
}

// ============================================
// COURSES
// ============================================
async function addCourse() {
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

  try {
    showLoading(true);

    const response = await fetch('/api/courses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: code,
        days: days.map(d => DAY_MAP[d] || d),
        start: start,
        end: end,
        color: "#1565c0"
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add course');
    }

    const savedCourse = await response.json();
    console.log("Course saved:", savedCourse);

    displayCourseInList(savedCourse);
    addCourseToCalendar(savedCourse);

    // Clear form
    document.getElementById("course-code").value = "";
    document.getElementById("course-start").value = "";
    document.getElementById("course-end").value = "";
    document.querySelectorAll('input[name="course-days"]').forEach(cb => cb.checked = false);

    showToast('Course added successfully!', 'success');
  } catch (error) {
    console.error('Error adding course:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

function displayCourseInList(course) {
  const li = document.createElement("li");
  li.setAttribute('data-id', course.id);
  li.innerHTML = `<strong>${course.name}</strong> (${course.days.join(", ")}) ${course.start}-${course.end}`;
  
  li.appendChild(createDeleteButton(() => deleteCourse(course.id, li)));
  
  document.getElementById("course-list")?.appendChild(li);
}

function addCourseToCalendar(course) {
  course.days.forEach(day => {
    calendar.addEvent({
      id: `course-${course.id}-${day}`,
      title: course.name,
      daysOfWeek: [dayToIndex(day)],
      startTime: course.start,
      endTime: course.end,
      backgroundColor: course.color || "#1565c0",
      borderColor: course.color || "#1565c0"
    });
  });
}

async function deleteCourse(courseId, listItem) {
  if (!confirm('Delete this course?')) return;

  try {
    showLoading(true);
    
    const response = await fetch(`/api/courses/${courseId}`, {
      method: 'DELETE'
    });

    if (!response.ok) throw new Error('Failed to delete course');

    // Remove from calendar
    calendar.getEvents().forEach(e => {
      if (e.id && e.id.startsWith(`course-${courseId}`)) {
        e.remove();
      }
    });

    listItem.remove();
    showToast('Course deleted', 'success');
  } catch (error) {
    console.error('Error deleting course:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// TASKS
// ============================================
async function addTask() {
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

  const due = formatDateTime(dueDate, dueTime);
  if (!due) {
    popup("Invalid date format. Use MM/DD/YYYY");
    return;
  }

  try {
    showLoading(true);

    const response = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name,
        duration: duration,
        due: due,
        difficulty: difficulty,
        is_exam: isExam,
        color: isExam ? "#E91E63" : "#4CAF50"
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add task');
    }

    const savedTask = await response.json();
    console.log("Task saved:", savedTask);

    displayTaskInList(savedTask);

    // Clear form
    document.getElementById("task-name").value = "";
    document.getElementById("task-duration").value = "";
    document.getElementById("task-due-date").value = "";
    document.getElementById("task-due-time").value = "23:59";
    document.getElementById("task-difficulty").value = "Medium";
    document.getElementById("task-exam").checked = false;

    showToast('Task added successfully!', 'success');
  } catch (error) {
    console.error('Error adding task:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

function displayTaskInList(task) {
  const li = document.createElement("li");
  li.setAttribute('data-id', task.id);
  li.className = 'task-item list-item';
  
  const examLabel = task.is_exam ? " 📝 EXAM" : "";
  const dueDate = new Date(task.due).toLocaleDateString();
  const dueTime = new Date(task.due).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  
  const taskInfo = document.createElement("div");
  taskInfo.className = "task-info";
  taskInfo.innerHTML = `<strong>${task.name}</strong>${examLabel} (${task.duration} min, ${task.difficulty}) - Due: ${dueDate} ${dueTime}`;
  
  const buttonGroup = document.createElement("div");
  buttonGroup.className = "task-buttons";
  
  buttonGroup.appendChild(createCompleteButton(task.id, task.name));
  buttonGroup.appendChild(createDeleteButton(() => deleteTask(task.id, li)));
  
  li.appendChild(taskInfo);
  li.appendChild(buttonGroup);
  
  document.getElementById("task-list")?.appendChild(li);
}

async function completeTask(taskId, taskName) {
  if (!confirm(`Mark "${taskName}" as complete?`)) return;

  try {
    showLoading(true);
    
    const response = await fetch(`/api/tasks/${taskId}/complete`, {
      method: 'PATCH'
    });

    if (!response.ok) throw new Error('Failed to mark task as complete');

    const result = await response.json();
    console.log("Task completed:", result);

    // Remove task from list
    const taskItem = document.querySelector(`li[data-id="${taskId}"]`);
    if (taskItem) {
      taskItem.classList.add('completing');
      setTimeout(() => taskItem.remove(), 300);
    }

    // Remove all related study sessions from calendar
    calendar.getEvents().forEach(event => {
      if (event.title && event.title.includes(taskName)) {
        event.remove();
      }
    });

    showToast(`✓ "${taskName}" marked as complete!`, 'success');
    
    // Optionally regenerate schedule automatically
    if (confirm('Task completed! Would you like to regenerate your schedule?')) {
      await generate();
    }
  } catch (error) {
    console.error('Error completing task:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

async function deleteTask(taskId, listItem) {
  if (!confirm('Delete this task?')) return;

  try {
    showLoading(true);
    
    const response = await fetch(`/api/tasks/${taskId}`, {
      method: 'DELETE'
    });

    if (!response.ok) throw new Error('Failed to delete task');

    listItem.remove();
    showToast('Task deleted', 'success');
  } catch (error) {
    console.error('Error deleting task:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// BREAKS
// ============================================
async function addBreak() {
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

  try {
    showLoading(true);

    const promises = days.map(day => 
      fetch('/api/breaks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          day: DAY_MAP[day] || day,
          start: start,
          end: end,
          color: "#FF9800"
        })
      })
    );

    const responses = await Promise.all(promises);
    const savedBreaks = await Promise.all(responses.map(r => r.json()));

    savedBreaks.forEach(b => {
      displayBreakInList(b);
      addBreakToCalendar(b);
    });

    document.getElementById("break-name").value = "";
    document.getElementById("break-start").value = "";
    document.getElementById("break-end").value = "";
    document.querySelectorAll('input[name="break-days"]').forEach(cb => cb.checked = false);

    showToast('Break added successfully!', 'success');
  } catch (error) {
    console.error('Error adding break:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

function displayBreakInList(breakItem) {
  const breakList = document.getElementById("break-list");
  if (!breakList) return;

  const groupKey = `${breakItem.name}-${breakItem.start}-${breakItem.end}`;
  let existingGroup = breakList.querySelector(`[data-group="${groupKey}"]`);

  if (existingGroup) {
    const daysSpan = existingGroup.querySelector('.break-days');
    const currentDays = daysSpan.textContent.split(', ');
    
    if (!currentDays.includes(breakItem.day)) {
      currentDays.push(breakItem.day);
      const dayOrder = {Sunday: 0, Monday: 1, Tuesday: 2, Wednesday: 3, Thursday: 4, Friday: 5, Saturday: 6};
      currentDays.sort((a, b) => dayOrder[a] - dayOrder[b]);
      daysSpan.textContent = currentDays.join(', ');
      
      const ids = existingGroup.getAttribute('data-ids').split(',');
      ids.push(breakItem.id);
      existingGroup.setAttribute('data-ids', ids.join(','));
    }
  } else {
    const li = document.createElement("li");
    li.setAttribute('data-group', groupKey);
    li.setAttribute('data-ids', breakItem.id);
    
    li.innerHTML = `<strong>${breakItem.name}</strong> (<span class="break-days">${breakItem.day}</span>) ${breakItem.start}-${breakItem.end}`;
    
    li.appendChild(createDeleteButton(() => deleteBreakGroup(li)));
    
    breakList.appendChild(li);
  }
}

function addBreakToCalendar(breakItem) {
  calendar.addEvent({
    id: `break-${breakItem.id}`,
    title: breakItem.name,
    daysOfWeek: [dayToIndex(breakItem.day)],
    startTime: breakItem.start,
    endTime: breakItem.end,
    backgroundColor: breakItem.color || "#FF9800",
    borderColor: breakItem.color || "#FF9800"
  });
}

async function deleteBreakGroup(listItem) {
  if (!confirm('Delete all instances of this break?')) return;

  try {
    showLoading(true);
    
    const ids = listItem.getAttribute('data-ids').split(',');
    
    await Promise.all(ids.map(id => 
      fetch(`/api/breaks/${id}`, { method: 'DELETE' })
    ));

    ids.forEach(id => {
      const event = calendar.getEventById(`break-${id}`);
      if (event) event.remove();
    });

    listItem.remove();
    showToast('Break deleted', 'success');
  } catch (error) {
    console.error('Error deleting break:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// JOBS
// ============================================
async function addJob() {
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

  try {
    showLoading(true);

    const response = await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name,
        days: days.map(d => DAY_MAP[d] || d),
        start: start,
        end: end,
        color: "#9C27B0"
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add job');
    }

    const savedJob = await response.json();
    console.log("Job saved:", savedJob);

    displayJobInList(savedJob);
    addJobToCalendar(savedJob);

    document.getElementById("job-name").value = "";
    document.getElementById("job-start").value = "";
    document.getElementById("job-end").value = "";
    document.querySelectorAll('input[name="job-days"]').forEach(cb => cb.checked = false);

    showToast('Job added successfully!', 'success');
  } catch (error) {
    console.error('Error adding job:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

function displayJobInList(job) {
  const li = document.createElement("li");
  li.setAttribute('data-id', job.id);
  li.innerHTML = `<strong>${job.name}</strong> (${job.days.join(", ")}) ${job.start}-${job.end}`;
  
  li.appendChild(createDeleteButton(() => deleteJob(job.id, li)));
  
  document.getElementById("job-list")?.appendChild(li);
}

function addJobToCalendar(job) {
  job.days.forEach(day => {
    calendar.addEvent({
      id: `job-${job.id}-${day}`,
      title: `Work: ${job.name}`,
      daysOfWeek: [dayToIndex(day)],
      startTime: job.start,
      endTime: job.end,
      backgroundColor: job.color || "#9C27B0",
      borderColor: job.color || "#9C27B0"
    });
  });
}

async function deleteJob(jobId, listItem) {
  if (!confirm('Delete this job?')) return;

  try {
    showLoading(true);
    
    const response = await fetch(`/api/jobs/${jobId}`, {
      method: 'DELETE'
    });

    if (!response.ok) throw new Error('Failed to delete job');

    calendar.getEvents().forEach(e => {
      if (e.id && e.id.startsWith(`job-${jobId}`)) {
        e.remove();
      }
    });

    listItem.remove();
    showToast('Job deleted', 'success');
  } catch (error) {
    console.error('Error deleting job:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// GENERATE SCHEDULE
// ============================================
async function generate() {
  try {
    showLoading(true);

    const response = await fetch('/api/schedule/from-database', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate schedule');
    }

    const result = await response.json();
    console.log("Schedule generated:", result);

    calendar.removeAllEvents();

    const [courses, breaks, jobs] = await Promise.all([
      fetch('/api/courses').then(r => r.json()),
      fetch('/api/breaks').then(r => r.json()),
      fetch('/api/jobs').then(r => r.json())
    ]);

    courses.forEach(c => addCourseToCalendar(c));
    breaks.forEach(b => addBreakToCalendar(b));
    jobs.forEach(j => addJobToCalendar(j));

const events = result.events || [];
    events.forEach(e => {
      let eventDate = null;
      if (e.date) {
        const [month, day, year] = e.date.split('/');
        eventDate = new Date(year, month - 1, day);
      }

      const color = e.status === 'overdue' ? '#E53935' : 
                   e.status === 'incomplete' ? '#FF9800' : 
                   e.color || '#4CAF50';

      if (eventDate) {
        // Create ISO string format for FullCalendar
        const year = eventDate.getFullYear();
        const month = String(eventDate.getMonth() + 1).padStart(2, '0');
        const day = String(eventDate.getDate()).padStart(2, '0');
        
        const startISO = `${year}-${month}-${day}T${e.start}:00`;
        const endISO = `${year}-${month}-${day}T${e.end}:00`;

        calendar.addEvent({
          title: e.title,
          start: startISO,
          end: endISO,
          backgroundColor: color,
          borderColor: color
        });
      }
    });

    const summary = result.summary || {};
    const summaryMsg = `Schedule Generated!\n\n` +
      `Total Tasks: ${summary.total_tasks || 0}\n` +
      `Successfully Scheduled: ${summary.scheduled || 0}\n` +
      `Incomplete: ${summary.incomplete || 0}\n` +
      `Overdue: ${summary.overdue || 0}`;
    
    showToast('Schedule generated successfully!', 'success');
    popup(summaryMsg);

  } catch (error) {
    console.error('Generation error:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// CLEAR ALL
// ============================================
async function clearAll() {
  if (!confirm("Are you sure you want to clear ALL data? This cannot be undone.")) {
    return;
  }

  try {
    showLoading(true);

    const response = await fetch('/api/clear-all?confirm=yes', {
      method: 'DELETE'
    });

    if (!response.ok) throw new Error('Failed to clear data');

    calendar.removeAllEvents();
    document.getElementById("course-list").innerHTML = "";
    document.getElementById("task-list").innerHTML = "";
    document.getElementById("break-list").innerHTML = "";
    document.getElementById("job-list").innerHTML = "";

    showToast('All data cleared!', 'success');
  } catch (error) {
    console.error('Error clearing data:', error);
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// PDF GENERATION
// ============================================
async function downloadPDF() {
  if (!calendar || calendar.getEvents().length === 0) {
    popup("Please generate a schedule first before downloading PDF");
    return;
  }

  try {
    showLoading(true);

    const events = calendar.getEvents();
    
    const scheduledTasks = events.filter(e => 
      e.backgroundColor === '#4CAF50' || 
      e.backgroundColor === '#E53935' || 
      (e.backgroundColor === '#FF9800' && e.title.includes('INCOMPLETE'))
    );
    const courseEvents = events.filter(e => e.backgroundColor === '#1565c0');
    const breakEvents = events.filter(e => e.backgroundColor === '#FF9800' && !e.title.includes('INCOMPLETE'));
    const jobEvents = events.filter(e => e.backgroundColor === '#9C27B0');

    const pdf = await fetch('/api/generate-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tasks: scheduledTasks.map(e => ({
          title: e.title,
          start: e.start,
          end: e.end,
          color: e.backgroundColor
        })),
        courses: courseEvents.map(e => ({
          title: e.title,
          start: e.start,
          end: e.end
        })),
        breaks: breakEvents.map(e => ({
          title: e.title,
          start: e.start,
          end: e.end
        })),
        jobs: jobEvents.map(e => ({
          title: e.title,
          start: e.start,
          end: e.end
        }))
      })
    });

    if (!pdf.ok) {
      const errorData = await pdf.json().catch(() => ({detail: 'Unknown error'}));
      throw new Error(errorData.detail || 'PDF generation failed');
    }

    const blob = await pdf.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `StudyTime_Schedule_${new Date().toISOString().split('T')[0]}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    showToast("PDF downloaded!", 'success');
  } catch (error) {
    console.error("PDF error:", error);
    showToast('Error generating PDF: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// Dark Mode
// ============================================
function toggleDarkMode() {
  document.body.classList.toggle("dark-mode");
  localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

if (localStorage.getItem('darkMode') === 'true') {
  document.body.classList.add('dark-mode');
}

// ============================================
// Toggle Exam Mode
// ============================================
function toggleExamMode() {
  const isExam = document.getElementById("task-exam").checked;
  const durationInput = document.getElementById("task-duration");
  
  if (isExam) {
    durationInput.value = "60";
    durationInput.disabled = true;
  } else {
    durationInput.disabled = false;
  }
}
//Save Schedule Function
async function saveSchedule() {
  if (!calendar) {
    popup("Calendar not ready");
    return;
  }

  const events = calendar.getEvents();

  // Only save STUDY TASKS (not courses, jobs, breaks)
  const studySessions = events.filter(e =>
    !e.id?.startsWith('course-') &&
    !e.id?.startsWith('job-') &&
    !e.id?.startsWith('break-')
  );

  if (studySessions.length === 0) {
    popup("No scheduled study sessions to save.");
    return;
  }

  const payload = studySessions.map(e => ({
    title: e.title,
    start: e.start,
    end: e.end,
    color: e.backgroundColor
  }));

  try {
    showLoading(true);

    const response = await fetch('/api/schedule/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessions: payload })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to save schedule");
    }

    showToast("Schedule saved successfully!", "success");
  } catch (error) {
    console.error("Save error:", error);
    showToast("Error saving schedule: " + error.message, "error");
  } finally {
    showLoading(false);
  }
}

// Export functions
window.addCourse = addCourse;
window.addTask = addTask;
window.addBreak = addBreak;
window.addJob = addJob;
window.generate = generate;
window.downloadPDF = downloadPDF;
window.clearAll = clearAll;
window.toggleDarkMode = toggleDarkMode;
window.toggleExamMode = toggleExamMode;
window.saveSchedule = saveSchedule;