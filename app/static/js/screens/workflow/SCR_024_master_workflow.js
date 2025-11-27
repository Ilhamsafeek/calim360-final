/**
 * Master Workflow Setup - JavaScript Functions
 * COMPLETE WORKING VERSION
 */

let stepCount = 0;
let currentStepForEmail = null;

// =====================================================
// USER SEARCH FUNCTIONS
// =====================================================

async function fetchUsers(searchTerm = '') {
    try {
        const url = searchTerm 
            ? `/api/workflow/users?search=${encodeURIComponent(searchTerm)}`
            : '/api/workflow/users';
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            return data.users;
        }
        return [];
    } catch (error) {
        console.error('Error fetching users:', error);
        return [];
    }
}

async function searchUsers(input, stepNum) {
    const searchTerm = input.value.trim();
    const dropdown = document.getElementById(`userDropdown_${stepNum}`);

    if (!dropdown) return;

    const users = await fetchUsers(searchTerm);

    let dropdownHtml = '';
    
    if (users.length > 0) {
        users.forEach(user => {
            const escapedName = user.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const escapedEmail = user.email.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            dropdownHtml += `
                <div class="dropdown-item" onclick='selectUser(${stepNum}, ${user.id}, "${escapedName}", "${escapedEmail}")'>
                    <div class="user-info">
                        <span class="user-name">${user.name}</span>
                        <span class="user-email">${user.email}</span>
                    </div>
                </div>
            `;
        });
    } else {
        dropdownHtml += `
            <div class="dropdown-item" style="color: var(--text-muted); cursor: default; text-align: center;">
                <i class="ti ti-user-x" style="margin-right: 0.5rem;"></i>
                No users found
            </div>
        `;
    }

    dropdownHtml += `
        <div class="dropdown-item add-email-option" onclick="showEmailInput(${stepNum})">
            <i class="ti ti-mail-plus"></i>
            <span>Add email address directly</span>
        </div>
    `;

    dropdown.innerHTML = dropdownHtml;
    dropdown.style.display = 'block';
}

async function showUserDropdown(input, stepNum) {
    const dropdown = document.getElementById(`userDropdown_${stepNum}`);
    if (!dropdown) return;

    dropdown.innerHTML = `
        <div class="dropdown-item" style="text-align: center; color: var(--text-muted);">
            <i class="ti ti-loader" style="animation: spin 1s linear infinite;"></i>
            Loading users...
        </div>
    `;
    dropdown.style.display = 'block';

    const users = await fetchUsers('');

    let dropdownHtml = '';
    
    if (users.length > 0) {
        dropdownHtml += `
            <div class="dropdown-header" style="padding: 0.5rem 1rem; background: var(--background-light); border-bottom: 1px solid var(--border-color); font-weight: 600; font-size: 0.75rem; color: var(--text-muted);">
                ${users.length} user(s) available
            </div>
        `;
        
        users.forEach(user => {
            const escapedName = user.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const escapedEmail = user.email.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            dropdownHtml += `
                <div class="dropdown-item" onclick='selectUser(${stepNum}, ${user.id}, "${escapedName}", "${escapedEmail}")'>
                    <div class="user-info">
                        <span class="user-name">${user.name}</span>
                        <span class="user-email">${user.email}</span>
                    </div>
                </div>
            `;
        });
    } else {
        dropdownHtml += `
            <div class="dropdown-item" style="color: var(--text-muted); cursor: default; text-align: center; padding: 1rem;">
                <i class="ti ti-user-x" style="margin-right: 0.5rem; font-size: 1.5rem; display: block; margin-bottom: 0.5rem;"></i>
                No users found in your company
            </div>
        `;
    }

    dropdownHtml += `
        <div class="dropdown-item add-email-option" onclick="showEmailInput(${stepNum})" style="border-top: 1px solid var(--border-color); margin-top: 0.25rem;">
            <i class="ti ti-mail-plus"></i>
            <span>Add email address directly</span>
        </div>
    `;

    dropdown.innerHTML = dropdownHtml;
}

