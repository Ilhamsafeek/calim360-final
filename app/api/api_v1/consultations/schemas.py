"""
app/api/api_v1/consultations/schemas.py
Pydantic schemas for My Consultations endpoints
FIXED: Made updated_at optional to handle NULL values from database
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# =====================================================
# CONSULTATION LIST SCHEMAS
# =====================================================
class ConsultationListResponse(BaseModel):
    """Schema for consultation list items"""
    session_id: Optional[str] = None
    session_code: Optional[str] = None
    query_id: str
    query_code: str
    subject: str
    question: str
    priority: str  # urgent, high, normal, low
    query_status: str
    expertise_area: Optional[str] = None
    session_type: Optional[str] = None  # chat, video
    session_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    session_status: str  # pending, scheduled, in_progress, completed, cancelled
    memo_file: Optional[str] = None
    recording_url: Optional[str] = None
    feedback_rating: Optional[int] = None
    expert_name: Optional[str] = None
    expert_picture: Optional[str] = None
    expert_email: Optional[str] = None
    contract_id: Optional[str] = None
    contract_name: Optional[str] = None
    contract_number: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None  # 🔧 FIXED: Made optional to handle NULL values
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_code": "CONS-2025-001",
                "query_id": "660e8400-e29b-41d4-a716-446655440001",
                "query_code": "QRY-2025-001",
                "subject": "QFCRA Rule 18 Compliance Review",
                "question": "Need guidance on arbitration clause compliance",
                "priority": "high",
                "query_status": "open",
                "expertise_area": "qfcra",
                "session_type": "video",
                "session_time": "2025-10-25T10:00:00",
                "duration_minutes": 60,
                "start_time": None,
                "end_time": None,
                "session_status": "scheduled",
                "memo_file": None,
                "recording_url": None,
                "feedback_rating": None,
                "expert_name": "Dr. Ahmed Al-Mansouri",
                "expert_picture": "/static/img/experts/ahmed.jpg",
                "expert_email": "ahmed@example.com",
                "contract_id": "770e8400-e29b-41d4-a716-446655440002",
                "contract_name": "Master Services Agreement",
                "contract_number": "MSA-2025-001",
                "created_at": "2025-10-20T08:30:00",
                "updated_at": "2025-10-20T09:15:00"
            }
        }

# =====================================================
# CONSULTATION STATISTICS
# =====================================================
class ConsultationStatsResponse(BaseModel):
    """Statistics for user's consultations"""
    total_queries: int
    scheduled_count: int
    completed_count: int
    cancelled_count: int
    pending_action_items: int
    average_rating: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_queries": 45,
                "scheduled_count": 3,
                "completed_count": 38,
                "cancelled_count": 4,
                "pending_action_items": 12,
                "average_rating": 4.7
            }
        }

# =====================================================
# NESTED INFO SCHEMAS
# =====================================================
class QueryInfo(BaseModel):
    """Query information for detail view"""
    query_id: str
    query_code: str
    subject: str
    question: str
    priority: str
    status: str
    expertise_area: Optional[str] = None

class ExpertInfo(BaseModel):
    """Expert information"""
    name: str
    email: str
    picture: Optional[str] = None
    expertise: Optional[str] = None

class ContractInfo(BaseModel):
    """Contract information"""
    contract_id: str
    contract_name: str
    contract_number: str

class AttachmentInfo(BaseModel):
    """Attachment information"""
    id: str
    file_name: str
    file_url: str
    file_size: Optional[int] = None
    uploaded_at: datetime
    uploaded_by: str

class ActionItemInfo(BaseModel):
    """Action item information"""
    id: str
    description: str
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    status: str  # open, in_progress, completed, deferred
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

