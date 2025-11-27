# =====================================================
# FILE: app/api/api_v1/experts/schemas.py
# COMPLETE SCHEMAS - Ask an Expert + Expert Directory
# =====================================================

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# =====================================================
# ASK AN EXPERT - QUERY SCHEMAS
# =====================================================

class ExpertQueryCreate(BaseModel):
    """Schema for creating a new expert query - contract_id is OPTIONAL"""
    contract_id: Optional[str] = Field(None, description="Contract ID (optional)")
    query_type: str = Field(..., description="Type of query")
    subject: str = Field(..., max_length=500, description="Brief subject")
    question: str = Field(..., min_length=20, description="Detailed question")
    expertise_areas: List[str] = Field(default_factory=list, description="Required expertise areas")
    priority: str = Field(default="normal", description="Priority: normal, high, urgent")
    preferred_language: str = Field(default="en", description="Language")
    session_type: str = Field(default="chat", description="Session type")
    
    @field_validator('contract_id', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty string to None for contract_id"""
        if v == '' or v == 'null' or v == 'undefined':
            return None
        return v
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        """Ensure question is not too short"""
        if len(v.strip()) < 20:
            raise ValueError('Question must be at least 20 characters long')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "contract_id": None,
                "query_type": "legal_compliance",
                "subject": "QFCRA Compliance Question",
                "question": "We need clarification on the arbitration clause compliance with QFCRA Rule 18...",
                "expertise_areas": ["qfcra", "arbitration"],
                "priority": "normal",
                "preferred_language": "en",
                "session_type": "chat"
            }
        }


class ExpertQueryResponse(BaseModel):
    """Schema for expert query response"""
    success: bool = True
    message: str
    query_id: str
    query_code: str
    status: str
    asked_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Query submitted successfully",
                "query_id": "550e8400-e29b-41d4-a716-446655440000",
                "query_code": "QRY-20251021-ABC123",
                "status": "open",
                "asked_at": "2025-10-21T10:30:00"
            }
        }


class QueryDetailResponse(BaseModel):
    """Schema for detailed query information"""
    query_id: str
    query_code: str
    query_type: str
    subject: str
    question: str
    response: Optional[str] = None
    priority: str
    status: str
    asked_at: datetime
    responded_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    asked_by_name: str
    contract_name: Optional[str] = None
    expert_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class QueryUpdateRequest(BaseModel):
    """Schema for updating query status"""
    status: str = Field(..., description="New status: open, in_progress, answered, closed")
    response: Optional[str] = Field(None, description="Expert response text")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "answered",
                "response": "Based on QFCRA Rule 18, the arbitration clause should include..."
            }
        }


# =====================================================
# EXPERT DIRECTORY - LIST SCHEMAS
# =====================================================

class ExpertBasicInfo(BaseModel):
    """Basic expert information"""
    expert_id: str
    first_name: str
    last_name: str
    full_name: str
    email: EmailStr
    profile_picture: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    is_available: bool = True
    availability_status: str = "available"
    
    class Config:
        from_attributes = True


class ExpertDetailedInfo(ExpertBasicInfo):
    """Detailed expert information for directory listing"""
    phone: Optional[str] = None
    expertise_areas: List[str] = []
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    license_authority: Optional[str] = None
    years_of_experience: int = 0
    bio: Optional[str] = None
    hourly_rate: float = 0.0
    total_consultations: int = 0
    average_rating: float = 0.0
    qfcra_certified: bool = False
    qid_verified: bool = False
    active_sessions: int = 0
    
    class Config:
        from_attributes = True


class ExpertListResponse(BaseModel):
    """Schema for expert directory listing response"""
    success: bool = True
    experts: List[ExpertDetailedInfo]
    total_count: int
    limit: int
    offset: int
    has_more: bool
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "success": True,
                "experts": [
                    {
                        "expert_id": "1",
                        "first_name": "Ahmad",
                        "last_name": "Al Kaabi",
                        "full_name": "Ahmad Al Kaabi",
                        "email": "ahmad@expert.qa",
                        "profile_picture": "/static/uploads/experts/ahmad.jpg",
                        "department": "Legal",
                        "job_title": "Senior Construction Law Specialist",
                        "expertise_areas": ["Construction Law", "QFCRA", "Arbitration"],
                        "specialization": "Construction Law",
                        "years_of_experience": 15,
                        "is_available": True,
                        "availability_status": "available",
                        "average_rating": 4.8,
                        "total_consultations": 45,
                        "qfcra_certified": True,
                        "qid_verified": True
                    }
                ],
                "total_count": 24,
                "limit": 50,
                "offset": 0,
                "has_more": False
            }
        }


class ExpertProfileResponse(ExpertDetailedInfo):
    """Complete expert profile with reviews"""
    recent_reviews: List[Dict[str, Any]] = []
    
    class Config:
        from_attributes = True


# =====================================================
# EXPERT DIRECTORY - STATISTICS
# =====================================================

class ExpertStatsResponse(BaseModel):
    """Response for expert statistics"""
    total_experts: int
    available_now: int
    avg_response_time: str
    platform_rating: float
    total_consultations: int
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "total_experts": 24,
                "available_now": 18,
                "avg_response_time": "< 5 min",
                "platform_rating": 4.7,
                "total_consultations": 856
            }
        }


# =====================================================
# EXPERT AVAILABILITY
# =====================================================

class ExpertAvailabilityResponse(BaseModel):
    """Response for expert availability schedule"""
    expert_id: str
    schedule: List[Dict[str, Any]]
    timezone: str = "Asia/Qatar"
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "expert_id": "1",
                "schedule": [
                    {
                        "day": "Sunday",
                        "day_of_week": 0,
                        "start_time": "09:00:00",
                        "end_time": "17:00:00",
                        "is_available": True,
                        "timezone": "Asia/Qatar"
                    }
                ],
                "timezone": "Asia/Qatar"
            }
        }


# =====================================================
# CONSULTATION SESSION SCHEMAS
# =====================================================

class ConsultationSessionCreate(BaseModel):
    """Schema for creating consultation session"""
    query_id: str
    expert_id: str
    session_type: str = Field(..., description="chat or video")
    scheduled_time: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "550e8400-e29b-41d4-a716-446655440000",
                "expert_id": "1",
                "session_type": "video",
                "scheduled_time": "2025-10-22T14:00:00"
            }
        }


class ConsultationSessionResponse(BaseModel):
    """Schema for consultation session details"""
    session_id: str
    query_id: str
    expert_id: str
    session_type: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    recording_url: Optional[str] = None
    memo_file: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConsultationResponse(BaseModel):
    """Response for consultation details"""
    session_id: str
    session_code: str
    session_type: str
    status: str
    created_at: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    expert_name: str
    expert_avatar: Optional[str] = None
    contract_name: Optional[str] = None
    subject: Optional[str] = None
    question: Optional[str] = None
    
    class Config:
        from_attributes = True


# =====================================================
# SESSION FEEDBACK
# =====================================================

class SessionFeedbackCreate(BaseModel):
    """Schema for submitting session feedback"""
    session_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating between 1-5")
    feedback_text: Optional[str] = None
    would_recommend: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "ses-uuid-here",
                "rating": 5,
                "feedback_text": "Excellent consultation, very helpful",
                "would_recommend": True
            }
        }


class SessionMessageResponse(BaseModel):
    """Response for session messages"""
    message_id: str
    session_id: str
    sender_id: str
    sender_name: str
    message_text: str
    message_type: str = "text"
    created_at: datetime
    is_read: bool = False
    
    class Config:
        from_attributes = True


class ActionItemResponse(BaseModel):
    """Response for action items"""
    item_id: str
    session_id: str
    task_description: str
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"
    status: str = "pending"
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =====================================================
# SEARCH AND FILTER SCHEMAS
# =====================================================

class ExpertSearchRequest(BaseModel):
    """Schema for expert search and filter request"""
    search: Optional[str] = Field(None, description="Search by name, email, or specialization")
    expertise_area: Optional[str] = Field(None, description="Filter by expertise area")
    availability_status: Optional[str] = Field(None, description="Filter by availability")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating")
    qfcra_certified: Optional[bool] = Field(None, description="Filter QFCRA certified experts")
    limit: int = Field(50, ge=1, le=100, description="Results per page")
    offset: int = Field(0, ge=0, description="Pagination offset")
    
    class Config:
        json_schema_extra = {
            "example": {
                "search": "construction",
                "expertise_area": "qfcra",
                "availability_status": "available",
                "min_rating": 4.0,
                "qfcra_certified": True,
                "limit": 20,
                "offset": 0
            }
        }


# =====================================================
# RESPONSE WRAPPERS
# =====================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {}
            }
        }


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "Operation failed",
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "error message"}
            }
        }