from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Correspondence(Base):
    __tablename__ = "correspondence"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    direction = Column(Enum('incoming', 'outgoing'), nullable=False)
    correspondence_type = Column(Enum('email', 'letter', 'notice', 'memo', 'other'), nullable=False)
    reference_number = Column(String(100), unique=True)
    subject = Column(String(500), nullable=False)
    body = Column(Text)
    sender = Column(String(255))
    recipients = Column(JSON)  # Store as JSON array
    cc_recipients = Column(JSON)  # Store as JSON array
    bcc_recipients = Column(JSON)  # Store as JSON array
    attachments = Column(JSON)  # Store file paths as JSON array
    sent_date = Column(DateTime)
    received_date = Column(DateTime)
    priority = Column(Enum('low', 'medium', 'high', 'urgent'), default='medium')
    status = Column(Enum('draft', 'sent', 'received', 'archived'), default='draft')
    is_ai_generated = Column(Boolean, default=False)
    ai_summary = Column(Text)
    tags = Column(JSON)  # Store tags as JSON array
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onUpdate=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="correspondences")
    creator = relationship("User", foreign_keys=[created_by])
    templates_used = relationship("CorrespondenceTemplate", secondary="correspondence_template_usage")


class CorrespondenceTemplate(Base):
    __tablename__ = "correspondence_templates"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    template_type = Column(Enum('email', 'letter', 'notice', 'memo', 'other'), nullable=False)
    subject_template = Column(String(500))
    body_template = Column(Text, nullable=False)
    variables = Column(JSON)  # Store template variables as JSON
    category = Column(String(100))
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onUpdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])


class CorrespondenceTemplateUsage(Base):
    __tablename__ = "correspondence_template_usage"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    correspondence_id = Column(Integer, ForeignKey("correspondence.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("correspondence_templates.id"), nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)


class CorrespondenceAttachment(Base):
    __tablename__ = "correspondence_attachments"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    correspondence_id = Column(Integer, ForeignKey("correspondence.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(100))
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    correspondence = relationship("Correspondence", backref="attachment_details")
    uploader = relationship("User")