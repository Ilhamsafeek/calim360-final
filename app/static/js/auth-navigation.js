/**
 * Authentication-aware Navigation Script
 * This script handles dynamic navigation based on user authentication status
 * Include this in your HTML files to enable auth-aware navigation
 */

// Check authentication status on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
});

// Check if user is authenticated
function checkAuthStatus() {
    const token = localStorage.getItem('access_token');
    const navActions = document.getElementById('navActions');
    
    if (token) {
        // User is authenticated - fetch user info
        fetchUserInfo(token);
    } else {
        // User is not authenticated - show login/register buttons
        showGuestNavigation();
    }
}

// Fetch user information from API
async function fetchUserInfo(token) {
    try {
        const response = await fetch('/api/v1/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            showAuthenticatedNavigation(data.user || data);
        } else {
            // Token is invalid or expired - clear it and show guest navigation
            console.log('Token validation failed');
            localStorage.removeItem('access_token');
            showGuestNavigation();
        }
    } catch (error) {
        console.error('Error fetching user info:', error);
        // On error, assume not authenticated
        localStorage.removeItem('access_token');
        showGuestNavigation();
    }
}

// Show navigation for authenticated users
function showAuthenticatedNavigation(user) {
    const navActions = document.getElementById('navActions');
    
    // Get user display name
    let userName = 'User';
    if (user.first_name) {
        userName = user.first_name;
    } else if (user.full_name) {
        userName = user.full_name.split(' ')[0];
    } else if (user.email) {
        userName = user.email.split('@')[0];
    }
    
    // Determine dashboard URL based on user role
    let dashboardUrl = '/dashboard';
    if (user.user_type === 'admin' || user.role === 'admin') {
        dashboardUrl = '/dashboard/admin';
    } else if (user.user_type === 'client' || user.role === 'client') {
        dashboardUrl = '/dashboard/client';
    } else if (user.user_type === 'employee' || user.role === 'employee') {
        dashboardUrl = '/dashboard/employee';
    }
    
    navActions.innerHTML = `
        <a href="${dashboardUrl}" class="btn btn-ghost">
            <i class="ti ti-layout-dashboard"></i> Dashboard
        </a>
        <div class="user-profile-dropdown show">
            <button class="profile-btn" onclick="toggleProfileDropdown()">
                <i class="ti ti-user"></i>
                <span>${userName}</span>
                <i class="ti ti-chevron-down"></i>
            </button>
            <div class="profile-dropdown-menu" id="profileDropdown">
                <a href="/profile">
                    <i class="ti ti-user"></i>
                    My Profile
                </a>
                <a href="/settings">
                    <i class="ti ti-settings"></i>
                    Settings
                </a>
                <a href="#" onclick="logout(event)">
                    <i class="ti ti-logout"></i>
                    Logout
                </a>
            </div>
        </div>
    `;
}

// Show navigation for guest users (not logged in)
function showGuestNavigation() {
    const navActions = document.getElementById('navActions');
    navActions.innerHTML = `
        <a href="/login" class="btn btn-ghost">
            <i class="ti ti-login"></i> Login
        </a>
        <a href="/register" class="btn btn-primary">
            <i class="ti ti-rocket"></i> Get Started
        </a>
    `;
}

// Toggle profile dropdown menu
function toggleProfileDropdown() {
    const dropdown = document.getElementById('profileDropdown');
    if (dropdown) {
        dropdown.classList.toggle('active');
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('profileDropdown');
    const profileBtn = event.target.closest('.profile-btn');
    
    if (dropdown && !profileBtn && !dropdown.contains(event.target)) {
        dropdown.classList.remove('active');
    }
});

// Logout function
function logout(event) {
    event.preventDefault();
    
    // Clear authentication data
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_data');
    
    // Optionally call logout API endpoint
    const token = localStorage.getItem('access_token');
    if (token) {
        fetch('/api/v1/auth/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        }).catch(err => console.error('Logout API error:', err));
    }
    
    // Redirect to home page
    window.location.href = '/';
}

// Handle product selection on products page
function selectProduct(productType, event) {
    event.preventDefault();
    const token = localStorage.getItem('access_token');
    
    if (token) {
        // User is logged in - redirect to dashboard with product selection
        window.location.href = `/dashboard?product=${productType}`;
    } else {
        // User is not logged in - redirect to registration with product parameter
        window.location.href = `/register?product=${productType}`;
    }
}

// Mobile menu toggle
function toggleMobileMenu() {
    const menu = document.querySelector('.nav-menu');
    if (menu) {
        menu.style.display = menu.style.display === 'flex' ? 'none' : 'flex';
    }
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        checkAuthStatus,
        logout,
        selectProduct,
        toggleMobileMenu,
        toggleProfileDropdown
    };
}