# =====================================================
# FILE: app/api/api_v1/experts/consultation_schemas.py
# Consultation Room Pydantic Schemas
# =====================================================

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# =====================================================
# Session Management Schemas
# =====================================================

class SessionCreate(BaseModel):
    """Schema for creating a consultation session"""
    query_id: str
    expert_id: Optional[str] = None
    session_type: str = Field(..., description="chat or video")
    selected_tone: Optional[str] = "professional"  # formal, casual, professional
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "550e8400-e29b-41d4-a716-446655440000",
                "expert_id": "1",
                "session_type": "video",
                "selected_tone": "professional"
            }
        }

class SessionJoin(BaseModel):
    """Schema for joining a session"""
    session_id: str
    device_info: Optional[Dict[str, str]] = None

class SessionResponse(BaseModel):
    """Schema for session details"""
    id: str
    session_code: str
    query_id: str
    expert_id: Optional[str]
    expert_name: Optional[str]
    user_id: str
    user_name: str
    session_type: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    recording_url: Optional[str]
    memo_file: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ActiveSessionResponse(BaseModel):
    """Schema for active session with full details"""
    session: SessionResponse
    query_details: Dict[str, Any]
    expert_details: Optional[Dict[str, Any]]
    contract_details: Optional[Dict[str, Any]]
    participants: List[Dict[str, Any]]
    message_count: int
    attachment_count: int

# =====================================================
# Message Schemas
# =====================================================

class MessageCreate(BaseModel):
    """Schema for creating a message"""
    session_id: str
    message_content: str
    message_type: str = "text"  # text, document, annotation, system
    attachments: Optional[List[Dict[str, str]]] = None
    
    @validator('message_content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class MessageResponse(BaseModel):
    """Schema for message response"""
    id: str
    session_id: str
    sender_id: str
    sender_name: str
    sender_type: str
    message_type: str
    message_content: str
    attachments: Optional[List[Dict]] = None
    is_ai_generated: bool = False
    is_read: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessageListResponse(BaseModel):
    """Schema for list of messages"""
    messages: List[MessageResponse]
    total_count: int
    unread_count: int

# =====================================================
# Attachment Schemas
# =====================================================

class AttachmentCreate(BaseModel):
    """Schema for creating an attachment"""
    session_id: str
    attachment_type: str  # contract, document, clause, obligation
    reference_id: Optional[str] = None
    file_url: Optional[str] = None
    file_name: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None

class AttachmentResponse(BaseModel):
    """Schema for attachment response"""
    id: str
    session_id: str
    attachment_type: str
    reference_id: Optional[str]
    file_url: Optional[str]
    file_name: str
    file_size: Optional[int]
    mime_type: Optional[str]
    uploaded_by: str
    uploader_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# =====================================================
# Action Item Schemas
# =====================================================

class ActionItemCreate(BaseModel):
    """Schema for creating an action item"""
    session_id: str
    task_description: str
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"  # low, medium, high, critical
    
    @validator('task_description')
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Task description cannot be empty')
        if len(v) < 10:
            raise ValueError('Task description must be at least 10 characters')
        return v.strip()

class ActionItemUpdate(BaseModel):
    """Schema for updating an action item"""
    status: Optional[str] = None  # open, in_progress, completed, deferred
    completion_notes: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None

class ActionItemResponse(BaseModel):
    """Schema for action item response"""
    id: str
    session_id: str
    task_description: str
    assigned_to: Optional[str]
    assignee_name: Optional[str]
    due_date: Optional[datetime]
    priority: str
    status: str
    completed_at: Optional[datetime]
    completion_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# =====================================================
# Feedback Schemas
# =====================================================

class FeedbackCreate(BaseModel):
    """Schema for creating session feedback"""
    session_id: str
    rating: int = Field(..., ge=1, le=5, description="Overall rating 1-5")
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    expertise_rating: Optional[int] = Field(None, ge=1, le=5)
    responsiveness_rating: Optional[int] = Field(None, ge=1, le=5)
    overall_satisfaction: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = None
    would_recommend: Optional[bool] = None
    
    @validator('comments')
    def validate_comments(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Comments must be less than 1000 characters')
        return v

class FeedbackResponse(BaseModel):
    """Schema for feedback response"""
    id: str
    session_id: str
    rated_by: str
    rating: int
    feedback_type: str
    communication_rating: Optional[int]
    expertise_rating: Optional[int]
    responsiveness_rating: Optional[int]
    overall_satisfaction: Optional[int]
    comments: Optional[str]
    would_recommend: Optional[bool]
    created_at: datetime
    
    class Config:
        from_attributes = True

# =====================================================
# Session End Schemas
# =====================================================

class SessionEndRequest(BaseModel):
    """Schema for ending a session"""
    session_id: str
    generate_memo: bool = True
    action_items: Optional[List[str]] = None
    summary_notes: Optional[str] = None

class SessionEndResponse(BaseModel):
    """Schema for session end response"""
    session_id: str
    end_time: datetime
    duration_minutes: int
    memo_file: Optional[str]
    action_items_created: int
    recording_url: Optional[str]
    blockchain_hash: Optional[str]
    message: str

# =====================================================
# Statistics Schemas
# =====================================================

class SessionStatistics(BaseModel):
    """Schema for session statistics"""
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    total_duration_minutes: int
    average_rating: Optional[float]
    total_messages: int
    total_action_items: int
    pending_action_items: int

class ExpertStatistics(BaseModel):
    """Schema for expert statistics"""
    expert_id: str
    expert_name: str
    total_consultations: int
    average_rating: Optional[float]
    total_duration_hours: float
    specializations: List[str]
    availability_status: str
    
# =====================================================
# Real-time Updates Schemas
# =====================================================

class TypingIndicator(BaseModel):
    """Schema for typing indicator"""
    session_id: str
    user_id: str
    user_name: str
    is_typing: bool

class SessionUpdate(BaseModel):
    """Schema for real-time session updates"""
    session_id: str
    update_type: str  # message, attachment, status, participant
    data: Dict[str, Any]
    timestamp: datetime

# =====================================================
# Memo Generation Schemas
# =====================================================

class MemoGenerateRequest(BaseModel):
    """Schema for memo generation request"""
    session_id: str
    include_transcript: bool = True
    include_action_items: bool = True
    include_attachments: bool = True
    language: str = "en"  # en, ar, both

class MemoResponse(BaseModel):
    """Schema for memo response"""
    session_id: str
    memo_file_url: str
    generated_at: datetime
    file_size: int
    format: str  # pdf, docx