// =====================================================
// FILE: app/static/js/screens/drafting/SCR_016_contract_editor.js
// Contract Editor - Full Database Integration
// =====================================================

const API_BASE = '/api/contracts';

// State Management
let currentContract = null;
let contractClauses = [];
let isDirty = false;
let autoSaveInterval = null;

// =====================================================
// Initialization
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeEditor();
});

function initializeEditor() {
    // Get contract ID from URL
    const contractId = getContractIdFromUrl();
    
    if (contractId) {
        loadContract(contractId);
    } else {
        initializeNewContract();
    }
    
    // Bind all event listeners
    bindEventListeners();
    
    // Start auto-save
    startAutoSave();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', handleBeforeUnload);
}

function getContractIdFromUrl() {
    const pathParts = window.location.pathname.split('/');
    const editIndex = pathParts.indexOf('edit');
    if (editIndex !== -1 && pathParts[editIndex + 1]) {
        return pathParts[editIndex + 1];
    }
    
    // Also check query params
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('contract_id');
}

// =====================================================
// Event Listeners
// =====================================================

function bindEventListeners() {
    // Save buttons
    bindButton('saveContractBtn', () => saveContract());
    bindButton('saveDraftBtn', () => saveContract('draft'));
    bindButton('saveReviewBtn', () => saveContract('under_review'));
    
    // Clause actions
    bindButton('addClauseBtn', showAddClauseModal);
    bindButton('aiDraftBtn', showAIDraftModal);
    
    // Form change tracking
    document.querySelectorAll('input, textarea, select').forEach(el => {
        el.addEventListener('change', () => {
            isDirty = true;
            updateSaveButton();
        });
    });
    
    // Modal handlers
    setupModals();
}

function bindButton(id, handler) {
    const btn = document.getElementById(id);
    if (btn) {
        btn.addEventListener('click', handler);
    }
}

function updateSaveButton() {
    const saveBtn = document.getElementById('saveContractBtn');
    if (saveBtn && isDirty) {
        saveBtn.classList.add('has-changes');
        saveBtn.innerHTML = '<i class="ti ti-device-floppy"></i> Save Changes';
    }
}

// =====================================================
// Contract Operations
// =====================================================

async function loadContract(contractId) {
    try {
        showLoader('Loading contract...');
        
        const response = await fetch(`${API_BASE}/${contractId}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load contract');
        }
        
        currentContract = await response.json();
        
        // Populate form
        populateContractForm(currentContract);
        
        // Load clauses
        await loadClauses(contractId);
        
        // Lock contract
        await lockContract(contractId);
        
        hideLoader();
        showSuccess('Contract loaded successfully');
        
    } catch (error) {
        hideLoader();
        showError('Error loading contract: ' + error.message);
        console.error('Error:', error);
    }
}

async function saveContract(status = null) {
    try {
        showLoader('Saving contract...');
        
        const contractData = gatherContractData();
        if (status) {
            contractData.status = status;
        }
        
        let response;
        
        if (currentContract && currentContract.id) {
            // Update existing
            response = await fetch(`${API_BASE}/${currentContract.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getAuthToken()}`
                },
                body: JSON.stringify(contractData)
            });
        } else {
            // Create new
            response = await fetch(`${API_BASE}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getAuthToken()}`
                },
                body: JSON.stringify(contractData)
            });
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save contract');
        }
        
        currentContract = await response.json();
        isDirty = false;
        
        hideLoader();
        showSuccess('Contract saved successfully');
        
        // Update URL if new contract
        if (!window.location.pathname.includes(currentContract.id)) {
            window.history.pushState({}, '', `/contract/edit/${currentContract.id}`);
        }
        
        // Update UI
        populateContractForm(currentContract);
        
    } catch (error) {
        hideLoader();
        showError('Error saving contract: ' + error.message);
        console.error('Error:', error);
    }
}

async function lockContract(contractId) {
    try {
        const response = await fetch(`${API_BASE}/${contractId}/lock`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok && response.status === 423) {
            const error = await response.json();
            showWarning('Contract is locked by another user');
            makeFormReadOnly();
        }
    } catch (error) {
        console.error('Error locking contract:', error);
    }
}

async function unlockContract(contractId) {
    if (!contractId) return;
    
    try {
        await fetch(`${API_BASE}/${contractId}/unlock`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
    } catch (error) {
        console.error('Error unlocking contract:', error);
    }
}

// =====================================================
// Clause Operations
// =====================================================

async function loadClauses(contractId) {
    try {
        const response = await fetch(`${API_BASE}/${contractId}/clauses`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load clauses');
        }
        
        const data = await response.json();
        contractClauses = data.items || [];
        
        renderClauses();
        
    } catch (error) {
        showError('Error loading clauses: ' + error.message);
        console.error('Error:', error);
    }
}

async function addClause(clauseData) {
    try {
        showLoader('Adding clause...');
        
        const response = await fetch(`${API_BASE}/clauses`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                contract_id: currentContract.id,
                ...clauseData,
                position: contractClauses.length + 1
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to add clause');
        }
        
        const newClause = await response.json();
        contractClauses.push(newClause);
        
        renderClauses();
        hideLoader();
        showSuccess('Clause added successfully');
        closeModal('addClauseModal');
        
    } catch (error) {
        hideLoader();
        showError('Error adding clause: ' + error.message);
        console.error('Error:', error);
    }
}

async function updateClause(clauseId, clauseData) {
    try {
        const response = await fetch(`${API_BASE}/clauses/${clauseId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify(clauseData)
        });
        
        if (!response.ok) {
            throw new Error('Failed to update clause');
        }
        
        const updatedClause = await response.json();
        
        const index = contractClauses.findIndex(c => c.id === clauseId);
        if (index !== -1) {
            contractClauses[index] = updatedClause;
        }
        
        renderClauses();
        showSuccess('Clause updated successfully');
        
    } catch (error) {
        showError('Error updating clause: ' + error.message);
        console.error('Error:', error);
    }
}

