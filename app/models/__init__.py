# =====================================================
# FILE: app/models/__init__.py
# COMPLETE VERSION - MERGE CONFLICTS RESOLVED
# =====================================================

from app.core.database import Base

# User and Company models
from app.models.user import User, Company, Role, Permission

# Contract and Obligation models
from app.models.contract import Contract
from app.models.obligation import Obligation, ObligationTracking

# Workflow models
from app.models.workflow import Workflow, WorkflowStep

# Audit and Notification models
from app.models.audit import AuditLog
from app.models.notification import Notification

from app.models.subscription import Module, CompanyModuleSubscription

# Consultation/Expert models
from app.models.consultation import (
    ExpertProfile,
    ExpertAvailability,
    ExpertQuery,
    ExpertSession,
    ExpertSessionMessage,
    ExpertSessionAttachment,
    ExpertActionItem,
    ExpertSessionFeedback
)

# Export all models
__all__ = [
    # Core
    "Base",
    
    # User & Company
    "User",
    "Company",
    "Role",
    "Permission",
    
    # Contract & Obligations
    "Contract",
    "Obligation",
    "ObligationTracking",
    
    # Workflow
    "Workflow",
    "WorkflowStep",
    
    # Audit & Notifications
    "AuditLog",
    "Notification",
    
    # Consultation/Expert
    "ExpertProfile",
    "ExpertAvailability",
    "ExpertQuery",
    "ExpertSession",
    "ExpertSessionMessage",
    "ExpertSessionAttachment",
    "ExpertActionItem",
    "ExpertSessionFeedback"
]