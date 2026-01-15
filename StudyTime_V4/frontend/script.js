const API_URL = ""; // Same origin

let calendar;
let scheduledEventIds = {}; // Map FullCalendar event IDs to database IDs

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
  await loadScheduledEvents(); // Load saved schedule
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
      editable: true, // Enable drag and drop
      selectable: true,
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'timeGridWeek,timeGridDay'
      },
      events: [],
      eventClick: function(info) {
        const event = info.event;
        let details = `${event.title}\n\n`;
        details += `Start: ${event.start.toLocaleString()}\n`;
        if (event.end) {
          details += `End: ${event.end.toLocaleString()}\n`;
        }
        if (event.extendedProps.difficulty) {
          details += `Difficulty: ${event.extendedProps.difficulty}\n`;
        }
        if (event.extendedProps.duration) {
          details += `Duration: ${event.extendedProps.duration} min\n`;
        }
        alert(details);
      },
      // 🔑 KEY: Handle event drop (when user drags)
      eventDrop: async function(info) {
        await handleEventMove(info);
      },
      // Handle event resize
      eventResize: async function(info) {
        await handleEventMove(info);
      }
    });
    calendar.render();
  }
}

// ============================================
// Handle Event Drag/Drop
// ============================================
async function handleEventMove(info) {
  const event = info.event;
  
  // Only handle scheduled study sessions (not courses, breaks, jobs)
  if (!event.id || event.id.startsWith('course-') || 
      event.id.startsWith('break-') || event.id.startsWith('job-')) {
    return; // Don't save recurring events
  }
  
  // Get the database ID for this event
  const dbId = scheduledEventIds[event.id];
  if (!dbId) {
    console.warn('No database ID found for event:', event.id);
    return;
  }
  
  // Extract new date and times
  const newDate = event.start;
  const newEnd = event.end || new Date(newDate.getTime() + 60*60*1000);
  
  const dateStr = `${String(newDate.getMonth() + 1).padStart(2, '0')}/${String(newDate.getDate()).padStart(2, '0')}/${newDate.getFullYear()}`;
  const startStr = `${String(newDate.getHours()).padStart(2, '0')}:${String(newDate.getMinutes()).padStart(2, '0')}`;
  const endStr = `${String(newEnd.getHours()).padStart(2, '0')}:${String(newEnd.getMinutes()).padStart(2, '0')}`;
  
  const durationMin = Math.round((newEnd - newDate) / (1000 * 60));
  
  try {
    showLoading(true);
    
    // Update in database
    const response = await fetch(`/api/schedule/events/${dbId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        date: dateStr,
        start: startStr,
        end: endStr,
        duration: durationMin
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to update event');
    }
    
    console.log(`✓ Event moved: ${event.title} -> ${dateStr} ${startStr}`);
    showToast('Event updated successfully!', 'success');
    
  } catch (error) {
    console.error('Error moving event:', error);
    showToast('Error updating event: ' + error.message, 'error');
    
    // Revert the change
    info.revert();
  } finally {
    showLoading(false);
  }
}

// ============================================
// Load Scheduled Events from Database
// ============================================
async function loadScheduledEvents() {
  try {
    const response = await fetch('/api/schedule');
    if (!response.ok) {
      console.log('No saved schedule found');
      return;
    }
    
    const data = await response.json();
    const schedule = data.schedule || [];
    
    console.log('Loading saved schedule:', schedule.length, 'events');
    
    // Clear existing scheduled events from calendar
    calendar.getEvents().forEach(event => {
      if (event.id && event.id.startsWith('scheduled-')) {
        event.remove();
      }
    });
    
    scheduledEventIds = {}; // Reset mapping
    
    // Add scheduled events to calendar
    schedule.forEach(item => {
      const [month, day, year] = item.date.split('/');
      const dateStr = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
      
      const startISO = `${dateStr}T${item.start}:00`;
      const endISO = `${dateStr}T${item.end}:00`;
      
      const eventColor = item.color || '#4CAF50';
      const calendarId = `scheduled-${item.id}`;
      
      const calEvent = calendar.addEvent({
        id: calendarId,
        title: item.title,
        start: startISO,
        end: endISO,
        backgroundColor: eventColor,
        borderColor: eventColor,
        editable: true, // Allow dragging
        extendedProps: {
          type: item.status === 'exam' ? 'Exam' : 'Study',
          duration: item.duration,
          difficulty: item.difficulty,
          status: item.status,
          dbId: item.id
        }
      });
      
      // Store mapping
      scheduledEventIds[calendarId] = item.id;
    });
    
    console.log('✓ Loaded scheduled events');
    
  } catch (error) {
    console.error('Error loading schedule:', error);
  }
}

// ============================================
// Load All Data from Database
// ============================================
async function loadAllData() {
  try {
    showLoading(true);
    
    const [courses, tasks, breaks, jobs] = await Promise.all([
      fetch('/api/courses').then(r => r.json()),
      fetch('/api/tasks?completed=false').then(r => r.json()),
      fetch('/api/breaks').then(r => r.json()),
      fetch('/api/jobs').then(r => r.json())
      
    ]);

    console.log("Loaded from database:", { courses, tasks, breaks, jobs });

    // Clear lists
    document.getElementById("course-list").innerHTML = "";
    document.getElementById("task-list").innerHTML = "";
    document.getElementById("break-list").innerHTML = "";
    document.getElementById("job-list").innerHTML = "";

    // Display in UI
    courses.forEach(c => displayCourseInList(c));
    tasks.forEach(t => displayTaskInList(t));
    breaks.forEach(b => displayBreakInList(b));
    jobs.forEach(j => displayJobInList(j));

    // Add to calendar (recurring events)
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
  
  const m24 = val.match(/^(\d{1,2}):(\d{2})$/);
  if (m24) {
    let hh = parseInt(m24[1], 10);
    const mm = parseInt(m24[2], 10);
    if (hh >= 0 && hh <= 23 && mm >= 0 && mm <= 59) {
      return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
    }
    return null;
  }
  
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
      credentials: 'include',
      body: JSON.stringify({
        name: code,
        days: days.map(d => DAY_MAP[d] || d),
        start: start,
        end: end,
        color: "#1565c0"
      })
    });

    if (!response.ok) throw new Error('Failed to add course');
    const savedCourse = await response.json();
    displayCourseInList(savedCourse);
    addCourseToCalendar(savedCourse);

    document.getElementById("course-code").value = "";
    document.getElementById("course-start").value = "";
    document.getElementById("course-end").value = "";
    document.querySelectorAll('input[name="course-days"]').forEach(cb => cb.checked = false);

    showToast('Course added successfully!', 'success');
  } catch (error) {
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
      borderColor: course.color || "#1565c0",
      editable: false // Courses are fixed
    });
  });
}

async function deleteCourse(courseId, listItem) {
  if (!confirm('Delete this course?')) return;
  try {
    showLoading(true);
    const response = await fetch(`/api/courses/${courseId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete course');
    calendar.getEvents().forEach(e => {
      if (e.id && e.id.startsWith(`course-${courseId}`)) e.remove();
    });
    listItem.remove();
    showToast('Course deleted', 'success');
  } catch (error) {
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
    popup("Fill all task fields"); 
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
      credentials: 'include',
      body: JSON.stringify({
        name, duration, due, difficulty, is_exam: isExam,
        color: isExam ? "#E91E63" : "#4CAF50"
      })
    });

    if (!response.ok) throw new Error('Failed to add task');
    const savedTask = await response.json();
    displayTaskInList(savedTask);

    document.getElementById("task-name").value = "";
    document.getElementById("task-duration").value = "";
    document.getElementById("task-due-date").value = "";
    document.getElementById("task-due-time").value = "23:59";
    document.getElementById("task-difficulty").value = "Medium";
    document.getElementById("task-exam").checked = false;

    showToast('Task added successfully!', 'success');
  } catch (error) {
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
    const response = await fetch(`/api/tasks/${taskId}/complete`, { method: 'PATCH' });
    if (!response.ok) throw new Error('Failed to complete task');

    const taskItem = document.querySelector(`li[data-id="${taskId}"]`);
    if (taskItem) {
      taskItem.classList.add('completing');
      setTimeout(() => taskItem.remove(), 300);
    }

    // Remove related scheduled events
    calendar.getEvents().forEach(event => {
      if (event.title && event.title.includes(taskName)) {
        event.remove();
      }
    });

    showToast(`✓ "${taskName}" completed!`, 'success');
  } catch (error) {
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

async function deleteTask(taskId, listItem) {
  if (!confirm('Delete this task?')) return;
  try {
    showLoading(true);
    const response = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete task');
    listItem.remove();
    showToast('Task deleted', 'success');
  } catch (error) {
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
    popup("Fill all break fields"); 
    return; 
  }

  try {
    showLoading(true);
    const promises = days.map(day => 
      fetch('/api/breaks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          name, day: DAY_MAP[day] || day, start, end, color: "#FF9800"
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
    borderColor: breakItem.color || "#FF9800",
    editable: false
  });
}

async function deleteBreakGroup(listItem) {
  if (!confirm('Delete all instances?')) return;
  try {
    showLoading(true);
    const ids = listItem.getAttribute('data-ids').split(',');
    await Promise.all(ids.map(id => fetch(`/api/breaks/${id}`, { method: 'DELETE' })));
    ids.forEach(id => {
      const event = calendar.getEventById(`break-${id}`);
      if (event) event.remove();
    });
    listItem.remove();
    showToast('Break deleted', 'success');
  } catch (error) {
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
    popup("Fill all job fields"); 
    return; 
  }

  try {
    showLoading(true);
    const response = await fetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        name, days: days.map(d => DAY_MAP[d] || d), start, end, color: "#9C27B0"
      })
    });

    if (!response.ok) throw new Error('Failed to add job');
    const savedJob = await response.json();
    displayJobInList(savedJob);
    addJobToCalendar(savedJob);

    document.getElementById("job-name").value = "";
    document.getElementById("job-start").value = "";
    document.getElementById("job-end").value = "";
    document.querySelectorAll('input[name="job-days"]').forEach(cb => cb.checked = false);

    showToast('Job added successfully!', 'success');
  } catch (error) {
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
      borderColor: job.color || "#9C27B0",
      editable: false
    });
  });
}

