# =====================================================
# FILE: app/api/api_v1/contracts/schemas.py
# Contract API Schemas - FIXED for Contract Creation
# =====================================================

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# =====================================================
# ENUMS
# =====================================================

class ProfileType(str, Enum):
    CLIENT = "client"
    CONSULTANT = "consultant"
    CONTRACTOR = "contractor"
    SUB_CONTRACTOR = "sub_contractor"


class ContractStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class ConfidentialityLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    STANDARD = "STANDARD"


# =====================================================
# CONTRACT CREATE REQUEST - SIMPLIFIED
# =====================================================

class ContractCreateRequest(BaseModel):
    """
    Simplified contract creation request.
    Only requires minimal fields - others can be added later.
    """
    contract_title: str = Field(..., min_length=3, max_length=500, description="Contract title")
    profile_type: ProfileType = Field(ProfileType.CLIENT, description="User's role in contract")
    
    # Optional fields
    project_id: Optional[int] = Field(None, description="Link to project")
    template_id: Optional[int] = Field(None, description="Template used")
    contract_type: Optional[str] = Field(None, max_length=100, description="Type of contract")
    
    # Dates - Optional for initial creation
    effective_date: Optional[date] = Field(None, description="Contract start date")
    expiry_date: Optional[date] = Field(None, description="Contract end date")
    auto_renewal: bool = Field(False, description="Auto-renewal enabled")
    renewal_period_months: Optional[int] = Field(None, ge=1, le=120)
    renewal_notice_days: Optional[int] = Field(None, ge=1, le=365)
    
    # Financial
    contract_value: Optional[float] = Field(None, ge=0)
    currency: str = Field("QAR", max_length=10)
    
    # Additional info
    confidentiality_level: Optional[ConfidentialityLevel] = Field(ConfidentialityLevel.STANDARD)
    language: str = Field("en", max_length=10)
    governing_law: Optional[str] = Field(None, max_length=100)
    
    tags: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('expiry_date')
    def validate_expiry_date(cls, v, values):
        """Validate expiry date is after effective date if both are provided"""
        if v and 'effective_date' in values and values['effective_date']:
            if v <= values['effective_date']:
                raise ValueError('Expiry date must be after effective date')
        return v
    
    @validator('contract_title')
    def validate_title(cls, v):
        """Validate contract title"""
        if not v or v.strip() == '':
            raise ValueError('Contract title cannot be empty')
        return v.strip()

    class Config:
        use_enum_values = True


# =====================================================
# CONTRACT UPDATE REQUEST
# =====================================================

class ContractUpdateRequest(BaseModel):
    """Update existing contract"""
    contract_title: Optional[str] = Field(None, max_length=500)
    contract_type: Optional[str] = None
    
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    auto_renewal: Optional[bool] = None
    renewal_period_months: Optional[int] = None
    renewal_notice_days: Optional[int] = None
    
    confidentiality_level: Optional[ConfidentialityLevel] = None
    language: Optional[str] = None
    governing_law: Optional[str] = None
    
    contract_value: Optional[float] = None
    currency: Optional[str] = None
    
    status: Optional[ContractStatus] = None
    tags: Optional[List[str]] = None

    class Config:
        use_enum_values = True


# =====================================================
# CONTRACT RESPONSE
# =====================================================

class ContractResponse(BaseModel):
    """Standard contract response"""
    id: int
    contract_number: str
    contract_title: str
    contract_type: Optional[str]
    profile_type: str
    
    template_id: Optional[int]
    project_id: Optional[int]
    
    contract_value: Optional[float]
    currency: Optional[str] = "QAR"  # Default to QAR if None
    
    effective_date: Optional[date]
    expiry_date: Optional[date]
    auto_renewal: bool
    renewal_period_months: Optional[int]
    renewal_notice_days: Optional[int]
    
    status: str
    workflow_status: Optional[str]
    current_version: int
    
    is_locked: bool
    locked_by: Optional[int]
    locked_at: Optional[datetime]
    
    confidentiality_level: Optional[str]
    language: Optional[str]
    governing_law: Optional[str]
    
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContractDetailResponse(ContractResponse):
    """Detailed contract response with additional data"""
    tags: Optional[Dict]
    metadata: Optional[Dict]


