// auth-header.js - Simple authentication check and logout
(function() {
  // Check if user is logged in
  function checkAuth() {
    const authToken = localStorage.getItem('authToken');
    const currentPath = window.location.pathname;
    
    // If not on login page and no token, redirect to login
    if (!currentPath.includes('/login') && !authToken) {
      window.location.href = '/login';
      return false;
    }
    
    return true;
  }

  // Logout function
  window.handleLogout = async function() {
    if (!confirm('Are you sure you want to logout?')) {
      return;
    }
    
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
    
    // Clear storage
    localStorage.removeItem('authToken');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    
    // Redirect to login
    window.location.href = '/login';
  };

  // Update user greeting on page load
  document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    
    // Update user greeting if element exists
    const greetingElement = document.querySelector('.user-greeting');
    if (greetingElement) {
      const userName = localStorage.getItem('userName') || 'User';
      greetingElement.textContent = `👋 ${userName}`;
    }
  });
})();