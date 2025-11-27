// =====================================================
// FILE: app/static/js/dashboard.js
// Dashboard JavaScript with Real-time Data Integration
// =====================================================

class DashboardManager {
    constructor() {
        this.statsData = null;
        this.isLoading = false;
        this.init();
    }

    init() {
        this.loadDashboardData();
        this.setupEventListeners();
        this.setupAutoRefresh();
    }

    async loadDashboardData() {
        try {
            this.showLoader();
            
            // Load all dashboard data in parallel
            await Promise.all([
                this.loadStats(),
                this.loadRecentActivity(),
                this.loadUpcomingObligations(),
                this.loadExpiringContracts(),
                this.loadWorkflows(),
                this.loadDocumentStats()
            ]);
            
            this.hideLoader();
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showError('Failed to load dashboard data');
            this.hideLoader();
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/dashboard/stats', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.statsData = result.data;
                this.updateStatsCards();
                this.updateSummaryWidgets();
            } else {
                throw new Error(result.detail || 'Failed to load stats');
            }
        } catch (error) {
            console.error('Error loading stats:', error);
            throw error;
        }
    }

    async loadRecentActivity() {
        try {
            const response = await fetch('/api/dashboard/recent-activity?limit=5', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.updateRecentActivity(result.data);
                }
            }
        } catch (error) {
            console.error('Error loading recent activity:', error);
        }
    }

    async loadUpcomingObligations() {
        try {
            const response = await fetch('/api/dashboard/upcoming-obligations?days=30&limit=5', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.updateUpcomingObligations(result.data);
                }
            }
        } catch (error) {
            console.error('Error loading upcoming obligations:', error);
        }
    }

    async loadExpiringContracts() {
        try {
            // Use the stats data for expiring contracts count
            if (this.statsData) {
                this.updateExpiringContracts(this.statsData.contracts.expiring_soon);
            }
        } catch (error) {
            console.error('Error loading expiring contracts:', error);
        }
    }

    async loadWorkflows() {
        try {
            const response = await fetch('/api/dashboard/pending-approvals?limit=5', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.updateWorkflows(result.data);
                }
            }
        } catch (error) {
            console.error('Error loading workflows:', error);
        }
    }

    async loadDocumentStats() {
        try {
            // For now, we'll use placeholder data since document stats aren't in the API
            // You can extend your API to include document statistics
            const documentStats = {
                total: 156,
                templates: 24,
                storage: '2.4 GB'
            };
            this.updateDocumentStats(documentStats);
        } catch (error) {
            console.error('Error loading document stats:', error);
        }
    }

    updateStatsCards() {
        if (!this.statsData) return;

        const stats = this.statsData;
        
        // Update main stats cards
        this.updateElement('active-contracts-count', stats.contracts.active || 0);
        this.updateElement('pending-contracts-count', stats.contracts.pending || 0);
        this.updateElement('active-projects-count', stats.projects.active || 0);
        this.updateElement('completed-contracts-count', stats.contracts.completed || 0);
        this.updateElement('due-obligations-count', stats.obligations.due_today || 0);
    }

    updateSummaryWidgets() {
        if (!this.statsData) return;

        const stats = this.statsData;
        
        // Update Recent Audit Activity
        this.updateElement('audit-activity-count', stats.activity.recent_count || 0);
        
        // Update AI Risk Analysis (placeholder - you can add this to your API)
        this.updateElement('high-risk-clauses', '3'); // Placeholder
        this.updateElement('compliance-issues', '2'); // Placeholder
        this.updateElement('ai-suggestions', '7'); // Placeholder
        
        // Update Active Workflows
        this.updateElement('pending-approvals-count', stats.workflows.my_pending_approvals || 0);
        this.updateElement('in-review-count', stats.workflows.in_progress || 0);
        this.updateElement('negotiation-phase-count', '2'); // Placeholder
    }

    updateRecentActivity(activities) {
        const container = document.getElementById('recent-activity-list');
        if (!container) return;

        if (activities.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    <i class="ti ti-activity" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>No recent activity</p>
                </div>
            `;
            return;
        }

        container.innerHTML = activities.slice(0, 3).map(activity => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid var(--background-light);">
                <span style="font-size: 0.875rem;">${this.formatActivityDescription(activity)}</span>
                <span style="font-weight: 600; color: var(--primary-color);">
                    ${this.formatTimeAgo(activity.created_at)}
                </span>
            </div>
        `).join('');
    }

    updateUpcomingObligations(obligations) {
        const container = document.getElementById('upcoming-obligations-list');
        if (!container) return;

        if (obligations.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    <i class="ti ti-calendar" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>No upcoming obligations</p>
                </div>
            `;
            return;
        }

        container.innerHTML = obligations.slice(0, 3).map(obligation => {
            const dueInDays = obligation.days_until_due;
            let statusColor = '#22c55e'; // Default green
            
            if (dueInDays < 0) {
                statusColor = '#dc2626'; // Red for overdue
            } else if (dueInDays <= 3) {
                statusColor = '#dc2626'; // Red for urgent
            } else if (dueInDays <= 7) {
                statusColor = '#f59e0b'; // Orange for warning
            }

            return `
                <div style="padding: 0.75rem; background: rgba(${this.hexToRgb(statusColor)}, 0.05); 
                          border-left: 3px solid ${statusColor}; border-radius: 6px; margin-bottom: 0.75rem;">
                    <div style="font-size: 0.875rem; font-weight: 500;">${obligation.title} - ${obligation.contract_title}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
                        Due ${this.formatDueDate(obligation.due_date, dueInDays)}
                    </div>
                </div>
            `;
        }).join('');
    }

    updateExpiringContracts(expiringCount) {
        const container = document.getElementById('expiring-contracts-list');
        if (!container) return;

        // For now, we'll show placeholder data since we don't have individual contract data
        // You can extend your API to return actual expiring contracts
        const placeholderContracts = [
            { title: 'Service Agreement - QE', days: 5 },
            { title: 'Consultancy - Tech Solutions', days: 15 },
            { title: 'NDA - Global Partners', days: 28 }
        ];

        container.innerHTML = placeholderContracts.map(contract => {
            let statusColor = '#22c55e';
            if (contract.days <= 7) statusColor = '#dc2626';
            else if (contract.days <= 14) statusColor = '#f59e0b';

            return `
                <div style="padding: 0.75rem; background: rgba(${this.hexToRgb(statusColor)}, 0.05); 
                          border-left: 3px solid ${statusColor}; border-radius: 6px; margin-bottom: 0.75rem;">
                    <div style="font-size: 0.875rem; font-weight: 500;">${contract.title}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
                        Expires in ${contract.days} days
                    </div>
                </div>
            `;
        }).join('');

        // Update the expiring count in stats if available
        if (expiringCount > 0) {
            this.updateElement('expiring-count', expiringCount);
        }
    }

    updateWorkflows(workflows) {
        const container = document.getElementById('workflows-list');
        if (!container) return;

        // Update counts in the workflow summary
        const pendingCount = workflows.length;
        const inProgressCount = workflows.filter(w => !w.is_overdue).length;
        const overdueCount = workflows.filter(w => w.is_overdue).length;

        this.updateElement('pending-approvals-count', pendingCount);
        this.updateElement('in-review-count', inProgressCount);
        this.updateElement('negotiation-phase-count', overdueCount);

        // You can also display individual workflow items if needed
    }

    updateDocumentStats(stats) {
        this.updateElement('total-documents', stats.total);
        this.updateElement('templates-count', stats.templates);
        this.updateElement('storage-used', stats.storage);
    }

    // Utility Methods
    updateElement(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    formatActivityDescription(activity) {
        // Create a readable description from activity data
        const actionMap = {
            'contract_created': 'Contract Created',
            'contract_updated': 'Contract Updated',
            'contract_deleted': 'Contract Deleted',
            'workflow_started': 'Workflow Started',
            'approval_given': 'Approval Given',
            'obligation_created': 'Obligation Created',
            'obligation_completed': 'Obligation Completed'
        };

        const actionText = actionMap[activity.action] || activity.action.replace('_', ' ').title();
        
        if (activity.description) {
            return activity.description;
        } else if (activity.contract_number) {
            return `${actionText} - Contract ${activity.contract_number}`;
        } else {
            return actionText;
        }
    }

    formatTimeAgo(timestamp) {
        if (!timestamp) return 'Just now';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }

    formatDueDate(dueDate, daysUntilDue) {
        if (daysUntilDue < 0) {
            return `${Math.abs(daysUntilDue)} days ago`;
        } else if (daysUntilDue === 0) {
            return 'today';
        } else if (daysUntilDue === 1) {
            return 'tomorrow';
        } else {
            return `in ${daysUntilDue} days`;
        }
    }

    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? 
            `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` 
            : '34, 197, 94'; // Default green
    }

    getAuthToken() {
        // Get auth token from cookies or localStorage
        // This is a simplified version - adjust based on your auth setup
        return localStorage.getItem('auth_token') || 
               document.cookie.replace(/(?:(?:^|.*;\s*)auth_token\s*=\s*([^;]*).*$)|^.*$/, "$1");
    }

    showLoader() {
        const loader = document.getElementById('dashboardLoader');
        if (loader) {
            loader.style.display = 'flex';
        }
        this.isLoading = true;
    }

    hideLoader() {
        const loader = document.getElementById('dashboardLoader');
        if (loader) {
            loader.style.display = 'none';
        }
        this.isLoading = false;
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="ti ti-${type === 'success' ? 'circle-check' : type === 'error' ? 'alert-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    setupEventListeners() {
        // Refresh button (if you add one)
        const refreshBtn = document.getElementById('refreshDashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadDashboardData());
        }

        // Auto-refresh when tab becomes visible
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !this.isLoading) {
                this.loadDashboardData();
            }
        });
    }

    setupAutoRefresh() {
        // Refresh data every 5 minutes
        setInterval(() => {
            if (!document.hidden && !this.isLoading) {
                this.loadDashboardData();
            }
        }, 5 * 60 * 1000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.dashboardManager = new DashboardManager();
});

// Make functions available globally for HTML onclick handlers
function filterContracts(status) {
    window.location.href = `/contracts?status=${status}`;
}

function viewProjects() {
    window.location.href = '/projects';
}

function viewObligations() {
    window.location.href = '/obligations';
}

function viewAuditTrail() {
    window.location.href = '/audit-trail';
}

function viewAllObligations() {
    window.location.href = '/obligations';
}

function viewAIInsights() {
    window.location.href = '/reports?tab=analytics';
}

function viewExpiringContracts() {
    window.location.href = '/contracts?status=expiring';
}

function viewWorkflows() {
    window.location.href = '/master-workflow';
}

function viewDocuments() {
    window.location.href = '/correspondence';
}