// =====================================================
// FILE: app/static/js/screens/workflow/SCR_024_master_workflow.js
// Master Workflow Setup JavaScript
// =====================================================

// Global variables
window.workflowSteps = [];
window.availableRoles = [];
window.availableDepartments = [];

// Make functions globally accessible
window.addNewStep = addNewStep;
window.removeStep = removeStep;
window.updateStepData = updateStepData;
window.searchUsers = searchUsers;
window.showSearchResults = showSearchResults;
window.hideSearchResults = hideSearchResults;
window.selectUser = selectUser;
window.removeUser = removeUser;
window.saveWorkflow = saveWorkflow;
window.submitWorkflow = submitWorkflow;

let workflowSteps = [];
let availableRoles = [];
let availableDepartments = [];

// =====================================================
// Initialize
// =====================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Master Workflow page loaded');
    setupEventListeners();
    loadWorkflowData();
    
    // Add initial step if no workflow exists
    setTimeout(() => {
        if (workflowSteps.length === 0) {
            addNewStep();
        }
    }, 1000);
});

// =====================================================
// Load Data
// =====================================================
async function loadWorkflowData() {
    try {
        showLoading();
        
        // Load existing master workflow
        const workflowResponse = await fetch('/api/workflows/master');
        if (workflowResponse.ok) {
            const workflow = await workflowResponse.json();
            if (workflow) {
                populateWorkflow(workflow);
            }
        }
        
        // Load roles
        const rolesResponse = await fetch('/api/workflows/roles');
        if (rolesResponse.ok) {
            const rolesData = await rolesResponse.json();
            availableRoles = rolesData.roles;
        }
        
        // Load departments
        const deptsResponse = await fetch('/api/workflows/departments');
        if (deptsResponse.ok) {
            const deptsData = await deptsResponse.json();
            availableDepartments = deptsData.departments;
        }
        
        hideLoading();
    } catch (error) {
        console.error('Error loading workflow data:', error);
        showNotification('Error loading workflow data', 'error');
        hideLoading();
    }
}

function populateWorkflow(workflow) {
    // Group steps by step_number
    const stepsMap = {};
    workflow.steps.forEach(step => {
        if (!stepsMap[step.step_number]) {
            stepsMap[step.step_number] = {
                step_number: step.step_number,
                step_name: step.step_name,
                step_type: step.step_type,
                assignee_role: step.assignee_role,
                sla_hours: step.sla_hours,
                is_mandatory: step.is_mandatory,
                users: []
            };
        }
        
        if (step.assignee_user_id) {
            stepsMap[step.step_number].users.push({
                id: step.assignee_user_id,
                // Will be populated when rendering
            });
        }
    });
    
    workflowSteps = Object.values(stepsMap);
    renderWorkflowSteps();
}

// =====================================================
// Event Listeners
// =====================================================
function setupEventListeners() {
    // Add step button - using event delegation and direct binding
    const addStepBtn = document.getElementById('addStepBtn');
    if (addStepBtn) {
        console.log('Add Step button found, attaching listener');
        addStepBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Add Step button clicked');
            addNewStep();
        });
    } else {
        console.error('Add Step button not found!');
    }
    
    // Also bind to any future buttons with onclick
    document.addEventListener('click', function(e) {
        if (e.target && e.target.id === 'addStepBtn') {
            e.preventDefault();
            addNewStep();
        }
    });
}

// =====================================================
// Workflow Step Management
// =====================================================
function addNewStep() {
    console.log('Adding new step, current steps:', workflowSteps.length);
    
    const newStep = {
        step_number: workflowSteps.length + 1,
        step_name: '',
        step_type: 'Reviewer',
        assignee_role: '',
        department: '',
        users: [],
        sla_hours: 24,
        is_mandatory: true
    };
    
    workflowSteps.push(newStep);
    console.log('New step added, total steps:', workflowSteps.length);
    
    renderWorkflowSteps();
}

function removeStep(button) {
    const stepRow = button.closest('.workflow-step');
    const stepIndex = Array.from(stepRow.parentElement.children).indexOf(stepRow);
    
    if (workflowSteps.length <= 1) {
        showNotification('At least one workflow step is required', 'warning');
        return;
    }
    
    if (confirm('Are you sure you want to remove this step?')) {
        workflowSteps.splice(stepIndex, 1);
        
        // Renumber steps
        workflowSteps.forEach((step, index) => {
            step.step_number = index + 1;
        });
        
        renderWorkflowSteps();
    }
}

