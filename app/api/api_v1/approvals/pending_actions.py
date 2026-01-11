"""
Pending Actions API Router - SIMPLIFIED VERSION
File: app/api/api_v1/approvals/pending_actions.py

Simplified to avoid problematic table joins
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pending-actions", tags=["pending-actions"])

@router.get("")
async def get_pending_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all pending actions for the current user
    SIMPLIFIED: Avoids problematic table structures
    """
    try:
        user_id = current_user.id
        company_id = current_user.company_id
        
        pending_actions = []
        
        # 1. Get Pending Approvals from workflow_stages
        approval_query = text("""
            SELECT DISTINCT
                ws.id as action_id,
                c.id as contract_id,
                c.contract_number,
                c.contract_title,
                c.status as contract_status,
                wi.id as workflow_instance_id,
                ws.stage_name,
                ws.deadline_hours,
                ws.started_at,
                wi.started_at as workflow_started_at,
                c.created_at as contract_created_at,
                'approval' as action_type,
                CONCAT('Approval required for: ', COALESCE(ws.stage_name, 'Review')) as description,
                CASE 
                    WHEN ws.deadline_hours IS NOT NULL 
                    AND DATE_ADD(COALESCE(ws.started_at, wi.started_at, c.created_at), INTERVAL ws.deadline_hours HOUR) < NOW() 
                    THEN 1
                    ELSE 0
                END as is_urgent
            FROM workflow_stages ws
            JOIN workflow_instances wi ON ws.workflow_instance_id = wi.id
            JOIN contracts c ON wi.contract_id = c.id
            WHERE ws.approver_user_id = :user_id
            AND ws.status = 'pending'
            AND c.is_deleted = 0
            AND (c.company_id = :company_id OR c.party_b_id = :company_id)
            ORDER BY COALESCE(ws.started_at, wi.started_at, c.created_at) DESC
            LIMIT 50
        """)
        
        approval_results = db.execute(approval_query, {
            "user_id": user_id,
            "company_id": company_id
        }).fetchall()
        
        for row in approval_results:
            # Calculate created_at (use first available)
            created_at = row.started_at or row.workflow_started_at or row.contract_created_at
            
            # Calculate due date based on deadline_hours
            due_date = None
            if row.deadline_hours:
                base_date = row.started_at or row.workflow_started_at or row.contract_created_at
                if base_date:
                    due_date = base_date + timedelta(hours=row.deadline_hours)
            
            pending_actions.append({
                "id": str(row.action_id),
                "contract_id": row.contract_id,
                "contract_number": row.contract_number,
                "contract_title": row.contract_title,
                "action_type": "approval",
                "description": row.description,
                "created_at": created_at.isoformat() if created_at else None,
                "due_date": due_date.isoformat() if due_date else None,
                "is_urgent": bool(row.is_urgent),
                "status": "pending"
            })
        
        # 2. Get Pending Approvals from approval_requests table (if exists)
        try:
            approval_requests_query = text("""
                SELECT DISTINCT
                    ar.id as action_id,
                    c.id as contract_id,
                    c.contract_number,
                    c.contract_title,
                    c.status as contract_status,
                    ar.due_date,
                    ar.created_at,
                    'approval' as action_type,
                    CONCAT('Contract approval required - ', c.contract_title) as description,
                    CASE 
                        WHEN ar.due_date IS NOT NULL 
                        AND ar.due_date < NOW() THEN 1
                        ELSE 0
                    END as is_urgent
                FROM approval_requests ar
                JOIN contracts c ON ar.contract_id = c.id
                WHERE ar.approver_id = :user_id
                AND ar.responded_at IS NULL
                AND c.is_deleted = 0
                AND (c.company_id = :company_id OR c.party_b_id = :company_id)
                ORDER BY ar.created_at DESC
                LIMIT 50
            """)
            
            approval_req_results = db.execute(approval_requests_query, {
                "user_id": user_id,
                "company_id": company_id
            }).fetchall()
            
            for row in approval_req_results:
                # Avoid duplicates
                if not any(a['contract_id'] == row.contract_id for a in pending_actions):
                    pending_actions.append({
                        "id": str(row.action_id),
                        "contract_id": row.contract_id,
                        "contract_number": row.contract_number,
                        "contract_title": row.contract_title,
                        "action_type": "approval",
                        "description": row.description,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "due_date": row.due_date.isoformat() if row.due_date else None,
                        "is_urgent": bool(row.is_urgent),
                        "status": "pending"
                    })
        except Exception as e:
            logger.warning(f"Could not query approval_requests table: {e}")
        
        # 3. Get Pending Reviews - SIMPLIFIED (just company contracts in review)
        review_query = text("""
            SELECT DISTINCT
                c.id as contract_id,
                c.contract_number,
                c.contract_title,
                c.status as contract_status,
                c.created_at,
                c.updated_at,
                'review' as action_type,
                CONCAT('Contract review required - ', c.contract_title) as description
            FROM contracts c
            WHERE c.status IN ('review', 'pending_review', 'internal_review', 'counterparty_internal_review')
            AND c.is_deleted = 0
            AND (c.company_id = :company_id OR c.party_b_id = :company_id)
            AND c.created_by = :user_id
            ORDER BY c.updated_at DESC
            LIMIT 20
        """)
        
        review_results = db.execute(review_query, {
            "user_id": user_id,
            "company_id": company_id
        }).fetchall()
        
        for row in review_results:
            # Avoid duplicates
            if not any(a['contract_id'] == row.contract_id for a in pending_actions):
                pending_actions.append({
                    "id": f"review_{row.contract_id}",
                    "contract_id": row.contract_id,
                    "contract_number": row.contract_number,
                    "contract_title": row.contract_title,
                    "action_type": "review",
                    "description": row.description,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "due_date": None,
                    "is_urgent": False,
                    "status": "pending"
                })
        
        # 4. Get Pending Signatures
        try:
            signature_query = text("""
                SELECT DISTINCT
                    s.id as signature_id,
                    c.id as contract_id,
                    c.contract_number,
                    c.contract_title,
                    c.status as contract_status,
                    s.created_at,
                    'signature' as action_type,
                    CONCAT('Signature required for contract - ', c.contract_title) as description
                FROM signatories s
                JOIN contracts c ON s.contract_id = c.id
                WHERE s.user_id = :user_id
                AND s.has_signed = 0
                AND s.signature_status = 'pending'
                AND c.is_deleted = 0
                AND (c.company_id = :company_id OR c.party_b_id = :company_id)
                ORDER BY s.created_at DESC
                LIMIT 20
            """)
            
            signature_results = db.execute(signature_query, {
                "user_id": user_id,
                "company_id": company_id
            }).fetchall()
            
            for row in signature_results:
                # Avoid duplicates
                if not any(a['contract_id'] == row.contract_id for a in pending_actions):
                    pending_actions.append({
                        "id": f"signature_{row.signature_id}",
                        "contract_id": row.contract_id,
                        "contract_number": row.contract_number,
                        "contract_title": row.contract_title,
                        "action_type": "signature",
                        "description": row.description,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "due_date": None,
                        "is_urgent": False,
                        "status": "pending"
                    })
        except Exception as e:
            logger.warning(f"Could not query signatories table: {e}")
        
        logger.info(f"✅ Found {len(pending_actions)} pending actions for user {user_id}")
        
        return {
            "success": True,
            "data": pending_actions,
            "total": len(pending_actions)
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching pending actions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending actions: {str(e)}"
        )


