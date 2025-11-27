# =====================================================
# FILE: app/models/contract_template.py
# Contract Template Model
# =====================================================

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime
from datetime import datetime
from app.core.database import Base


class ContractTemplate(Base):
    __tablename__ = "contract_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String(255), nullable=False)
    template_type = Column(String(100))
    template_category = Column(String(100))
    description = Column(Text)
    file_url = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)