async function deleteJob(jobId, listItem) {
  if (!confirm('Delete this job?')) return;
  try {
    showLoading(true);
    const response = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete job');
    calendar.getEvents().forEach(e => {
      if (e.id && e.id.startsWith(`job-${jobId}`)) e.remove();
    });
    listItem.remove();
    showToast('Job deleted', 'success');
  } catch (error) {
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// GENERATE SCHEDULE (Force New Schedule)
// ============================================
async function generate() {
  if (!confirm("Generate a NEW schedule? This will replace your current schedule.")) {
    return;
  }

  try {
    showLoading(true);

    // Force regeneration
    const response = await fetch('/api/schedule/from-database?force=true', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) throw new Error('Failed to generate schedule');
    const result = await response.json();

    // Clear ALL events
    calendar.removeAllEvents();
    scheduledEventIds = {};

    // Reload static events
    const [courses, breaks, jobs] = await Promise.all([
      fetch('/api/courses').then(r => r.json()),
      fetch('/api/breaks').then(r => r.json()),
      fetch('/api/jobs').then(r => r.json())
    ]);

    courses.forEach(c => addCourseToCalendar(c));
    breaks.forEach(b => addBreakToCalendar(b));
    jobs.forEach(j => addJobToCalendar(j));

    // Load new scheduled events
    await loadScheduledEvents();

    const summary = result.summary || {};
    showToast('Schedule generated!', 'success');
    popup(`Schedule Generated!\n\nTotal: ${summary.total_tasks || 0}\nScheduled: ${summary.scheduled || 0}`);

  } catch (error) {
    showToast('Error: ' + error.message, 'error');
  } finally {
    showLoading(false);
  }
}

// ============================================
// CLEAR ALL
// ============================================
async function clearAll() {
  if (!confirm("Clear ALL data? This cannot be undone.")) return;

  try {
    showLoading(true);
    const response = await fetch('/api/clear-all?confirm=yes', { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to clear data');

    calendar.removeAllEvents();
    scheduledEventIds = {};
    document.getElementById("course-list").innerHTML = "";
    document.getElementById("task-list").innerHTML = "";
    document.getElementById("break-list").innerHTML = "";
    document.getElementById("job-list").innerHTML = "";

    showToast('All data cleared!', 'success');
  } catch (error) {
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
    popup("Generate a schedule first");
    return;
  }

  try {
    showLoading(true);
    const events = calendar.getEvents();
    
    const scheduledTasks = events.filter(e => 
      e.id && e.id.startsWith('scheduled-')
    );
    const courseEvents = events.filter(e => e.id && e.id.startsWith('course-'));
    const breakEvents = events.filter(e => e.id && e.id.startsWith('break-'));
    const jobEvents = events.filter(e => e.id && e.id.startsWith('job-'));

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

    if (!pdf.ok) throw new Error('PDF generation failed');

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
    showToast('Error: ' + error.message, 'error');
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

// ============================================
// Save Schedule (Manual - Not Needed Anymore)
// ============================================
async function saveSchedule() {
  showToast("Schedule is auto-saved when you move events!", "info");
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