# =====================================================
# FILE: app/models/workflow.py
# Clean version
# =====================================================

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, JSON
from datetime import datetime
from app.core.database import Base

class Workflow(Base):
    __tablename__ = "workflows"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    workflow_name = Column(String(255), nullable=False)
    workflow_type = Column(String(100))
    description = Column(Text)
    is_master = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    workflow_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="CASCADE"))
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(255))
    step_type = Column(String(100))
    assignee_role = Column(String(100))
    assignee_user_id = Column(Integer, ForeignKey("users.id"))
    department = Column(String(255))
    sla_hours = Column(Integer)
    is_mandatory = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="CASCADE"))
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"))
    current_step = Column(Integer)
    status = Column(String(50))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
