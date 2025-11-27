# =====================================================
# FILE: app/models/audit_log.py
# Audit Log Model for tracking all system actions
# =====================================================

from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime
from datetime import datetime
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)  # created, updated, deleted, etc.
    user_id = Column(Integer, ForeignKey("users.id"))
    changes = Column(Text)  # JSON string or text description of changes
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)