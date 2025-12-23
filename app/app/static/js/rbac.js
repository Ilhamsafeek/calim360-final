/**
 * CALIM 360 - Frontend RBAC Helper
 * File: app/static/js/rbac.js
 */

class RBACHelper {
    constructor() {
        this.userRoles = [];
        this.permissions = [];
        this.isSuperAdmin = false;
        this.isCompanyAdmin = false;
        this.initialized = false;
    }

    /**
     * Initialize RBAC from user context
     */
    async init() {
        try {
            // Get from global user context or fetch
            if (window.userContext) {
                this.userRoles = window.userContext.roles || [];
                this.permissions = window.userContext.permissions || [];
                this.isSuperAdmin = window.userContext.is_super_admin || false;
                this.isCompanyAdmin = window.userContext.is_company_admin || false;
            } else {
                // Fetch from API
                const response = await fetch('/api/auth/me');
                if (response.ok) {
                    const data = await response.json();
                    this.userRoles = data.roles || [];
                    this.permissions = data.permissions || [];
                    this.isSuperAdmin = data.is_super_admin || false;
                    this.isCompanyAdmin = data.is_company_admin || false;
                }
            }
            this.initialized = true;
            this.applyUIRestrictions();
        } catch (error) {
            console.error('Failed to initialize RBAC:', error);
        }
    }

    /**
     * Check if user has a specific permission
     */
    hasPermission(permission) {
        if (this.isSuperAdmin) return true;
        return this.permissions.includes(permission);
    }

    /**
     * Check if user has a specific role
     */
    hasRole(role) {
        return this.userRoles.includes(role);
    }

    /**
     * Check if user has any of the specified permissions
     */
    hasAnyPermission(permissions) {
        if (this.isSuperAdmin) return true;
        return permissions.some(p => this.permissions.includes(p));
    }

    /**
     * Check if user has all specified permissions
     */
    hasAllPermissions(permissions) {
        if (this.isSuperAdmin) return true;
        return permissions.every(p => this.permissions.includes(p));
    }

    /**
     * Apply UI restrictions based on permissions
     */
    applyUIRestrictions() {
        // Hide elements requiring specific permissions
        document.querySelectorAll('[data-permission]').forEach(el => {
            const required = el.dataset.permission;
            if (!this.hasPermission(required)) {
                el.style.display = 'none';
                el.disabled = true;
            }
        });

        // Handle role-specific elements
        document.querySelectorAll('[data-role]').forEach(el => {
            const required = el.dataset.role.split(',');
            if (!required.some(r => this.hasRole(r.trim()))) {
                el.style.display = 'none';
            }
        });

        // Super Admin only elements
        document.querySelectorAll('[data-super-admin]').forEach(el => {
            if (!this.isSuperAdmin) {
                el.style.display = 'none';
            }
        });

        // Company Admin or higher elements
        document.querySelectorAll('[data-admin]').forEach(el => {
            if (!this.isSuperAdmin && !this.isCompanyAdmin) {
                el.style.display = 'none';
            }
        });

        console.log(' RBAC UI restrictions applied');
    }

    /**
     * Show element if user has permission
     */
    showIf(elementId, permission) {
        const el = document.getElementById(elementId);
        if (el) {
            el.style.display = this.hasPermission(permission) ? '' : 'none';
        }
    }

    /**
     * Enable element if user has permission
     */
    enableIf(elementId, permission) {
        const el = document.getElementById(elementId);
        if (el) {
            el.disabled = !this.hasPermission(permission);
        }
    }

    /**
     * Guard an action - throw error if no permission
     */
    guard(permission, actionName = 'this action') {
        if (!this.hasPermission(permission)) {
            showNotification(`You don't have permission to perform ${actionName}`, 'error');
            throw new Error(`Permission denied: ${permission}`);
        }
    }

    /**
     * Wrap a function with permission check
     */
    withPermission(permission, fn) {
        return (...args) => {
            if (this.hasPermission(permission)) {
                return fn(...args);
            } else {
                showNotification('Permission denied', 'error');
                return null;
            }
        };
    }
}

// Global instance
const rbac = new RBACHelper();

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    rbac.init();
});

// Permission constants for easy reference
const Permissions = {
    CONTRACT_CREATE: 'contract.create',
    CONTRACT_VIEW: 'contract.view',
    CONTRACT_EDIT: 'contract.edit',
    CONTRACT_DELETE: 'contract.delete',
    CONTRACT_APPROVE: 'contract.approve',
    CONTRACT_SIGN: 'contract.sign',
    WORKFLOW_CREATE: 'workflow.create',
    WORKFLOW_MANAGE: 'workflow.manage',
    USER_CREATE: 'user.create',
    USER_EDIT: 'user.edit',
    USER_DELETE: 'user.delete',
    ROLE_ASSIGN: 'role.assign',
    REPORT_VIEW: 'report.view',
    REPORT_EXPORT: 'report.export',
    AUDIT_VIEW: 'audit.view',
    SYSTEM_ADMIN: 'system.admin'
};

// Export for modules
if (typeof module !== 'undefined') {
    module.exports = { RBACHelper, rbac, Permissions };
}