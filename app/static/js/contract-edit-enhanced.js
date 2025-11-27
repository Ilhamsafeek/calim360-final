/**
 * Contract Edit Page - Enhanced Router
 * Auto-opens modals based on URL parameters
 * File: app/static/js/contract-edit-enhanced.js
 */

(function() {
    'use strict';

    // Action to modal mapping (same as contract-actions.js)
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
        'version-history': 'versionModal',
        'export': 'exportModal',
        'clause-edit': 'clauseModal',
        'ai-query': 'aiQueryModal'
    };

    // Stage to stepper mapping
    const STAGE_STEPPER_MAP = {
        'draft': 1,
        'review': 2,
        'negotiation': 3,
        'approval': 4,
        'signature': 5,
        'executed': 6
    };

    /**
     * Initialize page based on URL parameters
     */
    function initializePageFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const action = urlParams.get('action');
        const stage = urlParams.get('stage');
        const party = urlParams.get('party');
        const tab = urlParams.get('tab');

        console.log('Initializing page with params:', { action, stage, party, tab });

        // Handle stage navigation
        if (stage) {
            navigateToStage(stage);
        }

        // Handle action-based modal opening
        if (action) {
            handleAction(action, party);
        }

        // Handle tab switching (if applicable)
        if (tab) {
            switchToTab(tab);
        }

        // Clean URL after processing (optional)
        if (action || stage || party || tab) {
            setTimeout(() => {
                const cleanUrl = window.location.pathname;
                window.history.replaceState({}, document.title, cleanUrl);
            }, 500);
        }
    }

    /**
     * Handle action and open appropriate modal
     */
    function handleAction(action, party = null) {
        console.log('Handling action:', action, 'Party:', party);

        // Special handling for signature with party
        if (action === 'signature' || action === 'sign' || action === 'initiate-signature') {
            setTimeout(() => {
                if (party === 'client' || party === 'provider') {
                    openSignature(party);
                } else {
                    initSignatures();
                    showNotification('Signature fields are now active. Click on the signature areas to sign.', 'info');
                }
            }, 300);
            return;
        }

        // Get modal ID from action
        const modalId = ACTION_MODAL_MAP[action];
        
        if (modalId) {
            // Small delay to ensure page is fully loaded
            setTimeout(() => {
                openModal(modalId);
                highlightActionButton(action);
            }, 300);
        } else if (action === 'edit' || action === 'negotiation') {
            // Just focus on editor
            setTimeout(() => {
                focusEditor();
            }, 300);
        } else if (action === 'view') {
            // Set page to read-only mode
            setReadOnlyMode();
        } else {
            console.warn('Unknown action:', action);
        }
    }

    /**
     * Navigate stepper to specific stage
     */
    function navigateToStage(stage) {
        const stageNumber = STAGE_STEPPER_MAP[stage.toLowerCase()];
        if (stageNumber) {
            updateStepperProgress(stageNumber);
            showNotification(`Navigated to ${stage} stage`, 'info');
        }
    }

    /**
     * Update stepper progress
     */
    function updateStepperProgress(activeStage) {
        const steps = document.querySelectorAll('.stepper-step');
        const progressBar = document.getElementById('stepperProgress');
        
        if (!steps.length) return;

        steps.forEach((step, index) => {
            const stepNumber = index + 1;
            
            // Remove all classes
            step.classList.remove('completed', 'active', 'pending');
            
            // Add appropriate class
            if (stepNumber < activeStage) {
                step.classList.add('completed');
                step.querySelector('.step-date').textContent = 'Completed';
            } else if (stepNumber === activeStage) {
                step.classList.add('active');
                step.querySelector('.step-date').textContent = 'In Progress';
            } else {
                step.classList.add('pending');
                step.querySelector('.step-date').textContent = 'Pending';
            }
        });

        // Update progress bar
        if (progressBar) {
            const progressPercent = ((activeStage - 1) / (steps.length - 1)) * 100;
            progressBar.style.width = `${progressPercent}%`;
        }
    }

    /**
     * Highlight action button that triggered the modal
     */
    function highlightActionButton(action) {
        // Find and highlight the button that corresponds to this action
        const buttons = document.querySelectorAll('button, .btn');
        buttons.forEach(btn => {
            const text = btn.textContent.toLowerCase();
            if (text.includes(action.replace('-', ' '))) {
                btn.style.animation = 'pulse 1s ease-in-out';
                setTimeout(() => {
                    btn.style.animation = '';
                }, 1000);
            }
        });
    }

    /**
     * Focus on editor
     */
    function focusEditor() {
        const editor = document.getElementById('contractContent');
        if (editor) {
            editor.scrollIntoView({ behavior: 'smooth', block: 'start' });
            editor.focus();
        }
    }

    /**
     * Set page to read-only mode
     */
    function setReadOnlyMode() {
        const editor = document.getElementById('contractContent');
        if (editor) {
            editor.contentEditable = false;
            editor.style.opacity = '0.9';
        }

        // Disable all edit buttons
        const editButtons = document.querySelectorAll('.toolbar-btn, .editor-toolbar button');
        editButtons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.5';
        });

        showNotification('Document is in read-only mode', 'info');
    }

    /**
     * Switch to specific tab
     */
    function switchToTab(tabName) {
        // This would be used if the edit page has tabs
        const tabButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (tabButton) {
            tabButton.click();
        }
    }

    /**
     * Show notification
     */
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        const colors = {
            'success': 'var(--success-color)',
            'error': 'var(--danger-color)',
            'warning': 'var(--warning-color)',
            'info': 'var(--primary-color)'
        };
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${colors[type]};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
            max-width: 400px;
        `;
        
        const icons = {
            'success': 'ti-check',
            'error': 'ti-alert-circle',
            'warning': 'ti-alert-triangle',
            'info': 'ti-info-circle'
        };
        
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="ti ${icons[type]}"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }

    /**
     * Add CSS animations
     */
    function addAnimations() {
        if (document.getElementById('contractEditAnimations')) return;
        
        const style = document.createElement('style');
        style.id = 'contractEditAnimations';
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
            
            @keyframes pulse {
                0%, 100% {
                    transform: scale(1);
                    box-shadow: 0 0 0 0 rgba(39, 98, 203, 0.7);
                }
                50% {
                    transform: scale(1.05);
                    box-shadow: 0 0 0 10px rgba(39, 98, 203, 0);
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Enhanced openModal function that integrates with existing code
     */
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error('Modal not found:', modalId);
            return;
        }

        // Display modal
        modal.style.display = 'block';
        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';

        // Ensure modal content is properly centered
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            // Reset any inline styles that might interfere
            modalContent.style.margin = '50px auto';
            modalContent.style.position = 'relative';
            modalContent.style.top = '50%';
            modalContent.style.transform = 'translateY(-50%)';
            
            // On smaller viewports, adjust positioning
            if (window.innerHeight < 800) {
                modalContent.style.top = 'auto';
                modalContent.style.transform = 'none';
                modalContent.style.marginTop = '20px';
                modalContent.style.marginBottom = '20px';
            }
        }

        // Trigger any modal-specific initialization
        initializeModal(modalId);
        
        // Focus on modal for accessibility
        setTimeout(() => {
            if (modalContent) {
                modalContent.setAttribute('tabindex', '-1');
                modalContent.focus();
            }
        }, 100);
    }

    /**
     * Initialize specific modal content
     */
    function initializeModal(modalId) {
        switch(modalId) {
            case 'signatureModal':
                if (typeof initCanvas === 'function') {
                    initCanvas();
                }
                break;
            case 'contractWorkflowModal':
                // Reset workflow selection
                selectedContractWorkflow = null;
                break;
            // Add other modal initializations as needed
        }
    }

    /**
     * Enhanced closeModal function
     */
    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
        
        document.body.style.overflow = 'auto';
        
        // Remove backdrop
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.remove();
        }
    }

    // Make functions globally available
    window.openModal = openModal;
    window.closeModal = closeModal;
    window.showNotification = showNotification;

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            addAnimations();
            initializePageFromURL();
        });
    } else {
        addAnimations();
        initializePageFromURL();
    }

})();