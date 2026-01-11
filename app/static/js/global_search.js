/**
 * Global Search Functionality
 * File: app/static/js/global_search.js
 */

let globalSearchTimeout = null;
let currentSearchQuery = '';

/**
 * Initialize global search
 */
function initGlobalSearch() {
    const searchInput = document.querySelector('.global-search');
    
    if (!searchInput) {
        console.warn('Global search input not found');
        return;
    }
    
    // Create search results dropdown
    createSearchDropdown();
    
    // Add event listeners
    searchInput.addEventListener('input', handleSearchInput);
    searchInput.addEventListener('focus', handleSearchFocus);
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.header-search')) {
            closeSearchDropdown();
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
        }
        
        // Escape to close
        if (e.key === 'Escape') {
            closeSearchDropdown();
            searchInput.blur();
        }
    });
    
    console.log('✅ Global search initialized');
}

/**
 * Create search results dropdown
 */
function createSearchDropdown() {
    const searchWrapper = document.querySelector('.search-wrapper');
    
    if (!searchWrapper) return;
    
    // Check if dropdown already exists
    if (document.getElementById('globalSearchResults')) return;
    
    const dropdown = document.createElement('div');
    dropdown.id = 'globalSearchResults';
    dropdown.className = 'search-results-dropdown';
    dropdown.style.display = 'none';
    
    searchWrapper.appendChild(dropdown);
}

/**
 * Handle search input
 */
function handleSearchInput(e) {
    const query = e.target.value.trim();
    
    // Clear previous timeout
    clearTimeout(globalSearchTimeout);
    
    // Hide dropdown if query is empty
    if (query.length === 0) {
        closeSearchDropdown();
        return;
    }
    
    // Show loading state
    if (query.length >= 2) {
        showSearchLoading();
    }
    
    // Debounce search
    globalSearchTimeout = setTimeout(() => {
        if (query.length >= 2) {
            performGlobalSearch(query);
        }
    }, 300);
}

/**
 * Handle search focus
 */
function handleSearchFocus(e) {
    const query = e.target.value.trim();
    if (query.length >= 2) {
        performGlobalSearch(query);
    }
}

/**
 * Perform global search
 */
async function performGlobalSearch(query) {
    currentSearchQuery = query;
    
    try {
        const response = await fetch(`/api/search/global-search?query=${encodeURIComponent(query)}&limit=10`);
        
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const data = await response.json();
        displaySearchResults(data);
        
    } catch (error) {
        console.error('❌ Search error:', error);
        showSearchError();
    }
}

/**
 * Display search results
 */
function displaySearchResults(data) {
    const dropdown = document.getElementById('globalSearchResults');
    
    if (!dropdown) return;
    
    // Clear previous results
    dropdown.innerHTML = '';
    
    if (data.total === 0) {
        dropdown.innerHTML = `
            <div class="search-no-results">
                <i class="ti ti-search-off"></i>
                <p>No results found for "${data.query}"</p>
                <span>Try different keywords</span>
            </div>
        `;
        dropdown.style.display = 'block';
        return;
    }
    
    // Add header
    const header = document.createElement('div');
    header.className = 'search-results-header';
    header.innerHTML = `
        <span>Found ${data.total} results</span>
        <button class="search-close-btn" onclick="closeSearchDropdown()">
            <i class="ti ti-x"></i>
        </button>
    `;
    dropdown.appendChild(header);
    
    // Add contracts section
    if (data.contracts && data.contracts.length > 0) {
        const section = createResultSection('Contracts', data.contracts, 'file-text', 'contract');
        dropdown.appendChild(section);
    }
    
    // Add projects section
    if (data.projects && data.projects.length > 0) {
        const section = createResultSection('Projects', data.projects, 'folder', 'project');
        dropdown.appendChild(section);
    }
    
    // Add parties section
    if (data.parties && data.parties.length > 0) {
        const section = createResultSection('Parties', data.parties, 'building', 'party');
        dropdown.appendChild(section);
    }
    
    // Show dropdown
    dropdown.style.display = 'block';
}

/**
 * Create result section
 */
function createResultSection(title, items, iconClass, type) {
    const section = document.createElement('div');
    section.className = 'search-section';
    
    const sectionTitle = document.createElement('div');
    sectionTitle.className = 'search-section-title';
    sectionTitle.textContent = title;
    section.appendChild(sectionTitle);
    
    const list = document.createElement('div');
    list.className = 'search-results-list';
    
    items.forEach(item => {
        const resultItem = createResultItem(item, iconClass, type);
        list.appendChild(resultItem);
    });
    
    section.appendChild(list);
    return section;
}

/**
 * Create result item
 */
function createResultItem(item, iconClass, type) {
    const div = document.createElement('a');
    div.className = 'search-result-item';
    div.href = item.url;
    
    let title, subtitle, badge;
    
    if (type === 'contract') {
        title = item.title;
        subtitle = `${item.contract_number} • ${item.counterparty || 'N/A'}`;
        badge = item.status;
    } else if (type === 'project') {
        title = item.name;
        subtitle = `${item.project_code} • ${item.type || 'N/A'}`;
        badge = item.status;
    } else if (type === 'party') {
        title = item.name;
        subtitle = `${item.cr_number || 'No CR'} • ${item.type || 'N/A'}`;
        badge = item.type;
    }
    
    // Highlight matching text
    const highlightedTitle = highlightMatch(title, currentSearchQuery);
    const highlightedSubtitle = highlightMatch(subtitle, currentSearchQuery);
    
    div.innerHTML = `
        <div class="search-result-icon">
            <i class="ti ti-${iconClass}"></i>
        </div>
        <div class="search-result-content">
            <div class="search-result-title">${highlightedTitle}</div>
            <div class="search-result-subtitle">${highlightedSubtitle}</div>
        </div>
        ${badge ? `<div class="search-result-badge">${badge}</div>` : ''}
        <div class="search-result-arrow">
            <i class="ti ti-arrow-right"></i>
        </div>
    `;
    
    return div;
}

/**
 * Highlight matching text
 */
function highlightMatch(text, query) {
    if (!text || !query) return text || '';
    
    const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

/**
 * Escape regex special characters
 */
function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Show search loading
 */
function showSearchLoading() {
    const dropdown = document.getElementById('globalSearchResults');
    
    if (!dropdown) return;
    
    dropdown.innerHTML = `
        <div class="search-loading">
            <div class="spinner"></div>
            <span>Searching...</span>
        </div>
    `;
    dropdown.style.display = 'block';
}

/**
 * Show search error
 */
function showSearchError() {
    const dropdown = document.getElementById('globalSearchResults');
    
    if (!dropdown) return;
    
    dropdown.innerHTML = `
        <div class="search-error">
            <i class="ti ti-alert-circle"></i>
            <p>Search failed</p>
            <span>Please try again</span>
        </div>
    `;
    dropdown.style.display = 'block';
}

/**
 * Close search dropdown
 */
function closeSearchDropdown() {
    const dropdown = document.getElementById('globalSearchResults');
    if (dropdown) {
        dropdown.style.display = 'none';
    }
}

/**
 * Clear search
 */
function clearGlobalSearch() {
    const searchInput = document.querySelector('.global-search');
    if (searchInput) {
        searchInput.value = '';
        closeSearchDropdown();
    }
}

// Initialize on DOM load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGlobalSearch);
} else {
    initGlobalSearch();
}