async function deleteClause(clauseId) {
    if (!confirm('Are you sure you want to delete this clause?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/clauses/${clauseId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete clause');
        }
        
        contractClauses = contractClauses.filter(c => c.id !== clauseId);
        
        renderClauses();
        showSuccess('Clause deleted successfully');
        
    } catch (error) {
        showError('Error deleting clause: ' + error.message);
        console.error('Error:', error);
    }
}

function renderClauses() {
    const container = document.getElementById('clausesContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (contractClauses.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="ti ti-file-text"></i>
                <p>No clauses added yet</p>
                <button class="btn btn-primary" onclick="showAddClauseModal()">
                    <i class="ti ti-plus"></i> Add First Clause
                </button>
            </div>
        `;
        return;
    }
    
    contractClauses.forEach((clause, index) => {
        const clauseEl = createClauseElement(clause, index + 1);
        container.appendChild(clauseEl);
    });
}

function createClauseElement(clause, number) {
    const div = document.createElement('div');
    div.className = 'clause-item';
    div.dataset.clauseId = clause.id;
    
    div.innerHTML = `
        <div class="clause-header">
            <div class="clause-number">${number}</div>
            <div class="clause-title-section">
                <h4 class="clause-title">${escapeHtml(clause.clause_title)}</h4>
                ${clause.clause_number ? `<span class="clause-ref">${escapeHtml(clause.clause_number)}</span>` : ''}
            </div>
            <div class="clause-actions">
                ${clause.is_mandatory ? '<span class="badge badge-warning">Mandatory</span>' : ''}
                ${!clause.is_negotiable ? '<span class="badge badge-info">Non-negotiable</span>' : ''}
                <button class="btn btn-sm btn-icon" onclick="editClause(${clause.id})" title="Edit">
                    <i class="ti ti-edit"></i>
                </button>
                <button class="btn btn-sm btn-icon" onclick="deleteClause(${clause.id})" title="Delete">
                    <i class="ti ti-trash"></i>
                </button>
            </div>
        </div>
        <div class="clause-body">${escapeHtml(clause.clause_text)}</div>
    `;
    
    return div;
}

// =====================================================
// AI Drafting
// =====================================================

async function aiDraftClause(clauseTitle, jurisdiction, businessContext) {
    try {
        showLoader('AI is drafting the clause...');
        
        const response = await fetch(`${API_BASE}/ai/draft-clause`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                contract_id: currentContract.id,
                clause_title: clauseTitle,
                jurisdiction: jurisdiction,
                business_context: businessContext,
                language: 'en'
            })
        });
        
        if (!response.ok) {
            throw new Error('AI drafting failed');
        }
        
        const result = await response.json();
        
        hideLoader();
        displayAIDraftedClause(result);
        
    } catch (error) {
        hideLoader();
        showError('Error with AI drafting: ' + error.message);
        console.error('Error:', error);
    }
}

function displayAIDraftedClause(draftResult) {
    closeModal('aiDraftModal');
    
    const modal = showModal('aiReviewModal');
    if (modal) {
        document.getElementById('aiClauseTitle').value = draftResult.clause_title;
        document.getElementById('aiClauseBody').value = draftResult.clause_body;
        
        if (draftResult.suggestions) {
            const suggestionsHtml = draftResult.suggestions
                .map(s => `<li>${escapeHtml(s)}</li>`)
                .join('');
            document.getElementById('aiSuggestions').innerHTML = `<ul>${suggestionsHtml}</ul>`;
        }
    }
}

// =====================================================
// Form Handling
// =====================================================

function populateContractForm(contract) {
    setInputValue('contractTitle', contract.contract_title);
    setInputValue('contractNumber', contract.contract_number);
    setInputValue('contractType', contract.contract_type);
    setInputValue('profileType', contract.profile_type);
    setInputValue('effectiveDate', contract.effective_date);
    setInputValue('expiryDate', contract.expiry_date);
    setInputValue('contractValue', contract.contract_value);
    setInputValue('currency', contract.currency);
    setInputValue('governingLaw', contract.governing_law);
    setInputValue('status', contract.status);
    
    setCheckboxValue('autoRenewal', contract.auto_renewal);
    
    // Update header
    const titleEl = document.querySelector('.contract-header-left h1');
    if (titleEl) {
        titleEl.textContent = contract.contract_title;
    }
    
    const numberEl = document.querySelector('.contract-number');
    if (numberEl) {
        numberEl.textContent = contract.contract_number;
    }
    
    const statusBadge = document.querySelector('.contract-status-badge');
    if (statusBadge) {
        statusBadge.textContent = contract.status.replace('_', ' ');
        statusBadge.className = `contract-status-badge ${contract.status}`;
    }
}

function gatherContractData() {
    return {
        contract_title: getInputValue('contractTitle'),
        contract_type: getInputValue('contractType'),
        profile_type: getInputValue('profileType'),
        effective_date: getInputValue('effectiveDate'),
        expiry_date: getInputValue('expiryDate'),
        auto_renewal: getCheckboxValue('autoRenewal'),
        renewal_period_months: getInputValue('renewalPeriodMonths') || null,
        renewal_notice_days: getInputValue('renewalNoticeDays') || null,
        contract_value: getInputValue('contractValue') || null,
        currency: getInputValue('currency') || 'QAR',
        governing_law: getInputValue('governingLaw'),
        confidentiality_level: getInputValue('confidentialityLevel') || 'standard',
        language: 'en',
        project_id: getInputValue('projectId') || null
    };
}

function initializeNewContract() {
    const today = new Date().toISOString().split('T')[0];
    setInputValue('effectiveDate', today);
    setInputValue('currency', 'QAR');
}

// =====================================================
// Auto-save
// =====================================================

function startAutoSave() {
    autoSaveInterval = setInterval(autoSave, 30000); // Every 30 seconds
}

async function autoSave() {
    if (isDirty && currentContract && currentContract.id) {
        console.log('Auto-saving...');
        await saveContract();
    }
}

function handleBeforeUnload(e) {
    if (currentContract && currentContract.id) {
        unlockContract(currentContract.id);
    }
    
    if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
    }
}

// =====================================================
// Modal Management
// =====================================================

function setupModals() {
    // Add Clause Modal
    const addClauseForm = document.getElementById('addClauseForm');
    if (addClauseForm) {
        addClauseForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            addClause({
                clause_title: formData.get('clauseTitle'),
                clause_text: formData.get('clauseText'),
                clause_number: formData.get('clauseNumber'),
                is_mandatory: formData.get('isMandatory') === 'on',
                is_negotiable: formData.get('isNegotiable') === 'on'
            });
        });
    }
    
    // AI Draft Modal
    const aiDraftForm = document.getElementById('aiDraftForm');
    if (aiDraftForm) {
        aiDraftForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            aiDraftClause(
                formData.get('clauseTitle'),
                formData.get('jurisdiction'),
                formData.get('businessContext')
            );
        });
    }
}

function showAddClauseModal() {
    showModal('addClauseModal');
}

function showAIDraftModal() {
    showModal('aiDraftModal');
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');
    }
    return modal;
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
}

function makeFormReadOnly() {
    document.querySelectorAll('input, textarea, select, button').forEach(el => {
        el.disabled = true;
    });
}

// =====================================================
// Utility Functions
// =====================================================

function getAuthToken() {
    return getCookie('session_token') || localStorage.getItem('auth_token') || '';
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function getInputValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : '';
}

function setInputValue(id, value) {
    const el = document.getElementById(id);
    if (el && value !== null && value !== undefined) {
        el.value = value;
    }
}

function getCheckboxValue(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
}

function setCheckboxValue(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.checked = !!value;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoader(message) {
    let loader = document.getElementById('pageLoader');
    if (!loader) {
        loader = document.createElement('div');
        loader.id = 'pageLoader';
        loader.className = 'loader-overlay';
        loader.innerHTML = `
            <div class="loader">
                <div class="spinner"></div>
                <p>${message}</p>
            </div>
        `;
        document.body.appendChild(loader);
    }
    loader.style.display = 'flex';
}

function hideLoader() {
    const loader = document.getElementById('pageLoader');
    if (loader) {
        loader.style.display = 'none';
    }
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showWarning(message) {
    showNotification(message, 'warning');
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="ti ti-${type === 'success' ? 'check' : type === 'error' ? 'x' : 'alert-triangle'}"></i>
        <span>${message}</span>
    `;
    
    let container = document.getElementById('notificationContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notificationContainer';
        container.className = 'notification-container';
        document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}


// Add these functions to the editor JS

let contractContent = '';  // Store full HTML content

async function loadContractContent(contractId) {
    try {
        const response = await fetch(`${API_BASE}/${contractId}/content`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            contractContent = data.contract_content;
            
            // Render in editor (use a rich text editor like Quill or TinyMCE)
            const editor = document.getElementById('contractContentEditor');
            if (editor) {
                editor.innerHTML = contractContent;
            }
        }
    } catch (error) {
        console.error('Error loading content:', error);
    }
}

async function saveContractContent() {
    try {
        showLoader('Saving contract content...');
        
        // Get content from rich text editor
        const editor = document.getElementById('contractContentEditor');
        const content = editor.innerHTML;
        
        const response = await fetch(`${API_BASE}/${currentContract.id}/content`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                content: content,
                version_type: 'draft',
                change_summary: 'User edited contract'
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to save content');
        }
        
        const result = await response.json();
        
        hideLoader();
        showSuccess(`Content saved as version ${result.version_number}`);
        
    } catch (error) {
        hideLoader();
        showError('Error saving content: ' + error.message);
    }
}

// When AI generates a clause, it's automatically saved
async function aiDraftClause(clauseTitle, jurisdiction, businessContext) {
    try {
        showLoader('AI is drafting the clause...');
        
        const response = await fetch(`${API_BASE}/ai/draft-clause`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                contract_id: currentContract.id,
                clause_title: clauseTitle,
                jurisdiction: jurisdiction,
                business_context: businessContext,
                language: 'en',
                auto_save: true  // NEW: Auto-save to database
            })
        });
        
        if (!response.ok) {
            throw new Error('AI drafting failed');
        }
        
        const result = await response.json();
        
        hideLoader();
        
        // Reload clauses to show the newly saved one
        await loadClauses(currentContract.id);
        
        showSuccess('AI clause generated and saved!');
        
    } catch (error) {
        hideLoader();
        showError('Error with AI drafting: ' + error.message);
    }
}


// =====================================================
// Expose functions for HTML onclick handlers
// =====================================================

window.showAddClauseModal = showAddClauseModal;
window.showAIDraftModal = showAIDraftModal;
window.editClause = function(clauseId) {
    // TODO: Implement edit clause modal
    console.log('Edit clause:', clauseId);
};
window.deleteClause = deleteClause;