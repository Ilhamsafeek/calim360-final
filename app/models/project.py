"""
Project Model - Updated with project_manager_id
File: app/models/project.py
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, Numeric, Date
from datetime import datetime

from app.core.database import Base

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    project_code = Column(String(100), unique=True, nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    project_name_ar = Column(String(255))
    description = Column(Text)
    
    #  ADDED: project_manager_id column
    project_manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Existing client_id column
    client_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    
    project_type = Column(String(100))
    project_value = Column(Numeric(20, 2))
    currency = Column(String(10), default='QAR')
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(50), default='planning')
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)