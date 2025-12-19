# =====================================================
# FILE: app/models/obligation.py
# OBLIGATION SQLALCHEMY MODELS
# MATCHES EXISTING DATABASE SCHEMA
# =====================================================

from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, 
    ForeignKey, Text
)
from datetime import datetime
from app.core.database import Base


class Obligation(Base):
    """
    Main obligations table for tracking contract obligations.
    
    This model MATCHES the existing database schema exactly.
    
    Fields per Business Process Document:
    - Obligation (title): The name/type of obligation
    - Description: Detailed description of the obligation
    - Owner: Person responsible for fulfilling the obligation
    - Escalation: Contact for escalation if obligation is breached
    - Status: Current status (Initiated, In Progress, Pending Details, 
              Awaiting Approval, Approved, Rejected, Completed)
    - Threshold Date: Warning date for reminders
    - Due Date: Final deadline, breach triggers escalation
    """
    
    __tablename__ = "obligations"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key to Contract
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"))
    
    # Obligation Details
    obligation_title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    obligation_type = Column(String(100), nullable=True)
    
    # Owner & Escalation
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    escalation_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Dates
    threshold_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(50), default='initiated')
    
    # Flags
    is_ai_generated = Column(Boolean, default=False)
    is_preset = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Obligation(id={self.id}, title='{self.obligation_title}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert obligation to dictionary"""
        return {
            "id": self.id,
            "contract_id": self.contract_id,
            "obligation_title": self.obligation_title,
            "description": self.description,
            "obligation_type": self.obligation_type,
            "owner_user_id": self.owner_user_id,
            "escalation_user_id": self.escalation_user_id,
            "threshold_date": self.threshold_date.isoformat() if self.threshold_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "is_ai_generated": self.is_ai_generated,
            "is_preset": self.is_preset,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ObligationTracking(Base):
    """
    Tracks all actions/updates on obligations.
    Used for audit trail and progress tracking.
    """
    
    __tablename__ = "obligation_tracking"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key to Obligation
    obligation_id = Column(Integer, ForeignKey("obligations.id", ondelete="CASCADE"))
    
    # Action Details
    action_taken = Column(String(255), nullable=True)
    action_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ObligationTracking(id={self.id}, obligation_id={self.obligation_id})>"


# =====================================================
# HELPER CONSTANTS
# =====================================================

OBLIGATION_STATUSES = [
    "initiated",
    "in-progress", 
    "pending",
    "awaiting",
    "approved",
    "rejected",
    "completed",
    "overdue"
]

OBLIGATION_TYPES = [
    "payment",
    "deliverable",
    "compliance",
    "reporting",
    "insurance",
    "performance",
    "coordination",
    "indemnification",
    "timely_completion",
    "other"
]