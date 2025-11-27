// =====================================================
// FILE: app/static/js/modals/drafting/MOD_017_save_contract.js
// Enhanced Save Contract Modal with Dynamic Data
// =====================================================

class SaveContractModal {
    constructor() {
        this.projects = [];
        this.companies = [];
        this.isLoading = false;
        this.init();
    }

    init() {
        // Bind form submission
        const form = document.getElementById('saveContractForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        // Load data when modal is shown
        this.bindModalEvents();

        // Bind counterparty selection events
        this.bindCounterpartyEvents();
    }

    bindModalEvents() {
        // Override the openModal function to load data when Save Contract modal opens
        const originalOpenModal = window.openModal;
        window.openModal = (modalId) => {
            if (originalOpenModal) {
                originalOpenModal(modalId);
            } else {
                document.getElementById(modalId).classList.add('show');
            }
            
            if (modalId === 'saveContractModal') {
                this.loadModalData();
            }
        };
    }

    bindCounterpartyEvents() {
        const existingSelect = document.getElementById('existingCounterparty');
        const emailInput = document.getElementById('counterpartyEmail');

        if (existingSelect && emailInput) {
            // Clear email when selecting existing company
            existingSelect.addEventListener('change', () => {
                if (existingSelect.value) {
                    emailInput.value = '';
                }
            });

            // Clear selection when typing email
            emailInput.addEventListener('input', () => {
                if (emailInput.value) {
                    existingSelect.value = '';
                }
            });
        }
    }

    async loadModalData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        
        try {
            // Load projects and companies in parallel
            await Promise.all([
                this.loadProjects(),
                this.loadCompanies()
            ]);
        } catch (error) {
            console.error('Error loading modal data:', error);
            this.showError('Failed to load data. Please try again.');
        } finally {
            this.isLoading = false;
        }
    }

    async loadProjects() {
        try {
            const response = await fetch('/api/projects', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch projects');
            }

            const data = await response.json();
            this.projects = data.projects || data || [];
            this.populateProjectDropdown();

        } catch (error) {
            console.error('Error loading projects:', error);
            this.projects = [];
            this.populateProjectDropdown();
        }
    }

    async loadCompanies() {
        try {
            const response = await fetch('/api/companies', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch companies');
            }

            const data = await response.json();
            this.companies = data.companies || data || [];
            this.populateCompanyDropdown();

        } catch (error) {
            console.error('Error loading companies:', error);
            this.companies = [];
            this.populateCompanyDropdown();
        }
    }

