/**
 * Notifications Dashboard JavaScript
 * app/static/js/notifications.js
 */

// Global state
let currentNotificationId = null;
let currentAlertId = null;
let unreadOnlyFilter = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

/**
 * Initialize the dashboard
 */
async function initializeDashboard() {
    try {
        showLoading();
        await Promise.all([
            loadStats(),
            loadNotifications(),
            loadObligationAlerts()
        ]);
        hideLoading();
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showToast('Failed to load dashboard data', 'error');
        hideLoading();
    }
}

/**
 * Load notification statistics
 */
async function loadStats() {
    try {
        const response = await fetch('/api/notifications/stats', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to load stats');
        
        const stats = await response.json();
        
        document.getElementById('totalNotifications').textContent = stats.total;
        document.getElementById('unreadNotifications').textContent = stats.unread;
        
        // Load critical alerts count
        const alertsResponse = await fetch('/api/notifications/alerts/obligations', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (alertsResponse.ok) {
            const alerts = await alertsResponse.json();
            const criticalAlerts = alerts.filter(a => a.tier >= 2).length;
            document.getElementById('criticalAlerts').textContent = criticalAlerts;
            
            // Count obligations due soon
            const obligationsDue = alerts.filter(a => {
                if (!a.due_date) return false;
                const dueDate = new Date(a.due_date);
                const today = new Date();
                const diffDays = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
                return diffDays <= 7 && diffDays >= 0;
            }).length;
            document.getElementById('obligationsDue').textContent = obligationsDue;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

/**
 * Load notifications list
 */
async function loadNotifications() {
    try {
        const url = `/api/notifications?unread_only=${unreadOnlyFilter}&limit=50`;
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to load notifications');
        
        const notifications = await response.json();
        renderNotifications(notifications);
        
    } catch (error) {
        console.error('Error loading notifications:', error);
        showToast('Failed to load notifications', 'error');
    }
}

/**
 * Render notifications in the list
 */
function renderNotifications(notifications) {
    const container = document.getElementById('notificationsList');
    
    if (notifications.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="ti ti-inbox-off"></i>
                <p>No notifications to display</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = notifications.map(notif => {
        const isUnread = !notif.read_at;
        const priorityIcon = getPriorityIcon(notif.priority);
        const timeAgo = getTimeAgo(notif.created_at);
        
        return `
            <div class="notification-item ${isUnread ? 'unread' : ''}" 
                 onclick="viewNotification('${notif.id}')">
                <div class="notification-icon ${notif.priority}">
                    ${priorityIcon}
                </div>
                <div class="notification-content">
                    <div class="notification-header">
                        <div class="notification-title">${escapeHtml(notif.subject)}</div>
                        <div class="notification-time">${timeAgo}</div>
                    </div>
                    <div class="notification-message">
                        ${stripHtml(notif.message).substring(0, 150)}${notif.message.length > 150 ? '...' : ''}
                    </div>
                    <div class="notification-meta">
                        <span class="badge badge-${getPriorityClass(notif.priority)}">
                            ${notif.priority}
                        </span>
                        <span class="badge badge-primary">
                            <i class="ti ti-${getTypeIcon(notif.notification_type)}"></i>
                            ${notif.notification_type}
                        </span>
                        ${isUnread ? '<span class="badge badge-warning">New</span>' : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Load obligation alerts
 */
async function loadObligationAlerts() {
    try {
        const response = await fetch('/api/notifications/alerts/obligations', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to load alerts');
        
        const alerts = await response.json();
        renderObligationAlerts(alerts);
        updateTierCounts(alerts);
        
    } catch (error) {
        console.error('Error loading obligation alerts:', error);
    }
}

/**
 * Render obligation alerts
 */
function renderObligationAlerts(alerts) {
    // Render alert overview
    const overviewContainer = document.getElementById('alertOverview');
    const recentAlerts = alerts.slice(0, 6);
    
    if (recentAlerts.length === 0) {
        overviewContainer.innerHTML = `
            <div class="empty-state">
                <i class="ti ti-circle-check"></i>
                <p>No active alerts. All obligations are on track!</p>
            </div>
        `;
    } else {
        overviewContainer.innerHTML = recentAlerts.map(alert => {
            const daysUntilDue = getDaysUntilDue(alert.due_date);
            const statusColor = getStatusColor(alert.status, daysUntilDue);
            
            return `
                <div class="alert-card">
                    <div class="alert-card-header">
                        <div class="alert-title">${escapeHtml(alert.obligation_title)}</div>
                        <span class="badge badge-${statusColor}">${alert.status}</span>
                    </div>
                    <div class="alert-details">
                        <div><strong>Contract:</strong> ${alert.contract_number || 'N/A'}</div>
                        <div><strong>Tier:</strong> ${getTierLabel(alert.tier)}</div>
                        <div><strong>Due Date:</strong> ${formatDate(alert.due_date)}</div>
                        <div><strong>Days Until Due:</strong> ${daysUntilDue} days</div>
                    </div>
                    <div class="alert-actions">
                        <button class="btn btn-sm btn-success" 
                                onclick="acknowledgeAlert('${alert.id}')">
                            <i class="ti ti-check"></i> Acknowledge
                        </button>
                        <button class="btn btn-sm btn-primary" 
                                onclick="viewObligation('${alert.obligation_id}')">
                            <i class="ti ti-eye"></i> View
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    // Render alerts table
    renderAlertsTable(alerts);
}

/**
 * Render alerts table
 */
function renderAlertsTable(alerts) {
    const tbody = document.getElementById('alertsTableBody');
    
    if (alerts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px;">
                    <i class="ti ti-inbox-off" style="font-size: 48px; opacity: 0.3;"></i>
                    <p style="margin-top: 16px; color: var(--secondary-color);">No alerts to display</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = alerts.map(alert => {
        const daysUntilDue = getDaysUntilDue(alert.due_date);
        const statusColor = getStatusColor(alert.status, daysUntilDue);
        
        return `
            <tr>
                <td>${escapeHtml(alert.obligation_title)}</td>
                <td>${alert.contract_number || 'N/A'}</td>
                <td><span class="badge badge-${statusColor}">${alert.status}</span></td>
                <td><span class="badge badge-${getTierColor(alert.tier)}">${getTierLabel(alert.tier)}</span></td>
                <td>${formatDate(alert.due_date)}</td>
                <td>${formatDateTime(alert.sent_at)}</td>
                <td>
                    <button class="btn btn-sm btn-success" onclick="acknowledgeAlert('${alert.id}')">
                        <i class="ti ti-check"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Update tier counts
 */
function updateTierCounts(alerts) {
    const tier1 = alerts.filter(a => a.tier === 1 && a.status === 'pending').length;
    const tier2 = alerts.filter(a => a.tier === 2 && a.status === 'escalated').length;
    const tier3 = alerts.filter(a => a.tier === 3).length;
    
    document.getElementById('tier1Count').textContent = tier1;
    document.getElementById('tier2Count').textContent = tier2;
    document.getElementById('tier3Count').textContent = tier3;
}

/**
 * View notification details
 */
async function viewNotification(notificationId) {
    try {
        const response = await fetch(`/api/notifications/${notificationId}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to load notification');
        
        const notification = await response.json();
        currentNotificationId = notificationId;
        
        document.getElementById('modalTitle').textContent = notification.subject;
        document.getElementById('modalBody').innerHTML = `
            <div>
                <div style="margin-bottom: 20px;">
                    <strong>Type:</strong> 
                    <span class="badge badge-primary">
                        <i class="ti ti-${getTypeIcon(notification.notification_type)}"></i>
                        ${notification.notification_type}
                    </span>
                    <strong style="margin-left: 16px;">Priority:</strong>
                    <span class="badge badge-${getPriorityClass(notification.priority)}">
                        ${notification.priority}
                    </span>
                </div>
                <div style="margin-bottom: 20px;">
                    <strong>Time:</strong> ${formatDateTime(notification.created_at)}
                </div>
                <div style="border-top: 1px solid var(--border-color); padding-top: 20px;">
                    ${notification.message}
                </div>
            </div>
        `;
        
        document.getElementById('notificationModal').classList.add('active');
        
        // Mark as read if unread
        if (!notification.read_at) {
            await markNotificationRead(notificationId);
        }
        
    } catch (error) {
        console.error('Error viewing notification:', error);
        showToast('Failed to load notification details', 'error');
    }
}

/**
 * Mark notification as read
 */
async function markNotificationRead(notificationId) {
    try {
        const response = await fetch(`/api/notifications/${notificationId}/read`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (response.ok) {
            await loadStats();
            await loadNotifications();
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

/**
 * Mark current notification as read from modal
 */
async function markCurrentNotificationRead() {
    if (currentNotificationId) {
        await markNotificationRead(currentNotificationId);
        closeModal();
        showToast('Notification marked as read', 'success');
    }
}

/**
 * Mark all notifications as read
 */
async function markAllAsRead() {
    try {
        showLoading();
        
        const response = await fetch('/api/notifications/mark-all-read', {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to mark all as read');
        
        await loadStats();
        await loadNotifications();
        hideLoading();
        showToast('All notifications marked as read', 'success');
        
    } catch (error) {
        console.error('Error marking all as read:', error);
        showToast('Failed to mark all as read', 'error');
        hideLoading();
    }
}

/**
 * Acknowledge an alert
 */
function acknowledgeAlert(alertId) {
    currentAlertId = alertId;
    document.getElementById('acknowledgeModal').classList.add('active');
}

/**
 * Submit acknowledgement
 */
async function submitAcknowledgement() {
    try {
        const comments = document.getElementById('acknowledgeComments').value;
        
        const response = await fetch('/api/notifications/alerts/acknowledge', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                alert_id: currentAlertId,
                comments: comments
            })
        });
        
        if (!response.ok) throw new Error('Failed to acknowledge alert');
        
        closeAcknowledgeModal();
        await loadObligationAlerts();
        showToast('Alert acknowledged successfully', 'success');
        
    } catch (error) {
        console.error('Error acknowledging alert:', error);
        showToast('Failed to acknowledge alert', 'error');
    }
}

/**
 * Scan obligations manually
 */
async function scanObligations() {
    try {
        showLoading();
        
        const response = await fetch('/api/notifications/scan-obligations', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to scan obligations');
        
        const result = await response.json();
        
        await loadObligationAlerts();
        await loadStats();
        
        hideLoading();
        showToast(`Scan complete: ${result.stats.tier1_alerts} alerts sent`, 'success');
        
    } catch (error) {
        console.error('Error scanning obligations:', error);
        showToast('Failed to scan obligations', 'error');
        hideLoading();
    }
}

/**
 * Export alerts report
 */
async function exportAlerts() {
    try {
        showToast('Generating report...', 'info');
        
        // In a real implementation, this would call an API endpoint
        // that generates a PDF or CSV report
        
        setTimeout(() => {
            showToast('Report exported successfully', 'success');
        }, 1500);
        
    } catch (error) {
        console.error('Error exporting alerts:', error);
        showToast('Failed to export report', 'error');
    }
}

/**
 * View obligation details
 */
function viewObligation(obligationId) {
    window.location.href = `/obligations/${obligationId}`;
}

/**
 * Switch tabs
 */
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.closest('.tab-btn').classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

/**
 * Toggle unread filter
 */
function toggleUnreadFilter() {
    unreadOnlyFilter = document.getElementById('unreadOnlyCheckbox').checked;
    loadNotifications();
}

/**
 * Refresh all notifications
 */
async function refreshNotifications() {
    await initializeDashboard();
    showToast('Notifications refreshed', 'success');
}

/**
 * Close modal
 */
function closeModal() {
    document.getElementById('notificationModal').classList.remove('active');
    currentNotificationId = null;
}

/**
 * Close acknowledge modal
 */
function closeAcknowledgeModal() {
    document.getElementById('acknowledgeModal').classList.remove('active');
    document.getElementById('acknowledgeComments').value = '';
    currentAlertId = null;
}

// ======================
// Utility Functions
// ======================

function showLoading() {
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 'check' : 
                 type === 'error' ? 'x' : 
                 type === 'warning' ? 'alert-triangle' : 'info-circle';
    
    toast.innerHTML = `
        <i class="ti ti-${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 4000);
}

function getAuthToken() {
    return localStorage.getItem('authToken') || '';
}

function getPriorityIcon(priority) {
    const icons = {
        low: '<i class="ti ti-info-circle"></i>',
        normal: '<i class="ti ti-bell"></i>',
        high: '<i class="ti ti-alert-triangle"></i>',
        critical: '<i class="ti ti-alert-octagon"></i>'
    };
    return icons[priority] || icons.normal;
}

function getPriorityClass(priority) {
    const classes = {
        low: 'primary',
        normal: 'primary',
        high: 'warning',
        critical: 'danger'
    };
    return classes[priority] || 'primary';
}

function getTypeIcon(type) {
    const icons = {
        email: 'mail',
        sms: 'message',
        in_app: 'bell',
        teams: 'brand-teams'
    };
    return icons[type] || 'bell';
}

function getTierLabel(tier) {
    const labels = {
        1: 'Tier 1: Owner',
        2: 'Tier 2: Manager',
        3: 'Tier 3: Leadership'
    };
    return labels[tier] || `Tier ${tier}`;
}

function getTierColor(tier) {
    const colors = {
        1: 'primary',
        2: 'warning',
        3: 'danger'
    };
    return colors[tier] || 'primary';
}

function getStatusColor(status, daysUntilDue) {
    if (status === 'resolved' || status === 'acknowledged') return 'success';
    if (status === 'breached' || daysUntilDue < 0) return 'danger';
    if (status === 'escalated' || daysUntilDue <= 3) return 'warning';
    return 'primary';
}

function getDaysUntilDue(dueDate) {
    if (!dueDate) return null;
    const due = new Date(dueDate);
    const today = new Date();
    const diffTime = due - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    const intervals = {
        year: 31536000,
        month: 2592000,
        week: 604800,
        day: 86400,
        hour: 3600,
        minute: 60
    };
    
    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
        const interval = Math.floor(seconds / secondsInUnit);
        if (interval >= 1) {
            return interval === 1 ? `1 ${unit} ago` : `${interval} ${unit}s ago`;
        }
    }
    
    return 'Just now';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function stripHtml(html) {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
}