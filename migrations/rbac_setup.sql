-- =====================================================
-- CALIM 360 RBAC Database Migration
-- Run this script to setup proper RBAC
-- =====================================================

-- 1. Insert System Roles (if not exist)
INSERT IGNORE INTO roles (role_name, description, is_system_role, is_active, created_at) VALUES
('Super Admin', 'Full system access across all companies', 1, 1, NOW()),
('Company Admin', 'Company-wide administration access', 1, 1, NOW()),
('Contract Manager', 'Manage contracts and workflows', 1, 1, NOW()),
('Legal Reviewer', 'Review and approve contracts', 1, 1, NOW()),
('Approver', 'Approve contracts in workflow', 1, 1, NOW()),
('Negotiator', 'Participate in negotiations', 1, 1, NOW()),
('Viewer', 'Read-only access', 1, 1, NOW());

-- 2. Insert Permissions
INSERT IGNORE INTO permissions (permission_name, permission_category, description, created_at) VALUES
-- Contract permissions
('contract.create', 'contract', 'Create new contracts', NOW()),
('contract.view', 'contract', 'View contracts', NOW()),
('contract.edit', 'contract', 'Edit contracts', NOW()),
('contract.delete', 'contract', 'Delete contracts', NOW()),
('contract.approve', 'contract', 'Approve contracts', NOW()),
('contract.sign', 'contract', 'Sign contracts', NOW()),
-- Workflow permissions
('workflow.create', 'workflow', 'Create workflows', NOW()),
('workflow.manage', 'workflow', 'Manage workflows', NOW()),
('workflow.view', 'workflow', 'View workflows', NOW()),
-- User permissions
('user.create', 'user', 'Create users', NOW()),
('user.edit', 'user', 'Edit users', NOW()),
('user.delete', 'user', 'Delete users', NOW()),
('user.view', 'user', 'View users', NOW()),
-- Role permissions
('role.create', 'role', 'Create roles', NOW()),
('role.edit', 'role', 'Edit roles', NOW()),
('role.delete', 'role', 'Delete roles', NOW()),
('role.assign', 'role', 'Assign roles to users', NOW()),
-- Company permissions
('company.manage', 'company', 'Manage company settings', NOW()),
('company.view', 'company', 'View company info', NOW()),
-- Report permissions
('report.view', 'report', 'View reports', NOW()),
('report.generate', 'report', 'Generate reports', NOW()),
('report.export', 'report', 'Export reports', NOW()),
-- Audit permissions
('audit.view', 'audit', 'View audit logs', NOW()),
('audit.export', 'audit', 'Export audit logs', NOW()),
-- System permissions
('system.config', 'system', 'System configuration', NOW()),
('system.admin', 'system', 'System administration', NOW()),
-- Obligation permissions
('obligation.create', 'obligation', 'Create obligations', NOW()),
('obligation.edit', 'obligation', 'Edit obligations', NOW()),
('obligation.view', 'obligation', 'View obligations', NOW()),
-- Negotiation permissions
('negotiation.participate', 'negotiation', 'Participate in negotiations', NOW()),
('negotiation.manage', 'negotiation', 'Manage negotiations', NOW()),
-- Signature permissions
('signature.initiate', 'signature', 'Initiate signatures', NOW()),
('signature.sign', 'signature', 'Sign documents', NOW()),
('signature.manage', 'signature', 'Manage signatures', NOW());

-- 3. Map Permissions to Super Admin Role (all permissions)
INSERT IGNORE INTO role_permissions (role_id, permission_id, granted_at)
SELECT 
    (SELECT id FROM roles WHERE role_name = 'Super Admin'),
    id,
    NOW()
FROM permissions;

-- 4. Map Permissions to Company Admin Role
INSERT IGNORE INTO role_permissions (role_id, permission_id, granted_at)
SELECT 
    (SELECT id FROM roles WHERE role_name = 'Company Admin'),
    id,
    NOW()
FROM permissions
WHERE permission_name NOT IN ('system.config', 'system.admin');

-- 5. Map Permissions to Contract Manager Role
INSERT IGNORE INTO role_permissions (role_id, permission_id, granted_at)
SELECT 
    (SELECT id FROM roles WHERE role_name = 'Contract Manager'),
    id,
    NOW()
FROM permissions
WHERE permission_name IN (
    'contract.create', 'contract.view', 'contract.edit', 'contract.delete',
    'workflow.create', 'workflow.view',
    'user.view',
    'report.view', 'report.generate',
    'obligation.create', 'obligation.edit', 'obligation.view',
    'negotiation.participate', 'negotiation.manage',
    'signature.initiate'
);

-- 6. Create Super Admin User (if not exists)
-- First create a company for Super Admin
INSERT IGNORE INTO companies (company_name, cr_number, subscription_status, is_active, created_at)
VALUES ('System Administration', 'SYS-ADMIN-001', 'active', 1, NOW());

-- Get company ID and create Super Admin user
SET @super_admin_company = (SELECT id FROM companies WHERE cr_number = 'SYS-ADMIN-001');

INSERT IGNORE INTO users (
    email, username, password_hash, first_name, last_name,
    company_id, user_type, user_role, is_active, is_verified, created_at
) VALUES (
    'superadmin@calim360.qa',
    'superadmin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.PYF/XckjHt0gBq', -- 'SuperAdmin@123'
    'Super', 'Administrator',
    @super_admin_company, 'internal', 'Super Admin', 1, 1, NOW()
);

-- Assign Super Admin role
SET @super_admin_user = (SELECT id FROM users WHERE email = 'superadmin@calim360.qa');
SET @super_admin_role = (SELECT id FROM roles WHERE role_name = 'Super Admin');

INSERT IGNORE INTO user_roles (user_id, role_id, assigned_at)
VALUES (@super_admin_user, @super_admin_role, NOW());

-- 7. Add company_id to roles table if not exists (for company-specific roles)
-- This allows companies to create custom roles
ALTER TABLE roles ADD COLUMN IF NOT EXISTS company_id INT DEFAULT NULL;
ALTER TABLE roles ADD CONSTRAINT fk_roles_company 
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- 8. Create view for easy permission checking
CREATE OR REPLACE VIEW v_user_permissions AS
SELECT 
    u.id as user_id,
    u.email,
    u.company_id,
    r.role_name,
    p.permission_name,
    p.permission_category
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
WHERE u.is_active = 1 AND r.is_active = 1;

-- 9. Create function to check permission
DELIMITER //
CREATE FUNCTION IF NOT EXISTS check_permission(
    p_user_id INT,
    p_permission VARCHAR(100)
) RETURNS BOOLEAN
DETERMINISTIC
BEGIN
    DECLARE has_perm BOOLEAN DEFAULT FALSE;
    
    SELECT EXISTS(
        SELECT 1 FROM v_user_permissions 
        WHERE user_id = p_user_id 
        AND permission_name = p_permission
    ) INTO has_perm;
    
    RETURN has_perm;
END //
DELIMITER ;

-- 10. Update existing users with default Viewer role
INSERT IGNORE INTO user_roles (user_id, role_id, assigned_at)
SELECT 
    u.id,
    (SELECT id FROM roles WHERE role_name = 'Viewer'),
    NOW()
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM user_roles ur WHERE ur.user_id = u.id
);

SELECT 'RBAC Migration Complete!' as status;