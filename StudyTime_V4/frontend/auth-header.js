// auth-header.js - Authentication and Header Management
// Include this script in all protected pages (dashboard, calendar, schedule, preferences)

// ============================================
// Authentication Check
// ============================================
function checkAuth() {
  const authToken = localStorage.getItem('authToken');
  
  // If not on login page and no token, redirect to login
  if (!window.location.pathname.includes('/login') && !authToken) {
    window.location.href = '/login';
    return false;
  }
  
  return true;
}

// ============================================
// Logout Function
// ============================================
async function handleLogout() {
  if (!confirm('Are you sure you want to logout?')) {
    return;
  }
  
  try {
    // Call logout API
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    // Clear local storage
    localStorage.removeItem('authToken');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    
    // Show toast
    showToast('Logged out successfully', 'success');
    
    // Redirect to login
    setTimeout(() => {
      window.location.href = '/login';
    }, 500);
    
  } catch (error) {
    console.error('Logout error:', error);
    
    // Still clear and redirect even if API fails
    localStorage.removeItem('authToken');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    window.location.href = '/login';
  }
}

// ============================================
// Create Header with Logout Button
// ============================================
function createAuthHeader(activePage) {
  const userName = localStorage.getItem('userName') || 'User';
  
  return `
    <header class="header">
      <div class="header-content">
        <div class="logo-section">
          <img src="/static/StudyTime_Logo.png" alt="StudyTime" class="logo" onerror="this.style.display='none'">
        </div>
        <nav class="nav-tabs">
          <button class="nav-tab ${activePage === 'dashboard' ? 'active' : ''}" onclick="window.location.href='/dashboard'">Dashboard</button>
          <button class="nav-tab ${activePage === 'calendar' ? 'active' : ''}" onclick="window.location.href='/calendar'">Calendar</button>
          <button class="nav-tab ${activePage === 'schedule' ? 'active' : ''}" onclick="window.location.href='/schedule'">Schedule</button>
          <button class="nav-tab ${activePage === 'preferences' ? 'active' : ''}" onclick="window.location.href='/preferences'">Preferences</button>
        </nav>
        <div class="header-actions">
          <span class="user-greeting">👋 ${userName}</span>
          <button class="icon-btn" onclick="toggleDarkMode()" title="Toggle dark mode">
            <span class="theme-icon">🌙</span>
          </button>
          <button class="icon-btn logout-btn" onclick="handleLogout()" title="Logout">
            <span class="theme-icon">🚪</span>
          </button>
        </div>
      </div>
    </header>
  `;
}

// ============================================
// Initialize Auth Header
// ============================================
function initAuthHeader(activePage) {
  // Check authentication first
  if (!checkAuth()) {
    return;
  }
  
  // Find header element and replace it
  const existingHeader = document.querySelector('header.header');
  if (existingHeader) {
    existingHeader.outerHTML = createAuthHeader(activePage);
  }
}

// ============================================
// Dark Mode Toggle
// ============================================
function toggleDarkMode() {
  document.body.classList.toggle("dark-mode");
  localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

// Apply dark mode on load
if (localStorage.getItem('darkMode') === 'true') {
  document.body.classList.add('dark-mode');
}

// ============================================
// Toast Notifications (if not already defined)
// ============================================
if (typeof showToast === 'undefined') {
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
}

// ============================================
// Auto-run on page load
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  // Determine active page from URL
  const path = window.location.pathname;
  let activePage = 'dashboard';
  
  if (path.includes('/calendar')) {
    activePage = 'calendar';
  } else if (path.includes('/schedule') || path === '/') {
    activePage = 'schedule';
  } else if (path.includes('/preferences')) {
    activePage = 'preferences';
  }
  
  // Initialize header with auth check
  initAuthHeader(activePage);
});

// Export functions for use in other scripts
window.checkAuth = checkAuth;
window.handleLogout = handleLogout;
window.toggleDarkMode = toggleDarkMode;
