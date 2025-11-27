# =====================================================
# FILE: app/api/api_v1/workflow/router.py
# Master Workflow API Routes
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.api.api_v1.workflow.service import WorkflowService

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# =====================================================
# Pydantic Schemas
# =====================================================

class UserSelection(BaseModel):
    id: int
    name: str
    email: str
    department: Optional[str] = None

class WorkflowStepCreate(BaseModel):
    step_number: int
    step_name: str
    step_type: str  # reviewer, approver, e-sign, counter-party
    role: str
    department: Optional[str] = None
    users: List[UserSelection] = []
    sla_hours: Optional[int] = 24
    is_mandatory: bool = True

class MasterWorkflowCreate(BaseModel):
    workflow_name: str
    description: Optional[str] = None
    steps: List[WorkflowStepCreate]
    auto_escalation: bool = False
    escalation_hours: Optional[int] = None

class WorkflowStepResponse(BaseModel):
    id: int
    step_number: int
    step_name: str
    step_type: str
    assignee_role: str
    assignee_user_id: Optional[int] = None
    sla_hours: Optional[int] = None
    is_mandatory: bool = True
    department: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class MasterWorkflowResponse(BaseModel):
    id: int
    workflow_name: str
    description: Optional[str] = None
    is_master: bool = True
    is_active: bool = True
    created_at: datetime
    steps: List[WorkflowStepResponse] = []

    class Config:
        from_attributes = True
        populate_by_name = True

# =====================================================
# Helper Functions
# =====================================================

def get_user_display_name(user: User) -> str:
    """Get user's display name from available fields"""
    if hasattr(user, 'full_name') and user.full_name:
        return user.full_name
    elif hasattr(user, 'name') and user.name:
        return user.name
    elif hasattr(user, 'first_name') and hasattr(user, 'last_name'):
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        elif user.first_name:
            return user.first_name
    return user.email.split('@')[0] if user.email else "Unknown User"

# =====================================================
# API Endpoints
# =====================================================

@router.get("/master", response_model=Optional[MasterWorkflowResponse])
async def get_master_workflow(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the company's master workflow"""
    service = WorkflowService(db)
    workflow = service.get_master_workflow(current_user.company_id)
    
    if not workflow:
        return None
    
    # Check if workflow is a dict (from service) or a model object
    if isinstance(workflow, dict):
        # Handle dict response - enrich with user details
        if 'steps' in workflow and isinstance(workflow['steps'], list):
            for step in workflow['steps']:
                if step.get('assignee_user_id'):
                    user = db.query(User).filter(
                        User.id == step['assignee_user_id']
                    ).first()
                    if user:
                        step['user_name'] = get_user_display_name(user)
                        step['user_email'] = user.email
                        step['department'] = step.get('department') or getattr(user, 'department', None)
        return workflow
    else:
        # Handle model object response
        for step in workflow.steps:
            if step.assignee_user_id:
                user = db.query(User).filter(
                    User.id == step.assignee_user_id
                ).first()
                if user:
                    step.user_name = get_user_display_name(user)
                    step.user_email = user.email
                    step.department = step.department or getattr(user, 'department', None)
        return workflow

@router.post("/master", response_model=MasterWorkflowResponse)
async def create_master_workflow(
    workflow_data: MasterWorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create or update master workflow"""
    service = WorkflowService(db)
    
    # Validate that users exist and get their departments
    for step in workflow_data.steps:
        if step.users:
            for user_selection in step.users:
                user = db.query(User).filter(
                    User.id == user_selection.id,
                    User.company_id == current_user.company_id
                ).first()
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"User with ID {user_selection.id} not found"
                    )
                # Update department from actual user data if not provided
                if not step.department and hasattr(user, 'department'):
                    step.department = user.department
    
    workflow = service.create_or_update_master_workflow(
        company_id=current_user.company_id,
        workflow_data=workflow_data
    )
    
    # Handle both dict and model responses
    if isinstance(workflow, dict):
        if 'steps' in workflow and isinstance(workflow['steps'], list):
            for step in workflow['steps']:
                if step.get('assignee_user_id'):
                    user = db.query(User).filter(
                        User.id == step['assignee_user_id']
                    ).first()
                    if user:
                        step['user_name'] = get_user_display_name(user)
                        step['user_email'] = user.email
                        step['department'] = step.get('department') or getattr(user, 'department', None)
    else:
        for step in workflow.steps:
            if step.assignee_user_id:
                user = db.query(User).filter(
                    User.id == step.assignee_user_id
                ).first()
                if user:
                    step.user_name = get_user_display_name(user)
                    step.user_email = user.email
                    step.department = step.department or getattr(user, 'department', None)
    
    return workflow

@router.delete("/master")
async def delete_master_workflow(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete master workflow"""
    service = WorkflowService(db)
    success = service.delete_master_workflow(current_user.company_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master workflow not found"
        )
    
    return {"success": True, "message": "Master workflow deleted successfully"}

@router.get("/roles")
async def get_workflow_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available workflow roles"""
    service = WorkflowService(db)
    roles = service.get_available_roles()
    return {"roles": roles}

@router.get("/departments")
async def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get company departments"""
    service = WorkflowService(db)
    departments = service.get_company_departments(current_user.company_id)
    return {"departments": departments}

@router.get("/users/search")
async def search_users(
    query: str,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search users by name or email, optionally filter by department"""
    service = WorkflowService(db)
    users = service.search_users(
        company_id=current_user.company_id,
        query=query,
        department=department
    )
    return {"users": users}

@router.get("/users/by-department/{department}")
async def get_users_by_department(
    department: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users in a specific department"""
    users = db.query(User).filter(
        User.company_id == current_user.company_id,
        User.department == department,
        User.is_active == True
    ).all()
    
    return {
        "users": [
            {
                "id": user.id,
                "name": get_user_display_name(user),
                "email": user.email,
                "department": getattr(user, 'department', None)
            }
            for user in users
        ]
    }