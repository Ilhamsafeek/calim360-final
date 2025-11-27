/**
 * Contract Actions Router
 * Handles navigation from dashboard/list to contract edit page with appropriate modal context
 * File: app/static/js/contract-actions.js
 */

// Action type to modal mapping
const ACTION_MODAL_MAP = {
    'workflow-setup': 'contractWorkflowModal',
    'workflow': 'contractWorkflowModal',
    'send-review': 'internalReviewModal',
    'review': 'internalReviewModal',
    'submit-review': 'internalReviewModal',
    'risk-analysis': 'riskAnalysisModal',
    'ai-analysis': 'riskAnalysisModal',
    'clause-analysis': 'clauseSuggestionModal',
    'signature': 'signatureModal',
    'sign': 'signatureModal',
    'initiate-signature': 'signatureModal',
    'audit-trail': 'auditTrailModal',
    'audit': 'auditTrailModal',
    'negotiation': 'edit', // Just edit, no modal
    'edit': 'edit'
};

// Status-based default actions
const STATUS_DEFAULT_ACTIONS = {
    'Draft': 'edit',
    'InReview': 'send-review',
    'Negotiation': 'edit',
    'PendingApproval': 'workflow-setup',
    'Approved': 'signature',
    'PendingSignature': 'signature',
    'Executed': 'view',
    'Expired': 'view'
};

/**
 * Navigate to contract edit page with action context
 * @param {string} contractId - Contract ID
 * @param {string} action - Action to perform (workflow, review, signature, etc.)
 * @param {object} options - Additional options
 */
function navigateToContract(contractId, action = 'edit', options = {}) {
    if (!contractId) {
        console.error('Contract ID is required');
        return;
    }

    // Build URL with action parameter
    const url = new URL(`/contract/edit/${contractId}`, window.location.origin);
    
    // Add action parameter
    if (action && action !== 'edit') {
        url.searchParams.set('action', action);
    }
    
    // Add additional parameters
    if (options.stage) {
        url.searchParams.set('stage', options.stage);
    }
    if (options.party) {
        url.searchParams.set('party', options.party);
    }
    if (options.tab) {
        url.searchParams.set('tab', options.tab);
    }
    
    // Navigate
    window.location.href = url.toString();
}

/**
 * Contract action handlers - called from dashboard
 */

function createNewContract() {
    window.location.href = '/contract/create';
}

function viewContract(id) {
    navigateToContract(id, 'view');
}

function editContract(id) {
    navigateToContract(id, 'edit');
}

