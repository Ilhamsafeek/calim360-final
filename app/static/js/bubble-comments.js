// =====================================================
// BUBBLE COMMENTS - SIMPLIFIED JAVASCRIPT
// =====================================================

let allComments = [];
let currentBubble = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeBubbleComments();
});

function initializeBubbleComments() {
    console.log('🎨 Initializing Bubble Comments System');
    
    // Get contract ID from URL or data attribute
    const urlParams = new URLSearchParams(window.location.search);
    currentContractId = urlParams.get('id') || document.getElementById('contractId')?.value;
    
    if (currentContractId) {
        loadComments();
    }
    
    // Setup event listeners
    setupCommentListeners();
    
    // Close bubble when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.comment-bubble') && !e.target.closest('.comment-highlight, .track-insert, .track-delete')) {
            closeBubble();
        }
    });
}

function setupCommentListeners() {
    // Add comment button
    const addCommentBtn = document.getElementById('addCommentBtn');
    if (addCommentBtn) {
        addCommentBtn.addEventListener('click', openAddCommentModal);
    }
    
    // Toggle comments panel
    const toggleBtn = document.getElementById('toggleCommentsBtn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleCommentsPanel);
    }
}

// =====================================================
// LOAD COMMENTS
// =====================================================
async function loadComments() {
    try {
        console.log('📥 Loading comments for contract:', currentContractId);
        
        const response = await fetch(`/api/contracts/comments/${currentContractId}`, {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            allComments = data.comments;
            console.log(`✅ Loaded ${allComments.length} comments`);
            
            // Highlight comments in document
            highlightCommentsInDocument();
            
            // Update comments panel
            updateCommentsPanel();
            
            // Update badge count
            updateCommentBadge();
        }
    } catch (error) {
        console.error('❌ Error loading comments:', error);
    }
}

// =====================================================
// HIGHLIGHT COMMENTS IN DOCUMENT
// =====================================================
function highlightCommentsInDocument() {
    const content = document.getElementById('contractContent');
    if (!content) return;
    
    // Remove existing highlights
    const existing = content.querySelectorAll('.comment-highlight, .track-insert, .track-delete');
    existing.forEach(el => {
        const text = el.textContent;
        el.replaceWith(text);
    });
    
    // Apply highlights for each comment
    allComments.forEach(comment => {
        try {
            const className = getHighlightClass(comment.change_type);
            wrapTextWithHighlight(content, comment.selected_text, className, comment.id);
        } catch (error) {
            console.error('Error highlighting comment:', error);
        }
    });
}

function getHighlightClass(changeType) {
    switch (changeType) {
        case 'insert': return 'track-insert';
        case 'delete': return 'track-delete';
        default: return 'comment-highlight';
    }
}

function wrapTextWithHighlight(container, searchText, className, commentId) {
    const walker = document.createTreeWalker(
        container,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    let node;
    while (node = walker.nextNode()) {
        const text = node.textContent;
        const index = text.indexOf(searchText);
        
        if (index !== -1) {
            const range = document.createRange();
            range.setStart(node, index);
            range.setEnd(node, index + searchText.length);
            
            const span = document.createElement('span');
            span.className = className;
            span.dataset.commentId = commentId;
            span.addEventListener('click', (e) => {
                e.stopPropagation();
                showBubble(commentId, e);
            });
            
            range.surroundContents(span);
            break;
        }
    }
}

// =====================================================
// SHOW BUBBLE TOOLTIP
// =====================================================
function showBubble(commentId, event) {
    const comment = allComments.find(c => c.id === commentId);
    if (!comment) return;
    
    // Remove existing bubble
    closeBubble();
    
    // Create bubble
    const bubble = document.createElement('div');
    bubble.className = 'comment-bubble active';
    bubble.id = 'commentBubble';
    
    // Get initials
    const initials = comment.user_name.split(' ').map(n => n[0]).join('').toUpperCase();
    
    // Format time
    const timeAgo = formatTimeAgo(new Date(comment.created_at));
    
    // Build bubble HTML
    bubble.innerHTML = `
        <div class="comment-bubble-header">
            <div class="comment-author">
                <div class="comment-author-avatar">${initials}</div>
                <div class="comment-author-info">
                    <div class="comment-author-name">${comment.user_name}</div>
                    <div class="comment-time">${timeAgo}</div>
                </div>
            </div>
            <div class="comment-actions">
                ${comment.can_delete ? `
                    <button class="comment-action-btn delete" onclick="deleteComment(${comment.id})" title="Delete">
                        <i class="ti ti-trash" style="font-size: 18px;"></i>
                    </button>
                ` : ''}
                <button class="comment-action-btn" onclick="closeBubble()" title="Close">
                    <i class="ti ti-x" style="font-size: 18px;"></i>
                </button>
            </div>
        </div>
        <div class="comment-bubble-body">
            <div class="comment-text">${escapeHtml(comment.comment_text)}</div>
            ${comment.selected_text ? `
                <div class="comment-selected-text">
                    <i class="ti ti-quote"></i> "${escapeHtml(comment.selected_text)}"
                </div>
            ` : ''}
            ${renderTrackChanges(comment)}
        </div>
    `;
    
    document.body.appendChild(bubble);
    currentBubble = bubble;
    
    // Position bubble near clicked element
    positionBubble(bubble, event.target);
}

function renderTrackChanges(comment) {
    if (comment.change_type === 'comment') return '';
    
    let html = '<div class="track-changes-details">';
    
    if (comment.change_type === 'delete') {
        html += `
            <span class="track-change-label">
                <i class="ti ti-trash"></i> Deleted Text:
            </span>
            <div class="track-original">${escapeHtml(comment.original_text || comment.selected_text)}</div>
        `;
    } else if (comment.change_type === 'insert') {
        html += `
            <span class="track-change-label">
                <i class="ti ti-plus"></i> Inserted Text:
            </span>
            <div class="track-new">${escapeHtml(comment.new_text || comment.selected_text)}</div>
        `;
        if (comment.original_text) {
            html += `
                <span class="track-change-label" style="margin-top: 8px;">Original:</span>
                <div class="track-original">${escapeHtml(comment.original_text)}</div>
            `;
        }
    }
    
    html += '</div>';
    return html;
}

function positionBubble(bubble, target) {
    const rect = target.getBoundingClientRect();
    const bubbleRect = bubble.getBoundingClientRect();
    
    let top = rect.bottom + 10;
    let left = rect.left;
    
    // Adjust if bubble goes off screen
    if (left + bubbleRect.width > window.innerWidth) {
        left = window.innerWidth - bubbleRect.width - 20;
    }
    
    if (top + bubbleRect.height > window.innerHeight) {
        top = rect.top - bubbleRect.height - 10;
    }
    
    bubble.style.top = top + 'px';
    bubble.style.left = left + 'px';
}

function closeBubble() {
    if (currentBubble) {
        currentBubble.remove();
        currentBubble = null;
    }
}

// =====================================================
// ADD COMMENT
// =====================================================
function openAddCommentModal() {
    const selection = window.getSelection();
    if (!selection.rangeCount || selection.toString().trim() === '') {
        showNotification('Please select text to comment on', 'warning');
        return;
    }
    
    const selectedText = selection.toString().trim();
    const range = selection.getRangeAt(0);
    
    // Store selection
    window.commentSelection = {
        text: selectedText,
        range: range
    };
    
    // Show modal
    const modal = document.getElementById('commentModal');
    if (modal) {
        modal.style.display = 'flex';
        document.getElementById('commentText').value = '';
        document.getElementById('commentText').focus();
    }
}

async function submitComment() {
    const commentText = document.getElementById('commentText').value.trim();
    if (!commentText || !window.commentSelection) {
        showNotification('Please enter a comment', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/contracts/comments/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                contract_id: parseInt(currentContractId),
                comment_text: commentText,
                selected_text: window.commentSelection.text,
                position_start: 0,
                position_end: 0,
                change_type: 'comment'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            allComments.push(data.comment);
            highlightCommentsInDocument();
            updateCommentsPanel();
            updateCommentBadge();
            
            closeModal('commentModal');
            window.commentSelection = null;
            
            showNotification('Comment added successfully', 'success');
        }
    } catch (error) {
        console.error('❌ Error adding comment:', error);
        showNotification('Failed to add comment', 'error');
    }
}

// =====================================================
// DELETE COMMENT
// =====================================================
async function deleteComment(commentId) {
    if (!confirm('Delete this comment? The highlighted text will remain.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/contracts/comments/${commentId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Remove from array
            allComments = allComments.filter(c => c.id !== commentId);
            
            // Remove highlight
            const highlight = document.querySelector(`[data-comment-id="${commentId}"]`);
            if (highlight) {
                const text = highlight.textContent;
                highlight.replaceWith(text);
            }
            
            closeBubble();
            updateCommentsPanel();
            updateCommentBadge();
            
            showNotification('Comment deleted', 'success');
        }
    } catch (error) {
        console.error('❌ Error deleting comment:', error);
        showNotification('Failed to delete comment', 'error');
    }
}

// =====================================================
// COMMENTS PANEL
// =====================================================
function toggleCommentsPanel() {
    const panel = document.getElementById('commentsPanel');
    if (panel) {
        panel.classList.toggle('active');
    }
}

function updateCommentsPanel() {
    const panel = document.getElementById('commentsPanelBody');
    if (!panel) return;
    
    if (allComments.length === 0) {
        panel.innerHTML = `
            <div class="comments-empty">
                <i class="ti ti-message-off"></i>
                <p>No comments yet</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    allComments.forEach(comment => {
        const initials = comment.user_name.split(' ').map(n => n[0]).join('').toUpperCase();
        const timeAgo = formatTimeAgo(new Date(comment.created_at));
        const typeClass = `${comment.change_type}-type`;
        
        html += `
            <div class="comment-item ${typeClass}" onclick="scrollToComment(${comment.id})">
                <div class="comment-author" style="margin-bottom: 10px;">
                    <div class="comment-author-avatar" style="width: 28px; height: 28px; font-size: 12px;">${initials}</div>
                    <div class="comment-author-info">
                        <div class="comment-author-name" style="font-size: 13px;">${comment.user_name}</div>
                        <div class="comment-time">${timeAgo}</div>
                    </div>
                </div>
                <div class="comment-text" style="font-size: 13px;">${escapeHtml(comment.comment_text)}</div>
            </div>
        `;
    });
    
    panel.innerHTML = html;
}

function scrollToComment(commentId) {
    const highlight = document.querySelector(`[data-comment-id="${commentId}"]`);
    if (highlight) {
        highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
        highlight.style.animation = 'pulse 0.5s ease 2';
    }
}

function updateCommentBadge() {
    const badge = document.getElementById('commentsBadge');
    if (badge) {
        badge.textContent = allComments.length;
        badge.style.display = allComments.length > 0 ? 'flex' : 'none';
    }
}

// =====================================================
// UTILITY FUNCTIONS
// =====================================================
function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    
    return date.toLocaleDateString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Use your existing notification system
    console.log(`${type.toUpperCase()}: ${message}`);
    
    // Or create a simple toast
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#007bff'};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}