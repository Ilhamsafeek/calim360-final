# placeholder for: app/api/api_v1/workflow/schemas.py
"""
Master Workflow Pydantic Schemas
File: app/api/api_v1/workflow/schemas.py
Description: Data validation and serialization schemas for Master Workflow API
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


# =====================================================
# USER SELECTION SCHEMAS
# =====================================================

class UserSelection(BaseModel):
    """User selection for workflow step"""
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@company.qa"
            }
        }


# =====================================================
# WORKFLOW STEP SCHEMAS
# =====================================================

class WorkflowStepCreate(BaseModel):
    """Schema for creating workflow step"""
    step_order: int = Field(..., ge=1, description="Step order in workflow (1-based)")
    role: str = Field(..., min_length=1, description="Role name for this step")
    users: List[UserSelection] = Field(default=[], description="Assigned users for this step")
    department: Optional[str] = Field(None, description="Department name")
    sla_hours: Optional[int] = Field(48, ge=1, le=720, description="SLA in hours (1-720)")
    
    @validator('role')
    def validate_role(cls, v):
        """Validate role is not empty"""
        if not v or v.strip() == "":
            raise ValueError("Role cannot be empty")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "step_order": 1,
                "role": "reviewer",
                "users": [
                    {"name": "John Doe", "email": "john@company.qa"}
                ],
                "department": "Legal",
                "sla_hours": 48
            }
        }


class WorkflowStepUpdate(BaseModel):
    """Schema for updating workflow step"""
    step_order: Optional[int] = Field(None, ge=1)
    role: Optional[str] = None
    users: Optional[List[UserSelection]] = None
    department: Optional[str] = None
    sla_hours: Optional[int] = Field(None, ge=1, le=720)


class WorkflowStepResponse(BaseModel):
    """Schema for workflow step response"""
    id: int
    step_number: int
    step_name: str
    step_type: str
    assignee_role: Optional[str] = None
    assignee_user_id: Optional[int] = None
    sla_hours: Optional[int] = None
    is_mandatory: bool

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "step_number": 1,
                "step_name": "reviewer",
                "step_type": "reviewer",
                "assignee_role": "reviewer",
                "assignee_user_id": None,
                "sla_hours": 48,
                "is_mandatory": True
            }
        }


# =====================================================
# MASTER WORKFLOW SCHEMAS
# =====================================================

class MasterWorkflowCreate(BaseModel):
    """Schema for creating master workflow"""
    workflow_name: Optional[str] = Field(
        "Master Workflow", 
        min_length=1, 
        max_length=255,
        description="Workflow name"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000,
        description="Workflow description"
    )
    steps: List[WorkflowStepCreate] = Field(
        ..., 
        min_length=1,
        description="Workflow steps (at least 1 required)"
    )
    settings: Optional[Dict[str, Any]] = Field(
        default={
            "auto_escalation": True,
            "parallel_approval": False,
            "require_all_approvals": True
        },
        description="Workflow settings and configurations"
    )
    
    @validator('steps')
    def validate_steps(cls, v):
        """Validate steps have unique order"""
        if not v:
            raise ValueError("At least one workflow step is required")
        
        orders = [step.step_order for step in v]
        if len(orders) != len(set(orders)):
            raise ValueError("Duplicate step orders are not allowed")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_name": "Master Workflow",
                "description": "Company-wide default approval workflow",
                "steps": [
                    {
                        "step_order": 1,
                        "role": "reviewer",
                        "users": [{"name": "John Doe", "email": "john@company.qa"}],
                        "department": "Legal",
                        "sla_hours": 48
                    },
                    {
                        "step_order": 2,
                        "role": "approver",
                        "users": [{"name": "Jane Smith", "email": "jane@company.qa"}],
                        "department": "Finance",
                        "sla_hours": 24
                    }
                ],
                "settings": {
                    "auto_escalation": True,
                    "parallel_approval": False,
                    "require_all_approvals": True
                }
            }
        }


class MasterWorkflowUpdate(BaseModel):
    """Schema for updating master workflow"""
    workflow_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    steps: Optional[List[WorkflowStepCreate]] = None
    settings: Optional[Dict[str, Any]] = None
    
    @validator('steps')
    def validate_steps(cls, v):
        """Validate steps if provided"""
        if v is not None and len(v) == 0:
            raise ValueError("At least one workflow step is required")
        
        if v:
            orders = [step.step_order for step in v]
            if len(orders) != len(set(orders)):
                raise ValueError("Duplicate step orders are not allowed")
        
        return v


class MasterWorkflowData(BaseModel):
    """Master workflow data response"""
    id: int
    workflow_name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    steps: List[WorkflowStepResponse]
    
    class Config:
        from_attributes = True


class MasterWorkflowResponse(BaseModel):
    """Response schema for master workflow operations"""
    success: bool
    message: str
    data: Optional[MasterWorkflowData] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Master workflow retrieved successfully",
                "data": {
                    "id": 1,
                    "workflow_name": "Master Workflow",
                    "description": "Company default workflow",
                    "is_active": True,
                    "created_at": "2025-01-15T10:00:00",
                    "updated_at": "2025-01-15T10:00:00",
                    "steps": [
                        {
                            "id": 1,
                            "step_number": 1,
                            "step_name": "reviewer",
                            "step_type": "reviewer",
                            "assignee_role": "reviewer",
                            "assignee_user_id": None,
                            "sla_hours": 48,
                            "is_mandatory": True
                        }
                    ]
                }
            }
        }


# =====================================================
# ROLE AND DEPARTMENT SCHEMAS
# =====================================================

class UserByRoleResponse(BaseModel):
    """User response for role-based queries"""
    id: int
    name: str
    email: EmailStr
    role: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "John Doe",
                "email": "john@company.qa",
                "role": "reviewer"
            }
        }


class RoleOption(BaseModel):
    """Role option for dropdown"""
    value: str = Field(..., description="Role value/identifier")
    label: str = Field(..., description="Role display label")
    
    class Config:
        json_schema_extra = {
            "example": {
                "value": "reviewer",
                "label": "Reviewer"
            }
        }


class DepartmentOption(BaseModel):
    """Department option for dropdown"""
    id: int
    name: str
    code: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Legal Department",
                "code": "LEGAL"
            }
        }


# =====================================================
# VALIDATION SCHEMAS
# =====================================================

class WorkflowValidationError(BaseModel):
    """Workflow validation error"""
    field: str = Field(..., description="Field name with error")
    message: str = Field(..., description="Error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "field": "steps[0].role",
                "message": "Role is required"
            }
        }


class WorkflowValidationResponse(BaseModel):
    """Workflow validation response"""
    is_valid: bool
    errors: List[WorkflowValidationError] = Field(default=[])
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": False,
                "errors": [
                    {
                        "field": "steps[0].role",
                        "message": "Role is required"
                    }
                ]
            }
        }


# =====================================================
# GENERIC RESPONSE SCHEMAS
# =====================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    message: str
    detail: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None


class ListResponse(BaseModel):
    """Generic list response"""
    success: bool
    data: List[Any]
    count: Optional[int] = None


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def workflow_step_to_dict(step) -> dict:
    """Convert WorkflowStep model to dictionary"""
    return {
        "id": step.id,
        "step_number": step.step_number,
        "step_name": step.step_name,
        "step_type": step.step_type,
        "assignee_role": step.assignee_role,
        "assignee_user_id": step.assignee_user_id,
        "sla_hours": step.sla_hours,
        "is_mandatory": step.is_mandatory
    }


def workflow_to_dict(workflow, steps: list) -> dict:
    """Convert Workflow model to dictionary with steps"""
    return {
        "id": workflow.id,
        "workflow_name": workflow.workflow_name,
        "description": workflow.description,
        "is_active": workflow.is_active,
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at,
        "steps": [workflow_step_to_dict(step) for step in steps]
    }