function selectUser(stepNum, userId, userName, userEmail) {
    const selectedUsersDiv = document.getElementById(`selectedUsers_${stepNum}`);
    if (!selectedUsersDiv) return;

    const placeholder = selectedUsersDiv.querySelector('span');
    if (placeholder && placeholder.textContent.includes('No users selected')) {
        placeholder.remove();
    }

    const existing = selectedUsersDiv.querySelector(`[data-user-id="${userId}"]`);
    if (existing) {
        alert('User already added to this step');
        return;
    }

    const userTag = document.createElement('div');
    userTag.className = 'selected-tag';
    userTag.setAttribute('data-user-id', userId);
    userTag.innerHTML = `
        <i class="ti ti-user"></i>
        ${userName}
        <span class="tag-email">${userEmail}</span>
        <i class="ti ti-x" onclick="removeUser(this)"></i>
    `;

    selectedUsersDiv.appendChild(userTag);

    const searchInput = selectedUsersDiv.closest('td').querySelector('.user-search');
    if (searchInput) searchInput.value = '';
    
    const dropdown = document.getElementById(`userDropdown_${stepNum}`);
    if (dropdown) dropdown.style.display = 'none';
}

function removeUser(element) {
    const selectedUsersDiv = element.closest('.selected-users');
    element.closest('.selected-tag').remove();
    
    if (!selectedUsersDiv.querySelector('.selected-tag')) {
        const placeholder = document.createElement('span');
        placeholder.style.color = 'var(--text-muted)';
        placeholder.style.fontSize = '0.875rem';
        placeholder.textContent = 'No users selected';
        selectedUsersDiv.appendChild(placeholder);
    }
}

function addEmailDirectly(stepNum) {
    currentStepForEmail = stepNum;
    document.getElementById('emailInputModal').classList.add('show');
    document.getElementById('directEmailInput').value = '';
    document.getElementById('directEmailInput').focus();
}

function showEmailInput(stepNum) {
    currentStepForEmail = stepNum;
    document.getElementById('emailInputModal').classList.add('show');
    document.getElementById('directEmailInput').value = '';
    document.getElementById('directEmailInput').focus();
}

function closeEmailModal() {
    document.getElementById('emailInputModal').classList.remove('show');
    currentStepForEmail = null;
}

function addEmailToStep() {
    const email = document.getElementById('directEmailInput').value;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        alert('Please enter a valid email address');
        return;
    }

    if (currentStepForEmail) {
        const selectedUsersDiv = document.getElementById(`selectedUsers_${currentStepForEmail}`);

        const placeholder = selectedUsersDiv.querySelector('span');
        if (placeholder && placeholder.textContent.includes('No users selected')) {
            placeholder.remove();
        }

        const existingEmails = Array.from(selectedUsersDiv.querySelectorAll('.tag-email')).map(el => el.textContent);
        if (existingEmails.includes(email)) {
            alert('This email is already added to this step');
            return;
        }

        const userTag = document.createElement('div');
        userTag.className = 'selected-tag';
        userTag.setAttribute('data-user-email', email);
        userTag.innerHTML = `
            <i class="ti ti-mail"></i>
            External User
            <span class="tag-email">${email}</span>
            <i class="ti ti-x" onclick="removeUser(this)"></i>
        `;

        selectedUsersDiv.appendChild(userTag);

        const searchInput = selectedUsersDiv.closest('td').querySelector('.user-search');
        if (searchInput) searchInput.value = '';
        
        const dropdown = document.getElementById(`userDropdown_${currentStepForEmail}`);
        if (dropdown) dropdown.style.display = 'none';
        
        closeEmailModal();
    }
}

document.addEventListener('click', function (event) {
    if (!event.target.closest('.user-selection-wrapper')) {
        document.querySelectorAll('.user-dropdown').forEach(dropdown => {
            dropdown.style.display = 'none';
        });
    }
});

// =====================================================
// WORKFLOW STEP MANAGEMENT
// =====================================================

