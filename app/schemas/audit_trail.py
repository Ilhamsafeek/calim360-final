# =====================================================
# FILE: app/schemas/audit_trail.py
# Pydantic Schemas for Audit Trail API
# =====================================================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# =====================================================
# ENUMS
# =====================================================

class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"

class ActionType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    APPROVE = "approve"
    REJECT = "reject"
    SIGN = "sign"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    SHARE = "share"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"

class EntityType(str, Enum):
    CONTRACT = "contract"
    PROJECT = "project"
    DOCUMENT = "document"
    USER = "user"
    WORKFLOW = "workflow"
    OBLIGATION = "obligation"
    CLAUSE = "clause"

# =====================================================
# REQUEST SCHEMAS
# =====================================================

class AuditLogFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    action_type: Optional[str] = None
    entity_type: Optional[str] = None
    user_id: Optional[int] = None
    entity_id: Optional[str] = None
    search: Optional[str] = None

class CreateAuditLog(BaseModel):
    user_id: Optional[int] = None
    contract_id: Optional[int] = None
    action_type: str = Field(..., description="Type of action performed")
    action_details: Dict[str, Any] = Field(default={}, description="JSON details of the action")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

# =====================================================
# RESPONSE SCHEMAS
# =====================================================

class AuditLogResponse(BaseModel):
    id: int
    timestamp: Optional[str]
    action_type: str
    action_details: Dict[str, Any]
    user_id: Optional[int]
    user_name: str
    contract_id: Optional[int]
    ip_address: Optional[str]
    user_agent: Optional[str]
    entity_type: str
    entity_id: Optional[str]
    blockchain_verified: bool
    blockchain_hash: Optional[str]

    class Config:
        from_attributes = True

class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int

class AuditLogListResponse(BaseModel):
    success: bool
    data: List[AuditLogResponse]
    pagination: PaginationInfo

class AuditStatistics(BaseModel):
    success: bool
    total_events: int
    unique_users: int
    blockchain_verified: int
    action_breakdown: Dict[str, int]
    period: Dict[str, Optional[str]]

class BlockchainVerificationResponse(BaseModel):
    success: bool
    verified: bool
    message: str
    blockchain_hash: Optional[str]
    verification_timestamp: Optional[str]
    data_hash: Optional[str] = None
    current_hash: Optional[str] = None
    network: Optional[str] = None
    block_number: Optional[str] = None

class ActionTypesResponse(BaseModel):
    success: bool
    action_types: List[str]

class UserFilterResponse(BaseModel):
    id: int
    name: str
    email: str

class UsersListResponse(BaseModel):
    success: bool
    users: List[UserFilterResponse]

# =====================================================
# BLOCKCHAIN SCHEMAS
# =====================================================

class BlockchainRecordCreate(BaseModel):
    entity_type: str
    entity_id: str
    data_hash: str
    transaction_hash: Optional[str] = None
    blockchain_network: str = "hyperledger-fabric"
    block_number: Optional[str] = None

class BlockchainRecordResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    data_hash: str
    transaction_hash: Optional[str]
    blockchain_network: str
    block_number: Optional[str]
    verification_status: str
    created_at: datetime
    verified_at: Optional[datetime]

    class Config:
        from_attributes = True