/**
 * Authentication Utilities
 * Handles token refresh and authenticated API calls
 */

// Check if user is authenticated
function isAuthenticated() {
    return !!localStorage.getItem('access_token');
}

// Redirect to login if not authenticated
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login-corporate.html';
        return false;
    }
    return true;
}

// Refresh access token using refresh token
async function refreshAccessToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
        throw new Error('No refresh token available');
    }
    
    try {
        const response = await fetch('http://localhost:8000/api/v1/auth/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken })
        });
        
        if (!response.ok) {
            throw new Error('Token refresh failed');
        }
        
        const data = await response.json();
        localStorage.setItem('access_token', data.access);
        
        return data.access;
    } catch (error) {
        console.error('Token refresh error:', error);
        // Clear tokens and redirect to login
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = '/login-corporate.html';
        throw error;
    }
}

// Make authenticated API call with automatic token refresh
async function authenticatedFetch(url, options = {}) {
    let token = localStorage.getItem('access_token');
    
    // Add authorization header
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };
    
    // First attempt
    let response = await fetch(url, options);
    
    // If 401, try to refresh token and retry
    if (response.status === 401) {
        console.log('Token expired, refreshing...');
        
        try {
            token = await refreshAccessToken();
            
            // Retry with new token
            options.headers['Authorization'] = `Bearer ${token}`;
            response = await fetch(url, options);
        } catch (error) {
            console.error('Failed to refresh token:', error);
            throw error;
        }
    }
    
    return response;
}

// Logout function
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = '/login-corporate.html';
    }
}

// Load user info into page
function loadUserInfo() {
    const user = localStorage.getItem('user');
    
    if (user) {
        const userData = JSON.parse(user);
        const firstName = userData.email.split('@')[0].split('.')[0];
        const initials = firstName.substring(0, 2).toUpperCase();
        
        const userNameEl = document.getElementById('userName');
        const userRoleEl = document.getElementById('userRole');
        const userAvatarEl = document.getElementById('userAvatar');
        
        if (userNameEl) userNameEl.textContent = userData.email;
        if (userRoleEl) userRoleEl.textContent = userData.role || 'Admin';
        if (userAvatarEl) userAvatarEl.textContent = initials;
    }
}

// Initialize auth on page load
if (typeof window !== 'undefined') {
    // Check auth on page load
    if (!window.location.pathname.includes('login')) {
        requireAuth();
        loadUserInfo();
    }
}
