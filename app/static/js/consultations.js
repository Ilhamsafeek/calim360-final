/**
 * app/static/js/consultations.js
 * Frontend JavaScript for My Consultations Page (SCR_058)
 * Connects to FastAPI backend endpoints
 */

class ConsultationsManager {
    constructor() {
        this.currentFilter = 'all';
        this.currentSearch = '';
        this.consultations = [];
        this.stats = {};
        this.init();
    }

    async init() {
        await this.loadStats();
        await this.loadConsultations();
        this.attachEventListeners();
    }

    /**
     * Load consultation statistics
     */
    async loadStats() {
        try {
            const response = await fetch('/api/v1/consultations/my-consultations/stats', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load statistics');
            }

            this.stats = await response.json();
            console.log('Stats loaded:', this.stats); // Debug log
            this.updateStatsDisplay();
        } catch (error) {
            console.error('Error loading stats:', error);
            // Don't show error to user if stats just aren't available
            // this.showError('Failed to load statistics');
        }
    }

    /**
     * Load consultations list with filters
     */
    async loadConsultations(statusFilter = 'all', search = '') {
        try {
            this.showLoading();

            const params = new URLSearchParams();
            if (statusFilter && statusFilter !== 'all') {
                params.append('status_filter', statusFilter);
            }
            if (search) {
                params.append('search', search);
            }
            params.append('limit', '50');
            params.append('offset', '0');

            const url = `/api/v1/consultations/my-consultations?${params.toString()}`;
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('API Error:', errorData);
                throw new Error(errorData.detail || 'Failed to load consultations');
            }

            this.consultations = await response.json();
            console.log('Consultations loaded:', this.consultations.length); // Debug log
            this.renderConsultations();
            this.hideLoading();
        } catch (error) {
            console.error('Error loading consultations:', error);
            this.hideLoading();
            this.showEmptyState('Error loading consultations. Please try again.');
        }
    }

    /**
     * Load detailed consultation information
     */
    async loadConsultationDetail(sessionId) {
        try {
            const response = await fetch(`/api/v1/consultations/my-consultations/${sessionId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load consultation details');
            }

            const detail = await response.json();
            this.showDetailModal(detail);
        } catch (error) {
            console.error('Error loading detail:', error);
            this.showError('Failed to load consultation details');
        }
    }

    /**
     * Cancel a consultation
     */
    async cancelConsultation(sessionId, reason) {
        try {
            const response = await fetch(`/api/v1/consultations/my-consultations/${sessionId}/cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({ reason })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to cancel consultation');
            }

            const result = await response.json();
            this.showSuccess('Consultation cancelled successfully');
            await this.loadConsultations(this.currentFilter, this.currentSearch);
            await this.loadStats();
            this.closeModal('cancelModal');
        } catch (error) {
            console.error('Error cancelling consultation:', error);
            this.showError(error.message);
        }
    }

    /**
     * Submit feedback for a consultation
     */
    async submitFeedback(sessionId, feedbackData) {
        try {
            const response = await fetch(`/api/v1/consultations/my-consultations/${sessionId}/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify(feedbackData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to submit feedback');
            }

            const result = await response.json();
            this.showSuccess('Feedback submitted successfully');
            await this.loadConsultations(this.currentFilter, this.currentSearch);
            this.closeModal('feedbackModal');
        } catch (error) {
            console.error('Error submitting feedback:', error);
            this.showError(error.message);
        }
    }

    /**
     * Download consultation memo
     */
    async downloadMemo(sessionId) {
        try {
            const response = await fetch(`/api/v1/consultations/my-consultations/${sessionId}/memo`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Memo not found');
            }

            const data = await response.json();
            window.open(data.download_url, '_blank');
        } catch (error) {
            console.error('Error downloading memo:', error);
            this.showError('Failed to download memo');
        }
    }

    /**
     * View consultation recording
     */
    async viewRecording(sessionId) {
        try {
            const response = await fetch(`/api/v1/consultations/my-consultations/${sessionId}/recording`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Recording not found');
            }

            const data = await response.json();
            
            // Show recording modal with verification info
            this.showRecordingModal(data);
        } catch (error) {
            console.error('Error loading recording:', error);
            this.showError('Failed to load recording');
        }
    }

    /**
     * Load session messages/chat history
     */
    async loadSessionMessages(sessionId) {
        try {
            const response = await fetch(`/api/v1/consultations/my-consultations/${sessionId}/messages`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load messages');
            }

            const data = await response.json();
            this.renderMessages(data.messages);
        } catch (error) {
            console.error('Error loading messages:', error);
            this.showError('Failed to load chat history');
        }
    }

    /**
     * Render consultations list
     */
    renderConsultations() {
        const container = document.getElementById('consultationsList');
        
        if (!this.consultations || this.consultations.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="ti ti-clipboard-off"></i>
                    <h3>No Consultations Found</h3>
                    <p>You haven't scheduled any consultations yet.</p>
                    <button class="btn btn-primary" onclick="window.location.href='/experts'">
                        Find an Expert
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = this.consultations.map(consultation => `
            <div class="consultation-card" data-session-id="${consultation.session_id || consultation.query_id}">
                <div class="consultation-header">
                    <div class="consultation-main-info">
                        <div class="consultation-title-row">
                            <h3 class="consultation-title">${this.escapeHtml(consultation.subject)}</h3>
                            <span class="consultation-id">${consultation.query_code}</span>
                        </div>
                        <div class="consultation-meta">
                            ${consultation.session_time ? `
                                <div class="meta-item">
                                    <i class="ti ti-calendar"></i>
                                    <span>${this.formatDate(consultation.session_time)}</span>
                                </div>
                            ` : ''}
                            ${consultation.expert_name ? `
                                <div class="meta-item">
                                    <i class="ti ti-user"></i>
                                    <span>${this.escapeHtml(consultation.expert_name)}</span>
                                </div>
                            ` : ''}
                            ${consultation.contract_name ? `
                                <div class="meta-item">
                                    <i class="ti ti-file-text"></i>
                                    <span>${this.escapeHtml(consultation.contract_name)}</span>
                                </div>
                            ` : ''}
                            ${consultation.duration_minutes ? `
                                <div class="meta-item">
                                    <i class="ti ti-clock"></i>
                                    <span>${consultation.duration_minutes} min</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="consultation-badges">
                        <span class="status-badge ${this.getStatusClass(consultation.session_status)}">
                            ${this.getStatusLabel(consultation.session_status)}
                        </span>
                        <span class="priority-badge priority-${consultation.priority}">
                            ${consultation.priority}
                        </span>
                    </div>
                </div>
                
                <div class="consultation-actions">
                    ${this.renderConsultationActions(consultation)}
                </div>
            </div>
        `).join('');

        // Attach click handlers
        this.attachConsultationHandlers();
    }

    /**
     * Render action buttons based on consultation status
     */
    renderConsultationActions(consultation) {
        const actions = [];
        
        // View details - always available
        actions.push(`
            <button class="btn btn-outline btn-sm view-detail" 
                    data-session-id="${consultation.session_id || consultation.query_id}">
                <i class="ti ti-eye"></i> View Details
            </button>
        `);

        // Status-specific actions
        if (consultation.session_status === 'scheduled') {
            actions.push(`
                <button class="btn btn-primary btn-sm join-session"
                        data-session-id="${consultation.session_id}">
                    <i class="ti ti-video"></i> Join Session
                </button>
                <button class="btn btn-outline-danger btn-sm cancel-consultation"
                        data-session-id="${consultation.session_id}">
                    <i class="ti ti-x"></i> Cancel
                </button>
            `);
        }

        if (consultation.session_status === 'completed') {
            if (consultation.memo_file) {
                actions.push(`
                    <button class="btn btn-outline btn-sm download-memo"
                            data-session-id="${consultation.session_id}">
                        <i class="ti ti-download"></i> Download Memo
                    </button>
                `);
            }
            if (consultation.recording_url) {
                actions.push(`
                    <button class="btn btn-outline btn-sm view-recording"
                            data-session-id="${consultation.session_id}">
                        <i class="ti ti-video"></i> View Recording
                    </button>
                `);
            }
            if (!consultation.feedback_rating) {
                actions.push(`
                    <button class="btn btn-primary btn-sm submit-feedback"
                            data-session-id="${consultation.session_id}">
                        <i class="ti ti-star"></i> Submit Feedback
                    </button>
                `);
            }
        }

        return actions.join('');
    }

    /**
     * Update statistics display
     */
    updateStatsDisplay() {
        const totalEl = document.getElementById('totalCount');
        const scheduledEl = document.getElementById('scheduledCount');
        const completedEl = document.getElementById('completedCount');
        const ratingEl = document.getElementById('averageRating');
        
        if (totalEl) totalEl.textContent = this.stats.total_consultations || 0;
        if (scheduledEl) scheduledEl.textContent = this.stats.scheduled || 0;
        if (completedEl) completedEl.textContent = this.stats.completed || 0;
        if (ratingEl) ratingEl.textContent = this.stats.average_rating?.toFixed(1) || '0.0';
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Status filter tabs
        document.querySelectorAll('.status-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const filter = e.currentTarget.dataset.status;
                this.handleFilterChange(filter);
            });
        });

        // Search input
        const searchInput = document.getElementById('searchConsultations');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.currentSearch = e.target.value;
                this.loadConsultations(this.currentFilter, this.currentSearch);
            }, 300));
        }
    }

    /**
     * Attach handlers to consultation cards
     */
    attachConsultationHandlers() {
        // View details
        document.querySelectorAll('.view-detail').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.currentTarget.dataset.sessionId;
                this.loadConsultationDetail(sessionId);
            });
        });

        // Cancel consultation
        document.querySelectorAll('.cancel-consultation').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.currentTarget.dataset.sessionId;
                this.showCancelModal(sessionId);
            });
        });

        // Download memo
        document.querySelectorAll('.download-memo').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.currentTarget.dataset.sessionId;
                this.downloadMemo(sessionId);
            });
        });

        // View recording
        document.querySelectorAll('.view-recording').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.currentTarget.dataset.sessionId;
                this.viewRecording(sessionId);
            });
        });

        // Submit feedback
        document.querySelectorAll('.submit-feedback').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.currentTarget.dataset.sessionId;
                this.showFeedbackModal(sessionId);
            });
        });
    }

    /**
     * Handle filter change
     */
    handleFilterChange(filter) {
        this.currentFilter = filter;
        
        // Update active tab
        document.querySelectorAll('.status-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.status === filter);
        });

        // Load consultations with new filter
        this.loadConsultations(filter, this.currentSearch);
    }

    /**
     * Utility functions
     */
    getAuthToken() {
        return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
    }

    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    getStatusClass(status) {
        const statusMap = {
            'scheduled': 'scheduled',
            'completed': 'completed',
            'in_progress': 'in-progress',
            'cancelled': 'cancelled',
            'pending': 'pending'
        };
        return statusMap[status] || 'pending';
    }

    getStatusLabel(status) {
        const labelMap = {
            'scheduled': 'Scheduled',
            'completed': 'Completed',
            'in_progress': 'In Progress',
            'cancelled': 'Cancelled',
            'pending': 'Pending'
        };
        return labelMap[status] || 'Pending';
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    debounce(func, wait) {
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

    showLoading() {
        const container = document.getElementById('consultationsList');
        container.innerHTML = '<div class="loading-spinner">Loading consultations...</div>';
    }

    hideLoading() {
        // Loading will be replaced by content
    }

    showSuccess(message) {
        // Implement toast notification
        alert(message); // Replace with proper toast
    }

    showError(message) {
        // Implement error toast
        alert('Error: ' + message); // Replace with proper toast
    }

    showDetailModal(detail) {
        // Implement modal display logic
        console.log('Show detail modal:', detail);
    }

    showCancelModal(sessionId) {
        // Implement cancel modal
        const reason = prompt('Please provide a reason for cancellation (optional):');
        if (reason !== null) {
            this.cancelConsultation(sessionId, reason);
        }
    }

    showFeedbackModal(sessionId) {
        // Implement feedback modal
        console.log('Show feedback modal for:', sessionId);
    }

    showRecordingModal(data) {
        // Implement recording player modal
        console.log('Show recording:', data);
    }

    closeModal(modalId) {
        // Implement modal close
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('consultationsList')) {
        window.consultationsManager = new ConsultationsManager();
    }
});