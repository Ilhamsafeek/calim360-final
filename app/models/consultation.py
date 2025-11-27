# =====================================================
# FILE: app/models/consultation.py
# COMPLETE REPLACEMENT - Fixed Foreign Key Types
# =====================================================

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

# =====================================================
# Expert Profiles
# =====================================================
class ExpertProfile(Base):
    __tablename__ = "expert_profiles"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    expertise_areas = Column(Text)  # JSON string
    license_number = Column(String(100))
    license_authority = Column(String(100))
    years_of_experience = Column(Integer)
    specialization = Column(String(255))
    bio = Column(Text)
    is_available = Column(Boolean, default=True)
    hourly_rate = Column(Float)
    total_consultations = Column(Integer, default=0)
    average_rating = Column(Float)
    qfcra_certified = Column(Boolean, default=False)
    qid_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="expert_profile")
    sessions = relationship("ExpertSession", back_populates="expert", foreign_keys="ExpertSession.expert_id")
    availability = relationship("ExpertAvailability", back_populates="expert")

# =====================================================
# Expert Availability
# =====================================================
class ExpertAvailability(Base):
    __tablename__ = "expert_availability"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    expert_id = Column(Integer, ForeignKey("expert_profiles.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Sunday, 6=Saturday
    start_time = Column(String(10), nullable=False)  # HH:MM format
    end_time = Column(String(10), nullable=False)
    is_available = Column(Boolean, default=True)
    timezone = Column(String(50), default='Asia/Qatar')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    expert = relationship("ExpertProfile", back_populates="availability")

# =====================================================
# Expert Queries
# =====================================================
class ExpertQuery(Base):
    __tablename__ = "expert_queries"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    query_code = Column(String(100), unique=True, nullable=False)
    contract_id = Column(String(36))  # REMOVED FK - causes issue
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query_type = Column(String(100), nullable=False)  # legal, technical, compliance
    subject = Column(String(500), nullable=False)
    question = Column(Text, nullable=False)
    expertise_areas = Column(JSON)  # List of required expertise
    priority = Column(String(20), default='normal')  # standard, urgent, emergency
    status = Column(String(50), default='open')  # open, assigned, in_progress, answered, closed
    response = Column(Text)
    preferred_language = Column(String(10), default='en')
    session_type = Column(String(20), default='chat')  # chat, video
    asked_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    session = relationship("ExpertSession", back_populates="query", uselist=False)

# =====================================================
# Expert Sessions
# =====================================================
class ExpertSession(Base):
    __tablename__ = "expert_sessions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    query_id = Column(String(36), ForeignKey("expert_queries.id", ondelete="CASCADE"), unique=True, nullable=False)
    contract_id = Column(String(36))  # REMOVED FK - causes issue
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expert_id = Column(Integer, ForeignKey("expert_profiles.id", ondelete="SET NULL"))
    session_code = Column(String(100), unique=True)
    session_type = Column(String(20))  # chat, video, standard, urgent, panel
    session_time = Column(DateTime)
    session_duration_minutes = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    query_text = Column(Text)
    selected_tone = Column(String(50))  # formal, casual, professional
    attached_documents = Column(Text)  # JSON string
    recording_url = Column(String(255))
    memo_file = Column(String(255))
    transcript = Column(Text)
    feedback_rating = Column(Integer)
    feedback_comment = Column(Text)
    compliance_disclaimer = Column(Boolean, default=False)
    blockchain_hash = Column(String(256))
    session_cost = Column(Float)
    billing_status = Column(String(50))  # pending, paid, waived
    status = Column(String(50), default='scheduled')  # scheduled, active, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    query = relationship("ExpertQuery", back_populates="session")
    user = relationship("User", foreign_keys=[user_id])
    expert = relationship("ExpertProfile", foreign_keys=[expert_id], back_populates="sessions")
    messages = relationship("ExpertSessionMessage", back_populates="session", cascade="all, delete-orphan")
    attachments = relationship("ExpertSessionAttachment", back_populates="session", cascade="all, delete-orphan")
    action_items = relationship("ExpertActionItem", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("ExpertSessionFeedback", back_populates="session", cascade="all, delete-orphan")

# =====================================================
# Expert Session Messages
# =====================================================
class ExpertSessionMessage(Base):
    __tablename__ = "expert_session_messages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("expert_sessions.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender_type = Column(String(20), default='user')  # user, expert, system
    message_type = Column(String(50), default='text')  # text, document, annotation, system
    message_content = Column(Text)
    attachments = Column(JSON)
    is_ai_generated = Column(Boolean, default=False)
    ai_confidence = Column(Float)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ExpertSession", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])

# =====================================================
# Expert Session Attachments
# =====================================================
class ExpertSessionAttachment(Base):
    __tablename__ = "expert_session_attachments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("expert_sessions.id", ondelete="CASCADE"), nullable=False)
    attachment_type = Column(String(50))  # contract, document, clause, obligation
    reference_id = Column(String(36))
    file_url = Column(Text)
    file_name = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ExpertSession", back_populates="attachments")
    uploader = relationship("User", foreign_keys=[uploaded_by])

# =====================================================
# Expert Action Items
# =====================================================
class ExpertActionItem(Base):
    __tablename__ = "expert_action_items"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("expert_sessions.id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    task_description = Column(Text, nullable=False)
    due_date = Column(DateTime)
    priority = Column(String(20))  # low, medium, high, critical
    status = Column(String(20), default='open')  # open, in_progress, completed, deferred
    completed_at = Column(DateTime)
    completion_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("ExpertSession", back_populates="action_items")
    assignee = relationship("User", foreign_keys=[assigned_to])

# =====================================================
# Expert Session Feedback
# =====================================================
class ExpertSessionFeedback(Base):
    __tablename__ = "expert_session_feedback"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("expert_sessions.id", ondelete="CASCADE"), nullable=False)
    rated_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    feedback_type = Column(String(50), default='user')  # user, expert
    communication_rating = Column(Integer)
    expertise_rating = Column(Integer)
    responsiveness_rating = Column(Integer)
    overall_satisfaction = Column(Integer)
    comments = Column(Text)
    would_recommend = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ExpertSession", back_populates="feedback")
    rater = relationship("User", foreign_keys=[rated_by])