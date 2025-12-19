# =====================================================
# FILE: app/api/api_v1/obligations/obligations.py
# COMPLETE OBLIGATION MANAGEMENT API
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, desc
from typing import List, Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.contract import Contract
from app.models.obligation import Obligation, ObligationTracking
from app.core.dependencies import get_current_user
from app.services.claude_service import ClaudeService

router = APIRouter()
logger = logging.getLogger(__name__)
claude_service = ClaudeService()

# =====================================================
# SCHEMAS
# =====================================================

from pydantic import BaseModel

class ObligationCreate(BaseModel):
    contract_id: int
    obligation_title: str
    description: Optional[str] = None
    obligation_type: Optional[str] = None
    owner_user_id: Optional[int] = None
    escalation_user_id: Optional[int] = None
    threshold_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: str = 'initiated'
    is_ai_generated: bool = False

class ObligationUpdate(BaseModel):
    obligation_title: Optional[str] = None
    description: Optional[str] = None
    obligation_type: Optional[str] = None
    owner_user_id: Optional[int] = None
    escalation_user_id: Optional[int] = None
    threshold_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None

class AIObligationGenerate(BaseModel):
    contract_id: int

# =====================================================
# 1. GET ALL OBLIGATIONS FOR A CONTRACT
# =====================================================
@router.get("/contract/{contract_id}")
async def get_contract_obligations(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all obligations for a specific contract"""
    try:
        # Verify contract access
        contract = db.query(Contract).filter(
            Contract.id == contract_id,
            Contract.company_id == current_user.company_id
        ).first()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Get obligations
        obligations = db.query(Obligation).filter(
            Obligation.contract_id == contract_id
        ).order_by(desc(Obligation.created_at)).all()
        
        # ✅ CRITICAL: Enrich with user data
        enriched = []
        for obl in obligations:
            # ✅ Get owner information
            owner = db.query(User).filter(User.id == obl.owner_user_id).first() if obl.owner_user_id else None
            
            # ✅ Get escalation information
            escalation = db.query(User).filter(User.id == obl.escalation_user_id).first() if obl.escalation_user_id else None
            
            enriched.append({
                "id": obl.id,
                "contract_id": obl.contract_id,
                "obligation_title": obl.obligation_title,
                "description": obl.description,
                "obligation_type": obl.obligation_type,
                "priority": getattr(obl, "priority", "medium"),
                "owner_user_id": obl.owner_user_id,
                "owner_name": f"{owner.first_name} {owner.last_name}" if owner else None,
                "owner_email": owner.email if owner else None,
                "escalation_user_id": obl.escalation_user_id,
                "escalation_name": f"{escalation.first_name} {escalation.last_name}" if escalation else None,
                "escalation_email": escalation.email if escalation else None,
                "threshold_date": obl.threshold_date.isoformat() if obl.threshold_date else None,
                "due_date": obl.due_date.isoformat() if obl.due_date else None,
                "status": obl.status,
                "is_ai_generated": obl.is_ai_generated,
                "created_at": obl.created_at.isoformat() if obl.created_at else None,
                "updated_at": obl.updated_at.isoformat() if obl.updated_at else None
            })
        
        return enriched
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching obligations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 2. GENERATE OBLIGATIONS USING AI
# =====================================================
@router.post("/generate-ai/{contract_id}")
async def generate_obligations_ai(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Use AI to extract obligations from contract content"""
    try:
        logger.info(f"🤖 Generating AI obligations for contract {contract_id}")
        
        # Get contract
        contract = db.query(Contract).filter(
            Contract.id == contract_id,
            Contract.company_id == current_user.company_id
        ).first()
        
        if not contract:
            logger.error(f"❌ Contract {contract_id} not found")
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Get latest contract version content
        from app.models.contract import ContractVersion
        latest_version = db.query(ContractVersion).filter(
            ContractVersion.contract_id == contract_id
        ).order_by(desc(ContractVersion.version_number)).first()
        
        if not latest_version or not latest_version.contract_content:
            logger.error(f"❌ No contract content found for contract {contract_id}")
            raise HTTPException(
                status_code=400, 
                detail="No contract content found. Please ensure the contract has content."
            )
        
        logger.info(f"📄 Contract content length: {len(latest_version.contract_content)} characters")
        
        # Extract obligations using Claude AI
        prompt = f"""Analyze this {contract.contract_type} contract and extract ALL contractual obligations.

For each obligation, provide:
1. **title**: Clear obligation title (max 50 words)
2. **description**: Detailed description including specific requirements (max 150 words)  
3. **type**: One of [payment, deliverable, compliance, reporting, insurance, performance, coordination, indemnification, timely_completion]
4. **party**: Who has this obligation - 'contractor' or 'client'
5. **priority**: high, medium, or low based on criticality

Contract Details:
- Type: {contract.contract_type}
- Parties: {contract.party_a_name} and {contract.party_b_name}

Contract Content:
{latest_version.contract_content[:8000]}

CRITICAL: Return ONLY a valid JSON array with NO markdown formatting, NO code blocks, NO explanations.
Just the raw JSON array starting with [ and ending with ].

Example format:
[
  {{
    "title": "Payment Obligation",
    "description": "Timely payment for work completed as per agreed terms within 30 days of invoice submission with proper documentation",
    "type": "payment",
    "party": "client",
    "priority": "high"
  }},
  {{
    "title": "Quality Standards Compliance",
    "description": "Ensure all deliverables meet specified quality standards and industry requirements with proper testing and validation",
    "type": "performance", 
    "party": "contractor",
    "priority": "high"
  }}
]"""
        
        # Call Claude API
        logger.info("📡 Calling Claude API for obligation extraction...")
        response = await claude_service.generate_text(prompt, max_tokens=3000)
        logger.info(f"✅ Received response: {len(response)} characters")
        
        # Parse response
        import json
        import re
        
        # Clean response - remove markdown if present
        cleaned_response = response.strip()
        if cleaned_response.startswith("```"):
            # Remove markdown code blocks
            cleaned_response = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned_response, flags=re.MULTILINE)
            cleaned_response = cleaned_response.strip()
        
        # Extract JSON array
        json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
        if not json_match:
            logger.error("❌ Could not find JSON array in response")
            logger.error(f"Response preview: {response[:500]}")
            raise ValueError("AI response did not contain valid JSON array")
        
        # Parse JSON
        obligations_data = json.loads(json_match.group(0))
        
        if not obligations_data or len(obligations_data) == 0:
            logger.warning("⚠️ No obligations extracted from contract")
            return {
                "success": True,
                "obligations": [],
                "count": 0,
                "message": "No obligations found in contract content"
            }
        
        logger.info(f"✅ Successfully extracted {len(obligations_data)} obligations")
        
        # Format response for frontend
        formatted_obligations = []
        for idx, obl in enumerate(obligations_data, 1):
            formatted_obligations.append({
                "obligation_title": obl.get("title", f"Obligation {idx}"),
                "description": obl.get("description", ""),
                "obligation_type": obl.get("type", "performance"),
                "party": obl.get("party", "both"),
                "priority": obl.get("priority", "medium"),
                "contract_id": contract_id,
                "is_ai_generated": True
            })
        
        return formatted_obligations
        
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing error: {str(e)}")
        logger.error(f"Response that failed to parse: {response[:1000]}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to parse AI response. Please try again."
        )
    except Exception as e:
        logger.error(f"❌ Error generating AI obligations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate obligations: {str(e)}"
        )