function renderWorkflowSteps() {
    console.log('Rendering workflow steps, count:', workflowSteps.length);
    const tbody = document.querySelector('#workflowTable tbody');
    if (!tbody) {
        console.error('Workflow table tbody not found!');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (workflowSteps.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    <i class="ti ti-info-circle" style="font-size: 2rem; display: block; margin-bottom: 0.5rem;"></i>
                    No workflow steps defined. Click "Add Step" to get started.
                </td>
            </tr>
        `;
        return;
    }
    
    workflowSteps.forEach((step, index) => {
        const row = createStepRow(step, index);
        tbody.appendChild(row);
    });
    
    updateStepNumbers();
    console.log('Workflow steps rendered successfully');
}

function createStepRow(step, index) {
    const tr = document.createElement('tr');
    tr.className = 'workflow-step';
    
    tr.innerHTML = `
        <td style="text-align: center; font-weight: 600; color: var(--primary-color);">
            ${step.step_number}
        </td>
        <td>
            <select name="role_${index}" class="form-select" onchange="updateStepData(${index}, 'assignee_role', this.value)">
                <option value="">Select Role</option>
                ${availableRoles.map(role => `
                    <option value="${role}" ${step.assignee_role === role ? 'selected' : ''}>${role}</option>
                `).join('')}
            </select>
        </td>
        <td>
            <div class="user-select-wrapper">
                <div class="selected-users" id="selectedUsers_${index}">
                    ${step.users.map(user => `
                        <span class="selected-tag">
                            ${user.name}
                            <span class="tag-email">${user.email}</span>
                            <button type="button" class="remove-tag" onclick="removeUser(${index}, ${user.id})">×</button>
                        </span>
                    `).join('')}
                </div>
                <div class="search-container">
                    <input type="text" 
                           class="form-control user-search" 
                           placeholder="Search and add users..."
                           onkeyup="searchUsers(${index}, this.value)"
                           onfocus="showSearchResults(${index})">
                    <div class="search-results" id="searchResults_${index}" style="display: none;"></div>
                </div>
            </div>
        </td>
        <td>
            <select name="department_${index}" class="form-select" onchange="updateStepData(${index}, 'department', this.value)">
                <option value="">Select Department</option>
                ${availableDepartments.map(dept => `
                    <option value="${dept.name}" ${step.department === dept.name ? 'selected' : ''}>${dept.name}</option>
                `).join('')}
            </select>
        </td>
        <td style="text-align: center;">
            <button type="button" class="btn-icon-danger remove-step" onclick="removeStep(this)" title="Remove Step">
                <i class="ti ti-trash"></i>
            </button>
        </td>
    `;
    
    return tr;
}

function updateStepData(index, field, value) {
    if (workflowSteps[index]) {
        workflowSteps[index][field] = value;
    }
}

function updateStepNumbers() {
    document.querySelectorAll('.workflow-step').forEach((row, index) => {
        const stepNum = row.querySelector('td:first-child');
        if (stepNum) {
            stepNum.textContent = index + 1;
        }
    });
}

// =====================================================
// User Search and Selection
// =====================================================
let searchTimeout;

async function searchUsers(stepIndex, query) {
    clearTimeout(searchTimeout);
    
    if (query.length < 2) {
        hideSearchResults(stepIndex);
        return;
    }
    
    searchTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`/api/workflows/users/search?query=${encodeURIComponent(query)}`);
            if (response.ok) {
                const data = await response.json();
                displaySearchResults(stepIndex, data.users);
            }
        } catch (error) {
            console.error('Error searching users:', error);
        }
    }, 300);
}

function displaySearchResults(stepIndex, users) {
    const resultsDiv = document.getElementById(`searchResults_${stepIndex}`);
    if (!resultsDiv) return;
    
    if (users.length === 0) {
        resultsDiv.innerHTML = '<div class="search-result-item">No users found</div>';
    } else {
        resultsDiv.innerHTML = users.map(user => `
            <div class="search-result-item" onclick="selectUser(${stepIndex}, ${JSON.stringify(user).replace(/"/g, '&quot;')})">
                <div>
                    <strong>${user.name}</strong>
                    <br>
                    <small style="color: var(--text-muted);">${user.email}</small>
                </div>
                <span class="badge" style="background: var(--secondary-color); color: white; font-size: 0.75rem;">
                    ${user.user_type}
                </span>
            </div>
        `).join('');
    }
    
    resultsDiv.style.display = 'block';
}

function showSearchResults(stepIndex) {
    const resultsDiv = document.getElementById(`searchResults_${stepIndex}`);
    if (resultsDiv && resultsDiv.innerHTML) {
        resultsDiv.style.display = 'block';
    }
}

function hideSearchResults(stepIndex) {
    const resultsDiv = document.getElementById(`searchResults_${stepIndex}`);
    if (resultsDiv) {
        resultsDiv.style.display = 'none';
    }
}

function selectUser(stepIndex, user) {
    if (!workflowSteps[stepIndex]) return;
    
    // Check if user already selected
    const exists = workflowSteps[stepIndex].users.find(u => u.id === user.id);
    if (exists) {
        showNotification('User already added to this step', 'warning');
        return;
    }
    
    // Add user
    workflowSteps[stepIndex].users.push(user);
    
    // Re-render the step
    renderWorkflowSteps();
    
    // Clear search
    const searchInput = document.querySelector(`#searchResults_${stepIndex}`).previousElementSibling;
    if (searchInput) {
        searchInput.value = '';
    }
    hideSearchResults(stepIndex);
}

