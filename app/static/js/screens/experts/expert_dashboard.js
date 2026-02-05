// =====================================================
// FILE: app/static/js/screens/experts/expert_dashboard.js
// Expert Dashboard - View and Respond to Assigned Consultations
// =====================================================

(function() {
    'use strict';
    
    let currentSessionId = null;
    let currentClientId = null;
    let messagePollingInterval = null;

    // =====================================================
    // INITIALIZATION
    // =====================================================
    document.addEventListener('DOMContentLoaded', function() {
        loadChatHistory();
        
        // Auto-resize textarea
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight) + 'px';
            });
        }
    });

    // =====================================================
    // LOAD CHAT HISTORY (Expert's assigned consultations)
    // =====================================================
    async function loadChatHistory() {
        console.log('🔄 Loading assigned consultations...');
        try {
            const response = await fetch('/api/v1/experts/my-consultations', {
                credentials: 'include'
            });
            const data = await response.json();
            
            console.log('📦 API Response:', data);
            
            const chatList = document.getElementById('chatList');
            
            let sessions = [];
            if (Array.isArray(data)) {
                sessions = data;
            } else if (data.sessions) {
                sessions = data.sessions;
            } else if (data.consultations) {
                sessions = data.consultations;
            }
            
            console.log('✅ Found', sessions.length, 'consultations');
            
            if (sessions.length === 0) {
                chatList.innerHTML = `
                    <div class="empty-state">
                        <i class="ti ti-inbox"></i>
                        <p>No consultations assigned yet</p>
                    </div>
                `;
                return;
            }
            
            chatList.innerHTML = '';
            sessions.forEach(session => {
                const chatItem = createChatItem(session);
                chatList.appendChild(chatItem);
            });
            
        } catch (error) {
            console.error('❌ Error loading consultations:', error);
            document.getElementById('chatList').innerHTML = `
                <div class="empty-state">
                    <i class="ti ti-alert-circle"></i>
                    <p>Failed to load consultations</p>
                </div>
            `;
        }
    }

    // =====================================================
    // CREATE CHAT ITEM
    // =====================================================
    function createChatItem(session) {
        const div = document.createElement('div');
        div.className = 'chat-item';
        div.dataset.sessionId = session.session_id;
        
        div.onclick = function() {
            openChat(session.session_id);
        };
        
        // For experts, show CLIENT name, not expert name
        const clientName = session.expert_name || 'Unknown Client';
        const subject = session.subject || 'No subject';
        const lastMessage = session.last_message || 'No messages yet';
        const time = formatTime(session.updated_at || session.created_at);
        const unreadCount = session.unread_count || 0;
        
        div.innerHTML = `
            <div class="chat-item-header">
                <span class="chat-expert-name">${escapeHtml(clientName)}</span>
                <span class="chat-time">${time}</span>
            </div>
            <div class="chat-subject">${escapeHtml(subject)}</div>
            <div class="chat-preview">${escapeHtml(lastMessage)}</div>
            ${unreadCount > 0 ? `<span class="unread-badge">${unreadCount}</span>` : ''}
        `;
        
        return div;
    }

    // =====================================================
    // OPEN CHAT
    // =====================================================
    async function openChat(sessionId) {
        if (!sessionId) {
            console.error('❌ No sessionId provided');
            return;
        }
        
        console.log('📂 Opening chat for session:', sessionId);
        currentSessionId = sessionId;
        
        // Update active state
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        const activeItem = document.querySelector(`[data-session-id="${sessionId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }
        
        try {
            // Load session details
            const response = await fetch(`/api/v1/experts/sessions/${sessionId}`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Failed to load session details');
            }
            
            const sessionData = await response.json();
            console.log('✅ Session data loaded:', sessionData);
            
            // Update header with CLIENT info (not expert)
            updateChatHeader(sessionData);
            
            // Show header and input area
            document.getElementById('chatHeader').style.display = 'flex';
            document.getElementById('chatInputArea').style.display = 'block';
            
            // Load messages
            await loadMessages(sessionId);
            
            // Start polling for new messages
            startMessagePolling();
            
        } catch (error) {
            console.error('❌ Error opening chat:', error);
            showError('Failed to load consultation details');
        }
    }

    // =====================================================
    // UPDATE CHAT HEADER
    // =====================================================
    function updateChatHeader(sessionData) {
        // For experts, show CLIENT name, not expert name
        const clientName = sessionData.expert_name || 'Client';
        const subject = sessionData.subject || 'No subject';
        
        const clientNameEl = document.getElementById('clientName');
        const subjectEl = document.getElementById('consultationSubject');
        
        if (clientNameEl) clientNameEl.textContent = clientName;
        if (subjectEl) subjectEl.textContent = subject;
        
        // Set avatar
        const avatar = document.getElementById('clientAvatar');
        if (avatar) {
            if (sessionData.expert_picture) {
                avatar.innerHTML = `<img src="${sessionData.expert_picture}" alt="${clientName}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
            } else {
                const initials = clientName.split(' ').map(n => n[0]).join('').toUpperCase();
                avatar.textContent = initials;
            }
        }
    }

    // =====================================================
    // LOAD MESSAGES
    // =====================================================
    async function loadMessages(sessionId) {
        try {
            console.log('💬 Loading messages for session:', sessionId);
            
            const response = await fetch(`/api/v1/experts/sessions/${sessionId}/messages`, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Failed to load messages');
            }
            
            const data = await response.json();
            console.log('✅ Messages loaded:', data.messages?.length || 0);
            
            const messagesContainer = document.getElementById('chatMessages');
            messagesContainer.innerHTML = '';
            
            if (!data.messages || data.messages.length === 0) {
                messagesContainer.innerHTML = `
                    <div class="empty-state">
                        <i class="ti ti-message-circle"></i>
                        <h4>No messages yet</h4>
                        <p>Start the conversation by sending a response</p>
                    </div>
                `;
                return;
            }
            
            // Render messages
            data.messages.forEach(msg => {
                const isOwn = msg.sender_type === 'expert';
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isOwn ? 'own' : 'received'}`;
                messageDiv.innerHTML = `
                    <div class="message-content">
                        <div class="message-text">${escapeHtml(msg.message_content)}</div>
                        <div class="message-time">${formatTime(msg.created_at)}</div>
                    </div>
                `;
                messagesContainer.appendChild(messageDiv);
            });
            
            // Scroll to bottom
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
        } catch (error) {
            console.error('❌ Error loading messages:', error);
            showError('Failed to load messages');
        }
    }

    // =====================================================
    // SEND MESSAGE
    // =====================================================
    async function sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const messageText = messageInput.value.trim();
        
        if (!messageText || !currentSessionId) {
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/experts/sessions/${currentSessionId}/messages`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message_content: messageText,
                    message_type: 'text'
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to send message');
            }
            
            // Clear input
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            // Reload messages
            await loadMessages(currentSessionId);
            
        } catch (error) {
            console.error('❌ Error sending message:', error);
            showError('Failed to send message');
        }
    }

    // =====================================================
    // MESSAGE POLLING
    // =====================================================
    function startMessagePolling() {
        stopMessagePolling();
        messagePollingInterval = setInterval(() => {
            if (currentSessionId) {
                loadMessages(currentSessionId);
            }
        }, 5000); // Poll every 5 seconds
    }

    function stopMessagePolling() {
        if (messagePollingInterval) {
            clearInterval(messagePollingInterval);
            messagePollingInterval = null;
        }
    }

    // =====================================================
    // SEARCH CHATS
    // =====================================================
    function searchChats() {
        const searchTerm = document.getElementById('chatSearchInput').value.toLowerCase();
        const chatItems = document.querySelectorAll('.chat-item');
        
        chatItems.forEach(item => {
            const clientName = item.querySelector('.chat-expert-name').textContent.toLowerCase();
            const subject = item.querySelector('.chat-subject').textContent.toLowerCase();
            const preview = item.querySelector('.chat-preview').textContent.toLowerCase();
            
            if (clientName.includes(searchTerm) || subject.includes(searchTerm) || preview.includes(searchTerm)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }

    // =====================================================
    // END SESSION
    // =====================================================
    async function endSession() {
        if (!currentSessionId) return;
        
        if (!confirm('Are you sure you want to end this consultation session?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/experts/sessions/${currentSessionId}/end`, {
                credentials: 'include',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) throw new Error('Failed to end session');
            
            alert('Session ended successfully');
            
            // Reload chat history
            await loadChatHistory();
            
            // Clear current session
            currentSessionId = null;
            document.getElementById('chatHeader').style.display = 'none';
            document.getElementById('chatInputArea').style.display = 'none';
            document.getElementById('chatMessages').innerHTML = `
                <div class="empty-state">
                    <i class="ti ti-message-circle"></i>
                    <h4>No Consultation Selected</h4>
                    <p>Select a consultation from the list to respond</p>
                </div>
            `;
            
        } catch (error) {
            console.error('Error ending session:', error);
            alert('Failed to end session');
        }
    }

    // =====================================================
    // HELPER FUNCTIONS
    // =====================================================
    function handleEnterKey(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    }

    function formatTime(dateString) {
        if (!dateString) return '';
        
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diff = now - date;
            
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(diff / 3600000);
            const days = Math.floor(diff / 86400000);
            
            if (minutes < 1) return 'Just now';
            if (minutes < 60) return `${minutes}m ago`;
            if (hours < 24) return `${hours}h ago`;
            if (days < 7) return `${days}d ago`;
            
            return date.toLocaleDateString();
        } catch (error) {
            return '';
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showError(message) {
        console.error('❌', message);
        alert(message);
    }

    // =====================================================
    // EXPOSE GLOBAL FUNCTIONS
    // =====================================================
    window.sendMessage = sendMessage;
    window.handleEnterKey = handleEnterKey;
    window.searchChats = searchChats;
    window.endSession = endSession;

})();