function deleteContract(id) {
    if (confirm('Are you sure you want to delete this contract? This action cannot be undone.')) {
        // Call API to delete
        fetch(`/api/contracts/${id}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.ok) {
                showNotification('Contract deleted successfully', 'success');
                // Reload page or remove from list
                setTimeout(() => window.location.reload(), 1500);
            } else {
                throw new Error('Delete failed');
            }
        })
        .catch(error => {
            console.error('Error deleting contract:', error);
            showNotification('Failed to delete contract', 'error');
        });
    }
}

function viewNegotiation(id) {
    navigateToContract(id, 'negotiation');
}

function sendToCounterparty(id) {
    window.location.href = `/contract/invite/${id}`;
}

function viewWorkflow(id) {
    navigateToContract(id, 'workflow-setup');
}

function initiateSignature(id) {
    navigateToContract(id, 'signature', { party: 'initiator' });
}

function downloadContract(id) {
    // Show loading notification
    showNotification('Preparing download...', 'info');
    
    // Create a temporary link element for download
    const link = document.createElement('a');
    link.href = `/api/contract/download/${id}`;
    link.download = `contract-${id}.pdf`; // Suggest filename
    link.style.display = 'none';
    
    // Append to body, click, and remove
    document.body.appendChild(link);
    link.click();
    
    // Clean up
    setTimeout(() => {
        document.body.removeChild(link);
        showNotification('Download started successfully', 'success');
    }, 500);
}

function viewAuditTrail(id) {
    // Create and show audit trail modal
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'auditTrailModalPopup';
    modal.style.display = 'block';
    
    modal.innerHTML = `
        <div class="modal-content modal-lg" style="max-width: 800px;">
            <div class="modal-header" style="background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)); color: white; padding: 1.5rem; border-radius: 12px 12px 0 0;">
                <h3 class="modal-title" style="color: white; display: flex; align-items: center; gap: 0.75rem; margin: 0;">
                    <i class="ti ti-timeline"></i>
                    Audit Trail - Contract ${id}
                </h3>
                <button class="modal-close" onclick="closeAuditTrailPopup()" style="background: rgba(255,255,255,0.2); color: white; border: none; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                    <i class="ti ti-x"></i>
                </button>
            </div>
            
            <div class="modal-body" style="padding: 2rem; max-height: 500px; overflow-y: auto;">
                <div class="audit-timeline">
                    
                    <div class="audit-event">
                        <div class="audit-icon" style="background: var(--primary-color); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;">
                            <i class="ti ti-file-plus"></i>
                        </div>
                        <div class="audit-content" style="flex: 1; background: var(--background-light); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <strong>Contract Created</strong>
                                <span style="font-size: 0.875rem; color: var(--text-muted);">2 hours ago</span>
                            </div>
                            <div style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.25rem;">
                                <i class="ti ti-user"></i> John Doe
                            </div>
                            <p style="font-size: 0.875rem; margin: 0.5rem 0 0 0;">Contract draft created from template</p>
                        </div>
                    </div>
                    
                    <div class="audit-event">
                        <div class="audit-icon" style="background: var(--info-color); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;">
                            <i class="ti ti-edit"></i>
                        </div>
                        <div class="audit-content" style="flex: 1; background: var(--background-light); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <strong>Content Modified</strong>
                                <span style="font-size: 0.875rem; color: var(--text-muted);">1 hour ago</span>
                            </div>
                            <div style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.25rem;">
                                <i class="ti ti-user"></i> John Doe
                            </div>
                            <p style="font-size: 0.875rem; margin: 0.5rem 0 0 0;">Updated payment terms in Section 2</p>
                        </div>
                    </div>
                    
                    <div class="audit-event">
                        <div class="audit-icon" style="background: var(--secondary-color); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;">
                            <i class="ti ti-eye"></i>
                        </div>
                        <div class="audit-content" style="flex: 1; background: var(--background-light); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <strong>Internal Review</strong>
                                <span style="font-size: 0.875rem; color: var(--text-muted);">45 minutes ago</span>
                            </div>
                            <div style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.25rem;">
                                <i class="ti ti-user"></i> Jane Smith
                            </div>
                            <p style="font-size: 0.875rem; margin: 0.5rem 0 0 0;">Legal team review completed</p>
                        </div>
                    </div>
                    
                    <div class="audit-event">
                        <div class="audit-icon" style="background: var(--success-color); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;">
                            <i class="ti ti-circle-check"></i>
                        </div>
                        <div class="audit-content" style="flex: 1; background: var(--background-light); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <strong>Approved</strong>
                                <span style="font-size: 0.875rem; color: var(--text-muted);">30 minutes ago</span>
                            </div>
                            <div style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.25rem;">
                                <i class="ti ti-user"></i> Michael Johnson
                            </div>
                            <p style="font-size: 0.875rem; margin: 0.5rem 0 0 0;">Contract approved by Legal Department</p>
                        </div>
                    </div>
                    
                    <div class="audit-event">
                        <div class="audit-icon" style="background: var(--primary-color); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;">
                            <i class="ti ti-send"></i>
                        </div>
                        <div class="audit-content" style="flex: 1; background: var(--background-light); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <strong>Sent to Counterparty</strong>
                                <span style="font-size: 0.875rem; color: var(--text-muted);">15 minutes ago</span>
                            </div>
                            <div style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.25rem;">
                                <i class="ti ti-user"></i> John Doe
                            </div>
                            <p style="font-size: 0.875rem; margin: 0.5rem 0 0 0;">Contract sent to Qatar Energy Company for review</p>
                        </div>
                    </div>
                    
                    
                </div>
            </div>
            
            <div class="modal-footer" style="padding: 1.5rem; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                <button class="btn btn-primary" onclick="closeAuditTrailPopup()" style="padding: 0.5rem 1.5rem; background: var(--primary-color); color: white; border: none; border-radius: 8px; cursor: pointer;">
                    Close
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
}

// Close audit trail popup
function closeAuditTrailPopup() {
    const modal = document.getElementById('auditTrailModalPopup');
    if (modal) {
        modal.remove();
    }
    document.body.style.overflow = 'auto';
}

function viewObligations(id) {
    window.location.href = `/contract/obligations/${id}`;
}

function sendForReview(id) {
    navigateToContract(id, 'send-review');
}

function submitForReview(id) {
    navigateToContract(id, 'submit-review');
}

function continueEditing(id) {
    navigateToContract(id, 'edit');
}

function renewContract(id) {
    if (confirm('Are you sure you want to renew this contract? This will create a new draft based on the current contract.')) {
        showNotification('Preparing contract renewal...', 'info');
        
        // Call API to create renewal
        fetch(`/api/contract/${id}/renew`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Renewal failed');
            }
        })
        .then(data => {
            showNotification('Contract renewed successfully!', 'success');
            // Navigate to the new contract
            if (data.new_contract_id) {
                setTimeout(() => {
                    window.location.href = `/contract/edit/${data.new_contract_id}`;
                }, 1500);
            } else {
                setTimeout(() => window.location.reload(), 1500);
            }
        })
        .catch(error => {
            console.error('Error renewing contract:', error);
            showNotification('Failed to renew contract. Please try again.', 'error');
        });
    }
}

