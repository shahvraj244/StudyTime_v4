// StudyTime - Modern JavaScript with Fluid UX
// ============================================

const API_URL = "";
let courses = [];
let tasks = [];
let breaks = [];
let jobs = [];
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
// Toast Notifications
// ============================================

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  toast.innerHTML = `<span class="toast-icon">${icon}</span>${message}`;
  
  container.appendChild(toast);
  
  // Trigger animation
  setTimeout(() => toast.classList.add('show'), 10);
  
  // Remove after 3 seconds
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ============================================
// Loading Overlay
// ============================================

function showLoading() {
  document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
  document.getElementById('loading-overlay').classList.add('hidden');
}

// ============================================
// Calendar Initialization
// ============================================

document.addEventListener("DOMContentLoaded", () => {
  initCalendar();
  loadThemePreference();
  updateCounts();
  setupKeyboardShortcuts();
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
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'timeGridWeek,timeGridDay'
      },
      events: [],
      eventClick: function(info) {
        showEventDetails(info.event);
      }
    });
    calendar.render();
  }
}

function showEventDetails(event) {
  const start = event.start ? event.start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
  const end = event.end ? event.end.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
  alert(`${event.title}\n${start} - ${end}`);
}

// ============================================
// Dark Mode
// ============================================

function toggleDarkMode() {
  document.body.classList.toggle("dark-mode");
  const isDark = document.body.classList.contains("dark-mode");
  localStorage.setItem('darkMode', isDark);
  
  // Update icon
  const icon = document.querySelector('.theme-icon');
  icon.textContent = isDark ? '☀️' : '🌙';
  
  showToast(isDark ? 'Dark mode enabled' : 'Light mode enabled', 'info');
}

function loadThemePreference() {
  const isDark = localStorage.getItem('darkMode') === 'true';
  if (isDark) {
    document.body.classList.add('dark-mode');
    document.querySelector('.theme-icon').textContent = '☀️';
  }
}

// ============================================
// Keyboard Shortcuts
// ============================================

function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Ctrl+D: Toggle dark mode
    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault();
      toggleDarkMode();
    }
    
    // Esc: Close modals
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal:not(.hidden)').forEach(modal => {
        modal.classList.add('hidden');
      });
    }
  });
}

// ============================================
// Helper Functions
// ============================================

function getChecked(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)]
    .map(e => e.value);
}

function dayToIndex(day) {
  return DAY_INDEX[day] !== undefined ? DAY_INDEX[day] : DAY_INDEX[DAY_MAP[day]] || 0;
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
  }
  
  return null;
}

