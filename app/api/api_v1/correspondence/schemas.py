# =====================================================
# FILE: app/api/api_v1/correspondence/schemas.py
# Comprehensive Pydantic Models for Correspondence API
# =====================================================

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# =====================================================
# ENUMS
# =====================================================

class CorrespondenceType(str, Enum):
    """Correspondence types"""
    EMAIL = "email"
    LETTER = "letter"
    QUERY = "query"
    RESPONSE = "response"
    AI_QUERY = "ai_query"
    NOTICE = "notice"


class Priority(str, Enum):
    """Priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Status(str, Enum):
    """Correspondence status"""
    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"
    READ = "read"
    ARCHIVED = "archived"


class Tone(str, Enum):
    """AI response tone - aligned with Claude API tones"""
    DEFAULT = "default"
    APPRECIATIVE = "appreciative"
    ASSERTIVE = "assertive"
    CAUTIONARY = "cautionary"
    CONCILIATORY = "conciliatory"
    CONSULTATIVE = "consultative"
    CONVINCING = "convincing"
    ENTHUSIASTIC = "enthusiastic"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    MOTIVATING = "motivating"
    PROFESSIONAL = "professional"


class ExportFormat(str, Enum):
    """Export formats"""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"


# =====================================================
# BASE MODELS
# =====================================================

class DocumentReference(BaseModel):
    """Reference document for correspondence"""
    document_id: str = Field(..., description="Document UUID")
    document_name: str = Field(..., description="Document name")
    document_type: Optional[str] = Field(None, description="Document type")


class SourceReference(BaseModel):
    """Source reference in AI response"""
    document_id: str = Field(..., description="Document UUID")
    document_name: str = Field(..., description="Document name")
    page_number: Optional[int] = Field(None, description="Page number")
    section: Optional[str] = Field(None, description="Section reference (e.g., Clause 15.3)")
    excerpt: Optional[str] = Field(None, max_length=500, description="Text excerpt")
    relevance_score: float = Field(..., ge=0, le=1, description="AI relevance score")


class Recommendation(BaseModel):
    """AI recommendation"""
    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Detailed description")
    priority: Priority = Field(..., description="Priority level")
    action_items: List[str] = Field(default=[], description="Actionable steps")


# =====================================================
# AI GENERATION REQUEST/RESPONSE SCHEMAS
# =====================================================

class AIQueryRequest(BaseModel):
    """Request schema for AI-powered correspondence generation"""
    query_text: str = Field(
        ..., 
        min_length=10, 
        max_length=5000, 
        description="Query or instruction for AI"
    )
    selected_document_ids: List[str] = Field(
        default=[], 
        description="Document IDs to use as reference"
    )
    tone: Tone = Field(
        default=Tone.PROFESSIONAL, 
        description="Desired response tone"
    )
    correspondence_type: CorrespondenceType = Field(
        default=CorrespondenceType.EMAIL,
        description="Type of correspondence to generate"
    )
    urgency: Priority = Field(
        default=Priority.NORMAL, 
        description="Urgency level"
    )
    contract_id: Optional[str] = Field(
        None, 
        description="Contract ID for context"
    )
    additional_context: Optional[str] = Field(
        None, 
        max_length=2000, 
        description="Additional context information"
    )


class AIQueryResponse(BaseModel):
    """Response schema for AI query with comprehensive metadata"""
    correspondence_id: str = Field(..., description="Created correspondence ID")
    response_text: str = Field(..., description="AI generated response text")
    confidence_score: float = Field(
        ..., 
        ge=0, 
        le=100, 
        description="AI confidence score (0-100)"
    )
    analysis_time: float = Field(..., description="Analysis time in seconds")
    source_references: List[SourceReference] = Field(
        default=[], 
        description="Source documents and references used"
    )
    recommendations: List[Recommendation] = Field(
        default=[], 
        description="AI-generated recommendations"
    )
    tokens_used: Optional[int] = Field(None, description="API tokens consumed")
    model: Optional[str] = Field(None, description="AI model used")
    created_at: datetime = Field(..., description="Generation timestamp")


class CorrespondenceGenerateRequest(BaseModel):
    """Alternative simpler request format for backward compatibility"""
    query: str = Field(..., description="User's query or instruction")
    documents: List[DocumentReference] = Field(default=[], description="Reference documents")
    tone: str = Field(default="professional", description="Desired tone")
    correspondence_type: str = Field(default="email", description="Type of correspondence")
    contract_id: Optional[str] = None
    subject: Optional[str] = None


class CorrespondenceGenerateResponse(BaseModel):
    """Simple generation response format"""
    success: bool
    content: str
    tone: Optional[str] = None
    type: Optional[str] = None
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    generated_at: Optional[str] = None
    error: Optional[str] = None


# =====================================================
# CORRESPONDENCE CRUD SCHEMAS
# =====================================================

class CorrespondenceCreate(BaseModel):
    """Schema for creating correspondence"""
    contract_id: Optional[str] = Field(None, description="Contract ID")
    correspondence_type: CorrespondenceType = Field(..., description="Type of correspondence")
    subject: str = Field(..., min_length=1, max_length=500, description="Subject line")
    content: str = Field(..., min_length=1, description="Email/letter content")
    recipient_ids: List[str] = Field(default=[], description="Recipient user IDs (JSON array)")
    cc_ids: List[str] = Field(default=[], description="CC user IDs (JSON array)")
    priority: Priority = Field(default=Priority.NORMAL, description="Priority level")
    status: Status = Field(default=Status.DRAFT, description="Initial status")
    is_ai_generated: bool = Field(default=False, description="Was this AI-generated?")
    ai_tone: Optional[str] = Field(None, description="AI tone used if applicable")
    attachments: List[str] = Field(default=[], description="Document IDs to attach")


class CorrespondenceUpdate(BaseModel):
    """Schema for updating correspondence"""
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    recipient_ids: Optional[List[str]] = None
    cc_ids: Optional[List[str]] = None


# =====================================================
# RESPONSE SCHEMAS
# =====================================================

class AttachmentResponse(BaseModel):
    """Attachment information in response"""
    id: str = Field(..., description="Attachment ID")
    attachment_name: str = Field(..., description="File name")
    attachment_type: Optional[str] = Field(None, description="MIME type")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_url: Optional[str] = Field(None, description="Download URL")
    uploaded_at: Optional[datetime] = Field(None, description="Upload timestamp")


class CorrespondenceResponse(BaseModel):
    """Detailed correspondence response"""
    id: str = Field(..., description="Correspondence UUID")
    contract_id: Optional[str] = Field(None, description="Related contract ID")
    contract_number: Optional[str] = Field(None, description="Contract number")
    contract_title: Optional[str] = Field(None, description="Contract title")
    correspondence_type: str = Field(..., description="Type")
    subject: str = Field(..., description="Subject")
    content: str = Field(..., description="Full content")
    sender_id: str = Field(..., description="Sender user ID")
    sender_name: str = Field(..., description="Sender full name")
    sender_email: str = Field(..., description="Sender email")
    recipient_ids: List[str] = Field(default=[], description="Recipients")
    cc_ids: List[str] = Field(default=[], description="CC recipients")
    priority: str = Field(..., description="Priority level")
    status: str = Field(..., description="Status")
    is_ai_generated: bool = Field(..., description="AI generated flag")
    ai_tone: Optional[str] = Field(None, description="AI tone used")
    attachments: List[AttachmentResponse] = Field(default=[], description="Attachments")
    attachments_count: int = Field(default=0, description="Number of attachments")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")
    created_at: datetime = Field(..., description="Created timestamp")
    
    class Config:
        from_attributes = True


class CorrespondenceSummary(BaseModel):
    """Summary for list view - lighter weight"""
    id: str
    contract_id: Optional[str]
    contract_number: Optional[str]
    contract_title: Optional[str]
    correspondence_type: str
    subject: str
    sender_name: str
    sender_email: str
    priority: str
    status: str
    is_ai_generated: bool
    attachments_count: int = 0
    sent_at: Optional[datetime]
    created_at: datetime


class CorrespondenceListResponse(BaseModel):
    """Paginated list of correspondence"""
    items: List[Dict[str, Any]] = Field(..., description="Correspondence items")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total pages")
    
    @validator('pages', always=True)
    def calculate_pages(cls, v, values):
        """Auto-calculate total pages"""
        if 'total' in values and 'page_size' in values:
            total = values['total']
            page_size = values['page_size']
            return (total + page_size - 1) // page_size if page_size > 0 else 0
        return v


# =====================================================
# DOCUMENT ANALYSIS SCHEMAS
# =====================================================

class DocumentSelectionRequest(BaseModel):
    """Request for document selection"""
    document_ids: List[str] = Field(..., min_items=1, description="Document IDs to select")


class DocumentAnalysisRequest(BaseModel):
    """Request to analyze documents for correspondence insights"""
    documents: List[DocumentReference] = Field(..., min_items=1)
    query: str = Field(..., min_length=10)


class DocumentAnalysisResponse(BaseModel):
    """Document analysis response with insights"""
    success: bool
    analysis: Optional[str] = None
    key_findings: Optional[List[str]] = Field(default=[], description="Key findings")
    risks: Optional[List[str]] = Field(default=[], description="Identified risks")
    opportunities: Optional[List[str]] = Field(default=[], description="Opportunities")
    recommended_actions: Optional[List[str]] = Field(default=[], description="Actions")
    confidence_score: Optional[float] = Field(None, ge=0, le=100)
    error: Optional[str] = None


# =====================================================
# EXPORT SCHEMAS
# =====================================================

class ExportRequest(BaseModel):
    """Request schema for exporting correspondence"""
    format: ExportFormat = Field(..., description="Export format")
    include_attachments: bool = Field(default=True, description="Include attachments")
    include_metadata: bool = Field(default=True, description="Include metadata")


class ExportResponse(BaseModel):
    """Export response with file information"""
    success: bool
    file_url: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    format: Optional[str] = None
    generated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


# =====================================================
# ATTACHMENT SCHEMAS
# =====================================================

class AttachmentUpload(BaseModel):
    """Schema for attachment upload"""
    filename: str = Field(..., min_length=1, description="File name")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    content_type: str = Field(..., description="MIME type")
    
    @validator('file_size')
    def validate_file_size(cls, v):
        """Validate file size (max 50MB)"""
        max_size = 50 * 1024 * 1024  # 50MB
        if v > max_size:
            raise ValueError(f'File size exceeds maximum allowed size of 50MB')
        return v


# =====================================================
# STATISTICS SCHEMAS
# =====================================================

class CorrespondenceStats(BaseModel):
    """Comprehensive correspondence statistics"""
    total_count: int = Field(..., description="Total correspondence")
    by_status: Dict[str, int] = Field(default={}, description="Count by status")
    by_type: Dict[str, int] = Field(default={}, description="Count by type")
    by_priority: Dict[str, int] = Field(default={}, description="Count by priority")
    ai_generated_count: int = Field(..., description="AI generated count")
    ai_generated_percentage: float = Field(..., ge=0, le=100, description="AI percentage")
    avg_response_time: Optional[float] = Field(None, description="Avg response time (hours)")
    pending_responses: int = Field(..., description="Pending responses")
    overdue_count: int = Field(..., description="Overdue correspondence")


class TimeSeriesData(BaseModel):
    """Time series data point"""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    count: int = Field(..., description="Count for that date")


class CorrespondenceTrends(BaseModel):
    """Trend analysis over time"""
    period: str = Field(..., description="Period (daily, weekly, monthly)")
    data_points: List[TimeSeriesData] = Field(..., description="Time series data")
    total_in_period: int = Field(..., description="Total in period")
    growth_percentage: float = Field(..., description="Growth vs previous period")


# =====================================================
# FILTER SCHEMAS
# =====================================================

class CorrespondenceFilter(BaseModel):
    """Advanced filter options"""
    correspondence_type: Optional[CorrespondenceType] = None
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    contract_id: Optional[str] = None
    sender_id: Optional[str] = None
    is_ai_generated: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = Field(None, max_length=200)


# =====================================================
# BULK OPERATIONS SCHEMAS
# =====================================================

class BulkActionRequest(BaseModel):
    """Bulk action on multiple correspondence"""
    correspondence_ids: List[str] = Field(..., min_items=1, description="IDs to act on")
    action: str = Field(..., description="Action: archive, delete, mark_read, change_priority")
    new_status: Optional[Status] = None
    new_priority: Optional[Priority] = None


class BulkActionResponse(BaseModel):
    """Response from bulk action"""
    success: bool
    affected_count: int = Field(..., description="Number of items affected")
    failed_ids: List[str] = Field(default=[], description="Failed IDs")
    errors: List[str] = Field(default=[], description="Error messages")