function addWorkflowStep() {
    stepCount++;
    const tbody = document.getElementById('workflowSteps');
    const newRow = document.createElement('tr');
    newRow.className = 'workflow-step';
    newRow.innerHTML = `
        <td>
            <div class="step-number">${stepCount}</div>
        </td>
        <td>
            <select class="form-select" name="role_${stepCount}">
                <option value="">Select Role</option>
                <option value="reviewer">Reviewer</option>
                <option value="approver">Approver</option>
                <option value="legal_reviewer">Legal Reviewer</option>
                <option value="finance_approver">Finance Approver</option>
                <option value="executive_approver">Executive Approver</option>
                <option value="signatory">Signatory</option>
                <option value="counterparty">Counter-Party</option>
            </select>
        </td>
        <td>
            <div class="user-selection-wrapper">
                <div class="user-input-group">
                    <input type="text" class="form-input user-search" placeholder="Search by name or email..." 
                           onkeyup="searchUsers(this, ${stepCount})" onfocus="showUserDropdown(this, ${stepCount})">
                    <button type="button" class="btn-icon" onclick="addEmailDirectly(${stepCount})">
                        <i class="ti ti-mail-plus"></i>
                    </button>
                </div>
                <div class="user-dropdown" id="userDropdown_${stepCount}" style="display: none;"></div>
                <div class="selected-users" id="selectedUsers_${stepCount}">
                    <span style="color: var(--text-muted); font-size: 0.875rem;">No users selected</span>
                </div>
            </div>
        </td>
        <td>
            <select class="form-select" name="department_${stepCount}">
                <option value="">Select Department</option>
                <option value="legal">Legal</option>
                <option value="finance">Finance</option>
                <option value="operations">Operations</option>
                <option value="procurement">Procurement</option>
                <option value="executive">Executive</option>
            </select>
        </td>
        <td>
            <i class="ti ti-trash remove-step" onclick="removeStep(this)" style="cursor: pointer; color: var(--danger-color);"></i>
        </td>
    `;
    tbody.appendChild(newRow);
    console.log(`✅ Added empty workflow step #${stepCount}`);
}

function removeStep(element) {
    const tbody = document.getElementById('workflowSteps');
    const totalSteps = tbody?.querySelectorAll('.workflow-step').length || 0;

    if (totalSteps <= 1) {
        alert('⚠️ At least one workflow step is required');
        return;
    }

    if (confirm('Are you sure you want to remove this workflow step?')) {
        const row = element.closest('tr');
        if (row) {
            row.remove();
            updateStepNumbers();
            console.log('🗑️ Removed workflow step');
        }
    }
}

function updateStepNumbers() {
    const steps = document.querySelectorAll('.workflow-step');
    steps.forEach((step, index) => {
        const stepNumber = step.querySelector('.step-number');
        if (stepNumber) {
            stepNumber.textContent = index + 1;
        }
    });
    stepCount = steps.length;
}

// =====================================================
// SAVE AND SUBMIT
// =====================================================

async function saveWorkflow() {
    const workflowData = collectWorkflowData();
    
    console.log("📤 Sending workflow data:", JSON.stringify(workflowData, null, 2));
    
    try {
        const response = await fetch('/api/workflow/master', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(workflowData)
        });

        const data = await response.json();
        
        console.log("📥 Response:", data);

        if (response.ok && data.success) {
            alert('✅ Master workflow saved successfully!');
            await loadExistingWorkflow();
        } else {
            const errorMsg = data.detail || JSON.stringify(data);
            console.error("❌ Server error:", errorMsg);
            alert('❌ Error: ' + errorMsg);
        }
    } catch (error) {
        console.error('❌ Network error:', error);
        alert('❌ Network error: ' + error.message);
    }
}

async function submitWorkflow() {
    if (!confirm('Are you sure you want to submit this master workflow? It will be applied to all new contracts.')) {
        return;
    }

    const workflowData = collectWorkflowData();
    
    console.log("📤 Submitting workflow data:", JSON.stringify(workflowData, null, 2));

    try {
        const response = await fetch('/api/workflow/master', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(workflowData)
        });

        const data = await response.json();

        if (response.ok && data.success) {
            alert('✅ Master workflow submitted and activated successfully!');
            window.location.href = '/dashboard';
        } else {
            const errorMsg = data.detail || JSON.stringify(data);
            console.error("❌ Server error:", errorMsg);
            alert('❌ Error: ' + errorMsg);
        }
    } catch (error) {
        console.error('❌ Network error:', error);
        alert('❌ Network error: ' + error.message);
    }
}

