// =====================================================
// FILE: app/static/js/screens/drafting/SCR_017_clause_library.js
// Clause Library Page - Complete Working Version
// =====================================================

const API_BASE = '/api/clause-library';

// Current state variables
let currentCategory = 'all';
let currentSearchTerm = '';
let currentSort = 'recent';
let currentClauseId = null;
let allClauses = [];

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing Clause Library...');
    loadClausesFromAPI();
    
    // Add search input listener
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            currentSearchTerm = this.value.trim();
            // Debounce search
            clearTimeout(searchInput.searchTimeout);
            searchInput.searchTimeout = setTimeout(() => {
                loadClausesFromAPI();
            }, 500);
        });
    }
});

// =====================================================
// API FUNCTIONS
// =====================================================

async function loadClausesFromAPI() {
    console.log('📡 Loading clauses from API...');
    
    // Get DOM elements
    const loadingEl = document.getElementById('loadingState');
    const gridEl = document.getElementById('clausesGrid');
    const emptyEl = document.getElementById('emptyState');
    
    try {
        // Show loading state
        console.log('⏳ Showing loading state');
        if (loadingEl) loadingEl.style.display = 'flex';
        if (gridEl) gridEl.style.display = 'none';
        if (emptyEl) emptyEl.style.display = 'none';
        
        const params = new URLSearchParams({
            page: 1,
            page_size: 100,
            sort_by: currentSort
        });
        
        if (currentCategory && currentCategory !== 'all') {
            params.append('category', currentCategory);
        }
        
        if (currentSearchTerm) {
            params.append('search', currentSearchTerm);
        }
        
        console.log('🔍 Fetching with params:', params.toString());
        
        const response = await fetch(`${API_BASE}/clauses?${params}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        allClauses = (data.clauses || []).map(c => ({
            id: c.id,
            clause_code: c.clause_code,
            title: c.clause_title,
            description: c.clause_text,
            fullText: c.clause_text,
            category: c.category,
            type: c.clause_type,
            tags: c.tags || [],
            usageCount: c.usage_count || 0,
            updatedDays: (() => {
                try {
                    if (!c.created_at) return 0;
                    const created = new Date(c.created_at);
                    const diff = Date.now() - created.getTime();
                    return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
                } catch { return 0; }
            })(),
            icon: 'file-text'
        }));
        
        console.log(`✅ Loaded ${allClauses.length} clauses`);
        
        // Render clauses
        renderClauses();
        
        // Update counts
        await updateCategoryCounts();
        
    } catch (error) {
        console.error('❌ Error loading clauses:', error);
        
        // Show empty state on error
        if (gridEl) gridEl.style.display = 'none';
        if (emptyEl) {
            emptyEl.style.display = 'flex';
        }
        
        showNotification('Failed to load clauses: ' + error.message, 'error');
        
    } finally {
        // CRITICAL: Always hide loading state
        console.log('✅ Hiding loading state');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }
}

// Render clauses to the grid
function renderClauses() {
    console.log('🎨 Rendering clauses...');
    
    const grid = document.getElementById('clausesGrid');
    const emptyState = document.getElementById('emptyState');
    
    if (!grid) {
        console.error('❌ Grid element not found');
        return;
    }
    
    // Clear grid
    grid.innerHTML = '';
    
    if (allClauses.length === 0) {
        console.log('📭 No clauses to display');
        grid.style.display = 'none';
        if (emptyState) {
            emptyState.style.display = 'flex';
        }
        return;
    }
    
    grid.style.display = 'grid';
    if (emptyState) emptyState.style.display = 'none';
    
    // Render each clause
    allClauses.forEach(clause => {
        const card = createClauseCard(clause);
        grid.appendChild(card);
    });
    
    console.log(`✅ Rendered ${allClauses.length} clause cards`);
}

// Create clause card element
function createClauseCard(clause) {
    const card = document.createElement('div');
    card.className = 'clause-card';
    card.onclick = () => openClauseDetail(clause.id);
    
    const badgeClass = clause.type === 'standard' ? 'badge-standard' : 
                       clause.type === 'custom' ? 'badge-custom' : 'badge-mandatory';
    
    card.innerHTML = `
        <div class="clause-card-header">
            <div class="clause-icon">
                <i class="ti ti-${clause.icon || 'file-text'}"></i>
            </div>
            <span class="clause-type-badge ${badgeClass}">${capitalizeFirst(clause.type || 'standard')}</span>
        </div>
        
        <h3 class="clause-title">${escapeHtml(clause.title)}</h3>
        
        <p class="clause-description">${escapeHtml(clause.description)}</p>
        
        <div class="clause-meta">
            <span class="meta-item">
                <i class="ti ti-tag"></i>
                ${clause.category || 'Uncategorized'}
            </span>
            <span class="meta-item">
                <i class="ti ti-clock"></i>
                ${clause.updatedDays}d ago
            </span>
            <span class="meta-item">
                <i class="ti ti-repeat"></i>
                ${clause.usageCount || 0} uses
            </span>
        </div>
        
        <div class="clause-tags">
            ${(clause.tags || []).slice(0, 3).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
        </div>
    `;
    
    return card;
}

// =====================================================
// FILTER & SEARCH FUNCTIONS
// =====================================================

function filterByCategory(category, button) {
    console.log('🔍 Filtering by category:', category);
    currentCategory = category;
    
    // Update active button
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    if (button) button.classList.add('active');
    
    loadClausesFromAPI();
}

function sortClauses(sortBy) {
    console.log('🔃 Sorting by:', sortBy);
    currentSort = sortBy;
    loadClausesFromAPI();
}

// =====================================================
// CATEGORY COUNTS
// =====================================================

async function updateCategoryCounts() {
    try {
        const response = await fetch(`${API_BASE}/statistics`, {
            credentials: 'include'
        });
        
        if (!response.ok) return;
        
        const statsData = await response.json();
        console.log('📊 Stats loaded:', statsData);
        const statistics = statsData.statistics || {};
        const total = statistics.total_clauses || 0;
        const byCategory = statistics.categories || {};
        
        // Update total count
        const allButton = document.querySelector('.category-btn[onclick*="all"]');
        if (allButton) {
            const totalCount = allButton.querySelector('.category-count');
            if (totalCount) totalCount.textContent = total;
        }
        
        // Update individual category counts
        Object.keys(byCategory).forEach(category => {
            const button = document.querySelector(`.category-btn[onclick*="${category}"]`);
            if (button) {
                const countSpan = button.querySelector('.category-count');
                if (countSpan) countSpan.textContent = byCategory[category];
            }
        });
        
    } catch (error) {
        console.error('Error updating counts:', error);
    }
}

// =====================================================
// MODAL FUNCTIONS
// =====================================================

function openAddClauseModal() {
    console.log('➕ Opening add clause modal');
    document.getElementById('modalTitle').textContent = 'Add New Clause';
    const form = document.getElementById('clauseForm');
    if (form) form.reset();
    currentClauseId = null;
    document.getElementById('addClauseModal').classList.add('show');
}

async function saveClause() {
    console.log('💾 Saving clause...');
    
    const title = document.getElementById('clauseTitle').value.trim();
    const category = document.getElementById('clauseCategory').value;
    const text = document.getElementById('clauseText').value.trim();
    const tagsInput = document.getElementById('clauseTags').value.trim();
    const type = document.querySelector('input[name="clauseType"]:checked')?.value || 'standard';
    
    if (!title || !text) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }
    
    const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];
    
    const clauseData = {
        clause_title: title,
        clause_text: text,
        category: category,
        clause_type: type,
        tags: tags,
        risk_level: 'low',
        sub_category: category
    };
    
    try {
        const url = currentClauseId ? `${API_BASE}/clauses/${currentClauseId}` : `${API_BASE}/clauses`;
        const method = currentClauseId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(clauseData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save clause');
        }
        
        const result = await response.json();
        console.log('✅ Clause saved:', result);
        
        showNotification(currentClauseId ? 'Clause updated successfully!' : 'Clause added successfully!', 'success');
        closeModal('addClauseModal');
        
        // Reload clauses
        await loadClausesFromAPI();
        
    } catch (error) {
        console.error('❌ Error saving clause:', error);
        showNotification('Failed to save clause: ' + error.message, 'error');
    }
}

async function openClauseDetail(clauseId) {
    console.log('👁️ Opening clause detail:', clauseId);
    currentClauseId = clauseId;
    
    try {
        const clause = allClauses.find(c => c.id === clauseId);
        if (!clause) throw new Error('Clause not found');
        
        const badgeClass = clause.type === 'standard' ? 'badge-standard' : 
                          clause.type === 'custom' ? 'badge-custom' : 'badge-mandatory';
        
        const detailContent = `
            <div style="display: grid; gap: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h2 style="margin-bottom: 0.5rem;">${escapeHtml(clause.title)}</h2>
                        <span class="clause-type-badge ${badgeClass}">${capitalizeFirst(clause.type || 'standard')}</span>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 0.875rem; color: var(--text-muted);">Code: ${escapeHtml(clause.clause_code || '')}</div>
                    </div>
                </div>
                
                <div style="background: var(--background-light); padding: 1.5rem; border-radius: 8px;">
                    <h5 style="margin-bottom: 1rem;">Clause Text</h5>
                    <p style="line-height: 1.8; white-space: pre-wrap;">${escapeHtml(clause.fullText)}</p>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;">
                    <div style="padding: 1rem; background: var(--background-light); border-radius: 8px;">
                        <div style="font-size: 1.25rem; font-weight: 600;">${clause.usageCount || 0}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Times Used</div>
                    </div>
                    <div style="padding: 1rem; background: var(--background-light); border-radius: 8px;">
                        <div style="font-size: 1.25rem; font-weight: 600;">${clause.category || 'N/A'}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Category</div>
                    </div>
                    <div style="padding: 1rem; background: var(--background-light); border-radius: 8px;">
                        <div style="font-size: 1.25rem; font-weight: 600; color: var(--warning-color);">${clause.updatedDays}d</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">Last Updated</div>
                    </div>
                </div>
                
                <div>
                    <h5 style="margin-bottom: 0.75rem;">Tags</h5>
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        ${(clause.tags || []).map(tag => `<span style=\"padding: 0.25rem 0.75rem; background: var(--background-light); border-radius: 20px; font-size: 0.875rem;\">${escapeHtml(tag)}</span>`).join('')}
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('clauseDetailContent').innerHTML = detailContent;
        document.getElementById('clauseDetailModal').classList.add('show');
        
    } catch (error) {
        console.error('❌ Error loading clause detail:', error);
        showNotification('Failed to load clause details: ' + error.message, 'error');
    }
}

function editClauseFromDetail() {
    if (!currentClauseId) return;
    
    const clause = allClauses.find(c => c.id === currentClauseId);
    if (!clause) return;
    
    closeModal('clauseDetailModal');
    
    // Open edit modal with clause data
    document.getElementById('modalTitle').textContent = 'Edit Clause';
    document.getElementById('clauseTitle').value = clause.title;
    document.getElementById('clauseCategory').value = clause.category || '';
    document.getElementById('clauseText').value = clause.fullText;
    document.getElementById('clauseTags').value = (clause.tags || []).join(', ');
    
    const typeRadio = document.querySelector(`input[name="clauseType"][value="${clause.type}"]`);
    if (typeRadio) {
        typeRadio.checked = true;
    }
    
    document.getElementById('addClauseModal').classList.add('show');
}

function useClause() {
    if (currentClauseId) {
        showNotification('Clause added to contract editor', 'success');
        closeModal('clauseDetailModal');
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
    if (modalId === 'addClauseModal') {
        const form = document.getElementById('clauseForm');
        if (form) form.reset();
        currentClauseId = null;
    }
}

// =====================================================
// FILTER MODAL FUNCTIONS
// =====================================================

function openFilterModal() {
    document.getElementById('filterModal').classList.add('show');
}

function updateFilterCount() {
    let count = 0;
    
    // Type filters
    document.querySelectorAll('input[name="type-filter"]:checked').forEach(() => count++);
    
    // Usage filters
    document.querySelectorAll('input[name="usage-filter"]:checked').forEach(() => count++);
    
    // Date filters
    if (document.getElementById('dateFrom').value || document.getElementById('dateTo').value) count++;
    
    // Update badge
    const filterCount = document.getElementById('filterCount');
    if (filterCount) {
        filterCount.textContent = count;
        if (count > 0) {
            filterCount.classList.add('active');
        } else {
            filterCount.classList.remove('active');
        }
    }
}

function clearFilters() {
    // Clear all checkboxes
    document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
    
    // Clear date inputs
    document.getElementById('dateFrom').value = '';
    document.getElementById('dateTo').value = '';
    
    updateFilterCount();
}

function applyFilters() {
    console.log('🔍 Applying filters...');
    closeModal('filterModal');
    loadClausesFromAPI();
}

// =====================================================
// RESET FILTERS FUNCTION
// =====================================================

function resetAllFilters() {
    console.log('🔄 Resetting all filters...');
    
    // Reset search
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = '';
    currentSearchTerm = '';
    
    // Reset category
    currentCategory = 'all';
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const allButton = document.querySelector('.category-btn[onclick*="all"]');
    if (allButton) allButton.classList.add('active');
    
    // Reset sort
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) sortSelect.value = 'recent';
    currentSort = 'recent';
    
    // Clear filters
    clearFilters();
    
    // Reload clauses
    loadClausesFromAPI();
}

// =====================================================
// HELPER FUNCTIONS
// =====================================================

function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showNotification(message, type = 'info') {
    console.log(`${type.toUpperCase()}: ${message}`);
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    `;
    notification.innerHTML = `
        <i class="ti ti-${type === 'success' ? 'check' : type === 'error' ? 'x' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}