    populateProjectDropdown() {
        const select = document.getElementById('projectAssignment');
        if (!select) return;

        // Clear existing options
        select.innerHTML = '';

        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select project (optional)';
        select.appendChild(defaultOption);

        // Add projects
        this.projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = `${project.project_name || project.title} (${project.project_code || project.code})`;
            select.appendChild(option);
        });

        // Add "Create New Project" option
        const createOption = document.createElement('option');
        createOption.value = 'create_new';
        createOption.textContent = 'Create New Project...';
        createOption.style.fontStyle = 'italic';
        select.appendChild(createOption);

        console.log(`Loaded ${this.projects.length} projects`);
    }

    populateCompanyDropdown() {
        const select = document.getElementById('existingCounterparty');
        if (!select) return;

        // Clear existing options except the first one
        select.innerHTML = '<option value="">Select existing company...</option>';

        // Add companies
        this.companies.forEach(company => {
            const option = document.createElement('option');
            option.value = company.id;
            option.textContent = company.company_name || company.name;
            
            // Add additional info if available
            if (company.email) {
                option.textContent += ` (${company.email})`;
            }
            
            select.appendChild(option);
        });

        console.log(`Loaded ${this.companies.length} companies`);
    }

    async handleSubmit(e) {
        e.preventDefault();

        const formData = this.getFormData();
        
        // Validate required fields
        if (!formData.contractName.trim()) {
            this.showError('Contract name is required');
            return;
        }

        if (!formData.counterpartyId && !formData.counterpartyEmail) {
            this.showError('Please select a counterparty or enter an email address');
            return;
        }

        try {
            this.setSubmitLoading(true);
            
            const result = await this.saveContract(formData);
            
            if (result.success) {
                this.showSuccess('Contract saved successfully!');
                this.closeModal();
                
                // Redirect to contract editor if contract ID is provided
                if (result.contract_id) {
                    setTimeout(() => {
                        window.location.href = `/contract/edit/${result.contract_id}`;
                    }, 1000);
                }
            } else {
                this.showError(result.message || 'Failed to save contract');
            }

        } catch (error) {
            console.error('Error saving contract:', error);
            this.showError('Failed to save contract. Please try again.');
        } finally {
            this.setSubmitLoading(false);
        }
    }

    getFormData() {
        const contractName = document.getElementById('contractName').value;
        const projectId = document.getElementById('projectAssignment').value;
        const counterpartyId = document.getElementById('existingCounterparty').value;
        const counterpartyEmail = document.getElementById('counterpartyEmail').value;
        const tags = document.getElementById('contractTags').value;

        return {
            contractName: contractName.trim(),
            projectId: projectId === 'create_new' ? null : projectId,
            counterpartyId: counterpartyId || null,
            counterpartyEmail: counterpartyEmail.trim() || null,
            tags: tags.trim(),
            createNewProject: projectId === 'create_new'
        };
    }

    async saveContract(formData) {
        const contractData = {
            contract_title: formData.contractName,
            project_id: formData.projectId ? parseInt(formData.projectId) : null,
            profile_type: 'client', // Default profile type
            tags: formData.tags ? formData.tags.split(',').map(tag => tag.trim()) : []
        };

        // Create contract
        const contractResponse = await fetch('/api/contracts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            body: JSON.stringify(contractData)
        });

        if (!contractResponse.ok) {
            const error = await contractResponse.json();
            throw new Error(error.detail || 'Failed to create contract');
        }

        const contract = await contractResponse.json();

        // Handle counterparty if provided
        if (formData.counterpartyId || formData.counterpartyEmail) {
            await this.addCounterparty(contract.id, formData);
        }

        return {
            success: true,
            contract_id: contract.id,
            message: 'Contract created successfully'
        };
    }

    async addCounterparty(contractId, formData) {
        const counterpartyData = {
            contract_id: contractId,
            party_type: 'counterparty'
        };

        if (formData.counterpartyId) {
            // Use existing company
            counterpartyData.company_id = parseInt(formData.counterpartyId);
        } else if (formData.counterpartyEmail) {
            // Create new counterparty with email
            counterpartyData.email = formData.counterpartyEmail;
            
            // Extract company name from email domain if possible
            const domain = formData.counterpartyEmail.split('@')[1];
            counterpartyData.party_name = domain.split('.')[0].charAt(0).toUpperCase() + domain.split('.')[0].slice(1);
        }

        const response = await fetch(`/api/contracts/${contractId}/parties`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            body: JSON.stringify(counterpartyData)
        });

        if (!response.ok) {
            console.warn('Failed to add counterparty, but contract was created');
        }
    }

    getAuthToken() {
        return localStorage.getItem('access_token') || 
               localStorage.getItem('token') || 
               sessionStorage.getItem('access_token') || 
               this.getCookie('access_token') || 
               '';
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    setSubmitLoading(loading) {
        const submitBtn = document.querySelector('#saveContractForm button[type="submit"]');
        if (submitBtn) {
            if (loading) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="ti ti-loader" style="animation: spin 1s linear infinite; margin-right: 0.5rem;"></i>Saving...';
            } else {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Save & Continue';
            }
        }
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            padding: 1rem;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease;
        `;

        // Set background color based on type
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            info: '#17a2b8'
        };
        notification.style.backgroundColor = colors[type] || colors.info;
        
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="ti ti-${type === 'success' ? 'check' : type === 'error' ? 'x' : 'info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => {
                    notification.parentNode.removeChild(notification);
                }, 300);
            }
        }, 5000);
    }

    closeModal() {
        const modal = document.getElementById('saveContractModal');
        if (modal) {
            modal.classList.remove('show');
        }
        
        // Reset form
        const form = document.getElementById('saveContractForm');
        if (form) {
            form.reset();
        }
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.saveContractModal = new SaveContractModal();
});

// Export for use in other files
window.SaveContractModal = SaveContractModal;