# =====================================================
# 3. CREATE OBLIGATION
# =====================================================
@router.post("/")
async def create_obligation(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new obligation with email validation
    """
    try:
        # ✅ VALIDATE: Owner and Escalation must be different
        owner_user_id = request.get("owner_user_id")
        escalation_user_id = request.get("escalation_user_id")
        
        if owner_user_id and escalation_user_id and owner_user_id == escalation_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner and escalation user must be different"
            )
        
        # Verify emails are different if both provided
        if owner_user_id and escalation_user_id:
            owner = db.query(User).filter(User.id == owner_user_id).first()
            escalation = db.query(User).filter(User.id == escalation_user_id).first()
            
            if owner and escalation and owner.email == escalation.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Owner and escalation emails must be different"
                )
        
        # Create obligation
        new_obligation = Obligation(
            contract_id=request.get("contract_id"),
            obligation_title=request.get("obligation_title"),
            description=request.get("description"),
            obligation_type=request.get("obligation_type", "other"),
            owner_user_id=owner_user_id,
            escalation_user_id=escalation_user_id,
            threshold_date=request.get("threshold_date"),
            due_date=request.get("due_date"),
            status=request.get("status", "initiated"),
            is_ai_generated=request.get("is_ai_generated", False),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_obligation)
        db.commit()
        db.refresh(new_obligation)
        
        logger.info(f"✅ Created obligation {new_obligation.id}")
        
        return {
            "success": True,
            "message": "Obligation created successfully",
            "id": new_obligation.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating obligation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create obligation: {str(e)}"
        )

@router.get("/")
async def get_all_obligations(
    contract_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all obligations with proper user information display
    """
    try:
        query = db.query(Obligation).join(
            Contract, Obligation.contract_id == Contract.id
        ).filter(
            Contract.company_id == current_user.company_id
        )
        
        if contract_id:
            query = query.filter(Obligation.contract_id == contract_id)
        
        if status_filter:
            query = query.filter(Obligation.status == status_filter)
        
        obligations = query.order_by(Obligation.created_at.desc()).all()
        
        # Enrich with user and contract information
        enriched_obligations = []
        for obligation in obligations:
            # Get contract info
            contract = db.query(Contract).filter(Contract.id == obligation.contract_id).first()
            
            # Get owner info
            owner = db.query(User).filter(User.id == obligation.owner_user_id).first() if obligation.owner_user_id else None
            
            # Get escalation info
            escalation_user = db.query(User).filter(User.id == obligation.escalation_user_id).first() if obligation.escalation_user_id else None
            
            enriched_data = {
                "id": obligation.id,
                "contract_id": obligation.contract_id,
                "contract_number": contract.contract_number if contract else None,
                "contract_title": contract.contract_title if contract else None,
                "obligation_title": obligation.obligation_title,
                "description": obligation.description,
                "obligation_type": obligation.obligation_type,
                "priority": getattr(obligation, "priority", "medium"),
                "owner_user_id": getattr(obligation, "owner_user_id", None),
                "owner_name": f"{owner.first_name} {owner.last_name}" if owner else "Unassigned",
                "owner_email": owner.email if owner else None,
                "escalation_user_id": getattr(obligation, "escalation_user_id", None),
                "escalation_name": f"{escalation_user.first_name} {escalation_user.last_name}" if escalation_user else "Unassigned",
                "escalation_email": escalation_user.email if escalation_user else None,
                "threshold_date": getattr(obligation, "threshold_date", None).isoformat() if obligation.threshold_date else None,
                "due_date": obligation.due_date.isoformat() if obligation.due_date else None,
                "status": obligation.status or "initiated",
                "is_ai_generated": obligation.is_ai_generated or False,
                "created_at": obligation.created_at.isoformat() if obligation.created_at else None,
                "updated_at": obligation.updated_at.isoformat() if obligation.updated_at else None
            }
            
            enriched_obligations.append(enriched_data)
        
        return enriched_obligations
        
    except Exception as e:
        logger.error(f"❌ Error fetching obligations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch obligations: {str(e)}"
        )




# =====================================================
# 4. UPDATE OBLIGATION
# =====================================================

@router.put("/{obligation_id}")
async def update_obligation(
    obligation_id: int,
    data: ObligationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing obligation"""
    try:
        # Get obligation
        obligation = db.query(Obligation).filter(
            Obligation.id == obligation_id
        ).first()
        
        if not obligation:
            raise HTTPException(status_code=404, detail="Obligation not found")
        
        # Verify access
        contract = db.query(Contract).filter(
            Contract.id == obligation.contract_id,
            Contract.company_id == current_user.company_id
        ).first()
        
        if not contract:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update fields
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obligation, field, value)
        
        obligation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(obligation)
        
        # Create tracking entry
        tracking = ObligationTracking(
            obligation_id=obligation.id,
            action_taken="Obligation updated",
            action_by=current_user.id,
            notes=f"Updated by {current_user.first_name} {current_user.last_name}"
        )
        db.add(tracking)
        db.commit()
        
        return {
            "success": True,
            "message": "Obligation updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating obligation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# 5. DELETE OBLIGATION
# =====================================================
# =====================================================
# DELETE OBLIGATION
# =====================================================
@router.delete("/{obligation_id}")
async def delete_obligation(
    obligation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an obligation with proper cascading and UI refresh
    """
    try:
        logger.info(f"🗑️ Deleting obligation {obligation_id}")
        
        # Get the obligation first
        obligation = db.query(Obligation).filter(Obligation.id == obligation_id).first()
        
        if not obligation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obligation not found"
            )
        
        # Verify user has access
        contract = db.query(Contract).filter(Contract.id == obligation.contract_id).first()
        if contract and contract.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # ✅ DELETE WITH FK CHECKS DISABLED
        try:
            # Disable foreign key checks to force delete
            db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            
            # Delete related records
            db.execute(text("DELETE FROM obligation_updates WHERE obligation_id = :id"), {"id": obligation_id})
            db.execute(text("DELETE FROM obligation_escalations WHERE obligation_id = :id"), {"id": obligation_id})
            db.execute(text("DELETE FROM obligation_tracking WHERE obligation_id = :id"), {"id": obligation_id})
            db.execute(text("DELETE FROM kpis WHERE obligation_id = :id"), {"id": obligation_id})
            
            # Delete the obligation itself using RAW SQL (not ORM)
            result = db.execute(text("DELETE FROM obligations WHERE id = :id"), {"id": obligation_id})
            
            # Re-enable foreign key checks
            db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            
            # Commit everything
            db.commit()
            
            logger.info(f"✅ Obligation {obligation_id} deleted successfully (rows: {result.rowcount})")
            
            return {
                "success": True,
                "message": "Obligation deleted successfully",
                "id": obligation_id
            }
            
        except Exception as e:
            db.rollback()
            db.execute(text("SET FOREIGN_KEY_CHECKS=1"))  # Re-enable on error
            logger.error(f"❌ Error during cascading delete: {str(e)}")
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error deleting obligation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete obligation: {str(e)}"
        )


