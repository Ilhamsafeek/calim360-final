/**
 * Ask Expert Page JavaScript - COMPLETE VERSION
 * File: app/static/js/ask-expert.js
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('ask-expert:2683  Initializing Ask Expert page');
    
    // Initialize page
    loadContracts();
    loadQueryTypes();
    loadAvailableExperts();
    initializeFormHandlers();
    loadDraft();
    initializeFileUpload(); // Add this line
    
    // Character counter
    const queryDetails = document.getElementById('queryDetails');
    const charCount = document.getElementById('charCount');
    if (queryDetails && charCount) {
        queryDetails.addEventListener('input', function() {
            charCount.textContent = this.value.length;
        });
    }
    
    // =====================================================
    // File Upload Functionality - ADD THIS FUNCTION
    // =====================================================
    function initializeFileUpload() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const attachedFiles = document.getElementById('attachedFiles');
        
        if (!dropZone || !fileInput || !attachedFiles) {
            console.log('ask-expert:2683  File upload elements not found');
            return;
        }
        
        // Click to browse files
        dropZone.addEventListener('click', () => {
            fileInput.click();
        });
        
        // Handle file selection
        fileInput.addEventListener('change', handleFileSelect);
        
        // Drag and drop functionality
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropZone.classList.add('drag-over');
        }
        
        function unhighlight() {
            dropZone.classList.remove('drag-over');
        }
        
        // Handle dropped files
        dropZone.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }
        
        function handleFileSelect(e) {
            const files = e.target.files;
            handleFiles(files);
        }
        
        function handleFiles(files) {
            [...files].forEach(file => {
                if (validateFile(file)) {
                    addFilePreview(file);
                }
            });
        }
        
        function validateFile(file) {
            const allowedTypes = [
                'application/pdf', 
                'application/msword', 
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ];
            
            const maxSize = 10 * 1024 * 1024; // 10MB
            
            if (!allowedTypes.includes(file.type)) {
                showToast('File type not supported. Please upload PDF, DOC, DOCX, XLS, or XLSX files.', 'error');
                return false;
            }
            
            if (file.size > maxSize) {
                showToast('File size exceeds 10MB limit.', 'error');
                return false;
            }
            
            return true;
        }
        
        function addFilePreview(file) {
            // Create file preview element
            const fileElement = document.createElement('div');
            fileElement.className = 'file-item';
            fileElement.dataset.fileName = file.name;
            fileElement.dataset.fileSize = file.size;
            fileElement.dataset.fileType = file.type;
            
            fileElement.innerHTML = `
                <div class="file-info">
                    <div class="file-icon">
                        <i class="ti ti-file-text"></i>
                    </div>
                    <div class="file-details">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${formatFileSize(file.size)}</div>
                    </div>
                </div>
                <div class="file-actions">
                    <button class="btn-remove" type="button">
                        <i class="ti ti-x"></i>
                    </button>
                </div>
            `;
            
            attachedFiles.appendChild(fileElement);
            
            // Remove file functionality
            const removeBtn = fileElement.querySelector('.btn-remove');
            removeBtn.addEventListener('click', () => {
                fileElement.remove();
            });
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        console.log('ask-expert:2683  File upload functionality initialized');
    }

    // =====================================================
    // Load Contracts from Database
    // =====================================================
    async function loadContracts() {
        try {
            const response = await fetch('/api/contracts/my-contracts', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                let contracts = [];
                if (Array.isArray(data)) {
                    contracts = data;
                } else if (data.contracts && Array.isArray(data.contracts)) {
                    contracts = data.contracts;
                } else if (data.items && Array.isArray(data.items)) {
                    contracts = data.items;
                }
                
                console.log('ask-expert:2683  Loaded contracts:', contracts.length);
                
                const contractSelect = document.getElementById('contractSelect');
                if (!contractSelect) return;
                
                contractSelect.innerHTML = '<option value="">Select a contract (optional)...</option>';
                
                if (contracts.length === 0) {
                    const option = document.createElement('option');
                    option.value = '';
                    option.disabled = true;
                    option.textContent = 'No contracts available - You can still submit a query';
                    contractSelect.appendChild(option);
                } else {
                    contracts.forEach(contract => {
                        const option = document.createElement('option');
                        option.value = contract.id;
                        const contractNum = contract.contract_number || contract.contract_code || 'N/A';
                        const contractTitle = contract.contract_title || contract.contract_name || contract.title || 'Untitled';
                        option.textContent = `${contractNum} - ${contractTitle}`;
                        contractSelect.appendChild(option);
                    });
                }
                
                const newOption = document.createElement('option');
                newOption.value = 'new';
                newOption.textContent = '+ Create New Contract';
                contractSelect.appendChild(newOption);
                
            } else {
                console.error('ask-expert:2860 Failed to load contracts');
                showToast('Failed to load contracts', 'error');
            }
        } catch (error) {
            console.error('ask-expert:2860 Error loading contracts:', error);
            showToast('Error loading contracts', 'error');
        }
    }
    
    // =====================================================
    // Load Query Types
    // =====================================================
    function loadQueryTypes() {
        const queryTypes = [
            { value: 'review', label: 'Contract Review' },
            { value: 'negotiation', label: 'Negotiation Support' },
            { value: 'compliance', label: 'Compliance Check' },
            { value: 'dispute', label: 'Dispute Resolution' },
            { value: 'drafting', label: 'Clause Drafting' },
            { value: 'risk', label: 'Risk Assessment' },
            { value: 'general', label: 'General Inquiry' },
            { value: 'other', label: 'Other' }
        ];
        
        const queryTypeSelect = document.getElementById('queryType');
        if (!queryTypeSelect) return;
        
        queryTypeSelect.innerHTML = '<option value="">Select query type...</option>';
        
        queryTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type.value;
            option.textContent = type.label;
            queryTypeSelect.appendChild(option);
        });
        
        console.log('ask-expert:2683  Query types populated');
    }
    
    // =====================================================
    // Load Available Experts
    // =====================================================
    async function loadAvailableExperts(expertiseArea = null) {
        try {
            let url = '/api/experts/available';
            if (expertiseArea) {
                url += `?expertise_area=${encodeURIComponent(expertiseArea)}`;
            }
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const experts = await response.json();
                console.log('ask-expert:2683  Loaded experts:', experts.length);
                displayExperts(experts);
            } else {
                console.error('ask-expert:2683  Failed to load experts');
                displayExperts([]);
            }
        } catch (error) {
            console.error('ask-expert:2683  Error loading experts:', error);
            displayExperts([]);
        }
    }
    
    // =====================================================
    // Display Experts
    // =====================================================
    function displayExperts(experts) {
        const expertsContainer = document.querySelector('.experts-list');
        if (!expertsContainer) {
            console.error('ask-expert:2683  Experts list container not found');
            return;
        }
        
        if (experts.length === 0) {
            expertsContainer.innerHTML = `
                <div class="info-box">
                    <div class="info-box-content">
                        <i class="ti ti-info-circle"></i>
                        <span>No experts currently available. Your query will be queued and assigned when an expert becomes available.</span>
                    </div>
                </div>
            `;
            return;
        }
        
        expertsContainer.innerHTML = experts.map(expert => `
            <div class="expert-card-mini" data-expert-id="${expert.expert_id}">
                <div class="expert-mini-header">
                    <div class="expert-mini-avatar">
                        ${expert.profile_picture 
                            ? `<img src="${expert.profile_picture}" alt="${expert.name}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">` 
                            : expert.name.split(' ').map(n => n[0]).join('').substring(0, 2)
                        }
                    </div>
                    <div class="expert-mini-info">
                        <h4>${expert.name}</h4>
                        <div class="expert-mini-title">${expert.specialization || 'Legal Expert'}</div>
                    </div>
                </div>
                <div class="expert-mini-stats">
                    <span class="mini-stat"><strong>${expert.total_consultations || 0}</strong> consults</span>
                    <span class="mini-stat"><strong>${expert.rating ? expert.rating.toFixed(1) : 'N/A'}</strong> rating</span>
                    <span class="mini-stat"><strong>${expert.years_of_experience || 0}y</strong> exp</span>
                </div>
                <div>
                    <span class="expert-availability-badge" style="background: ${expert.availability_status === 'available' ? 'var(--success-bg)' : '#fee2e2'}; color: ${expert.availability_status === 'available' ? 'var(--success-color)' : '#991b1b'};">
                        <span class="availability-dot"></span> ${expert.availability_status === 'available' ? 'Available Now' : 'Busy'}
                    </span>
                </div>
            </div>
        `).join('');
        
        // Add click handlers
        document.querySelectorAll('.expert-card-mini').forEach(card => {
            card.addEventListener('click', function() {
                document.querySelectorAll('.expert-card-mini').forEach(c => c.classList.remove('selected'));
                this.classList.add('selected');
                console.log('ask-expert:2683  Expert selected:', this.dataset.expertId);
            });
        });
    }
    
    // =====================================================
    // Form Handlers
    // =====================================================
    function initializeFormHandlers() {
        // Priority selection
        document.querySelectorAll('.priority-option').forEach(option => {
            option.addEventListener('click', function() {
                document.querySelectorAll('.priority-option').forEach(o => o.classList.remove('selected'));
                this.classList.add('selected');
            });
        });
        
        // Session type selection
        document.querySelectorAll('.session-option').forEach(option => {
            option.addEventListener('click', function() {
                document.querySelectorAll('.session-option').forEach(o => o.classList.remove('selected'));
                this.classList.add('selected');
            });
        });
        
        // Expertise area chips
        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', function() {
                this.classList.toggle('selected');
                updateExpertRecommendations();
            });
        });
        
        // Form submission
        const form = document.getElementById('expertQueryForm');
        if (form) {
            form.addEventListener('input', saveDraft);
            form.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Simple validation
    const queryType = document.getElementById('queryType').value;
    const querySubject = document.getElementById('querySubject').value;
    const queryDetails = document.getElementById('queryDetails').value;
    
    if (!queryType || !querySubject || !queryDetails) {
        showToast('Please fill in all required fields', 'error');
        return;
    }
    
    if (queryDetails.length < 10) {
        showToast('Please provide more details (at least 10 characters)', 'error');
        return;
    }
    
    // Get selected expert (if any)
    const selectedExpert = document.querySelector('.expert-card-mini.selected');
    const expertId = selectedExpert ? selectedExpert.dataset.expertId : null;
    
    // Get selected priority
    const selectedPriority = document.querySelector('.priority-option.selected');
    const priority = selectedPriority ? selectedPriority.dataset.priority : 'normal';
    
    // Get selected session type
    const selectedSession = document.querySelector('.session-option.selected');
    const sessionType = selectedSession ? selectedSession.dataset.type : 'chat';
    
    // Get selected expertise areas
    const selectedExpertise = Array.from(document.querySelectorAll('.chip.selected'))
        .map(chip => chip.dataset.expertise);
    
    // Prepare data
    const formData = {
        contract_id: document.getElementById('contractSelect')?.value || null,
        query_type: queryType,
        subject: querySubject,
        question: queryDetails,
        expertise_areas: selectedExpertise,
        priority: priority,
        preferred_language: document.querySelector('select.form-control')?.value || 'en',
        session_type: sessionType
    };
    
    try {
        // Show loading
        document.getElementById('loadingOverlay').classList.add('active');
        
        // Submit query to backend
        const response = await fetch('/api/experts/queries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        // Hide loading
        document.getElementById('loadingOverlay').classList.remove('active');
        
        if (response.ok && data.success) {
            // Clear draft if exists
            localStorage.removeItem('expertQueryDraft');
            
            // Show success message
            showToast(`Query submitted successfully! Code: ${data.query_code}`, 'success');
            
            // REDIRECT TO CONSULTATION ROOM
            setTimeout(() => {
                // Generate session ID
                const sessionId = 'SES-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9).toUpperCase();
                
                // Redirect with query_id and session_id
                if (expertId) {
                    // If expert selected, go to consultation room with expert
                    window.location.href = `/consultation-room?expert=${expertId}&session=${sessionId}&query=${data.query_id}`;
                } else {
                    // No expert selected, still go to consultation room (system will assign)
                    window.location.href = `/consultation-room?session=${sessionId}&query=${data.query_id}`;
                }
            }, 1000);
            
        } else {
            throw new Error(data.message || 'Failed to submit query');
        }
        
    } catch (error) {
        document.getElementById('loadingOverlay').classList.remove('active');
        console.error('Error submitting query:', error);
        showToast(`Failed to submit query: ${error.message}`, 'error');
    }
});
        }
        
        // Reset button
        const resetButton = document.querySelector('.btn-secondary');
        if (resetButton) {
            resetButton.addEventListener('click', function(e) {
                e.preventDefault();
                if (confirm('Are you sure you want to reset the form?')) {
                    document.getElementById('expertQueryForm').reset();
                    document.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
                    document.querySelector('.priority-option[data-priority="standard"]')?.classList.add('selected');
                    document.querySelector('.session-option[data-type="chat"]')?.classList.add('selected');
                    localStorage.removeItem('expertQueryDraft');
                    showToast('Form reset successfully', 'info');
                }
            });
        }
    }
    
    // =====================================================
    // Form Submission
    // =====================================================
    async function handleFormSubmit(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }
        
        const selectedExpert = document.querySelector('.expert-card-mini.selected');
        const selectedPriority = document.querySelector('.priority-option.selected');
        const selectedSession = document.querySelector('.session-option.selected');
        const selectedExpertise = Array.from(document.querySelectorAll('.chip.selected'))
            .map(chip => chip.dataset.expertise);
        
        const contractSelect = document.getElementById('contractSelect');
        const contractId = contractSelect.value && contractSelect.value !== 'new' ? contractSelect.value : null;
        
        const formData = {
            contract_id: contractId,
            query_type: document.getElementById('queryType').value,
            subject: document.getElementById('querySubject').value,
            question: document.getElementById('queryDetails').value,
            expertise_areas: selectedExpertise.length > 0 ? selectedExpertise : ['general'],
            priority: selectedPriority ? selectedPriority.dataset.priority : 'standard',
            preferred_language: 'en',
            session_type: selectedSession ? selectedSession.dataset.type : 'chat',
            preferred_expert_id: selectedExpert ? selectedExpert.dataset.expertId : null
        };
        
        console.log('ask-expert:2683  Submitting query:', formData);
        
        try {
            const loadingOverlay = document.getElementById('loadingOverlay');
            if (loadingOverlay) loadingOverlay.classList.add('active');
            
            const response = await fetch('/api/experts/queries', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            
            if (loadingOverlay) loadingOverlay.classList.remove('active');
            
            if (response.ok && data.success) {
                localStorage.removeItem('expertQueryDraft');
                showToast(`Query submitted successfully! Query Code: ${data.query_code}`, 'success');
                console.log('ask-expert:2683  Query submitted:', data.query_code);
                
                setTimeout(() => {
                    window.location.href = `/consultations?highlight=${data.query_id}`;
                }, 1500);
            } else {
                throw new Error(data.detail || data.message || 'Failed to submit query');
            }
        } catch (error) {
            const loadingOverlay = document.getElementById('loadingOverlay');
            if (loadingOverlay) loadingOverlay.classList.remove('active');
            console.error('ask-expert:2683  Error submitting query:', error);
            showToast(`Failed to submit query: ${error.message}`, 'error');
        }
    }
    
    // =====================================================
    // Form Validation
    // =====================================================
    function validateForm() {
        const queryType = document.getElementById('queryType');
        const querySubject = document.getElementById('querySubject');
        const queryDetails = document.getElementById('queryDetails');
        
        let valid = true;
        const errors = [];
        
        if (!queryType || !queryType.value) {
            if (queryType) queryType.classList.add('error');
            errors.push('Please select a query type');
            valid = false;
        } else {
            if (queryType) queryType.classList.remove('error');
        }
        
        if (!querySubject || !querySubject.value.trim()) {
            if (querySubject) querySubject.classList.add('error');
            errors.push('Please enter a subject');
            valid = false;
        } else {
            if (querySubject) querySubject.classList.remove('error');
        }
        
        if (!queryDetails || !queryDetails.value.trim()) {
            if (queryDetails) queryDetails.classList.add('error');
            errors.push('Please enter query details');
            valid = false;
        } else {
            if (queryDetails) queryDetails.classList.remove('error');
        }
        
        if (!valid) {
            showToast(errors.join(', '), 'error');
        }
        
        return valid;
    }
    
    // =====================================================
    // Update Expert Recommendations
    // =====================================================
    function updateExpertRecommendations() {
        const selectedExpertise = Array.from(document.querySelectorAll('.chip.selected'))
            .map(c => c.dataset.expertise);
        
        if (selectedExpertise.length > 0) {
            loadAvailableExperts(selectedExpertise[0]);
        } else {
            loadAvailableExperts();
        }
    }
    
    // =====================================================
    // Draft Management
    // =====================================================
    function saveDraft() {
        const draft = {
            contract_id: document.getElementById('contractSelect')?.value || '',
            query_type: document.getElementById('queryType')?.value || '',
            subject: document.getElementById('querySubject')?.value || '',
            question: document.getElementById('queryDetails')?.value || '',
            timestamp: new Date().toISOString()
        };
        localStorage.setItem('expertQueryDraft', JSON.stringify(draft));
    }
    
    function loadDraft() {
        const draftStr = localStorage.getItem('expertQueryDraft');
        if (!draftStr) return;
        
        try {
            const draft = JSON.parse(draftStr);
            const draftAge = Date.now() - new Date(draft.timestamp).getTime();
            const maxAge = 24 * 60 * 60 * 1000;
            
            if (draftAge > maxAge) {
                localStorage.removeItem('expertQueryDraft');
                return;
            }
            
            if (draft.contract_id && document.getElementById('contractSelect')) {
                document.getElementById('contractSelect').value = draft.contract_id;
            }
            if (draft.query_type && document.getElementById('queryType')) {
                document.getElementById('queryType').value = draft.query_type;
            }
            if (draft.subject && document.getElementById('querySubject')) {
                document.getElementById('querySubject').value = draft.subject;
            }
            if (draft.question && document.getElementById('queryDetails')) {
                document.getElementById('queryDetails').value = draft.question;
            }
            
            showToast('Draft restored', 'info');
        } catch (error) {
            localStorage.removeItem('expertQueryDraft');
        }
    }
    
    // =====================================================
    // Toast Notifications
    // =====================================================
    function showToast(message, type = 'info') {
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            toastContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 12px;';
            document.body.appendChild(toastContainer);
        }
        
        const toast = document.createElement('div');
        toast.style.cssText = `
            background: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 300px;
            opacity: 0;
            transform: translateX(400px);
            transition: all 0.3s ease;
            border-left: 4px solid ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
        `;
        
        const iconMap = {
            'success': 'check-circle',
            'error': 'alert-circle',
            'warning': 'alert-triangle',
            'info': 'info-circle'
        };
        
        toast.innerHTML = `
            <i class="ti ti-${iconMap[type]}" style="font-size: 24px; color: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};"></i>
            <span style="flex: 1; font-size: 14px; color: #333;">${message}</span>
        `;
        
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        }, 100);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(400px)';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
    
    console.log('ask-expert:2683  Ask Expert page initialization complete');
});