class ConsultationDetailResponse(BaseModel):
    """Detailed consultation session information"""
    session_id: str
    session_code: str
    session_type: str
    status: str
    session_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    query_text: Optional[str] = None
    selected_tone: Optional[str] = None
    recording_url: Optional[str] = None
    memo_file: Optional[str] = None
    transcript: Optional[str] = None
    feedback_rating: Optional[int] = None
    feedback_comment: Optional[str] = None
    compliance_disclaimer: bool
    blockchain_hash: Optional[str] = None
    session_cost: Optional[float] = None
    billing_status: Optional[str] = None
    query: QueryInfo
    expert: Optional[ExpertInfo] = None
    contract: Optional[ContractInfo] = None
    asked_by: str
    attachments: List[AttachmentInfo] = []
    action_items: List[ActionItemInfo] = []
    
    class Config:
        from_attributes = True

# =====================================================
# FILTER AND REQUEST SCHEMAS
# =====================================================
class ConsultationFilterRequest(BaseModel):
    """Filter parameters for consultation list"""
    status: Optional[str] = Field(None, description="scheduled, completed, cancelled, all")
    expertise_area: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    expert_id: Optional[str] = None
    contract_id: Optional[str] = None
    priority: Optional[str] = None
    search: Optional[str] = None

# =====================================================
# SESSION MESSAGE SCHEMAS
# =====================================================
class SessionMessage(BaseModel):
    """Chat message in consultation session"""
    message_id: str
    sender_id: Optional[str] = None
    sender_type: str  # user, expert, system
    message_type: str  # text, document, annotation, system
    content: Optional[str] = None
    attachments: Optional[dict] = None
    is_ai_generated: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime
    sender_name: Optional[str] = None
    sender_picture: Optional[str] = None

# =====================================================
# FEEDBACK SCHEMAS
# =====================================================
class FeedbackCreateRequest(BaseModel):
    """Request to submit feedback"""
    rating: int = Field(..., ge=1, le=5, description="Overall rating 1-5")
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    expertise_rating: Optional[int] = Field(None, ge=1, le=5)
    responsiveness_rating: Optional[int] = Field(None, ge=1, le=5)
    overall_satisfaction: Optional[int] = Field(None, ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=1000)
    would_recommend: Optional[bool] = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "rating": 5,
                "communication_rating": 5,
                "expertise_rating": 5,
                "responsiveness_rating": 4,
                "overall_satisfaction": 5,
                "comments": "Excellent consultation, very helpful and knowledgeable",
                "would_recommend": True
            }
        }

class FeedbackResponse(BaseModel):
    """Response after submitting feedback"""
    success: bool
    message: str
    session_id: str
    rating: int

# =====================================================
# ACTION ITEM SCHEMAS
# =====================================================
class ActionItemResponse(BaseModel):
    """Action item detail"""
    id: str
    session_id: str
    assigned_to: Optional[str] = None
    task_description: str
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    status: str
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None  # 🔧 FIXED: Made optional
    
    class Config:
        from_attributes = True

# =====================================================
# SESSION DETAIL SCHEMAS
# =====================================================
class SessionDetailResponse(BaseModel):
    """Detailed session information"""
    session_id: str
    session_code: str
    query_id: str
    contract_id: Optional[str] = None
    user_id: str
    expert_id: Optional[str] = None
    session_type: str
    session_time: Optional[datetime] = None
    session_duration_minutes: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str
    recording_url: Optional[str] = None
    memo_file: Optional[str] = None
    transcript: Optional[str] = None
    blockchain_hash: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None  # 🔧 FIXED: Made optional
    
    class Config:
        from_attributes = True

# =====================================================
# CANCELLATION SCHEMAS
# =====================================================
class CancellationRequest(BaseModel):
    """Request to cancel consultation"""
    reason: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Schedule conflict, need to reschedule"
            }
        }

class CancellationResponse(BaseModel):
    """Response after cancellation"""
    success: bool
    message: str
    session_id: str

# =====================================================
# DOWNLOAD SCHEMAS
# =====================================================
class MemoDownloadResponse(BaseModel):
    """Response for memo download"""
    session_id: str
    memo_url: str
    download_url: str

class RecordingResponse(BaseModel):
    """Response for recording access"""
    session_id: str
    recording_url: str
    blockchain_hash: Optional[str] = None
    verified: bool