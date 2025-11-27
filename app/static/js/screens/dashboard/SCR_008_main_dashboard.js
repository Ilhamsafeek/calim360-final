/**
 * SCR-008 Main Dashboard (Initiator View) JavaScript
 * Handles all dashboard interactions and functionality
 */

// Global variables
let currentTab = 'drafting';
let searchTimeout;
let contracts = [];
let filteredContracts = [];

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    loadContracts();
    setupEventListeners();
});

/**
 * Initialize dashboard components
 */
function initializeDashboard() {
    // Initialize tabs
    const tabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });

    // Initialize floating menu
    initializeFloatingMenu();
    
    // Initialize search
    initializeSearch();
    
    // Initialize tooltips
    initializeTooltips();
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Search functionality
    const searchInput = document.getElementById('contractSearch');
    const clearSearchBtn = document.getElementById('clearSearch');
    
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
    
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', clearSearch);
    }

    // Filter button
    const filterBtn = document.getElementById('searchFiltersBtn');
    if (filterBtn) {
        filterBtn.addEventListener('click', () => {
            showModal('searchFiltersModal');
        });
    }

    // Close modal when clicking outside
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            closeModal(e.target.id);
        }
        
        // Close dropdown menus when clicking outside
        if (!e.target.closest('.dropdown')) {
            closeAllDropdowns();
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

/**
 * Handle keyboard shortcuts
 */
function handleKeyboardShortcuts(e) {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('contractSearch');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to close modals and menus
    if (e.key === 'Escape') {
        const activeModal = document.querySelector('.modal.show');
        if (activeModal) {
            closeModal(activeModal.id);
        }
        closeAllDropdowns();
    }
}

/**
 * Switch between tabs
 */
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    currentTab = tabName;
    
    // Load tab-specific data
    loadTabData(tabName);
}

/**
 * Load data for specific tab
 */
function loadTabData(tabName) {
    switch(tabName) {
        case 'drafting':
            loadDraftingContracts();
            break;
        case 'negotiation':
            loadNegotiationContracts();
            break;
        case 'operations':
            loadOperationsContracts();
            break;
    }
}

/**
 * Load contracts from API
 */
async function loadContracts() {
    try {
        showLoading();
        
        const response = await fetch('/api/contracts/dashboard', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            contracts = data.contracts || [];
            updateDashboardStats(data.stats);
            updateContractCounts(data.counts);
            renderContracts();
        } else {
            showError('Failed to load contracts');
        }
    } catch (error) {
        console.error('Error loading contracts:', error);
        showError('Error loading contracts');
    } finally {
        hideLoading();
    }
}

/**
 * Load drafting contracts
 */
function loadDraftingContracts() {
    const draftingContracts = contracts.filter(contract => 
        ['draft', 'in-progress', 'internal-review'].includes(contract.status)
    );
    renderContractsGrid(draftingContracts, 'drafting-tab');
}

/**
 * Load negotiation contracts
 */
function loadNegotiationContracts() {
    const negotiationContracts = contracts.filter(contract => 
        ['negotiation', 'counter-party-review', 'under-negotiation'].includes(contract.status)
    );
    renderContractsGrid(negotiationContracts, 'negotiation-tab');
}

/**
 * Load operations contracts
 */
function loadOperationsContracts() {
    const operationsContracts = contracts.filter(contract => 
        ['approved', 'signed', 'active', 'executed'].includes(contract.status)
    );
    renderContractsGrid(operationsContracts, 'operations-tab');
}

/**
 * Render contracts in grid format
 */
function renderContractsGrid(contractsList, containerId) {
    const container = document.querySelector(`#${containerId} .contracts-grid`);
    if (!container) return;

    // Group contracts by project
    const projectGroups = groupContractsByProject(contractsList);
    
    let html = '';
    
    Object.keys(projectGroups).forEach(projectName => {
        const projectContracts = projectGroups[projectName];
        html += renderProjectSection(projectName, projectContracts);
    });

    // Show empty state if no contracts
    if (contractsList.length === 0) {
        html = `
            <div class="empty-state">
                <div class="empty-icon">
                    <i class="ti ti-file-plus"></i>
                </div>
                <h3>No Contracts Found</h3>
                <p>No contracts found in this section. Create a new contract to get started.</p>
                <button class="btn btn-primary" onclick="createNewContract()">
                    <i class="ti ti-plus"></i>
                    Create New Contract
                </button>
            </div>
        `;
    }

    container.innerHTML = html;
}