function collectWorkflowData() {
    const steps = [];
    
    const stepRows = document.querySelectorAll('.workflow-step');
    console.log(`📊 Collecting data from ${stepRows.length} workflow steps`);
    
    stepRows.forEach((step, index) => {
        const roleSelect = step.querySelector('select[name^="role_"]');
        const deptSelect = step.querySelector('select[name^="department_"]');
        
        const role = roleSelect ? roleSelect.value : '';
        const department = deptSelect ? deptSelect.value : '';
        
        const users = [];
        const selectedTags = step.querySelectorAll('.selected-tag');
        
        selectedTags.forEach(tag => {
            const emailEl = tag.querySelector('.tag-email');
            if (emailEl) {
                const email = emailEl.textContent.trim();
                
                let name = '';
                const textNodes = Array.from(tag.childNodes).filter(node => node.nodeType === Node.TEXT_NODE);
                textNodes.forEach(node => {
                    const text = node.textContent.trim();
                    if (text && text !== '×') {
                        name += text + ' ';
                    }
                });
                name = name.trim();
                
                if (!name) {
                    const clonedTag = tag.cloneNode(true);
                    const emailSpan = clonedTag.querySelector('.tag-email');
                    const icons = clonedTag.querySelectorAll('i');
                    
                    if (emailSpan) emailSpan.remove();
                    icons.forEach(icon => icon.remove());
                    
                    name = clonedTag.textContent.trim() || 'External User';
                }
                
                if (email) {
                    users.push({ name, email });
                }
            }
        });

        if (role) {
            steps.push({
                step_order: index + 1,
                role: role,
                users: users,
                department: department || ''
            });
        }
    });

    const autoEscalation = parseInt(document.getElementById('autoEscalation')?.value) || 48;
    const contractThreshold = parseFloat(document.getElementById('contractThreshold')?.value) || 50000;
    const parallelApproval = document.getElementById('parallelApproval')?.checked || false;
    const skipEmptySteps = document.getElementById('skipEmptySteps')?.checked || false;
    const requireComments = document.getElementById('requireComments')?.checked || false;
    const qatarCompliance = document.getElementById('qatarCompliance')?.checked || false;

    const excludedTypes = [];
    const excludedSection = document.getElementById('excludedTypes');
    if (excludedSection) {
        const checkboxes = excludedSection.querySelectorAll('input[type="checkbox"]:checked');
        checkboxes.forEach(cb => {
            excludedTypes.push(cb.value);
        });
    }

    const result = {
        name: "Master Workflow",
        steps: steps,
        settings: {
            auto_escalation_hours: autoEscalation,
            contract_threshold: contractThreshold,
            parallel_approval: parallelApproval,
            skip_empty_steps: skipEmptySteps,
            require_comments: requireComments,
            qatar_compliance: qatarCompliance
        },
        excluded_contract_types: excludedTypes
    };
    
    console.log("✅ Collected workflow data:", result);
    return result;
}

function goBack() {
    if (confirm('Are you sure you want to go back? Unsaved changes will be lost.')) {
        window.location.href = '/dashboard';
    }
}

// =====================================================
// LOAD EXISTING WORKFLOW
// =====================================================

async function loadExistingWorkflow() {
    try {
        console.log('📥 ===== LOADING WORKFLOW =====');
        
        const response = await fetch('/api/workflow/master', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            console.log('ℹ️ No existing workflow found');
            return false;
        }

        const data = await response.json();
        console.log('📦 API Response:', JSON.stringify(data, null, 2));
        
        if (data.success && data.workflow && data.workflow.steps && data.workflow.steps.length > 0) {
            console.log(`✅ Found ${data.workflow.steps.length} workflow steps`);
            await populateWorkflow(data.workflow);
            return true;
        }
        
        console.log('ℹ️ No workflow steps to load');
        return false;
    } catch (error) {
        console.error('❌ Error loading workflow:', error);
        return false;
    }
}

