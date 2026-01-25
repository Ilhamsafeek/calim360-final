// =====================================================
// Blockchain Verification UI Functions - WITH AUTO-VERIFY
// FILE: app/static/js/blockchain-verification.js
// =====================================================

function getContractId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('contract_id') || 
           urlParams.get('id') ||
           document.querySelector('[name="contract_id"]')?.value ||
           document.querySelector('[data-contract-id]')?.dataset.contractId;
}

// Show blockchain verification status
async function verifyContract(contractId) {
    console.log('🔍 Verifying contract', contractId);
    
    try {
        const response = await fetch('/api/blockchain/verify-contract-hash', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                contract_id: parseInt(contractId)
            })
        });
        
        if (!response.ok) {
            console.error('❌ Verification API error:', response.status);
            showErrorIndicator(contractId);
            return;
        }
        
        const result = await response.json();
        console.log('📊 Verification result:', result);
        
        if (result.success && result.verified) {
            // ✅ VERIFIED
            showVerifiedIndicator(contractId, result);
        } else {
            // 🚨 TAMPERING DETECTED
            console.error('🚨 TAMPERING DETECTED!', result);
            showTamperAlert(contractId, result);
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
    
    indicator.innerHTML = `
        <div class="alert alert-success" style="display: flex; align-items: center; gap: 10px; margin: 10px 0; padding: 12px 15px;">
            <i class="ti ti-shield-check" style="font-size: 24px; color: #28a745;"></i>
            <div style="flex: 1;">
                <strong>Blockchain Verified</strong>
                <p style="margin: 0; font-size: 13px; color: #666;">
                    Contract integrity confirmed - No tampering detected
                </p>
                ${result.stored_hash ? `<small style="color: #999;">Hash: ${result.stored_hash.substring(0, 16)}...</small>` : ''}
            </div>
           
        </div>
    `;
    
    console.log('✅ Showing verified indicator');
}

// Show tamper alert
function showTamperAlert(contractId, result) {
    const indicator = document.getElementById('blockchain-indicator');
    if (!indicator) {
        console.warn('⚠️ No blockchain-indicator element found');
        // Still show browser alert as fallback
        alert('🚨 TAMPERING DETECTED!\n\nThis contract has been modified after blockchain approval.\nThe document has been frozen for security.');
        return;
    }
    
    indicator.innerHTML = `
        <div class="alert alert-danger" style="margin: 10px 0; padding: 15px; border-left: 4px solid #dc3545;">
            <div style="display: flex; align-items: start; gap: 10px;">
                <i class="ti ti-alert-triangle" style="font-size: 32px; color: #dc3545;"></i>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 10px 0; color: #dc3545;">
                        TAMPERING DETECTED!
                    </h4>
                    <p style="margin: 0 0 10px 0; font-weight: bold;">
                        This contract has been modified after blockchain approval.
                    </p>
                    <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
                        The current content does not match the blockchain-secured version. 
                        This document has been locked and cannot be edited until reviewed by an administrator.
                    </p>
                    
                    <div style="background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; font-size: 12px;">
                        <div><strong>Stored Hash:</strong> <span style="color: #28a745;">${result.stored_hash ? result.stored_hash.substring(0, 32) + '...' : 'N/A'}</span></div>
                        <div><strong>Current Hash:</strong> <span style="color: #dc3545;">${result.current_hash ? result.current_hash.substring(0, 32) + '...' : 'N/A'}</span></div>
                    </div>
                    
                   
                </div>
            </div>
        </div>
    `;
    
    // Add watermark overlay
    addTamperWatermark();
    
    // Disable all edit controls
    disableEditing();
    
    console.error('🚨 Showing tamper alert');
}

// Add tamper watermark
function addTamperWatermark() {
    // Remove existing watermark if any
    const existing = document.getElementById('tamper-watermark');
    if (existing) existing.remove();
    
    const watermark = document.createElement('div');
    watermark.id = 'tamper-watermark';
    watermark.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-45deg);
        font-size: 120px;
        color: rgba(220, 53, 69, 0.1);
        font-weight: bold;
        pointer-events: none;
        z-index: 9999;
        user-select: none;
    `;
    watermark.textContent = 'TAMPERED';
    document.body.appendChild(watermark);
}

// Disable all editing functions
function disableEditing() {
    // Disable all input fields
    document.querySelectorAll('input, textarea, select').forEach(el => {
        el.disabled = true;
        el.style.opacity = '0.6';
    });
    
    // Disable all edit buttons
    document.querySelectorAll('.btn-primary, .btn-success, button[onclick*="save"], button[onclick*="edit"]').forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.title = 'Editing disabled - Contract has been tampered';
    });
    
    // Hide edit controls
    document.querySelectorAll('.contract-edit-controls').forEach(el => {
        el.style.display = 'none';
    });
    
    console.log('🔒 Editing disabled due to tampering');
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

// View audit log
function viewAuditLog(contractId) {
    window.location.href = `/audit-log?contract_id=${contractId}&event=tampering`;
}

// Contact administrator
function contactAdministrator(contractId) {
    alert(`Administrator has been notified about tampering in Contract ID: ${contractId}\n\nA support ticket has been created.`);
    
    // Optional: Send notification to admin
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

// Show blockchain certificate (placeholder function)
function showBlockchainCertificate() {
    const contractId = getContractId();
    if (contractId) {
        window.open(`/api/blockchain/certificate/${contractId}`, '_blank');
    } else {
        alert('Contract ID not found');
    }
}

// =====================================================
// ✅ AUTO-VERIFY ON PAGE LOAD (ENABLED)
// =====================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔐 Blockchain verification system loaded');
    
    // Get contract ID from URL or data attribute
    const contractId = getContractId();
    
    if (contractId) {
        console.log('📋 Contract ID found:', contractId);
        
        // Show loading indicator
        const indicator = document.getElementById('blockchain-indicator');
        if (indicator) {
            indicator.innerHTML = `
                <div class="alert alert-info" style="display: flex; align-items: center; gap: 10px; margin: 10px 0;">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span>Verifying blockchain integrity...</span>
                </div>
            `;
        }
        
        // Auto-verify after 1 second
        setTimeout(() => {
            verifyContract(contractId);
        }, 1000);
        
        // Also re-verify every 30 seconds
        setInterval(() => {
            console.log('🔄 Re-verifying contract...');
            verifyContract(contractId);
        }, 30000); // 30 seconds
        
    } else {
        console.warn('⚠️ No contract ID found - skipping blockchain verification');
    }
});

// =====================================================
// EXPORT FUNCTIONS
// =====================================================

if (typeof window !== 'undefined') {
    window.verifyContract = verifyContract;
    window.showTamperAlert = showTamperAlert;
    window.viewAuditLog = viewAuditLog;
    window.contactAdministrator = contactAdministrator;
    window.showBlockchainCertificate = showBlockchainCertificate;
}