/**
 * Group contracts by project
 */
function groupContractsByProject(contractsList) {
    const groups = {};
    contractsList.forEach(contract => {
        const projectName = contract.project_name || 'Unassigned';
        if (!groups[projectName]) {
            groups[projectName] = [];
        }
        groups[projectName].push(contract);
    });
    return groups;
}

/**
 * Render project section with contracts
 */
function renderProjectSection(projectName, projectContracts) {
    const contractsHtml = projectContracts.map(contract => renderContractCard(contract)).join('');
    
    return `
        <div class="project-section" data-project="${projectName}">
            <div class="project-header">
                <div class="project-info">
                    <i class="ti ti-folder project-icon"></i>
                    <h3 class="project-name">${projectName}</h3>
                    <span class="project-count">(${projectContracts.length} contracts)</span>
                </div>
                <div class="project-actions">
                    <button class="btn-icon" onclick="toggleProject('${projectName}')">
                        <i class="ti ti-chevron-up project-toggle"></i>
                    </button>
                </div>
            </div>
            <div class="contracts-container">
                ${contractsHtml}
                <div class="contract-card add-contract-card" onclick="createContractInProject('${projectName}')">
                    <div class="add-contract-content">
                        <div class="add-contract-icon">
                            <i class="ti ti-plus"></i>
                        </div>
                        <h4>Add New Contract</h4>
                        <p>Create a new contract in ${projectName}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Render individual contract card
 */
function renderContractCard(contract) {
    const progress = contract.progress || 0;
    const createdDate = contract.created_at ? new Date(contract.created_at).toLocaleDateString() : 'N/A';
    
    return `
        <div class="contract-card" data-contract-id="${contract.id}" data-status="${contract.status}">
            <div class="contract-header">
                <div class="contract-icon">
                    <i class="ti ti-file-text"></i>
                </div>
                <div class="contract-info">
                    <h4 class="contract-title">${contract.title}</h4>
                    <p class="contract-id">Contract No. ${contract.internal_code}</p>
                </div>
                <div class="contract-status">
                    <span class="status-badge status-${contract.status.toLowerCase().replace(' ', '-')}">
                        ${formatStatus(contract.status)}
                    </span>
                </div>
            </div>
            <div class="contract-body">
                <div class="contract-details">
                    <div class="detail-row">
                        <span class="detail-label">Type:</span>
                        <span class="detail-value">${contract.type || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Category:</span>
                        <span class="detail-value">${contract.category || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Created:</span>
                        <span class="detail-value">${createdDate}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Progress:</span>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progress}%"></div>
                            <span class="progress-text">${progress}%</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="contract-actions">
                <button class="action-btn" onclick="openContract(${contract.id})" title="Open Contract">
                    <i class="ti ti-eye"></i>
                </button>
                <button class="action-btn" onclick="editContract(${contract.id})" title="Edit Contract">
                    <i class="ti ti-edit"></i>
                </button>
                <button class="action-btn" onclick="workflowSetup(${contract.id})" title="Workflow Setup">
                    <i class="ti ti-settings"></i>
                </button>
                <button class="action-btn" onclick="initiateWorkflow(${contract.id})" title="Initiate Workflow">
                    <i class="ti ti-play"></i>
                </button>
                <button class="action-btn" onclick="attachDocuments(${contract.id})" title="Attach Documents">
                    <i class="ti ti-paperclip"></i>
                </button>
                <div class="dropdown">
                    <button class="action-btn dropdown-toggle" onclick="toggleContractMenu(${contract.id})">
                        <i class="ti ti-dots-vertical"></i>
                    </button>
                    <div class="dropdown-menu" id="menu-${contract.id}">
                        <a href="#" onclick="duplicateContract(${contract.id})">
                            <i class="ti ti-copy"></i>
                            Duplicate
                        </a>
                        <a href="#" onclick="shareContract(${contract.id})">
                            <i class="ti ti-share"></i>
                            Share
                        </a>
                        <a href="#" onclick="auditTrail(${contract.id})">
                            <i class="ti ti-history"></i>
                            Audit Trail
                        </a>
                        <hr>
                        <a href="#" onclick="deleteContract(${contract.id})" class="danger">
                            <i class="ti ti-trash"></i>
                            Delete
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Format contract status for display
 */
function formatStatus(status) {
    return status.split('-').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

/**
 * Toggle project section collapse/expand
 */
function toggleProject(projectName) {
    const projectSection = document.querySelector(`[data-project="${projectName}"]`);
    if (projectSection) {
        projectSection.classList.toggle('collapsed');
        
        const toggle = projectSection.querySelector('.project-toggle');
        if (toggle) {
            toggle.style.transform = projectSection.classList.contains('collapsed') 
                ? 'rotate(180deg)' : 'rotate(0deg)';
        }
    }
}

/**
 * Toggle contract dropdown menu
 */
function toggleContractMenu(contractId) {
    const menu = document.getElementById(`menu-${contractId}`);
    if (menu) {
        // Close all other menus first
        closeAllDropdowns();
        menu.classList.toggle('show');
    }
}

/**
 * Close all dropdown menus
 */
function closeAllDropdowns() {
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
        menu.classList.remove('show');
    });
}

/**
 * Search functionality
 */
function initializeSearch() {
    const searchInput = document.getElementById('contractSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value;
            const clearBtn = document.getElementById('clearSearch');
            
            if (query.length > 0) {
                clearBtn.style.display = 'block';
            } else {
                clearBtn.style.display = 'none';
            }
            
            // Debounce search
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300);
        });
    }
}

