# =====================================================
# FILE: app/models/audit.py
# Clean version
# =====================================================

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, JSON
from datetime import datetime
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    contract_id = Column(Integer, ForeignKey("contracts.id"))
    action_type = Column(String(100))
    action_details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