function archiveContract(id) {
    if (confirm('Are you sure you want to archive this contract?')) {
        fetch(`/api/contract/${id}/archive`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.ok) {
                showNotification('Contract archived successfully', 'success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                throw new Error('Archive failed');
            }
        })
        .catch(error => {
            console.error('Error archiving contract:', error);
            showNotification('Failed to archive contract', 'error');
        });
    }
}

function viewHistory(id) {
    navigateToContract(id, 'history');
}

// Additional action handlers for AI and workflow
function performRiskAnalysis(id) {
    navigateToContract(id, 'risk-analysis');
}

function performClauseAnalysis(id) {
    navigateToContract(id, 'clause-analysis');
}

function setupWorkflow(id) {
    navigateToContract(id, 'workflow-setup');
}

/**
 * Smart action based on contract status
 * Determines the most appropriate action based on current status
 */
function smartAction(id, status) {
    const action = STATUS_DEFAULT_ACTIONS[status] || 'edit';
    navigateToContract(id, action);
}

/**
 * Show notification helper
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? 'var(--success-color)' : 
                     type === 'error' ? 'var(--danger-color)' : 
                     'var(--primary-color)'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    const icon = type === 'success' ? 'ti-check' : 
                 type === 'error' ? 'ti-x' : 'ti-info-circle';
    
    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <i class="ti ${icon}"></i>
            ${message}
        </div>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add slide animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
    
    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
    
    /* Audit Trail Styles */
    .audit-timeline {
        position: relative;
        padding: 1rem 0;
    }
    
    .audit-event {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
        position: relative;
    }
    
    .audit-event:not(:last-child)::before {
        content: '';
        position: absolute;
        left: 19px;
        top: 40px;
        bottom: -24px;
        width: 2px;
        background: var(--border-color);
    }
    
    .audit-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
        font-size: 1.25rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .audit-content {
        flex: 1;
        background: var(--background-light);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid var(--border-color);
    }
    
    .audit-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .audit-time {
        font-size: 0.875rem;
        color: var(--text-muted);
    }
    
    .audit-details {
        display: flex;
        gap: 1rem;
        font-size: 0.875rem;
        color: var(--text-muted);
        margin-bottom: 0.5rem;
    }
    
    .audit-user, .audit-ip {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    .audit-description {
        margin: 0.5rem 0 0 0;
        font-size: 0.875rem;
        color: var(--text-color);
    }
    
    .audit-changes {
        margin-top: 0.75rem;
    }
    
    .audit-changes-detail {
        margin-top: 0.5rem;
        background: white;
        padding: 0.75rem;
        border-radius: 6px;
        border: 1px solid var(--border-color);
    }
    
    .audit-changes-detail pre {
        margin: 0;
        font-size: 0.8rem;
        color: var(--text-color);
        white-space: pre-wrap;
        word-wrap: break-word;
    }
`;
document.head.appendChild(style);

// Export functions for use in HTML
window.contractActions = {
    navigate: navigateToContract,
    createNew: createNewContract,
    view: viewContract,
    edit: editContract,
    delete: deleteContract,
    viewNegotiation,
    sendToCounterparty,
    viewWorkflow,
    initiateSignature,
    download: downloadContract,
    viewAuditTrail,
    viewObligations,
    sendForReview,
    submitForReview,
    continueEditing,
    renew: renewContract,
    archive: archiveContract,
    viewHistory,
    performRiskAnalysis,
    performClauseAnalysis,
    setupWorkflow,
    smartAction
};