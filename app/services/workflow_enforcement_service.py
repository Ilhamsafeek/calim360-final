# =====================================================
# FILE: app/services/workflow_enforcement_service.py
# Workflow Enforcement and Auto-Assignment
# =====================================================

from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class WorkflowEnforcementService:
    """
    Service to enforce workflow rules and auto-assign workflows
    """
    
    # Valid status transitions
    STATUS_TRANSITIONS = {
        "Draft": ["InReview", "Cancelled"],
        "InReview": ["Draft", "PendingApproval", "Cancelled"],
        "PendingApproval": ["InReview", "Approved", "Rejected"],
        "Approved": ["PendingSignature", "InReview"],
        "PendingSignature": ["Executed", "Approved"],
        "Executed": ["Expired", "Renewed"],
        "Rejected": ["Draft", "Cancelled"],
        "Expired": ["Renewed"],
        "Renewed": ["Draft"],
        "Cancelled": []
    }
    
    @staticmethod
    def validate_status_transition(
        current_status: str, 
        new_status: str
    ) -> bool:
        """Check if status transition is valid"""
        allowed = WorkflowEnforcementService.STATUS_TRANSITIONS.get(
            current_status, []
        )
        return new_status in allowed
    
    @staticmethod
    def get_master_workflow(db: Session, company_id: int) -> Optional[Dict]:
        """Get company's master workflow"""
        query = text("""
            SELECT w.*, ws.id as step_id, ws.step_order, 
                   ws.step_type, ws.assignee_role, ws.assignee_user_id,
                   ws.sla_hours, ws.is_mandatory
            FROM workflows w
            LEFT JOIN workflow_steps ws ON w.id = ws.workflow_id
            WHERE w.company_id = :company_id 
            AND w.is_master = 1
            AND w.is_active = 1
            ORDER BY ws.step_order
        """)
        
        result = db.execute(query, {"company_id": company_id})
        rows = result.fetchall()
        
        if not rows:
            return None
        
        workflow = {
            "id": rows[0].id,
            "name": rows[0].workflow_name,
            "steps": []
        }
        
        for row in rows:
            if row.step_id:
                workflow["steps"].append({
                    "id": row.step_id,
                    "order": row.step_order,
                    "type": row.step_type,
                    "role": row.assignee_role,
                    "user_id": row.assignee_user_id,
                    "sla_hours": row.sla_hours,
                    "is_mandatory": row.is_mandatory
                })
        
        return workflow
    
    @staticmethod
    def assign_workflow_to_contract(
        db: Session,
        contract_id: int,
        company_id: int,
        use_master: bool = True,
        custom_workflow_id: Optional[int] = None
    ) -> Dict:
        """
        Assign workflow to contract
        """
        try:
            # Get workflow to use
            if use_master:
                workflow = WorkflowEnforcementService.get_master_workflow(
                    db, company_id
                )
                if not workflow:
                    return {"success": False, "error": "No master workflow found"}
                workflow_id = workflow["id"]
            else:
                workflow_id = custom_workflow_id
            
            # Create workflow instance
            instance_query = text("""
                INSERT INTO workflow_instances 
                (workflow_id, contract_id, status, current_step, 
                 started_at, created_at)
                VALUES 
                (:workflow_id, :contract_id, 'active', 1, NOW(), NOW())
            """)
            
            db.execute(instance_query, {
                "workflow_id": workflow_id,
                "contract_id": contract_id
            })
            
            instance_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
            
            # Create workflow stages from steps
            steps_query = text("""
                SELECT * FROM workflow_steps 
                WHERE workflow_id = :workflow_id
                ORDER BY step_order
            """)
            steps = db.execute(steps_query, {"workflow_id": workflow_id}).fetchall()
            
            for step in steps:
                stage_query = text("""
                    INSERT INTO workflow_stages 
                    (workflow_instance_id, stage_order, stage_name, 
                     approver_role_id, approver_user_id, status,
                     sla_hours, sla_deadline, created_at)
                    VALUES 
                    (:instance_id, :order, :name, :role_id, :user_id, 
                     :status, :sla_hours, :deadline, NOW())
                """)
                
                # Calculate SLA deadline
                sla_deadline = None
                if step.sla_hours:
                    sla_deadline = datetime.utcnow() + timedelta(hours=step.sla_hours)
                
                db.execute(stage_query, {
                    "instance_id": instance_id,
                    "order": step.step_order,
                    "name": step.step_type,
                    "role_id": None,  # Will be resolved
                    "user_id": step.assignee_user_id,
                    "status": "pending" if step.step_order == 1 else "waiting",
                    "sla_hours": step.sla_hours,
                    "deadline": sla_deadline
                })
            
            # Update contract with workflow info
            db.execute(text("""
                UPDATE contracts 
                SET workflow_id = :workflow_id,
                    workflow_status = 'active',
                    current_workflow_step = 1,
                    updated_at = NOW()
                WHERE id = :contract_id
            """), {
                "workflow_id": workflow_id,
                "contract_id": contract_id
            })
            
            db.commit()
            
            logger.info(f"Workflow {workflow_id} assigned to contract {contract_id}")
            
            return {
                "success": True,
                "workflow_instance_id": instance_id,
                "message": "Workflow assigned successfully"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error assigning workflow: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def advance_workflow(
        db: Session,
        contract_id: int,
        user_id: int,
        action: str,
        comments: Optional[str] = None
    ) -> Dict:
        """
        Advance workflow to next stage
        action: 'approve', 'reject', 'skip'
        """
        try:
            # Get current workflow state
            query = text("""
                SELECT wi.id as instance_id, wi.current_step,
                       ws.id as stage_id, ws.stage_order, ws.status as stage_status,
                       c.status as contract_status
                FROM workflow_instances wi
                JOIN workflow_stages ws ON wi.id = ws.workflow_instance_id
                JOIN contracts c ON wi.contract_id = c.id
                WHERE wi.contract_id = :contract_id
                AND wi.status = 'active'
                AND ws.status = 'pending'
                ORDER BY ws.stage_order
                LIMIT 1
            """)
            
            current = db.execute(query, {"contract_id": contract_id}).first()
            
            if not current:
                return {"success": False, "error": "No active workflow stage"}
            
            # Update current stage
            if action == "approve":
                new_stage_status = "approved"
            elif action == "reject":
                new_stage_status = "rejected"
            else:
                new_stage_status = "skipped"
            
            db.execute(text("""
                UPDATE workflow_stages 
                SET status = :status,
                    approved_by = :user_id,
                    approved_at = NOW(),
                    comments = :comments
                WHERE id = :stage_id
            """), {
                "status": new_stage_status,
                "user_id": user_id,
                "comments": comments,
                "stage_id": current.stage_id
            })
            
            # Create approval request record
            db.execute(text("""
                INSERT INTO approval_requests 
                (workflow_stage_id, contract_id, approver_id, 
                 action, comments, created_at)
                VALUES 
                (:stage_id, :contract_id, :user_id, 
                 :action, :comments, NOW())
            """), {
                "stage_id": current.stage_id,
                "contract_id": contract_id,
                "user_id": user_id,
                "action": action,
                "comments": comments
            })
            
            if action == "reject":
                # Workflow rejected - update contract
                db.execute(text("""
                    UPDATE contracts 
                    SET status = 'Rejected',
                        workflow_status = 'rejected',
                        updated_at = NOW()
                    WHERE id = :contract_id
                """), {"contract_id": contract_id})
                
                db.execute(text("""
                    UPDATE workflow_instances 
                    SET status = 'rejected', completed_at = NOW()
                    WHERE id = :instance_id
                """), {"instance_id": current.instance_id})
                
            else:
                # Check if there are more stages
                next_stage = db.execute(text("""
                    SELECT id, stage_order FROM workflow_stages
                    WHERE workflow_instance_id = :instance_id
                    AND stage_order > :current_order
                    AND status = 'waiting'
                    ORDER BY stage_order
                    LIMIT 1
                """), {
                    "instance_id": current.instance_id,
                    "current_order": current.stage_order
                }).first()
                
                if next_stage:
                    # Activate next stage
                    db.execute(text("""
                        UPDATE workflow_stages 
                        SET status = 'pending',
                            sla_deadline = DATE_ADD(NOW(), INTERVAL sla_hours HOUR)
                        WHERE id = :stage_id
                    """), {"stage_id": next_stage.id})
                    
                    db.execute(text("""
                        UPDATE workflow_instances 
                        SET current_step = :step
                        WHERE id = :instance_id
                    """), {
                        "step": next_stage.stage_order,
                        "instance_id": current.instance_id
                    })
                    
                    # Update contract step
                    db.execute(text("""
                        UPDATE contracts 
                        SET current_workflow_step = :step,
                            status = 'PendingApproval',
                            updated_at = NOW()
                        WHERE id = :contract_id
                    """), {
                        "step": next_stage.stage_order,
                        "contract_id": contract_id
                    })
                    
                    # Send notification to next approver
                    WorkflowEnforcementService._notify_next_approver(
                        db, next_stage.id, contract_id
                    )
                    
                else:
                    # Workflow complete
                    db.execute(text("""
                        UPDATE workflow_instances 
                        SET status = 'completed', completed_at = NOW()
                        WHERE id = :instance_id
                    """), {"instance_id": current.instance_id})
                    
                    db.execute(text("""
                        UPDATE contracts 
                        SET status = 'Approved',
                            workflow_status = 'completed',
                            updated_at = NOW()
                        WHERE id = :contract_id
                    """), {"contract_id": contract_id})
            
            db.commit()
            
            return {
                "success": True,
                "action": action,
                "message": f"Workflow {action}d successfully"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error advancing workflow: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _notify_next_approver(db: Session, stage_id: int, contract_id: int):
        """Send notification to next approver"""
        try:
            # Get stage and assignee info
            stage = db.execute(text("""
                SELECT ws.*, u.email, u.first_name,
                       c.contract_title, c.contract_number
                FROM workflow_stages ws
                LEFT JOIN users u ON ws.approver_user_id = u.id
                JOIN workflow_instances wi ON ws.workflow_instance_id = wi.id
                JOIN contracts c ON wi.contract_id = c.id
                WHERE ws.id = :stage_id
            """), {"stage_id": stage_id}).first()
            
            if stage and stage.approver_user_id:
                # Create notification
                db.execute(text("""
                    INSERT INTO notifications 
                    (user_id, title, message, type, entity_type, 
                     entity_id, is_read, created_at)
                    VALUES 
                    (:user_id, :title, :message, 'workflow', 
                     'contract', :contract_id, 0, NOW())
                """), {
                    "user_id": stage.approver_user_id,
                    "title": "Contract Requires Your Approval",
                    "message": f"Contract {stage.contract_number} - {stage.contract_title} is waiting for your approval.",
                    "contract_id": contract_id
                })
                
                logger.info(f"Notification sent to user {stage.approver_user_id}")
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    @staticmethod
    def check_sla_breaches(db: Session) -> List[Dict]:
        """
        Check for SLA breaches and escalate
        This should run as a scheduled job
        """
        breaches = []
        
        try:
            query = text("""
                SELECT ws.id, ws.stage_name, ws.sla_deadline,
                       ws.approver_user_id, wi.contract_id,
                       c.contract_number, c.contract_title,
                       u.email as approver_email
                FROM workflow_stages ws
                JOIN workflow_instances wi ON ws.workflow_instance_id = wi.id
                JOIN contracts c ON wi.contract_id = c.id
                LEFT JOIN users u ON ws.approver_user_id = u.id
                WHERE ws.status = 'pending'
                AND ws.sla_deadline < NOW()
                AND ws.escalated = 0 OR ws.escalated IS NULL
            """)
            
            results = db.execute(query).fetchall()
            
            for row in results:
                # Mark as escalated
                db.execute(text("""
                    UPDATE workflow_stages 
                    SET escalated = 1, escalated_at = NOW()
                    WHERE id = :stage_id
                """), {"stage_id": row.id})
                
                # Create escalation notification
                # (In production, also send email)
                db.execute(text("""
                    INSERT INTO notifications 
                    (user_id, title, message, type, priority, 
                     entity_type, entity_id, is_read, created_at)
                    VALUES 
                    (:user_id, :title, :message, 'escalation', 'high',
                     'contract', :contract_id, 0, NOW())
                """), {
                    "user_id": row.approver_user_id,
                    "title": " SLA BREACH - Approval Required",
                    "message": f"Contract {row.contract_number} has exceeded SLA deadline. Immediate action required.",
                    "contract_id": row.contract_id
                })
                
                breaches.append({
                    "contract_id": row.contract_id,
                    "contract_number": row.contract_number,
                    "stage": row.stage_name,
                    "deadline": row.sla_deadline
                })
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error checking SLA breaches: {e}")
        
        return breaches