function removeUser(stepIndex, userId) {
    if (!workflowSteps[stepIndex]) return;
    
    workflowSteps[stepIndex].users = workflowSteps[stepIndex].users.filter(u => u.id !== userId);
    renderWorkflowSteps();
}

// =====================================================
// Save & Submit
// =====================================================
async function saveWorkflow() {
    if (!validateWorkflow()) {
        return;
    }
    
    try {
        showLoading();
        
        const workflowData = {
            workflow_name: "Master Workflow",
            description: "Company-wide default workflow",
            steps: workflowSteps.map(step => ({
                step_number: step.step_number,
                step_name: step.assignee_role || `Step ${step.step_number}`,
                step_type: step.assignee_role || 'Reviewer',
                role: step.assignee_role,
                department: step.department,
                users: step.users,
                sla_hours: step.sla_hours || 24,
                is_mandatory: step.is_mandatory !== false
            })),
            auto_escalation: document.querySelector('input[type="checkbox"]')?.checked || false,
            escalation_hours: 48
        };
        
        const response = await fetch('/api/workflows/master', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(workflowData)
        });
        
        if (response.ok) {
            showNotification('Workflow saved successfully', 'success');
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Error saving workflow', 'error');
        }
        
        hideLoading();
    } catch (error) {
        console.error('Error saving workflow:', error);
        showNotification('Error saving workflow', 'error');
        hideLoading();
    }
}

async function submitWorkflow() {
    if (!validateWorkflow()) {
        return;
    }
    
    if (!confirm('Are you sure you want to submit this master workflow? It will be applied to all new contracts.')) {
        return;
    }
    
    await saveWorkflow();
}

function validateWorkflow() {
    if (workflowSteps.length === 0) {
        showNotification('Please add at least one workflow step', 'warning');
        return false;
    }
    
    for (let i = 0; i < workflowSteps.length; i++) {
        const step = workflowSteps[i];
        
        if (!step.assignee_role) {
            showNotification(`Please select a role for step ${i + 1}`, 'warning');
            return false;
        }
        
        if (step.users.length === 0) {
            showNotification(`Please add at least one user for step ${i + 1}`, 'warning');
            return false;
        }
    }
    
    return true;
}

// =====================================================
// Utility Functions
// =====================================================
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('active');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="ti ti-${type === 'success' ? 'check' : type === 'error' ? 'x' : type === 'warning' ? 'alert-triangle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Add notification styles
const style = document.createElement('style');
style.textContent = `
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: white;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    display: flex;
    align-items: center;
    gap: 0.75rem;
    z-index: 10000;
    transform: translateX(400px);
    transition: transform 0.3s ease;
}

.notification.show {
    transform: translateX(0);
}

.notification-success {
    border-left: 4px solid var(--success-color);
}

.notification-error {
    border-left: 4px solid var(--danger-color);
}

.notification-warning {
    border-left: 4px solid var(--warning-color);
}

.notification-info {
    border-left: 4px solid var(--primary-color);
}

.notification i {
    font-size: 1.25rem;
}

.notification-success i {
    color: var(--success-color);
}

.notification-error i {
    color: var(--danger-color);
}

.notification-warning i {
    color: var(--warning-color);
}

.notification-info i {
    color: var(--primary-color);
}
`;
document.head.appendChild(style);