# =====================================================
# CONTRACT LIST RESPONSE
# =====================================================

class ContractListResponse(BaseModel):
    """Paginated list of contracts"""
    total: int
    items: List[ContractResponse]
    page: int = 1
    page_size: int = 20


# =====================================================
# CLAUSE SCHEMAS
# =====================================================

class ClauseCreateRequest(BaseModel):
    """Create a new clause"""
    contract_id: int
    clause_title: str = Field(..., max_length=255)
    clause_text: str = Field(..., description="Clause content")
    clause_number: Optional[str] = Field(None, max_length=50)
    position: int = Field(..., description="Order position in contract")
    is_mandatory: bool = Field(False)
    is_negotiable: bool = Field(True)
    clause_library_id: Optional[int] = None


class ClauseUpdateRequest(BaseModel):
    """Update existing clause"""
    clause_title: Optional[str] = None
    clause_text: Optional[str] = None
    clause_number: Optional[str] = None
    position: Optional[int] = None
    is_mandatory: Optional[bool] = None
    is_negotiable: Optional[bool] = None
    status: Optional[str] = None


class ClauseResponse(BaseModel):
    """Clause response"""
    id: int
    contract_id: int
    clause_library_id: Optional[int]
    clause_number: Optional[str]
    clause_title: str
    clause_text: str
    position: int
    is_mandatory: bool
    is_negotiable: bool
    status: str
    added_by: int
    added_at: datetime
    modified_at: Optional[datetime]

    class Config:
        from_attributes = True


class ClauseListResponse(BaseModel):
    """List of clauses"""
    total: int
    items: List[ClauseResponse]


# =====================================================
# TEMPLATE SCHEMAS
# =====================================================

class TemplateResponse(BaseModel):
    """Template response"""
    id: int
    template_name: str
    template_type: Optional[str]
    template_category: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreationOptionsResponse(BaseModel):
    """Response for contract creation options"""
    profile_type: str
    template_categories: Dict[str, List[TemplateResponse]]
    creation_methods: List[str]
    ai_capabilities: Dict[str, bool]


# =====================================================
# AI DRAFTING SCHEMAS
# =====================================================

class AIDraftingRequest(BaseModel):
    """Request for AI clause drafting"""
    contract_id: int
    clause_title: str = Field(..., description="Title/topic of the clause to draft")
    jurisdiction: Optional[str] = Field("Qatar", description="Legal jurisdiction")
    business_context: Optional[str] = Field(None, description="Business context")
    contract_type: Optional[str] = Field(None, description="Contract type")
    language: str = Field("en", description="Language for drafted clause")
    party_role: Optional[str] = Field(None, description="User role")


class AIDraftingResponse(BaseModel):
    """Response from AI drafting"""
    clause_title: str
    clause_body: str
    ai_generated: bool = True
    confidence_score: Optional[float] = None
    suggestions: Optional[List[str]] = None
    clause_id: Optional[int] = None
    saved_to_database: bool = False
    model_used: Optional[str] = None


# =====================================================
# UPLOAD SCHEMAS
# =====================================================

class ContractUploadRequest(BaseModel):
    """Request for contract upload"""
    contract_title: str
    project_id: Optional[int] = None
    profile_type: ProfileType = ProfileType.CLIENT
    extract_clauses: bool = True
    analyze_risks: bool = True


class ContractUploadResponse(BaseModel):
    """Response for contract upload"""
    success: bool
    contract_id: int
    contract_number: str
    extracted_clauses_count: Optional[int]
    identified_risks_count: Optional[int]
    message: str