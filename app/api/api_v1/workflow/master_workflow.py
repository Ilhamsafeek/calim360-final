"""
Workflow API Router - Master Workflow Management
File: app/api/api_v1/workflow/workflow.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.workflow import Workflow, WorkflowStep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# =====================================================
# Pydantic Schemas
# =====================================================

class WorkflowUser(BaseModel):
    name: str
    email: str

class WorkflowStepData(BaseModel):
    step_order: int
    role: str
    users: List[WorkflowUser]
    department: str

class WorkflowSettings(BaseModel):
    auto_escalation_hours: int = 48
    contract_threshold: float = 50000
    parallel_approval: bool = True
    skip_empty_steps: bool = False
    require_comments: bool = True
    qatar_compliance: bool = True

class MasterWorkflowCreate(BaseModel):
    name: str
    steps: List[WorkflowStepData]
    settings: WorkflowSettings
    excluded_contract_types: List[str] = []

# =====================================================
# Create/Update Master Workflow
# =====================================================

@router.post("/master")
async def create_master_workflow(
    workflow_data: MasterWorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update master workflow for the company
    """
    try:
        logger.info(f"Received workflow data: {workflow_data.dict()}")
        
        # Check if master workflow already exists
        existing_workflow = db.query(Workflow).filter(
            Workflow.company_id == current_user.company_id,
            Workflow.is_master == True
        ).first()

        workflow_json_data = {
            "settings": workflow_data.settings.dict(),
            "excluded_types": workflow_data.excluded_contract_types,
            "steps": [step.dict() for step in workflow_data.steps]
        }

        if existing_workflow:
            # Update existing
            existing_workflow.workflow_name = workflow_data.name
            existing_workflow.workflow_json = workflow_json_data
            existing_workflow.updated_at = datetime.utcnow()
            
            # Delete old steps
            db.query(WorkflowStep).filter(
                WorkflowStep.workflow_id == existing_workflow.id
            ).delete()
            
            workflow = existing_workflow
            logger.info(f" Updated master workflow for company {current_user.company_id}")
        else:
            # Create new
            workflow = Workflow(
                company_id=current_user.company_id,
                workflow_name=workflow_data.name,
                workflow_type="master",
                is_master=True,
                is_active=True,
                workflow_json=workflow_json_data
            )
            db.add(workflow)
            db.flush()
            logger.info(f" Created new master workflow for company {current_user.company_id}")

        # Create workflow steps
        for step_data in workflow_data.steps:
            # Convert users list to JSON string for storage
            users_json = [{"name": u.name, "email": u.email} for u in step_data.users]
            
            workflow_step = WorkflowStep(
                workflow_id=workflow.id,
                step_number=step_data.step_order,
                step_name=step_data.role,
                step_type=step_data.role.lower().replace(" ", "_"),
                assignee_role=step_data.department,
                sla_hours=workflow_data.settings.auto_escalation_hours
            )
            db.add(workflow_step)

        db.commit()
        db.refresh(workflow)

        logger.info(f" Workflow saved successfully with {len(workflow_data.steps)} steps")

        return {
            "success": True,
            "message": "Master workflow saved successfully",
            "workflow_id": workflow.id
        }

    except Exception as e:
        db.rollback()
        logger.error(f" Error saving master workflow: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# =====================================================
# Get Master Workflow
# =====================================================

@router.get("/master")
async def get_master_workflow(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get master workflow for the current company
    """
    try:
        workflow = db.query(Workflow).filter(
            Workflow.company_id == current_user.company_id,
            Workflow.is_master == True
        ).first()

        if not workflow:
            return {
                "success": True,
                "message": "No master workflow found",
                "workflow": None
            }

        # Get workflow steps
        steps = db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow.id
        ).order_by(WorkflowStep.step_number).all()

        return {
            "success": True,
            "workflow": {
                "id": workflow.id,
                "name": workflow.workflow_name,
                "settings": workflow.workflow_json.get("settings", {}),
                "excluded_types": workflow.workflow_json.get("excluded_types", []),
                "steps": [
                    {
                        "step_number": step.step_number,
                        "step_name": step.step_name,
                        "role": step.assignee_role,
                        "sla_hours": step.sla_hours
                    }
                    for step in steps
                ]
            }
        }

    except Exception as e:
        logger.error(f" Error retrieving master workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )