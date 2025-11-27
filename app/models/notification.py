# =====================================================
# FILE: app/models/notification.py
# Clean version
# =====================================================

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from datetime import datetime
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    notification_type = Column(String(100))
    title = Column(String(255))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)