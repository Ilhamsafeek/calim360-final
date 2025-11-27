# =====================================================
# FILE: app/models/clause_library.py
# Clause Library Model - WITH NULLABLE created_by
# =====================================================

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.models import Base
import uuid

class ClauseLibrary(Base):
    __tablename__ = "clause_library"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True)
    clause_code = Column(String(100), unique=True, nullable=False)
    clause_title = Column(String(255), nullable=False)
    clause_title_ar = Column(String(255), nullable=True)
    clause_text = Column(Text, nullable=False)
    clause_text_ar = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    sub_category = Column(String(100), nullable=True)
    clause_type = Column(String(50), nullable=True)
    risk_level = Column(String(20), nullable=True)
    tags = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)  # NOW NULLABLE
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'clause_code': self.clause_code,
            'clause_title': self.clause_title,
            'clause_title_ar': self.clause_title_ar,
            'clause_text': self.clause_text,
            'clause_text_ar': self.clause_text_ar,
            'category': self.category,
            'sub_category': self.sub_category,
            'clause_type': self.clause_type,
            'risk_level': self.risk_level,
            'tags': self.tags,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }