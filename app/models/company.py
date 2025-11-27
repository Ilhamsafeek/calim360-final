# =====================================================
# FILE: app/models/company.py
# Create this file if it doesn't exist or replace if broken
# =====================================================

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base

class Company(Base):
    """
    Company/Organization Model
    """
    __tablename__ = "companies"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    cr_number = Column(String(100), unique=True)
    qid = Column(String(100))
    company_type = Column(String(50))
    industry = Column(String(100))
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    phone = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Company(id={self.id}, name={self.company_name})>"