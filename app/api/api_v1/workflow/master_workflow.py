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
from sqlalchemy import text

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
                department=step_data.department or "General",
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


@router.get("/master-workflows/{workflow_id}")
async def get_master_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        user_id = current_user.id
        company_id = current_user.company_id
        
        # Fetch workflow details
        workflow_query = text("""
            SELECT id, workflow_name, company_id
            FROM master_workflows
            WHERE id = :workflow_id 
            AND company_id = :company_id
        """)
        workflow = db.execute(workflow_query, {
            "workflow_id": workflow_id,
            "company_id": company_id
        }).fetchone()
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Fetch workflow steps with user details
        steps_query = text("""
            SELECT 
                mws.id,
                mws.step_order,
                mws.step_type,
                mws.user_id,
                u.full_name as user_name,
                r.role_name
            FROM master_workflow_steps mws
            LEFT JOIN users u ON mws.user_id = u.id
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE mws.master_workflow_id = :workflow_id
            ORDER BY mws.step_order
        """)
        steps = db.execute(steps_query, {"workflow_id": workflow_id}).fetchall()
        
        return {
            "success": True,
            "workflow": {
                "id": workflow.id,
                "workflow_name": workflow.workflow_name
            },
            "steps": [
                {
                    "id": step.id,
                    "step_order": step.step_order,
                    "step_type": step.step_type,
                    "user_id": step.user_id,
                    "user_name": step.user_name,
                    "role_name": step.role_name
                }
                for step in steps
            ]
        }
        
    except HTTPException as he:
        raise
    except Exception as e:
        logger.error(f"Error fetching master workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/master-workflows/company/users")
async def get_company_workflow_users(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all users from the company's master workflow + Party B lead"""
    try:
        company_id = current_user.company_id
        
        # Get contract_id from query parameter
        from fastapi import Query
        
        # Get the master workflow for this company
        workflow_query = text("""
            SELECT id, workflow_name
            FROM workflows
            WHERE company_id = :company_id
            AND is_master = 1
            AND is_active = 1
            LIMIT 1
        """)
        workflow = db.execute(workflow_query, {"company_id": company_id}).fetchone()
        
        if not workflow:
            return {
                "success": False,
                "message": "No master workflow found for company",
                "users": []
            }
        
        # Get unique users from workflow steps
        users_query = text("""
            SELECT DISTINCT
                ws.assignee_user_id as user_id,
                CONCAT(u.first_name, ' ', u.last_name) as full_name,
                u.user_role as role_name
            FROM workflow_steps ws
            INNER JOIN users u ON ws.assignee_user_id = u.id
            WHERE ws.workflow_id = :workflow_id
            AND u.company_id = :company_id
            AND ws.assignee_user_id IS NOT NULL
            ORDER BY full_name
        """)
        users = db.execute(users_query, {
            "workflow_id": workflow.id,
            "company_id": company_id
        }).fetchall()
        
        users_list = [
            {
                "user_id": user.user_id,
                "full_name": user.full_name,
                "role_name": user.role_name
            }
            for user in users
        ]
        
        return {
            "success": True,
            "workflow_name": workflow.workflow_name,
            "users": users_list
        }
        
    except Exception as e:
        logger.error(f"Error fetching company workflow users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# NEW ENDPOINT - Get participants for specific contract negotiation
@router.get("/negotiation/internal-participants/{contract_id}")
async def get_internal_negotiation_participants(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all participants for internal negotiation: master workflow users + party B lead"""
    try:
        company_id = current_user.company_id
        
        # Get contract details including party_b_lead_id
        contract_query = text("""
            SELECT party_b_lead_id, company_id
            FROM contracts
            WHERE id = :contract_id
        """)
        contract = db.execute(contract_query, {"contract_id": contract_id}).fetchone()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Get the master workflow for this company
        workflow_query = text("""
            SELECT id, workflow_name
            FROM workflows
            WHERE company_id = :company_id
            AND is_master = 1
            AND is_active = 1
            LIMIT 1
        """)
        workflow = db.execute(workflow_query, {"company_id": company_id}).fetchone()
        
        if not workflow:
            return {
                "success": False,
                "message": "No master workflow found for company",
                "users": []
            }
        
        # Get unique users from workflow steps
        users_query = text("""
            SELECT DISTINCT
                ws.assignee_user_id as user_id,
                CONCAT(u.first_name, ' ', u.last_name) as full_name,
                u.user_role as role_name,
                'workflow' as source
            FROM workflow_steps ws
            INNER JOIN users u ON ws.assignee_user_id = u.id
            WHERE ws.workflow_id = :workflow_id
            AND u.company_id = :company_id
            AND ws.assignee_user_id IS NOT NULL
        """)
        workflow_users = db.execute(users_query, {
            "workflow_id": workflow.id,
            "company_id": company_id
        }).fetchall()
        
        users_list = []
        user_ids_added = set()
        
        # Add workflow users
        for user in workflow_users:
            if user.user_id not in user_ids_added:
                users_list.append({
                    "user_id": user.user_id,
                    "full_name": user.full_name,
                    "role_name": user.role_name
                })
                user_ids_added.add(user.user_id)
        
        # Add Party B lead if exists and not already in list
        if contract.party_b_lead_id and contract.party_b_lead_id not in user_ids_added:
            party_b_query = text("""
                SELECT 
                    id as user_id,
                    CONCAT(first_name, ' ', last_name) as full_name,
                    user_role as role_name
                FROM users
                WHERE id = :party_b_lead_id
            """)
            party_b_user = db.execute(party_b_query, {
                "party_b_lead_id": contract.party_b_lead_id
            }).fetchone()
            
            if party_b_user:
                users_list.append({
                    "user_id": party_b_user.user_id,
                    "full_name": party_b_user.full_name,
                    "role_name": party_b_user.role_name
                })
        
        # Sort by full_name
        users_list.sort(key=lambda x: x["full_name"])
        
        return {
            "success": True,
            "workflow_name": workflow.workflow_name,
            "users": users_list
        }
        
    except HTTPException as he:
        raise
    except Exception as e:
        logger.error(f"Error fetching internal negotiation participants: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))