async function populateWorkflow(workflowData) {
    console.log('📝 ===== POPULATING WORKFLOW =====');
    
    const tbody = document.getElementById('workflowSteps');
    if (!tbody) {
        console.error('❌ workflowSteps tbody not found');
        return;
    }

    // Clear existing rows
    tbody.innerHTML = '';
    stepCount = 0;

    console.log('📊 Workflow data:', workflowData);
    console.log('📊 Steps:', workflowData.steps);

    // Populate settings
    if (workflowData.settings) {
        const settings = workflowData.settings;
            
        const autoEscalationInput = document.getElementById('autoEscalation');
        const contractThresholdInput = document.getElementById('contractThreshold');
        const parallelApprovalInput = document.getElementById('parallelApproval');
        const skipEmptyStepsInput = document.getElementById('skipEmptySteps');
        const requireCommentsInput = document.getElementById('requireComments');
        const qatarComplianceInput = document.getElementById('qatarCompliance');
        
        if (autoEscalationInput) autoEscalationInput.value = settings.auto_escalation_hours || 48;
        if (contractThresholdInput) contractThresholdInput.value = settings.contract_threshold || 50000;
        if (parallelApprovalInput) parallelApprovalInput.checked = settings.parallel_approval !== false;
        if (skipEmptyStepsInput) skipEmptyStepsInput.checked = settings.skip_empty_steps || false;
        if (requireCommentsInput) requireCommentsInput.checked = settings.require_comments !== false;
        if (qatarComplianceInput) qatarComplianceInput.checked = settings.qatar_compliance !== false;

        console.log('✅ Settings populated');
    }

    // Populate excluded types
    if (workflowData.excluded_types && workflowData.excluded_types.length > 0) {
        const excludedSection = document.getElementById('excludedTypes');
        if (excludedSection) {
            const checkboxes = excludedSection.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(cb => {
                if (workflowData.excluded_types.includes(cb.value)) {
                    cb.checked = true;
                }
            });
            console.log('✅ Excluded types populated:', workflowData.excluded_types.length);
        }
    }

    // Populate workflow steps
    console.log(`\n🔄 Adding ${workflowData.steps.length} steps to table...`);
    for (const stepData of workflowData.steps) {
        await addWorkflowStepWithData(stepData);
    }
    
    console.log(`✅ Successfully populated ${workflowData.steps.length} workflow steps`);
}