@router.post("/bulk-delete")
async def bulk_delete_obligations(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk delete obligations with proper error handling
    """
    try:
        obligation_ids = request.get("obligation_ids", [])
        
        if not obligation_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No obligation IDs provided"
            )
        
        logger.info(f"🗑️ Bulk deleting {len(obligation_ids)} obligations")
        
        deleted_count = 0
        errors = []
        
        for obligation_id in obligation_ids:
            try:
                obligation = db.query(Obligation).filter(Obligation.id == obligation_id).first()
                
                if not obligation:
                    errors.append(f"Obligation {obligation_id} not found")
                    continue
                
                # Verify access
                contract = db.query(Contract).filter(Contract.id == obligation.contract_id).first()
                if contract and contract.company_id != current_user.company_id:
                    errors.append(f"Access denied for obligation {obligation_id}")
                    continue
                
                # Delete related records
                try:
                    db.execute(text("DELETE FROM obligation_updates WHERE obligation_id = :id"), {"id": obligation_id})
                    db.execute(text("DELETE FROM obligation_escalations WHERE obligation_id = :id"), {"id": obligation_id})
                    db.execute(text("DELETE FROM obligation_tracking WHERE obligation_id = :id"), {"id": obligation_id})
                    db.execute(text("DELETE FROM kpis WHERE obligation_id = :id"), {"id": obligation_id})
                    
                    # Delete the obligation
                    db.delete(obligation)
                    deleted_count += 1
                    
                except Exception as e:
                    errors.append(f"Error deleting obligation {obligation_id}: {str(e)}")
                    db.rollback()
                    continue
                
            except Exception as e:
                errors.append(f"Error processing obligation {obligation_id}: {str(e)}")
                continue
        
        # Commit all successful deletions
        if deleted_count > 0:
            db.commit()
        
        logger.info(f"✅ Deleted {deleted_count}/{len(obligation_ids)} obligations")
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} obligation(s)",
            "deleted_count": deleted_count,
            "total_requested": len(obligation_ids),
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error in bulk delete: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete obligations: {str(e)}"
        )


# =====================================================
# 6. GET ALL USERS (FOR DROPDOWNS)
# =====================================================

@router.get("/users/list")
async def get_users_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of users for owner/escalation dropdowns"""
    try:
        users = db.query(User).filter(
            User.company_id == current_user.company_id,
            User.is_active == True
        ).all()
        
        return [
            {
                "id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email
            }
            for user in users
        ]
        
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# 7. BULK CREATE AI OBLIGATIONS
# =====================================================
@router.post("/bulk-create")
async def bulk_create_obligations(
    obligations: List[ObligationCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multiple obligations at once (from AI generation)"""
    try:
        logger.info(f"💾 Bulk creating {len(obligations)} obligations")
        
        created_obligations = []
        
        for obl_data in obligations:
            # Verify contract access
            contract = db.query(Contract).filter(
                Contract.id == obl_data.contract_id,
                Contract.company_id == current_user.company_id
            ).first()
            
            if not contract:
                logger.warning(f"⚠️ Skipping obligation - contract {obl_data.contract_id} not found")
                continue
            
            # Create obligation
            new_obligation = Obligation(
                company_id=current_user.company_id,
                contract_id=obl_data.contract_id,
                obligation_title=obl_data.obligation_title,
                description=obl_data.description,
                obligation_type=obl_data.obligation_type,
                owner_user_id=obl_data.owner_user_id,
                escalation_user_id=obl_data.escalation_user_id,
                threshold_date=obl_data.threshold_date,
                due_date=obl_data.due_date,
                status=obl_data.status or 'initiated',
                is_ai_generated=obl_data.is_ai_generated,
                created_by=current_user.id,
                created_at=datetime.utcnow()
            )
            
            db.add(new_obligation)
            created_obligations.append(new_obligation)
        
        # Commit all at once
        db.commit()
        
        # Refresh to get IDs
        for obl in created_obligations:
            db.refresh(obl)
        
        logger.info(f"✅ Successfully created {len(created_obligations)} obligations")
        
        return {
            "success": True,
            "created_count": len(created_obligations),
            "obligations": [
                {
                    "id": obl.id,
                    "obligation_title": obl.obligation_title,
                    "status": obl.status
                }
                for obl in created_obligations
            ]
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error bulk creating obligations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create obligations: {str(e)}"
        )

        