/**
 * Perform search
 */
function performSearch(query = '') {
    if (!query) {
        query = document.getElementById('contractSearch').value;
    }
    
    if (query.length === 0) {
        // Show all contracts
        filteredContracts = contracts;
    } else {
        // Filter contracts based on search query
        filteredContracts = contracts.filter(contract => {
            const searchText = query.toLowerCase();
            return (
                contract.title.toLowerCase().includes(searchText) ||
                contract.internal_code.toLowerCase().includes(searchText) ||
                contract.type.toLowerCase().includes(searchText) ||
                contract.category.toLowerCase().includes(searchText) ||
                contract.project_name.toLowerCase().includes(searchText)
            );
        });
    }
    
    // Re-render current tab with filtered contracts
    loadTabData(currentTab);
    
    // Update search results count
    updateSearchResults(query, filteredContracts.length);
}

/**
 * Clear search
 */
function clearSearch() {
    const searchInput = document.getElementById('contractSearch');
    const clearBtn = document.getElementById('clearSearch');
    
    if (searchInput) {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        searchInput.focus();
    }
    
    // Reset filtered contracts
    filteredContracts = contracts;
    loadTabData(currentTab);
    updateSearchResults('', contracts.length);
}

/**
 * Update search results display
 */
function updateSearchResults(query, count) {
    // You can add a search results indicator here if needed
    console.log(`Search: "${query}" - ${count} results found`);
}

/**
 * Contract Actions
 */

// Create new contract
function createNewContract() {
    window.location.href = '/screens/drafting/contract-creation';
}

// Create contract in specific project
function createContractInProject(projectName) {
    window.location.href = `/screens/drafting/contract-creation?project=${encodeURIComponent(projectName)}`;
}

// Open contract for viewing
function openContract(contractId) {
    window.location.href = `/screens/drafting/contract-editor/${contractId}`;
}

// Edit contract
function editContract(contractId) {
    window.location.href = `/screens/drafting/contract-editor/${contractId}?mode=edit`;
}

// Workflow setup
function workflowSetup(contractId) {
    showModal('workflowSetupModal', { contractId });
}

// Initiate workflow
function initiateWorkflow(contractId) {
    if (confirm('Are you sure you want to initiate the workflow for this contract?')) {
        // API call to initiate workflow
        fetch(`/api/contracts/${contractId}/workflow/initiate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccess('Workflow initiated successfully');
                loadContracts(); // Refresh data
            } else {
                showError('Failed to initiate workflow');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error initiating workflow');
        });
    }
}

// Attach documents
function attachDocuments(contractId) {
    showModal('attachDocumentsModal', { contractId });
}

// Duplicate contract
function duplicateContract(contractId) {
    if (confirm('Are you sure you want to duplicate this contract?')) {
        fetch(`/api/contracts/${contractId}/duplicate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccess('Contract duplicated successfully');
                loadContracts(); // Refresh data
            } else {
                showError('Failed to duplicate contract');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error duplicating contract');
        });
    }
}

