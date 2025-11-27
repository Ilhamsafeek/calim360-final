# =====================================================
# FILE: app/models/signature.py
# Clean version
# =====================================================

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from datetime import datetime
from app.core.database import Base

class SignatureSession(Base):
    __tablename__ = "signature_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"))
    signer_user_id = Column(Integer, ForeignKey("users.id"))
    signer_type = Column(String(20))
    qid_number = Column(String(20))
    otp_sent_to = Column(String(15))
    otp_validated = Column(Boolean, default=False)
    auth_method = Column(String(50))
    signed_at = Column(DateTime)
    ip_address = Column(String(45))
    signed_file_url = Column(Text)
    certificate_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class SignatureAuditLog(Base):
    __tablename__ = "signature_audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("signature_sessions.id", ondelete="CASCADE"))
    event_type = Column(String(50))
    user_id = Column(Integer, ForeignKey("users.id"))
    note = Column(Text)
    event_time = Column(DateTime, default=datetime.utcnow)