@router.get("/count")
async def get_pending_actions_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get count of pending actions for dashboard badge
    """
    try:
        user_id = current_user.id
        company_id = current_user.company_id
        
        # Count from workflow_stages
        workflow_count = db.execute(text("""
            SELECT COUNT(DISTINCT c.id) as count
            FROM workflow_stages ws
            JOIN workflow_instances wi ON ws.workflow_instance_id = wi.id
            JOIN contracts c ON wi.contract_id = c.id
            WHERE ws.approver_user_id = :user_id
            AND ws.status = 'pending'
            AND c.is_deleted = 0
            AND (c.company_id = :company_id OR c.party_b_id = :company_id)
        """), {"user_id": user_id, "company_id": company_id}).scalar() or 0
        
        # Count from approval_requests (if table exists)
        approval_count = 0
        try:
            approval_count = db.execute(text("""
                SELECT COUNT(DISTINCT c.id) as count
                FROM approval_requests ar
                JOIN contracts c ON ar.contract_id = c.id
                WHERE ar.approver_id = :user_id
                AND ar.responded_at IS NULL
                AND c.is_deleted = 0
                AND (c.company_id = :company_id OR c.party_b_id = :company_id)
            """), {"user_id": user_id, "company_id": company_id}).scalar() or 0
        except:
            pass
        
        # Count pending signatures
        signature_count = 0
        try:
            signature_count = db.execute(text("""
                SELECT COUNT(*) as count
                FROM signatories s
                JOIN contracts c ON s.contract_id = c.id
                WHERE s.user_id = :user_id
                AND s.has_signed = 0
                AND c.is_deleted = 0
                AND (c.company_id = :company_id OR c.party_b_id = :company_id)
            """), {"user_id": user_id, "company_id": company_id}).scalar() or 0
        except:
            pass
        
        total_count = workflow_count + approval_count + signature_count
        
        return {
            "success": True,
            "total": total_count,
            "breakdown": {
                "approvals": workflow_count + approval_count,
                "signatures": signature_count
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching pending actions count: {str(e)}")
        return {
            "success": False,
            "total": 0,
            "error": str(e)
        }