async function addWorkflowStepWithData(stepData) {
    stepCount++;
    console.log(`\n  📝 Adding Step #${stepCount}:`, JSON.stringify(stepData, null, 2));
    
    const tbody = document.getElementById('workflowSteps');
    const newRow = document.createElement('tr');
    newRow.className = 'workflow-step';
    newRow.innerHTML = `
        <td>
            <div class="step-number">${stepCount}</div>
        </td>
        <td>
            <select class="form-select" name="role_${stepCount}" id="role_${stepCount}">
                <option value="">Select Role</option>
                <option value="reviewer">Reviewer</option>
                <option value="approver">Approver</option>
                <option value="legal_reviewer">Legal Reviewer</option>
                <option value="finance_approver">Finance Approver</option>
                <option value="executive_approver">Executive Approver</option>
                <option value="signatory">Signatory</option>
                <option value="counterparty">Counter-Party</option>
            </select>
        </td>
        <td>
            <div class="user-selection-wrapper">
                <div class="user-input-group">
                    <input type="text" class="form-input user-search" placeholder="Search by name or email..." 
                           onkeyup="searchUsers(this, ${stepCount})" onfocus="showUserDropdown(this, ${stepCount})">
                    <button type="button" class="btn-icon" onclick="addEmailDirectly(${stepCount})">
                        <i class="ti ti-mail-plus"></i>
                    </button>
                </div>
                <div class="user-dropdown" id="userDropdown_${stepCount}" style="display: none;"></div>
                <div class="selected-users" id="selectedUsers_${stepCount}"></div>
            </div>
        </td>
        <td>
            <select class="form-select" name="department_${stepCount}" id="department_${stepCount}">
                <option value="">Select Department</option>
                <option value="legal">Legal</option>
                <option value="finance">Finance</option>
                <option value="operations">Operations</option>
                <option value="procurement">Procurement</option>
                <option value="executive">Executive</option>
            </select>
        </td>
        <td>
            <i class="ti ti-trash remove-step" onclick="removeStep(this)" style="cursor: pointer; color: var(--danger-color); font-size: 20px;"></i>
        </td>
    `;
    
    // IMPORTANT: Append row to tbody FIRST before setting values
    tbody.appendChild(newRow);
    console.log('  ✅ Row added to DOM');

    // Now set the values using getElementById (more reliable)
    
    // Set role value
    if (stepData.role) {
        const roleSelect = document.getElementById(`role_${stepCount}`);
        if (roleSelect) {
            roleSelect.value = stepData.role;
            console.log(`  ✓ Role: "${stepData.role}" → Selected: "${roleSelect.value}"`);
            
            if (!roleSelect.value || roleSelect.value === '') {
                console.log(`  ⚠️ Role "${stepData.role}" not found in options!`);
            }
        } else {
            console.error(`  ❌ Could not find role select with id role_${stepCount}`);
        }
    }

    // Set department value - COMPLETELY FIXED
    if (stepData.department) {
        const deptSelect = document.getElementById(`department_${stepCount}`);
        
        if (deptSelect) {
            console.log(`  🔍 Setting department...`);
            console.log(`     Input value: "${stepData.department}"`);
            console.log(`     Dropdown ID: department_${stepCount}`);
            
            // Set the value directly (should work since data is already lowercase)
            deptSelect.value = stepData.department;
            
            console.log(`     Result: "${deptSelect.value}"`);
            
            if (deptSelect.value === stepData.department) {
                console.log(`  ✅ Department successfully set to: "${deptSelect.value}"`);
            } else {
                console.error(`  ❌ Department NOT set! Expected: "${stepData.department}", Got: "${deptSelect.value}"`);
                
                // Debug: show all available options
                const options = Array.from(deptSelect.options).map(o => `"${o.value}"`);
                console.log(`     Available options: [${options.join(', ')}]`);
            }
        } else {
            console.error(`  ❌ Could not find department select with id department_${stepCount}`);
        }
    } else {
        console.log(`  ℹ️ No department specified for this step`);
    }

    // Add users
    const selectedUsersDiv = document.getElementById(`selectedUsers_${stepCount}`);
    if (stepData.users && Array.isArray(stepData.users) && stepData.users.length > 0) {
        console.log(`  👥 Adding ${stepData.users.length} users`);
        if (selectedUsersDiv) {
            stepData.users.forEach((user, idx) => {
                const userTag = document.createElement('div');
                userTag.className = 'selected-tag';
                userTag.setAttribute('data-user-id', user.id || '');
                userTag.innerHTML = `
                    <i class="ti ti-user"></i>
                    ${user.name}
                    <span class="tag-email">${user.email}</span>
                    <i class="ti ti-x" onclick="removeUser(this)"></i>
                `;
                selectedUsersDiv.appendChild(userTag);
                console.log(`     User ${idx + 1}: ${user.name} (${user.email})`);
            });
            console.log(`  ✅ All users added`);
        }
    } else {
        console.log('  ℹ️ No users for this step');
        if (selectedUsersDiv) {
            const placeholder = document.createElement('span');
            placeholder.style.color = 'var(--text-muted)';
            placeholder.style.fontSize = '0.875rem';
            placeholder.textContent = 'No users selected';
            selectedUsersDiv.appendChild(placeholder);
        }
    }
}

// =====================================================
// INITIALIZE ON PAGE LOAD
// =====================================================

window.addEventListener('DOMContentLoaded', async function() {
    console.log('🚀 ===== INITIALIZING MASTER WORKFLOW =====');
    
    const workflowLoaded = await loadExistingWorkflow();
    
    if (!workflowLoaded) {
        console.log('ℹ️ No existing workflow - adding empty step');
        addWorkflowStep();
    }
    
    console.log('✅ ===== INITIALIZATION COMPLETE =====');
});