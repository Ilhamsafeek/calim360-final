// placeholder for: app/static/js/screens/experts/SCR_057_expert_directory.js
// =====================================================
// FILE: app/static/js/screens/experts/SCR_057_expert_directory.js
// EXPERT DIRECTORY FRONTEND WITH BACKEND INTEGRATION
// =====================================================

// Global state
let allExperts = [];
let filteredExperts = [];
let currentFilter = 'all';
let currentSearch = '';

// =====================================================
// INITIALIZATION
// =====================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Expert Directory initialized');
    
    // Load initial data
    loadExpertStats();
    loadExperts();
    
    // Setup event listeners
    setupEventListeners();
});

// =====================================================
// SETUP EVENT LISTENERS
// =====================================================
function setupEventListeners() {
    // Search functionality
    const searchInput = document.getElementById('expertSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }
    
    // Filter tags
    const filterTags = document.querySelectorAll('.filter-tag');
    filterTags.forEach(tag => {
        tag.addEventListener('click', function() {
            handleFilterClick(this);
        });
    });
    
    // Refresh button
    const refreshBtn = document.querySelector('[onclick="refreshExperts()"]');
    if (refreshBtn) {
        refreshBtn.onclick = function(e) {
            e.preventDefault();
            refreshExperts();
        };
    }
}

// =====================================================
// LOAD EXPERT STATISTICS
// =====================================================
async function loadExpertStats() {
    try {
        showLoading('stats');
        
        const response = await fetch('/api/experts/stats', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load statistics');
        }
        
        const data = await response.json();
        updateStatsDisplay(data);
        
    } catch (error) {
        console.error('Error loading stats:', error);
        showToast('Failed to load statistics', 'error');
    } finally {
        hideLoading('stats');
    }
}

// =====================================================
// UPDATE STATISTICS DISPLAY
// =====================================================
function updateStatsDisplay(stats) {
    // Total Experts
    const totalExpertsElem = document.querySelector('.stat-card:nth-child(1) h3');
    if (totalExpertsElem) {
        totalExpertsElem.textContent = stats.total_experts || '0';
    }
    
    // Available Now
    const availableElem = document.querySelector('.stat-card:nth-child(2) h3');
    if (availableElem) {
        availableElem.textContent = stats.available_now || '0';
    }
    
    // Average Response Time
    const responseTimeElem = document.querySelector('.stat-card:nth-child(3) h3');
    if (responseTimeElem) {
        responseTimeElem.textContent = stats.avg_response_time || '< 5 min';
    }
    
    // Platform Rating
    const ratingElem = document.querySelector('.stat-card:nth-child(4) h3');
    if (ratingElem) {
        ratingElem.textContent = `${stats.platform_rating || '4.5'} ⭐`;
    }
}

// =====================================================
// LOAD EXPERTS FROM BACKEND
// =====================================================
// Load Experts from Backend
async function loadExperts() {
    try {
        const grid = document.getElementById('expertsGrid');
        grid.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
        
        // Build query parameters
        const params = new URLSearchParams();
        if (currentSearch) params.append('search', currentSearch);
        
        // Map frontend filter values to backend-compatible values
        if (currentFilter && currentFilter !== 'all') {
            const filterMapping = {
                'qfcra': 'QFCRA',
                'construction': 'Construction',
                'arbitration': 'Arbitration',
                'contracts': 'Contract',
                'compliance': 'Compliance',
                'dispute': 'Dispute'
            };
            params.append('expertise_area', filterMapping[currentFilter] || currentFilter);
        }
        
        params.append('limit', '50');
        
        const response = await fetch(`/api/experts/directory?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load experts');
        }
        
        const data = await response.json();
        console.log('✅ Experts loaded:', data);
        
        if (data.success && data.experts && data.experts.length > 0) {
            allExperts = data.experts;
            renderExperts(allExperts);
        } else {
            renderEmptyState();
        }
        
    } catch (error) {
        console.error('❌ Error loading experts:', error);
        renderEmptyState();
    }
}

// =====================================================
// RENDER EXPERTS GRID
// =====================================================
function renderExperts(experts) {
    const container = document.getElementById('expertsGrid');
    if (!container) {
        console.error('Experts grid container not found');
        return;
    }
    
    if (!experts || experts.length === 0) {
        renderEmptyState();
        return;
    }
    
    container.innerHTML = experts.map(expert => createExpertCard(expert)).join('');
    
    // Add click event listeners to cards
    const expertCards = container.querySelectorAll('.expert-card');
    expertCards.forEach(card => {
        const expertId = card.dataset.expertId;
        
        // Card click - view profile
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.expert-actions')) {
                viewExpertProfile(expertId);
            }
        });
        
        // Action buttons
        const viewBtn = card.querySelector('.view-profile-btn');
        if (viewBtn) {
            viewBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                viewExpertProfile(expertId);
            });
        }
        
        const consultBtn = card.querySelector('.consult-btn');
        if (consultBtn) {
            consultBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                consultWithExpert(expertId);
            });
        }
    });
}

// =====================================================
// CREATE EXPERT CARD HTML
// =====================================================
function createExpertCard(expert) {
    const availabilityClass = expert.is_available ? 'available' : 'busy';
    const availabilityText = expert.is_available ? 'Available' : 'Busy';
    const certificationBadge = expert.qfcra_certified ? '<span class="certification-badge"><i class="ti ti-certificate"></i> QFCRA Certified</span>' : '';
    const verificationBadge = expert.qid_verified ? '<i class="ti ti-shield-check verification-icon" title="QID Verified"></i>' : '';
    
    const expertiseAreas = Array.isArray(expert.expertise_areas) 
        ? expert.expertise_areas.slice(0, 3).map(area => 
            `<span class="expertise-tag">${area}</span>`
          ).join('')
        : '<span class="expertise-tag">General Consultation</span>';
    
    return `
        <div class="expert-card" data-expert-id="${expert.expert_id}">
            <div class="expert-card-header">
                <div class="expert-avatar-wrapper">
                    <img src="${expert.profile_picture || '/static/assets/images/default-avatar.png'}" 
                         alt="${expert.full_name}" 
                         class="expert-avatar"
                         onerror="this.src='/static/assets/images/default-avatar.png'">
                    <span class="availability-badge ${availabilityClass}">${availabilityText}</span>
                </div>
                <div class="expert-basic-info">
                    <h3 class="expert-name">
                        ${expert.full_name}
                        ${verificationBadge}
                    </h3>
                    <p class="expert-title">${expert.job_title || expert.specialization || 'Legal Expert'}</p>
                    ${certificationBadge}
                </div>
            </div>
            
            <div class="expert-card-body">
                <div class="expertise-areas">
                    ${expertiseAreas}
                </div>
                
                <div class="expert-stats-row">
                    <div class="expert-stat">
                        <i class="ti ti-star-filled"></i>
                        <span>${expert.average_rating ? expert.average_rating.toFixed(1) : 'N/A'}</span>
                    </div>
                    <div class="expert-stat">
                        <i class="ti ti-briefcase"></i>
                        <span>${expert.years_of_experience || 0}+ years</span>
                    </div>
                    <div class="expert-stat">
                        <i class="ti ti-users"></i>
                        <span>${expert.total_consultations || 0} consultations</span>
                    </div>
                </div>
                
                ${expert.bio ? `<p class="expert-bio">${truncateText(expert.bio, 120)}</p>` : ''}
            </div>
            
            <div class="expert-card-footer">
                <div class="expert-actions">
                    <button class="btn btn-outline view-profile-btn" title="View Profile">
                        <i class="ti ti-user"></i>
                        View Profile
                    </button>
                    <button class="btn btn-primary consult-btn" title="Book Consultation">
                        <i class="ti ti-message-circle"></i>
                        Consult Now
                    </button>
                </div>
            </div>
        </div>
    `;
}

// =====================================================
// HANDLE SEARCH
// =====================================================
function handleSearch(event) {
    currentSearch = event.target.value.trim();
    console.log('Searching for:', currentSearch);
    loadExperts();
}

// =====================================================
// HANDLE FILTER CLICK
// =====================================================
function handleFilterClick(element) {
    // Remove active class from all tags
    document.querySelectorAll('.filter-tag').forEach(tag => {
        tag.classList.remove('active');
    });
    
    // Add active class to clicked tag
    element.classList.add('active');
    
    // Get filter value
    currentFilter = element.getAttribute('data-filter');
    console.log('Filter changed to:', currentFilter);
    
    // Reload experts with filter
    loadExperts();
}
// =====================================================
// VIEW EXPERT PROFILE
// =====================================================
async function viewExpertProfile(expertId) {
    try {
        const response = await fetch(`/api/experts/profile/${expertId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load expert profile');
        }
        
        const expert = await response.json();
        showExpertProfileModal(expert);
        
    } catch (error) {
        console.error('Error loading expert profile:', error);
        showToast('Failed to load expert profile', 'error');
    }
}

// =====================================================
// SHOW EXPERT PROFILE MODAL
// =====================================================
function showExpertProfileModal(expert) {
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h2 class="modal-title">
                        ${expert.full_name}
                        ${expert.qid_verified ? '<i class="ti ti-shield-check verification-icon"></i>' : ''}
                    </h2>
                    <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                </div>
                <div class="modal-body">
                    <div class="expert-profile-details">
                        <div class="profile-header">
                            <img src="${expert.profile_picture || '/static/assets/images/default-avatar.png'}" 
                                 alt="${expert.full_name}" 
                                 class="profile-avatar-large">
                            <div class="profile-info">
                                <h3>${expert.full_name}</h3>
                                <p>${expert.job_title || expert.specialization}</p>
                                <div class="profile-badges">
                                    ${expert.qfcra_certified ? '<span class="badge badge-success">QFCRA Certified</span>' : ''}
                                    ${expert.is_available ? '<span class="badge badge-info">Available Now</span>' : '<span class="badge badge-warning">Busy</span>'}
                                </div>
                            </div>
                        </div>
                        
                        <div class="profile-section">
                            <h4>About</h4>
                            <p>${expert.bio || 'No bio available.'}</p>
                        </div>
                        
                        <div class="profile-section">
                            <h4>Expertise Areas</h4>
                            <div class="expertise-tags">
                                ${expert.expertise_areas.map(area => `<span class="tag">${area}</span>`).join('')}
                            </div>
                        </div>
                        
                        <div class="profile-stats">
                            <div class="stat">
                                <i class="ti ti-star-filled"></i>
                                <span>${expert.average_rating ? expert.average_rating.toFixed(1) : 'N/A'} Rating</span>
                            </div>
                            <div class="stat">
                                <i class="ti ti-briefcase"></i>
                                <span>${expert.years_of_experience}+ Years Experience</span>
                            </div>
                            <div class="stat">
                                <i class="ti ti-users"></i>
                                <span>${expert.total_consultations} Consultations</span>
                            </div>
                        </div>
                        
                        ${expert.recent_reviews && expert.recent_reviews.length > 0 ? `
                            <div class="profile-section">
                                <h4>Recent Reviews</h4>
                                ${expert.recent_reviews.map(review => `
                                    <div class="review-item">
                                        <div class="review-header">
                                            <span class="reviewer-name">${review.reviewer}</span>
                                            <span class="review-rating">${'⭐'.repeat(review.rating)}</span>
                                        </div>
                                        <p class="review-text">${review.comment || 'No comment provided.'}</p>
                                        <span class="review-date">${formatDate(review.date)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline" onclick="this.closest('.modal').remove()">
                        Close
                    </button>
                    <button type="button" class="btn btn-primary" onclick="consultWithExpert('${expert.expert_id}')">
                        <i class="ti ti-message-circle"></i>
                        Book Consultation
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// =====================================================
// CONSULT WITH EXPERT
// =====================================================
function consultWithExpert(expertId) {
    // Close any open modals
    document.querySelectorAll('.modal').forEach(modal => modal.remove());
    
    // Redirect to Ask an Expert page with pre-selected expert
    window.location.href = `/ask-expert?expert=${expertId}`;
}

// =====================================================
// REFRESH EXPERTS
// =====================================================
function refreshExperts() {
    console.log('Refreshing experts...');
    currentSearch = '';
    currentFilter = 'all';
    
    // Reset search input
    const searchInput = document.getElementById('expertSearch');
    if (searchInput) searchInput.value = '';
    
    // Reset filters
    document.querySelectorAll('.filter-tag').forEach(tag => {
        tag.classList.remove('active');
    });
    document.querySelector('.filter-tag[data-filter="all"]')?.classList.add('active');
    
    // Reload data
    loadExpertStats();
    loadExperts();
    
    showToast('Experts refreshed', 'success');
}

// =====================================================
// RENDER EMPTY STATE
// =====================================================
function renderEmptyState() {
    const container = document.getElementById('expertsGrid');
    if (!container) return;
    
    container.innerHTML = `
        <div class="empty-state">
            <i class="ti ti-users-off"></i>
            <h3>No Experts Found</h3>
            <p>Try adjusting your search or filter criteria</p>
            <button class="btn btn-primary" onclick="refreshExperts()">
                <i class="ti ti-refresh"></i>
                Reset Filters
            </button>
        </div>
    `;
}

// =====================================================
// UTILITY FUNCTIONS
// =====================================================

function getAuthToken() {
    return localStorage.getItem('access_token') || 
           sessionStorage.getItem('access_token') || '';
}

function showLoading(section) {
    const loadingHTML = '<div class="loading-spinner"><i class="ti ti-loader rotating"></i> Loading...</div>';
    
    if (section === 'experts') {
        const container = document.getElementById('expertsGrid');
        if (container) container.innerHTML = loadingHTML;
    }
}

function hideLoading(section) {
    // Loading is automatically hidden when content is rendered
}

function showToast(message, type = 'info') {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="ti ti-${type === 'success' ? 'check' : type === 'error' ? 'alert-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for global access
window.refreshExperts = refreshExperts;
window.viewExpertProfile = viewExpertProfile;
window.consultWithExpert = consultWithExpert;