// Share contract
function shareContract(contractId) {
    showModal('shareContractModal', { contractId });
}

// Show audit trail
function auditTrail(contractId) {
    window.location.href = `/screens/audit/contract-audit/${contractId}`;
}

// Delete contract
function deleteContract(contractId) {
    if (confirm('Are you sure you want to delete this contract? This action cannot be undone.')) {
        fetch(`/api/contracts/${contractId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccess('Contract deleted successfully');
                loadContracts(); // Refresh data
            } else {
                showError('Failed to delete contract');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Error deleting contract');
        });
    }
}

/**
 * Floating Menu Actions (Based on Business Process Flow)
 */

// Send for internal review
function sendForInternalReview() {
    showModal('internalReviewModal');
}

// Perform review analysis
function performReviewAnalysis() {
    showModal('reviewAnalysisModal');
}

// Perform clause analysis
function performClauseAnalysis() {
    showModal('clauseAnalysisModal');
}

// Upload documents
function uploadDocuments() {
    showModal('uploadDocumentsModal');
}

// Ask an expert
function askAnExpert() {
    showModal('askExpertModal');
}

/**
 * Modal Functions
 */

// Show modal
function showModal(modalId, data = {}) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        
        // Trigger modal-specific initialization if needed
        initializeModal(modalId, data);
    }
}

// Close modal
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
}

// Initialize specific modal
function initializeModal(modalId, data) {
    switch(modalId) {
        case 'searchFiltersModal':
            initializeSearchFilters();
            break;
        case 'workflowSetupModal':
            initializeWorkflowSetup(data.contractId);
            break;
        // Add other modal initializations as needed
    }
}

/**
 * Filter Functions
 */

// Initialize search filters
function initializeSearchFilters() {
    // Set current filter values
    // Implementation depends on your filter requirements
}

// Apply filters
function applyFilters() {
    const formData = new FormData(document.querySelector('#searchFiltersModal form'));
    const filters = Object.fromEntries(formData.entries());
    
    // Apply filters to contracts
    filteredContracts = contracts.filter(contract => {
        // Implement filter logic based on form data
        return true; // Placeholder
    });
    
    loadTabData(currentTab);
    closeModal('searchFiltersModal');
    showSuccess('Filters applied successfully');
}

// Clear filters
function clearFilters() {
    const form = document.querySelector('#searchFiltersModal form');
    if (form) {
        form.reset();
    }
    
    filteredContracts = contracts;
    loadTabData(currentTab);
    showSuccess('Filters cleared');
}

/**
 * Utility Functions
 */

// Get auth token from localStorage or cookies
function getAuthToken() {
    return localStorage.getItem('auth_token') || '';
}

// Update dashboard stats
function updateDashboardStats(stats) {
    const statElements = {
        'active_contracts': document.querySelector('.stat-item:nth-child(1) .stat-number'),
        'pending_review': document.querySelector('.stat-item:nth-child(2) .stat-number'),
        'completed': document.querySelector('.stat-item:nth-child(3) .stat-number')
    };
    
    Object.keys(statElements).forEach(key => {
        if (statElements[key] && stats[key] !== undefined) {
            statElements[key].textContent = stats[key];
        }
    });
}

// Update contract counts in tabs
function updateContractCounts(counts) {
    const countElements = {
        'drafting': document.querySelector('[data-tab="drafting"] .tab-badge'),
        'negotiation': document.querySelector('[data-tab="negotiation"] .tab-badge'),
        'operations': document.querySelector('[data-tab="operations"] .tab-badge')
    };
    
    Object.keys(countElements).forEach(key => {
        if (countElements[key] && counts[key] !== undefined) {
            countElements[key].textContent = counts[key];
        }
    });
}

// Show loading state
function showLoading() {
    // Add loading spinner or skeleton
    console.log('Loading...');
}

// Hide loading state
function hideLoading() {
    console.log('Loading complete');
}

// Show success message
function showSuccess(message) {
    // Implement toast notification
    console.log('Success:', message);
}

// Show error message
function showError(message) {
    // Implement toast notification
    console.error('Error:', message);
}

// Initialize tooltips
function initializeTooltips() {
    // Add tooltip functionality if needed
    console.log('Tooltips initialized');
}

/**
 * View Options
 */
function showViewOptions() {
    // Show view options modal (grid/list view, sorting, etc.)
    showModal('viewOptionsModal');
}