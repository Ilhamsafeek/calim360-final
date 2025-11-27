# =====================================================
# FILE: app/core/permissions.py
# Role-Based Access Control Permission Definitions
# =====================================================

from enum import Enum
from typing import List, Dict, Set

class Permission(str, Enum):
    # Contract Permissions
    CONTRACT_CREATE = "contract.create"
    CONTRACT_VIEW = "contract.view"
    CONTRACT_EDIT = "contract.edit"
    CONTRACT_DELETE = "contract.delete"
    CONTRACT_APPROVE = "contract.approve"
    CONTRACT_SIGN = "contract.sign"
    
    # Workflow Permissions
    WORKFLOW_CREATE = "workflow.create"
    WORKFLOW_MANAGE = "workflow.manage"
    WORKFLOW_VIEW = "workflow.view"
    
    # User Management
    USER_CREATE = "user.create"
    USER_EDIT = "user.edit"
    USER_DELETE = "user.delete"
    USER_VIEW = "user.view"
    
    # Role Management
    ROLE_CREATE = "role.create"
    ROLE_EDIT = "role.edit"
    ROLE_DELETE = "role.delete"
    ROLE_ASSIGN = "role.assign"
    
    # Company Management
    COMPANY_MANAGE = "company.manage"
    COMPANY_VIEW = "company.view"
    
    # Reports
    REPORT_VIEW = "report.view"
    REPORT_GENERATE = "report.generate"
    REPORT_EXPORT = "report.export"
    
    # Audit
    AUDIT_VIEW = "audit.view"
    AUDIT_EXPORT = "audit.export"
    
    # System Administration
    SYSTEM_CONFIG = "system.config"
    SYSTEM_ADMIN = "system.admin"
    
    # Obligation Management
    OBLIGATION_CREATE = "obligation.create"
    OBLIGATION_EDIT = "obligation.edit"
    OBLIGATION_VIEW = "obligation.view"
    
    # Negotiation
    NEGOTIATION_PARTICIPATE = "negotiation.participate"
    NEGOTIATION_MANAGE = "negotiation.manage"
    
    # E-Signature
    SIGNATURE_INITIATE = "signature.initiate"
    SIGNATURE_SIGN = "signature.sign"
    SIGNATURE_MANAGE = "signature.manage"


# Role to Permissions Mapping
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    "Super Admin": {p for p in Permission},  # All permissions
    
    "Company Admin": {
        Permission.CONTRACT_CREATE, Permission.CONTRACT_VIEW,
        Permission.CONTRACT_EDIT, Permission.CONTRACT_DELETE,
        Permission.CONTRACT_APPROVE, Permission.CONTRACT_SIGN,
        Permission.WORKFLOW_CREATE, Permission.WORKFLOW_MANAGE,
        Permission.WORKFLOW_VIEW,
        Permission.USER_CREATE, Permission.USER_EDIT,
        Permission.USER_DELETE, Permission.USER_VIEW,
        Permission.ROLE_ASSIGN,
        Permission.COMPANY_VIEW,
        Permission.REPORT_VIEW, Permission.REPORT_GENERATE,
        Permission.REPORT_EXPORT,
        Permission.AUDIT_VIEW,
        Permission.OBLIGATION_CREATE, Permission.OBLIGATION_EDIT,
        Permission.OBLIGATION_VIEW,
        Permission.NEGOTIATION_PARTICIPATE, Permission.NEGOTIATION_MANAGE,
        Permission.SIGNATURE_INITIATE, Permission.SIGNATURE_SIGN,
        Permission.SIGNATURE_MANAGE,
    },
    
    "Contract Manager": {
        Permission.CONTRACT_CREATE, Permission.CONTRACT_VIEW,
        Permission.CONTRACT_EDIT, Permission.CONTRACT_DELETE,
        Permission.WORKFLOW_CREATE, Permission.WORKFLOW_VIEW,
        Permission.USER_VIEW,
        Permission.REPORT_VIEW, Permission.REPORT_GENERATE,
        Permission.OBLIGATION_CREATE, Permission.OBLIGATION_EDIT,
        Permission.OBLIGATION_VIEW,
        Permission.NEGOTIATION_PARTICIPATE, Permission.NEGOTIATION_MANAGE,
        Permission.SIGNATURE_INITIATE,
    },
    
    "Legal Reviewer": {
        Permission.CONTRACT_VIEW, Permission.CONTRACT_EDIT,
        Permission.CONTRACT_APPROVE,
        Permission.WORKFLOW_VIEW,
        Permission.USER_VIEW,
        Permission.REPORT_VIEW,
        Permission.OBLIGATION_VIEW,
        Permission.NEGOTIATION_PARTICIPATE,
    },
    
    "Approver": {
        Permission.CONTRACT_VIEW, Permission.CONTRACT_APPROVE,
        Permission.CONTRACT_SIGN,
        Permission.WORKFLOW_VIEW,
        Permission.SIGNATURE_SIGN,
    },
    
    "Negotiator": {
        Permission.CONTRACT_VIEW,
        Permission.NEGOTIATION_PARTICIPATE,
        Permission.OBLIGATION_VIEW,
    },
    
    "Viewer": {
        Permission.CONTRACT_VIEW,
        Permission.WORKFLOW_VIEW,
        Permission.REPORT_VIEW,
        Permission.OBLIGATION_VIEW,
    },
}


def get_permissions_for_role(role_name: str) -> Set[Permission]:
    """Get all permissions for a role"""
    return ROLE_PERMISSIONS.get(role_name, set())


def has_permission(user_roles: List[str], permission: Permission) -> bool:
    """Check if user has a specific permission based on their roles"""
    for role in user_roles:
        if permission in ROLE_PERMISSIONS.get(role, set()):
            return True
    return False


def get_all_permissions(user_roles: List[str]) -> Set[Permission]:
    """Get all permissions for a user based on their roles"""
    permissions = set()
    for role in user_roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))
    return permissions