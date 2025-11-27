# =====================================================
# FILE: app/models/obligation.py
# =====================================================

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from datetime import datetime
from app.core.database import Base

class Obligation(Base):
    __tablename__ = "obligations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"))
    obligation_title = Column(String(500), nullable=False)
    description = Column(Text)
    obligation_type = Column(String(100))
    owner_user_id = Column(Integer, ForeignKey("users.id"))
    escalation_user_id = Column(Integer, ForeignKey("users.id"))
    threshold_date = Column(DateTime)
    due_date = Column(DateTime)
    status = Column(String(50), default='initiated')
    is_ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ObligationTracking(Base):
    __tablename__ = "obligation_tracking"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    obligation_id = Column(Integer, ForeignKey("obligations.id", ondelete="CASCADE"))
    action_taken = Column(String(255))
    action_by = Column(Integer, ForeignKey("users.id"))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)