function formatDateTime(dateStr, timeStr) {
  if (!dateStr || !timeStr) return null;
  const [month, day, year] = dateStr.split('/');
  if (!month || !day || !year) return null;
  return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T${timeStr}:00`;
}

function updateCounts() {
  document.getElementById('course-count').textContent = courses.length;
  document.getElementById('task-count').textContent = tasks.length;
  document.getElementById('break-count').textContent = breaks.length;
  document.getElementById('job-count').textContent = jobs.length;
}

function createListItem(text, onDelete) {
  const li = document.createElement("li");
  li.className = "list-item";
  li.innerHTML = `<span class="item-text">${text}</span>`;
  
  const deleteBtn = document.createElement("button");
  deleteBtn.className = "delete-btn";
  deleteBtn.innerHTML = "×";
  deleteBtn.onclick = (e) => {
    e.stopPropagation();
    li.classList.add('removing');
    setTimeout(() => {
      onDelete();
      li.remove();
      updateCounts();
    }, 300);
  };
  
  li.appendChild(deleteBtn);
  return li;
}

// ============================================
// Add Functions
// ============================================

function addCourse() {
  const code = document.getElementById("course-code")?.value.trim();
  const startRaw = document.getElementById("course-start")?.value.trim();
  const endRaw = document.getElementById("course-end")?.value.trim();
  const days = getChecked("course-days");

  const start = normalizeTimeInput(startRaw);
  const end = normalizeTimeInput(endRaw);

  if (!code || !start || !end || days.length === 0) {
    showToast("Please fill all course fields", "error");
    return;
  }

  const course = { code, start, end, days, color: "#1565c0" };
  courses.push(course);

  const li = createListItem(
    `<strong>${code}</strong> (${days.join(", ")}) ${start}-${end}`,
    () => {
      courses = courses.filter(c => c !== course);
      calendar.getEvents().filter(e => e.title === code).forEach(e => e.remove());
    }
  );
  
  document.getElementById("course-list").appendChild(li);

  days.forEach(d => {
    calendar.addEvent({
      title: code,
      daysOfWeek: [dayToIndex(d)],
      startTime: start,
      endTime: end,
      backgroundColor: "#1565c0",
      borderColor: "#1565c0"
    });
  });

  showToast("Course added successfully");
  clearForm(['course-code', 'course-start', 'course-end'], 'course-days');
  updateCounts();
}

function addTask() {
  const name = document.getElementById("task-name")?.value.trim();
  const duration = parseInt(document.getElementById("task-duration")?.value || "0", 10);
  const dueDate = document.getElementById("task-due-date")?.value;
  const dueTime = document.getElementById("task-due-time")?.value || "23:59";
  const difficulty = document.getElementById("task-difficulty")?.value || "Medium";
  const isExam = document.getElementById("task-exam")?.checked || false;

  if (!name || !duration || !dueDate) {
    showToast("Please fill all task fields", "error");
    return;
  }

  const due = formatDateTime(dueDate, dueTime);
  if (!due) {
    showToast("Invalid date format. Use MM/DD/YYYY", "error");
    return;
  }

  const task = { name, duration, due, difficulty, is_exam: isExam };
  tasks.push(task);

  const examLabel = isExam ? " 📝" : "";
  const li = createListItem(
    `<strong>${name}</strong>${examLabel} (${duration}min, ${difficulty}) - ${dueDate}`,
    () => {
      tasks = tasks.filter(t => t !== task);
    }
  );
  
  document.getElementById("task-list").appendChild(li);

  showToast("Assignment added successfully");
  clearForm(['task-name', 'task-duration', 'task-due-date'], null, {
    'task-due-time': '23:59',
    'task-difficulty': 'Medium',
    'task-exam': false
  });
  updateCounts();
}

function addBreak() {
  const name = document.getElementById("break-name")?.value.trim();
  const startRaw = document.getElementById("break-start")?.value.trim();
  const endRaw = document.getElementById("break-end")?.value.trim();
  const days = getChecked("break-days");

  const start = normalizeTimeInput(startRaw);
  const end = normalizeTimeInput(endRaw);

  if (!name || !start || !end || days.length === 0) {
    showToast("Please fill all break fields", "error");
    return;
  }

  days.forEach(d => {
    const breakItem = { name, day: d, start, end };
    breaks.push(breakItem);
    
    calendar.addEvent({
      title: name,
      daysOfWeek: [dayToIndex(d)],
      startTime: start,
      endTime: end,
      backgroundColor: "#FF9800",
      borderColor: "#FF9800"
    });
  });

  const li = createListItem(
    `<strong>${name}</strong> (${days.join(", ")}) ${start}-${end}`,
    () => {
      breaks = breaks.filter(b => b.name !== name);
      calendar.getEvents().filter(e => e.title === name).forEach(e => e.remove());
    }
  );
  
  document.getElementById("break-list").appendChild(li);

  showToast("Break added successfully");
  clearForm(['break-name', 'break-start', 'break-end'], 'break-days');
  updateCounts();
}

function addJob() {
  const name = document.getElementById("job-name")?.value.trim();
  const startRaw = document.getElementById("job-start")?.value.trim();
  const endRaw = document.getElementById("job-end")?.value.trim();
  const days = getChecked("job-days");

  const start = normalizeTimeInput(startRaw);
  const end = normalizeTimeInput(endRaw);

  if (!name || !start || !end || days.length === 0) {
    showToast("Please fill all job fields", "error");
    return;
  }

  const job = { name, days, start, end };
  jobs.push(job);

  days.forEach(d => {
    calendar.addEvent({
      title: `Work: ${name}`,
      daysOfWeek: [dayToIndex(d)],
      startTime: start,
      endTime: end,
      backgroundColor: "#9C27B0",
      borderColor: "#9C27B0"
    });
  });

  const li = createListItem(
    `<strong>${name}</strong> (${days.join(", ")}) ${start}-${end}`,
    () => {
      jobs = jobs.filter(j => j !== job);
      calendar.getEvents().filter(e => e.title === `Work: ${name}`).forEach(e => e.remove());
    }
  );
  
  document.getElementById("job-list").appendChild(li);

  showToast("Job added successfully");
  clearForm(['job-name', 'job-start', 'job-end'], 'job-days');
  updateCounts();
}

function clearForm(inputIds, checkboxName, defaults = {}) {
  inputIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = defaults[id] || '';
  });
  
  if (checkboxName) {
    document.querySelectorAll(`input[name="${checkboxName}"]`).forEach(cb => cb.checked = false);
  }
  
  Object.keys(defaults).forEach(key => {
    const el = document.getElementById(key);
    if (el && typeof defaults[key] === 'boolean') {
      el.checked = defaults[key];
    }
  });
}

// ============================================
// Generate Schedule
// ============================================

async function generate() {
  if (tasks.length === 0) {
    showToast("Add at least one assignment first", "error");
    return;
  }

  showLoading();

  const payload = {
    courses: courses.map(c => ({
      name: c.code,
      days: c.days.map(d => DAY_MAP[d] || d),
      start: c.start,
      end: c.end
    })),
    tasks: tasks,
    breaks: breaks.map(b => ({
      name: b.name,
      day: DAY_MAP[b.day] || b.day,
      start: b.start,
      end: b.end
    })),
    jobs: jobs.map(j => ({
      name: j.name,
      days: j.days.map(d => DAY_MAP[d] || d),
      start: j.start,
      end: j.end
    })),
    commutes: [],
    preferences: { wake: "08:00", sleep: "23:00" }
  };

  try {
    const res = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error("Backend error");

    const result = await res.json();
    calendar.removeAllEvents();

    // Redraw everything
    payload.courses.forEach(c => {
      c.days.forEach(d => {
        calendar.addEvent({
          title: c.name,
          daysOfWeek: [dayToIndex(d)],
          startTime: c.start,
          endTime: c.end,
          backgroundColor: "#1565c0"
        });
      });
    });

    payload.breaks.forEach(b => {
      calendar.addEvent({
        title: b.name,
        daysOfWeek: [dayToIndex(b.day)],
        startTime: b.start,
        endTime: b.end,
        backgroundColor: "#FF9800"
      });
    });

    payload.jobs.forEach(j => {
      j.days.forEach(d => {
        calendar.addEvent({
          title: `Work: ${j.name}`,
          daysOfWeek: [dayToIndex(d)],
          startTime: j.start,
          endTime: j.end,
          backgroundColor: "#9C27B0"
        });
      });
    });

    // Add study sessions
    (result.events || []).forEach(e => {
      if (e.date) {
        const [month, day, year] = e.date.split('/');
        const eventDate = new Date(year, month - 1, day);
        const [startHour, startMin] = e.start.split(':');
        const [endHour, endMin] = e.end.split(':');
        
        const start = new Date(eventDate);
        start.setHours(parseInt(startHour), parseInt(startMin));
        
        const end = new Date(eventDate);
        end.setHours(parseInt(endHour), parseInt(endMin));

        calendar.addEvent({
          title: e.title,
          start: start,
          end: end,
          backgroundColor: e.color || '#4CAF50'
        });
      }
    });

    const summary = result.summary || {};
    showToast(`Schedule generated! ${summary.scheduled || 0} sessions scheduled`, "success");

  } catch (err) {
    showToast("Error generating schedule. Check backend connection.", "error");
  } finally {
    hideLoading();
  }
}

// ============================================
// Other Functions
// ============================================

function clearAll() {
  if (!confirm("Clear all data? This cannot be undone.")) return;

  courses = [];
  tasks = [];
  breaks = [];
  jobs = [];
  
  calendar.removeAllEvents();
  
  ['course-list', 'task-list', 'break-list', 'job-list'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '';
  });
  
  updateCounts();
  showToast("All data cleared", "info");
}

function downloadPDF() {
  showToast("PDF download feature coming soon!", "info");
}

function toggleExamMode() {
  const isExam = document.getElementById("task-exam")?.checked;
  const duration = document.getElementById("task-duration");
  const difficulty = document.getElementById("task-difficulty");
  
  [duration, difficulty].forEach(el => {
    el.disabled = isExam;
    el.style.opacity = isExam ? '0.5' : '1';
  });
}

function showHelp() {
  document.getElementById('help-modal').classList.remove('hidden');
}

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

// Expose to window
window.addCourse = addCourse;
window.addTask = addTask;
window.addBreak = addBreak;
window.addJob = addJob;
window.generate = generate;
window.clearAll = clearAll;
window.downloadPDF = downloadPDF;
window.toggleDarkMode = toggleDarkMode;
window.toggleExamMode = toggleExamMode;
window.showHelp = showHelp;
window.closeModal = closeModal;