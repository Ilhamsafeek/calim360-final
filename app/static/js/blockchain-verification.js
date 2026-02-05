// =====================================================
// FILE: app/static/js/blockchain-verification.js
// COMPLETE FIXED VERSION - Tampering Detection
// =====================================================

function getContractId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('contract_id') || 
           urlParams.get('id') ||
           document.querySelector('[name="contract_id"]')?.value ||
           document.querySelector('[data-contract-id]')?.dataset.contractId;
}

function getAuthToken() {
    // Try multiple sources in order of preference
    return localStorage.getItem('access_token') || 
           localStorage.getItem('auth_token') ||
           localStorage.getItem('token') ||
           sessionStorage.getItem('access_token') ||
           sessionStorage.getItem('token') ||
           getCookie('session_token');
}

// Helper to get cookie
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

//  MAIN VERIFICATION FUNCTION - FIXED
async function verifyContract(contractId) {
    try {
        console.log('🔍 Starting verification for contract:', contractId);
        
        const token = getAuthToken();
        if (!token) {
            console.error('❌ No auth token found');
            return;
        }
        
        //  CORRECT ENDPOINT WITH POST METHOD
        const response = await fetch(`/api/blockchain/verify-contract-hash`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` })
            },
            credentials: 'include', //  CRITICAL: Send cookies for session auth
            body: JSON.stringify({ contract_id: parseInt(contractId) })
        });
        
        if (!response.ok) {
            console.error('❌ Verification failed:', response.status);
            showErrorIndicator(contractId);
            return;
        }
        
        const result = await response.json();
        console.log('📊 Verification result:', result);
        
        if (result.is_tampered || !result.verified) {
            console.warn('🚨 TAMPERING DETECTED!');
            showTamperAlert(contractId, result);
        } else {
            console.log(' Contract verified');
            showVerifiedIndicator(contractId, result);
        }
        
    } catch (error) {
        console.error('❌ Verification error:', error);
        showErrorIndicator(contractId);
    }
}

// Show verified indicator
function showVerifiedIndicator(contractId, result) {
    const indicator = document.getElementById('blockchain-indicator');
    if (!indicator) {
        console.warn('⚠️ No blockchain-indicator element found');
        return;
    }
    

    indicator.style.display = 'none';
    // indicator.innerHTML = `
    //     <div class="alert alert-success" style="display: flex; align-items: center; gap: 10px; margin: 10px 0; padding: 12px 15px;">
    //         <i class="ti ti-shield-check" style="font-size: 24px; color: #28a745;"></i>
    //         <div style="flex: 1;">
    //             <strong>Blockchain Verified</strong>
    //             <p style="margin: 0; font-size: 13px; color: #666;">
    //                 Contract integrity confirmed - No tampering detected
    //             </p>
    //             ${result.stored_hash ? `<small style="color: #999;">Hash: ${result.stored_hash.substring(0, 16)}...</small>` : ''}
    //         </div>
    //     </div>
    // `;
    
    console.log(' Showing verified indicator');
}

// Show tamper alert
function showTamperAlert(contractId, result) {
    //  SHOW MODAL POPUP
    showTamperingModal(result);
    
    //  DISABLE ALL EDITING
    disableContractEditing();
    
    // Also show inline alert with recovery button
    const indicator = document.getElementById('blockchain-indicator');
    
    // Create alert HTML
    const alertHTML = `
        <div class="alert alert-danger" style="margin: 20px; padding: 15px; border-left: 4px solid #dc3545; box-shadow: 0 2px 8px rgba(220,53,69,0.2);">
            <div style="display: flex; align-items: start; gap: 10px;">
                <i class="ti ti-alert-triangle" style="font-size: 32px; color: #dc3545;"></i>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 10px 0; color: #dc3545;">
                        TAMPERING DETECTED!
                    </h4>
                    <p style="margin: 0 0 10px 0; font-weight: 600; font-size: 15px;">
                        Internal user modified contract without blockchain verification
                    </p>
                    <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
                        This contract was edited by an internal user. The modifications were saved to the database 
                        but were not recorded on the blockchain.
                    </p>
                    
                    ${result.stored_hash && result.current_hash ? `
                    <div style="background: #f8f9fa; padding: 12px; margin: 10px 0; border-radius: 6px; border: 1px solid #dee2e6;">
                        <strong style="color: #495057; display: block; margin-bottom: 8px;">Hash Comparison:</strong>
                        <div style="font-family: monospace; font-size: 12px;">
                            <div style="margin-bottom: 5px;">
                                <strong style="color: #28a745;">Blockchain:</strong><br>
                                <span style="color: #28a745; word-break: break-all;">${result.stored_hash}</span>
                            </div>
                            <div>
                                <strong style="color: #dc3545;">Current:</strong><br>
                                <span style="color: #dc3545; word-break: break-all;">${result.current_hash}</span>
                            </div>
                        </div>
                    </div>
                    ` : ''}

                    <!-- Recovery Button -->
                    <div id="recovery-button-container" style="margin-top: 15px; display: none;">
                        <button id="recover-contract-btn" class="btn btn-warning" onclick="recoverContract()">
                            <i class="ti ti-refresh me-1"></i>
                            Recover Previous Version
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    if (indicator) {
        indicator.innerHTML = alertHTML;
    } else {
        const existingAlert = document.getElementById('tampering-alert-top');
        if (existingAlert) existingAlert.remove();
        
        const alertDiv = document.createElement('div');
        alertDiv.id = 'tampering-alert-top';
        alertDiv.innerHTML = alertHTML;
        
        const mainContent = document.querySelector('.page-body') || 
                           document.querySelector('.contract-editor') || 
                           document.querySelector('main') || 
                           document.body;
        
        if (mainContent) {
            mainContent.insertBefore(alertDiv, mainContent.firstChild);
        }
    }
    
    // Now check if user can recover and show button
    checkIfCanRecoverAfterTamper();
    
    console.error('🚨 Showing tamper alert');
}



// Check if user can see recovery button AFTER tamper alert is shown
async function checkIfCanRecoverAfterTamper() {
    const token = getAuthToken();
    
    if (!token) {
        console.log('❌ No auth token found');
        return;
    }
    
    try {
        const contractId = getContractId();
        
        if (!contractId) {
            console.error('❌ No contract ID found');
            return;
        }
        
        console.log('🔍 Checking recovery authorization for contract:', contractId);
        
        // DEBUG: Check all localStorage keys
        console.log('📦 Checking localStorage for user data...');
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            console.log(`  - ${key}:`, localStorage.getItem(key));
        }
        
        // Try to get current user info from various sources
        let currentUserId = null;
        let currentUserType = null;
        
        // Check common localStorage keys
        const possibleKeys = ['user', 'userData', 'currentUser', 'user_data', 'auth_user', 'userInfo'];
        
        for (const key of possibleKeys) {
            const value = localStorage.getItem(key);
            if (value) {
                try {
                    const parsed = JSON.parse(value);
                    console.log(`Found data in '${key}':`, parsed);
                    
                    // Try different property names
                    currentUserId = parsed.user_id || parsed.id || parsed.userId || parsed.ID;
                    currentUserType = parsed.user_type || parsed.type || parsed.userType || parsed.role;
                    
                    if (currentUserId) {
                        console.log(' Found user ID:', currentUserId, 'Type:', currentUserType);
                        break;
                    }
                } catch (e) {
                    // Not JSON, might be a plain value
                    console.log(`'${key}' is not JSON:`, value);
                }
            }
        }
        
        // If still no user ID, try to decode JWT token
        if (!currentUserId && token) {
            console.log('Trying to decode JWT token...');
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                console.log('JWT payload:', payload);
                currentUserId = payload.user_id || payload.id || payload.sub || payload.userId;
                currentUserType = payload.user_type || payload.type || payload.role;
                console.log('From JWT - User ID:', currentUserId, 'Type:', currentUserType);
            } catch (e) {
                console.error('Failed to decode JWT:', e);
            }
        }
        
        if (!currentUserId) {
            console.error('❌ Could not get current user ID from any source');
            console.log('Available localStorage keys:', Object.keys(localStorage));
            return;
        }
        
        // Get contract info
        const contractResponse = await fetch(`/api/contracts/${contractId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!contractResponse.ok) {
            console.error('❌ Failed to get contract info:', contractResponse.status);
            return;
        }
        
        const contractData = await contractResponse.json();
        const contractCreatorId = contractData.created_by;
        
        // Check authorization
        const isInternal = currentUserType === 'internal';
        const isInitiator = currentUserId === contractCreatorId;
        
        console.log('Recovery check:', { 
            isInternal, 
            isInitiator, 
            currentUserId, 
            contractCreatorId,
            currentUserType
        });
        
        // Show button if authorized
        if (isInternal || isInitiator) {
            const recoveryContainer = document.getElementById('recovery-button-container');
            if (recoveryContainer) {
                recoveryContainer.style.display = 'block';
                console.log(' Recovery button shown');
            }
        } else {
            console.log('❌ User not authorized to recover');
        }
        
    } catch (error) {
        console.error('❌ Error checking recovery authorization:', error);
    }
}

// Recover contract function
async function recoverContract() {
    const contractId = getContractId();
    
    if (!confirm('Are you sure you want to delete the latest tampered version and restore the previous valid version?\n\nThis action cannot be undone.')) {
        return;
    }
    
    const token = getAuthToken();
    const recoverBtn = document.getElementById('recover-contract-btn');
    
    if (!recoverBtn) {
        alert('Recovery button not found');
        return;
    }
    
    // Show loading
    recoverBtn.disabled = true;
    const originalHTML = recoverBtn.innerHTML;
    recoverBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Recovering...';
    
    try {
        const response = await fetch(`/api/contracts/${contractId}/recover-tampered-version`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            alert(' Contract recovered successfully!\n\nThe tampered version has been deleted and the previous valid version has been restored.');
            window.location.reload();
        } else {
            throw new Error(result.detail || 'Recovery failed');
        }
        
    } catch (error) {
        console.error('Recovery error:', error);
        alert('❌ Recovery failed: ' + error.message);
        
        // Reset button
        recoverBtn.disabled = false;
        recoverBtn.innerHTML = originalHTML;
    }
}


//  NEW: SHOW MODAL POPUP FOR TAMPERING
function showTamperingModal(result) {
    // Remove existing modal if any
    const existingModal = document.getElementById('tampering-modal');
    if (existingModal) existingModal.remove();
    
    // Create modal
    const modal = document.createElement('div');
    modal.id = 'tampering-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;
    
    modal.innerHTML = `
        <div style="
            background: white;
            border-radius: 12px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            animation: slideDown 0.3s ease;
        ">
            <!-- Header (Fixed) -->
            <div style="
                background: linear-gradient(135deg, #dc3545, #c82333);
                color: white;
                padding: 20px;
                border-radius: 12px 12px 0 0;
                display: flex;
                align-items: center;
                gap: 15px;
                flex-shrink: 0;
            ">
                <i class="ti ti-alert-triangle" style="font-size: 48px;"></i>
                <div>
                    <h3 style="margin: 0; font-size: 24px; font-weight: 700;">TAMPERING DETECTED</h3>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Contract integrity compromised</p>
                </div>
            </div>
            
            <!-- Body (Scrollable) -->
            <div style="
                padding: 25px;
                overflow-y: auto;
                flex: 1;
            ">
                <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                    <strong style="color: #856404; display: block; margin-bottom: 8px;">
                        <i class="ti ti-info-circle"></i> What happened?
                    </strong>
                    <p style="margin: 0; color: #856404; font-size: 14px;">
                        This contract was modified by an <strong>internal user</strong> without recording the changes on the blockchain. 
                        This means the content integrity cannot be verified.
                    </p>
                </div>
                
                ${result.stored_hash && result.current_hash ? `
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <strong style="display: block; margin-bottom: 12px; color: #495057;">
                        <i class="ti ti-fingerprint"></i> Hash Comparison
                    </strong>
                    <div style="font-family: monospace; font-size: 12px; line-height: 1.6;">
                        <div style="margin-bottom: 10px;">
                            <div style="color: #28a745; font-weight: 600; margin-bottom: 4px;">✓ Blockchain Hash (Before Edit):</div>
                            <div style="background: white; padding: 8px; border-radius: 4px; word-break: break-all; border: 1px solid #28a745;">
                                ${result.stored_hash}
                            </div>
                        </div>
                        <div>
                            <div style="color: #dc3545; font-weight: 600; margin-bottom: 4px;">✗ Current Content Hash (After Edit):</div>
                            <div style="background: white; padding: 8px; border-radius: 4px; word-break: break-all; border: 1px solid #dc3545;">
                                ${result.current_hash}
                            </div>
                        </div>
                    </div>
                </div>
                ` : ''}
                
                ${result.explanation ? `
                <div style="background: #e7f3ff; border-left: 4px solid #0066cc; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                    <strong style="color: #004085; display: block; margin-bottom: 8px;">
                        <i class="ti ti-clock"></i> Technical Details
                    </strong>
                    <p style="margin: 0; color: #004085; font-size: 13px;">${result.explanation}</p>
                </div>
                ` : ''}
                
                <div style="background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 8px;">
                    <strong style="color: #721c24; display: block; margin-bottom: 8px;">
                        <i class="ti ti-shield-x"></i> Security Impact
                    </strong>
                    <ul style="margin: 0; padding-left: 20px; color: #721c24; font-size: 14px;">
                        <li>Content cannot be verified against blockchain</li>
                        <li>Modifications are not permanently recorded</li>
                        <li>Audit trail may be incomplete</li>
                        <li><strong>Contract is now READ-ONLY and locked</strong></li>
                    </ul>
                </div>
            </div>
            
            <!-- Footer (Fixed) -->
            <div style="
                padding: 20px;
                border-top: 1px solid #dee2e6;
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                flex-shrink: 0;
                background: white;
                border-radius: 0 0 12px 12px;
            ">
                <button onclick="document.getElementById('tampering-modal').remove()" style="
                    padding: 10px 24px;
                    background: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-weight: 600;
                    font-size: 14px;
                ">
                    Close
                </button>
                <button onclick="document.getElementById('tampering-modal').remove()" style="
                    padding: 10px 24px;
                    background: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-weight: 600;
                    font-size: 14px;
                ">
                    I Understand
                </button>
            </div>
        </div>
    `;
    
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideDown {
            from { transform: translateY(-50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
    
    // Add to page
    document.body.appendChild(modal);
    
    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
    
    console.log('🚨 Tampering modal displayed');
}

// Show error indicator
function showErrorIndicator(contractId) {
    const indicator = document.getElementById('blockchain-indicator');
    if (!indicator) return;
    
    indicator.innerHTML = `
        <div class="alert alert-warning" style="display: flex; align-items: center; gap: 10px; margin: 10px 0;">
            <i class="ti ti-alert-circle" style="font-size: 24px; color: #ffc107;"></i>
            <div style="flex: 1;">
                <strong>⚠️ Verification Failed</strong>
                <p style="margin: 0; font-size: 13px;">
                    Unable to verify blockchain integrity. Please try again or contact support.
                </p>
            </div>
            <button onclick="verifyContract(${contractId})" class="btn btn-sm btn-warning">
                <i class="ti ti-refresh"></i> Retry
            </button>
        </div>
    `;
}

//  DISABLE ONLY CONTRACT EDITING (NOT ENTIRE PAGE)
function disableContractEditing() {
    console.log('🔒 Disabling contract editing due to tampering');
    
    // 1. Disable Quill editor if it exists
    if (typeof quill !== 'undefined' && quill) {
        quill.disable();
        console.log('✓ Quill editor disabled');
    }
    
    // 2. Disable only inputs/textareas/selects INSIDE contract editor
    const contractEditor = document.querySelector('.contract-editor') || 
                          document.querySelector('.ql-container') ||
                          document.querySelector('#contractContent');
    
    if (contractEditor) {
        contractEditor.querySelectorAll('input, textarea, select').forEach(el => {
            el.disabled = true;
            el.style.opacity = '0.6';
            el.style.cursor = 'not-allowed';
        });
        console.log('✓ Contract editor inputs disabled');
    }
    
    // 3. Disable only CONTRACT-RELATED buttons
    const contractButtons = [
        'button[onclick*="save"]',
        'button[onclick*="Save"]',
        'button[onclick*="edit"]',
        'button[onclick*="Edit"]',
        'button[onclick*="update"]',
        'button[onclick*="Update"]',
        'button[onclick*="submit"]',
        'button[onclick*="Submit"]',
        'button[onclick*="approve"]',
        'button[onclick*="Approve"]',
        'button[onclick*="sign"]',
        'button[onclick*="Sign"]',
        'button[onclick*="regenerate"]',
        'button[onclick*="Regenerate"]',
        '#saveButton',
        '#saveDraftButton',
        '#submitButton',
        '#approveButton',
        '#signButton',
        '.btn-save',
        '.btn-submit',
        '.btn-approve',
        '.btn-edit'
    ];
    
    contractButtons.forEach(selector => {
        document.querySelectorAll(selector).forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            btn.title = 'Editing disabled - Contract has been tampered';
        });
    });
    
    //  Disable buttons by text content (proper way without :has-text)
    document.querySelectorAll('button').forEach(btn => {
        const text = btn.textContent.trim();
        const id = btn.id || '';
        const classList = btn.className || '';
        
        // Skip maximize button
        if (id === 'maximizeToggleBtn' || classList.includes('maximize')) {
            return;
        }
        
        const isContractButton = 
            text.includes('Save Contract') ||
            text.includes('Setup Custom Workflow') ||
            text.includes('Review Analysis') ||
            text.includes('Clause Analysis') ||
            text.includes('Regenerate') ||
            text.includes('Generate') ||
            (text.includes('Save') && !text.includes('Save As')) ||
            text.includes('Submit') ||
            text.includes('Approve') ||
            text.includes('Sign') ||
            (text.includes('Edit') && !text.includes('Credit'));
        
        if (isContractButton && !text.includes('Close') && !text.includes('Cancel') && !text.includes('View')) {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            btn.title = 'Editing disabled - Contract has been tampered';
        }
    });
    
    //  Disable Quill toolbar buttons and formatting controls
    document.querySelectorAll('.ql-toolbar button, .ql-toolbar select, .ql-formats button, .toolbar-btn').forEach(btn => {
        // Skip maximize button
        if (btn.id === 'maximizeToggleBtn' || btn.className.includes('maximize')) {
            return;
        }
        btn.disabled = true;
        btn.style.opacity = '0.4';
        btn.style.cursor = 'not-allowed';
    });
    
    console.log('✓ Contract action buttons and toolbar disabled');
    
    // 4. Add visual overlay/watermark on contract content only
    addTamperWatermark();
    
    // 5. Disable contenteditable ONLY in contract editor
    if (contractEditor) {
        contractEditor.querySelectorAll('[contenteditable="true"]').forEach(el => {
            el.contentEditable = 'false';
            el.style.opacity = '0.7';
        });
        console.log('✓ Contract ContentEditable disabled');
    }
    
    // 6. Add CSS to prevent editing ONLY in contract editor
    const style = document.createElement('style');
    style.id = 'tamper-disable-style';
    style.textContent = `
        .ql-editor {
            pointer-events: none !important;
            user-select: none !important;
            opacity: 0.7 !important;
        }
        .contract-editor .ql-container,
        .contract-editor .ql-editor,
        #contractContent {
            pointer-events: none !important;
            background: #f8f9fa !important;
        }
        /* Disable Quill toolbar */
        .ql-toolbar {
            pointer-events: none !important;
            opacity: 0.5 !important;
        }
        .ql-toolbar button,
        .ql-toolbar select {
            cursor: not-allowed !important;
        }
        /* Keep navigation, sidebar, other UI elements working */
        .navbar, .sidebar, .nav, .menu, 
        button[onclick*="close"], 
        button[onclick*="view"],
        button[onclick*="logout"],
        #tampering-modal button {
            pointer-events: auto !important;
        }
    `;
    document.head.appendChild(style);
    console.log('✓ CSS restrictions applied to contract editor and toolbar');
    
    console.log('🔒 Contract editing disabled (navigation and other UI still work)');
}

//  ADD TAMPER WATERMARK ONLY ON CONTRACT EDITOR
function addTamperWatermark() {
    // Remove existing watermark if any
    const existing = document.getElementById('tamper-watermark');
    if (existing) existing.remove();
    
    // Find contract editor container
    const contractEditor = document.querySelector('.contract-editor') || 
                          document.querySelector('.ql-container') ||
                          document.querySelector('#contractContent') ||
                          document.querySelector('.page-body');
    
    if (!contractEditor) return;
    
    const watermark = document.createElement('div');
    watermark.id = 'tamper-watermark';
    watermark.style.cssText = `
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-45deg);
        font-size: 80px;
        font-weight: bold;
        color: rgba(220, 53, 69, 0.08);
        pointer-events: none;
        z-index: 999;
        user-select: none;
        white-space: nowrap;
    `;
    watermark.textContent = 'TAMPERED • LOCKED';
    
    // Make parent position relative if not already
    if (getComputedStyle(contractEditor).position === 'static') {
        contractEditor.style.position = 'relative';
    }
    
    contractEditor.appendChild(watermark);
    
    console.log('✓ Watermark overlay added to contract editor');
}
function viewAuditLog(contractId) {
    window.location.href = `/audit-log?contract_id=${contractId}&event=tampering`;
}

// Contact administrator
function contactAdministrator(contractId) {
    alert(`Administrator has been notified about tampering in Contract ID: ${contractId}\n\nA support ticket has been created.`);
    
    fetch('/api/notifications/send-admin-alert', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({
            type: 'tampering_detected',
            contract_id: contractId,
            severity: 'critical'
        })
    }).catch(err => console.error('Failed to send admin alert:', err));
}


async function showBlockchainCertificate() {
    const contractId = getContractId();
    if (!contractId) {
        alert('Contract ID not found');
        return;
    }
    
    try {
        // First verify the contract to check tampering status
        const verifyResponse = await fetch(`/api/blockchain/verify-contract-hash`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            credentials: 'include',
            body: JSON.stringify({ contract_id: parseInt(contractId) })
        });
        
        const verifyResult = await verifyResponse.json();
        
        // Get blockchain record
        const response = await fetch(`/api/blockchain/contract-record/${contractId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            },
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (!result.success) {
            alert('Blockchain record not found');
            return;
        }
        
        // Check tampering status
        const isTampered = verifyResult.is_tampered || !verifyResult.verified;
        
        // Show certificate modal based on tampering status
        const modal = isTampered ? showTamperingModal(result) : createVerifiedCertificate(result);
        
        document.body.insertAdjacentHTML('beforeend', modal);
        document.body.style.overflow = 'hidden';
        
    } catch (error) {
        console.error('Failed to get certificate:', error);
        alert('Failed to retrieve blockchain certificate');
    }
}

// Create verified certificate modal
function createVerifiedCertificate(result) {
    const contractId = getContractId();
    
    // Show certificate modal (you can customize this)
    const modal = `
        <div class="modal fade show" id="blockchainCertificateModal" style="display: block; background: rgba(0,0,0,0.5);">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content" style="border-radius: 12px; overflow: hidden;">
                    <div class="modal-header" style="background: linear-gradient(135deg, #2762cb 0%, #73B4E0 100%); color: white; padding: 1.5rem;">
                        <h5 class="modal-title" style="display: flex; align-items: center; gap: 10px; margin: 0;">
                            <i class="ti ti-award" style="font-size: 24px;"></i>
                            Blockchain Certificate
                        </h5>
                        <button type="button" class="btn-close btn-close-white" onclick="closeBlockchainModal()" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer; opacity: 0.8;">
                            <i class="ti ti-x"></i>
                        </button>
                    </div>
                    <div class="modal-body" style="padding: 2rem;">
                        <div class="text-center mb-4">
                            <i class="ti ti-shield-check" style="font-size: 64px; color: #28a745;"></i>
                            <h4 class="mt-3" style="margin-top: 1rem; margin-bottom: 0;">Document Integrity Verified</h4>
                        </div>
                        
                        <table class="table" style="width: 100%; margin-bottom: 1rem;">
                            <tbody>
                                
                                <tr style="border-bottom: 1px solid #dee2e6;">
                                    <td style="padding: 12px 8px; font-weight: 600;">
                                        <i class="ti ti-fingerprint" style="margin-right: 8px; color: #6c757d;"></i>
                                        Document Hash:
                                    </td>
                                    <td style="padding: 12px 8px;">
                                        <code style="background: #f8f9fa; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; word-break: break-all;">${result.integrity_record?.document_hash || 'N/A'}</code>
                                    </td>
                                </tr>
                                <tr style="border-bottom: 1px solid #dee2e6;">
                                    <td style="padding: 12px 8px; font-weight: 600;">
                                        <i class="ti ti-git-commit" style="margin-right: 8px; color: #6c757d;"></i>
                                        Transaction Hash:
                                    </td>
                                    <td style="padding: 12px 8px;">
                                        <code style="background: #f8f9fa; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; word-break: break-all;">${result.blockchain_record?.transaction_hash || 'N/A'}</code>
                                    </td>
                                </tr>
                                <tr style="border-bottom: 1px solid #dee2e6;">
                                    <td style="padding: 12px 8px; font-weight: 600;">
                                        <i class="ti ti-box" style="margin-right: 8px; color: #6c757d;"></i>
                                        Block Number:
                                    </td>
                                    <td style="padding: 12px 8px;">${result.blockchain_record?.block_number || 'N/A'}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #dee2e6;">
                                    <td style="padding: 12px 8px; font-weight: 600;">
                                        <i class="ti ti-network" style="margin-right: 8px; color: #6c757d;"></i>
                                        Network:
                                    </td>
                                    <td style="padding: 12px 8px;">${result.blockchain_record?.network || 'calim360-network'}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 8px; font-weight: 600;">
                                        <i class="ti ti-circle-check" style="margin-right: 8px; color: #6c757d;"></i>
                                        Status:
                                    </td>
                                    <td style="padding: 12px 8px;">
                                        <span class="badge bg-success" style="background: #28a745 !important; color: white; padding: 0.35rem 0.65rem; border-radius: 0.25rem; font-size: 0.875rem;">Verified</span>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="modal-footer" style="padding: 1rem 1.5rem; border-top: 1px solid #dee2e6; display: flex; justify-content: flex-end;">
                        <button type="button" class="btn btn-secondary" onclick="closeBlockchainModal()" style="padding: 0.5rem 1rem; border-radius: 6px; border: none; cursor: pointer; background: #6c757d; color: white;">
                            <i class="ti ti-x" style="margin-right: 6px;"></i>
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modal);
}
// Create tampered certificate modal
function createTamperedCertificate(result, verifyResult) {
    return `
        <div class="modal fade show" id="blockchainCertificateModal" style="display: block; background: rgba(0,0,0,0.85); z-index: 10000; backdrop-filter: blur(4px);">
            <div class="modal-dialog modal-lg modal-dialog-centered" style="max-width: 700px;">
                <div class="modal-content" style="border: none; border-radius: 20px; overflow: hidden; box-shadow: 0 30px 80px rgba(220, 53, 69, 0.5);">
                    
                    <!-- Header with red gradient -->
                    <div style="background: linear-gradient(135deg, #7f1d1d 0%, #dc2626 50%, #ef4444 100%); padding: 40px 30px; position: relative; overflow: hidden;">
                        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(255,255,255,0.1); border-radius: 50%; filter: blur(40px);"></div>
                        
                        <button type="button" onclick="closeBlockchainModal()" style="position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.2); border: none; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.3s; z-index: 10;">
                            <i class="ti ti-x" style="color: white; font-size: 20px;"></i>
                        </button>
                        
                        <div style="position: relative; z-index: 1; text-align: center;">
                            <div style="width: 100px; height: 100px; background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 40px rgba(220, 38, 38, 0.5); animation: shake 0.5s infinite;">
                                <i class="ti ti-alert-triangle" style="font-size: 50px; color: white;"></i>
                            </div>
                            <h3 style="color: white; margin: 0 0 10px 0; font-size: 28px; font-weight: 700; text-shadow: 0 2px 10px rgba(0,0,0,0.3);">TAMPERING DETECTED</h3>
                            <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 16px;">Certificate Invalid - Document Modified</p>
                        </div>
                    </div>
                    
                    <!-- Body -->
                    <div style="padding: 40px 30px; background: white;">
                        
                        <!-- Status Badge -->
                        <div style="text-align: center; margin-bottom: 35px;">
                            <div style="display: inline-flex; align-items: center; gap: 10px; background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); padding: 12px 24px; border-radius: 50px; border: 2px solid #dc2626;">
                                <i class="ti ti-shield-x" style="font-size: 24px; color: #991b1b;"></i>
                                <span style="color: #7f1d1d; font-weight: 700; font-size: 16px; text-transform: uppercase; letter-spacing: 1px;">✗ INVALID</span>
                            </div>
                        </div>
                        
                        <!-- Warning Box -->
                        <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 12px; padding: 20px; border-left: 4px solid #f59e0b; margin-bottom: 25px;">
                            <div style="display: flex; gap: 15px;">
                                <i class="ti ti-alert-circle" style="color: #92400e; font-size: 24px; flex-shrink: 0;"></i>
                                <div>
                                    <strong style="color: #78350f; font-size: 14px; display: block; margin-bottom: 6px;">Security Alert</strong>
                                    <p style="margin: 0; color: #92400e; font-size: 13px; line-height: 1.6;">
                                        This contract has been modified by an internal user without blockchain verification. The current content does not match the blockchain record.
                                    </p>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Hash Comparison -->
                        <div style="background: #fef2f2; border-radius: 16px; padding: 25px; border: 2px solid #fecaca; margin-bottom: 25px;">
                            <h6 style="margin: 0 0 20px 0; color: #991b1b; font-weight: 700; font-size: 15px; display: flex; align-items: center; gap: 8px;">
                                <i class="ti ti-git-compare" style="font-size: 20px;"></i>
                                Hash Comparison
                            </h6>
                            
                            <!-- Original Hash -->
                            <div style="margin-bottom: 20px;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                    <i class="ti ti-circle-check" style="color: #16a34a; font-size: 18px;"></i>
                                    <span style="color: #15803d; font-weight: 600; font-size: 12px; text-transform: uppercase;">Original (Blockchain)</span>
                                </div>
                                <code style="display: block; background: white; padding: 12px 16px; border-radius: 10px; font-size: 11px; color: #15803d; border: 2px solid #86efac; word-break: break-all; font-family: 'Courier New', monospace;">
                                    ${verifyResult.stored_hash || 'N/A'}
                                </code>
                            </div>
                            
                            <!-- Modified Hash -->
                            <div>
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                    <i class="ti ti-circle-x" style="color: #dc2626; font-size: 18px;"></i>
                                    <span style="color: #991b1b; font-weight: 600; font-size: 12px; text-transform: uppercase;">Current (Modified)</span>
                                </div>
                                <code style="display: block; background: white; padding: 12px 16px; border-radius: 10px; font-size: 11px; color: #991b1b; border: 2px solid #fca5a5; word-break: break-all; font-family: 'Courier New', monospace;">
                                    ${verifyResult.current_hash || 'N/A'}
                                </code>
                            </div>
                        </div>
                        
                        <!-- Original Blockchain Record -->
                        <div style="background: #f9fafb; border-radius: 12px; padding: 20px; border: 1px solid #e5e7eb;">
                            <h6 style="margin: 0 0 15px 0; color: #4b5563; font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                                <i class="ti ti-database" style="font-size: 16px;"></i>
                                Original Blockchain Record
                            </h6>
                            <div style="display: grid; gap: 12px; font-size: 13px;">
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #6b7280;">Block Number:</span>
                                    <span style="color: #1f2937; font-weight: 600;">#${result.blockchain_record?.block_number || 'N/A'}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #6b7280;">Network:</span>
                                    <span style="color: #1f2937; font-weight: 600;">Hyperledger Fabric</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #6b7280;">Timestamp:</span>
                                    <span style="color: #1f2937; font-weight: 600;">
                                        ${result.blockchain_record?.timestamp ? new Date(result.blockchain_record.timestamp).toLocaleString('en-US', { 
                                            month: 'short', 
                                            day: 'numeric', 
                                            year: 'numeric',
                                            hour: '2-digit', 
                                            minute: '2-digit'
                                        }) : 'N/A'}
                                    </span>
                                </div>
                            </div>
                        </div>
                        
                    </div>
                    
                    <!-- Footer -->
                    <div style="background: #fef2f2; padding: 20px 30px; border-top: 2px solid #fecaca; display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 8px; color: #991b1b; font-size: 13px; font-weight: 600;">
                            <i class="ti ti-lock-off" style="font-size: 16px;"></i>
                            <span>Certificate Invalid</span>
                        </div>
                        <button onclick="closeBlockchainModal()" style="background: #dc2626; color: white; border: none; padding: 10px 24px; border-radius: 10px; font-weight: 600; cursor: pointer; transition: all 0.3s; font-size: 14px;">
                            Close
                        </button>
                    </div>
                    
                </div>
            </div>
        </div>
        
        <style>
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-5px); }
                75% { transform: translateX(5px); }
            }
        </style>
    `;
}

// Close modal function
function closeBlockchainModal() {
    const modal = document.getElementById('blockchainCertificateModal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
}



// =====================================================
// EXPORT FUNCTIONS
// =====================================================

if (typeof window !== 'undefined') {
    window.verifyContract = verifyContract;
    window.showTamperAlert = showTamperAlert;
    window.viewAuditLog = viewAuditLog;
    window.contactAdministrator = contactAdministrator;
    window.showBlockchainCertificate = showBlockchainCertificate;
    window.recoverContract = recoverContract; 
    window.checkIfCanRecoverAfterTamper = checkIfCanRecoverAfterTamper; 
}