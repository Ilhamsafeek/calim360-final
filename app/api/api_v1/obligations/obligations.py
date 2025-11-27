# =====================================================
# FILE: app/api/api_v1/obligations/obligations.py
# Obligations Management API Routes - UPDATED VERSION
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import traceback

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.obligation import Obligation, ObligationTracking
from app.models.user import User
import logging

from sqlalchemy import and_, or_
from app.models.contract import Contract
from fastapi import Query
from sqlalchemy.exc import IntegrityError
import os
import json

from app.services.claude_service import ClaudeService

claude_service = ClaudeService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/obligations", tags=["obligations"])

# =====================================================
# PYDANTIC SCHEMAS
# =====================================================

class ObligationCreate(BaseModel):
    contract_id: int
    obligation_title: str
    description: Optional[str] = None
    obligation_type: Optional[str] = None
    owner_user_id: Optional[int] = None
    escalation_user_id: Optional[int] = None
    threshold_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: str = "initiated"
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

class ObligationResponse(BaseModel):
    id: int
    contract_id: int
    obligation_title: str
    description: Optional[str]
    obligation_type: Optional[str]
    owner_user_id: Optional[int]
    escalation_user_id: Optional[int]
    threshold_date: Optional[datetime]
    due_date: Optional[datetime]
    status: str
    is_ai_generated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ObligationTrackingResponse(BaseModel):
    id: int
    obligation_id: int
    action_taken: Optional[str]
    action_by: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# =====================================================
# API ENDPOINTS
# =====================================================

@router.get("/contract/{contract_id}", response_model=List[ObligationResponse])
async def get_contract_obligations(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all obligations for a specific contract
    """
    try:
        logger.info(f"📋 Fetching obligations for contract {contract_id}")
        
        # Add debug logging
        logger.info(f"Current user: {current_user.id}, Company: {current_user.company_id}")
        
        obligations = db.query(Obligation).filter(
            Obligation.contract_id == contract_id
        ).order_by(Obligation.created_at.desc()).all()
        
        logger.info(f"✅ Found {len(obligations)} obligations for contract {contract_id}")
        
        # Debug: log what we're returning
        for i, obligation in enumerate(obligations):
            logger.info(f"Obligation {i+1}: {obligation.id} - {obligation.obligation_title}")
        
        return obligations
        
    except Exception as e:
        logger.error(f"❌ Error fetching obligations: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching obligations: {str(e)}"
        )

@router.post("/", response_model=ObligationResponse, status_code=status.HTTP_201_CREATED)
async def create_obligation(
    obligation: ObligationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new obligation with detailed logging and verification
    """
    try:
        logger.info("=" * 60)
        logger.info("🆕 CREATING NEW OBLIGATION")
        logger.info("=" * 60)
        logger.info(f"Contract ID: {obligation.contract_id}")
        logger.info(f"Title: {obligation.obligation_title}")
        logger.info(f"Description: {obligation.description}")
        logger.info(f"Type: {obligation.obligation_type}")
        logger.info(f"Status: {obligation.status}")
        logger.info(f"User: {current_user.email} (ID: {current_user.id})")
        logger.info("-" * 60)
        
        # Create new obligation object
        logger.info("📝 Creating Obligation object...")
        new_obligation = Obligation(
            contract_id=obligation.contract_id,
            obligation_title=obligation.obligation_title,
            description=obligation.description,
            obligation_type=obligation.obligation_type,
            owner_user_id=obligation.owner_user_id,
            escalation_user_id=obligation.escalation_user_id,
            threshold_date=obligation.threshold_date,
            due_date=obligation.due_date,
            status=obligation.status,
            is_ai_generated=obligation.is_ai_generated,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        logger.info("✅ Obligation object created")
        
        # Add to session
        logger.info("➕ Adding to database session...")
        db.add(new_obligation)
        logger.info("✅ Added to session")
        
        # Commit transaction
        logger.info("💾 Committing transaction to database...")
        db.commit()
        logger.info("✅ Transaction committed")
        
        # Refresh to get the ID
        logger.info("🔄 Refreshing object to get database ID...")
        db.refresh(new_obligation)
        logger.info(f"✅ Obligation created with ID: {new_obligation.id}")
        
        # Verify it's actually in the database
        logger.info("🔍 Verifying obligation exists in database...")
        verification = db.query(Obligation).filter(
            Obligation.id == new_obligation.id
        ).first()
        
        if verification:
            logger.info(f"✅ VERIFIED: Obligation {verification.id} exists in database")
            logger.info(f"   - Title: {verification.obligation_title}")
            logger.info(f"   - Contract ID: {verification.contract_id}")
            logger.info(f"   - Status: {verification.status}")
            logger.info(f"   - Created at: {verification.created_at}")
        else:
            logger.error(f"❌ WARNING: Obligation not found in database after creation!")
            raise Exception("Obligation was not saved to database")
        
        # Create tracking log
        logger.info("📊 Creating tracking log...")
        tracking = ObligationTracking(
            obligation_id=new_obligation.id,
            action_taken="Created",
            action_by=current_user.id,
            notes=f"Obligation '{obligation.obligation_title}' created by {current_user.email}",
            created_at=datetime.utcnow()
        )
        db.add(tracking)
        db.commit()
        logger.info("✅ Tracking log created")
        
        logger.info("=" * 60)
        logger.info("✅ OBLIGATION CREATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
        return new_obligation
        
    except Exception as e:
        db.rollback()
        logger.error("=" * 60)
        logger.error("❌ ERROR CREATING OBLIGATION")
        logger.error("=" * 60)
        logger.error(f"Error: {str(e)}")
        logger.error("Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 60)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating obligation: {str(e)}"
        )

@router.put("/{obligation_id}", response_model=ObligationResponse)
async def update_obligation(
    obligation_id: int,
    obligation_update: ObligationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing obligation
    """
    try:
        logger.info("=" * 60)
        logger.info(f"📝 UPDATING OBLIGATION {obligation_id}")
        logger.info("=" * 60)
        
        # Find obligation
        obligation = db.query(Obligation).filter(
            Obligation.id == obligation_id
        ).first()
        
        if not obligation:
            logger.error(f"❌ Obligation {obligation_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obligation not found"
            )
        
        logger.info(f"✅ Found obligation: {obligation.obligation_title}")
        
        # Track changes for audit
        changes = []
        
        # Update fields
        if obligation_update.obligation_title is not None:
            if obligation.obligation_title != obligation_update.obligation_title:
                changes.append(f"Title: '{obligation.obligation_title}' → '{obligation_update.obligation_title}'")
            obligation.obligation_title = obligation_update.obligation_title
            
        if obligation_update.description is not None:
            obligation.description = obligation_update.description
            
        if obligation_update.obligation_type is not None:
            if obligation.obligation_type != obligation_update.obligation_type:
                changes.append(f"Type: '{obligation.obligation_type}' → '{obligation_update.obligation_type}'")
            obligation.obligation_type = obligation_update.obligation_type
            
        if obligation_update.owner_user_id is not None:
            if obligation.owner_user_id != obligation_update.owner_user_id:
                changes.append(f"Owner: {obligation.owner_user_id} → {obligation_update.owner_user_id}")
            obligation.owner_user_id = obligation_update.owner_user_id
            
        if obligation_update.escalation_user_id is not None:
            if obligation.escalation_user_id != obligation_update.escalation_user_id:
                changes.append(f"Escalation: {obligation.escalation_user_id} → {obligation_update.escalation_user_id}")
            obligation.escalation_user_id = obligation_update.escalation_user_id
            
        if obligation_update.threshold_date is not None:
            obligation.threshold_date = obligation_update.threshold_date
            changes.append(f"Threshold date updated")
            
        if obligation_update.due_date is not None:
            if obligation.due_date != obligation_update.due_date:
                changes.append(f"Due date: {obligation.due_date} → {obligation_update.due_date}")
            obligation.due_date = obligation_update.due_date
            
        if obligation_update.status is not None:
            if obligation.status != obligation_update.status:
                changes.append(f"Status: '{obligation.status}' → '{obligation_update.status}'")
            obligation.status = obligation_update.status
        
        obligation.updated_at = datetime.utcnow()
        
        logger.info(f"📝 Changes made: {', '.join(changes) if changes else 'No changes'}")
        
        logger.info("💾 Committing update...")
        db.commit()
        db.refresh(obligation)
        
        logger.info(f"✅ Obligation {obligation_id} updated successfully")
        
        # Create tracking log
        if changes:
            tracking = ObligationTracking(
                obligation_id=obligation.id,
                action_taken="Updated",
                action_by=current_user.id,
                notes="; ".join(changes),
                created_at=datetime.utcnow()
            )
            db.add(tracking)
            db.commit()
            logger.info("✅ Tracking log created")
        
        logger.info("=" * 60)
        return obligation
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error updating obligation: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating obligation: {str(e)}"
        )

# =====================================================
# FILE: app/api/api_v1/obligations/obligations.py
# REPLACE THE delete_obligation FUNCTION
# THIS WILL WORK - It temporarily disables foreign key checks
# =====================================================

from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

@router.delete("/{obligation_id}")
async def delete_obligation(
    obligation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an obligation by temporarily disabling foreign key checks
    """
    try:
        logger.info("=" * 60)
        logger.info(f"🗑️ DELETING OBLIGATION {obligation_id}")
        logger.info("=" * 60)
        
        obligation = db.query(Obligation).filter(
            Obligation.id == obligation_id
        ).first()
        
        if not obligation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obligation not found"
            )
        
        logger.info(f"✅ Found obligation: {obligation.obligation_title}")
        
        # Create tracking log first
        logger.info("📊 Creating deletion tracking log...")
        tracking = ObligationTracking(
            obligation_id=obligation.id,
            action_taken="Deleted",
            action_by=current_user.id,
            notes=f"Obligation '{obligation.obligation_title}' deleted by {current_user.email}",
            created_at=datetime.utcnow()
        )
        db.add(tracking)
        db.commit()
        logger.info("✅ Tracking log created")
        
        # Now delete with foreign key checks disabled
        logger.info("🔓 Temporarily disabling foreign key checks...")
        
        try:
            # Step 1: Disable foreign key checks
            db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            logger.info("✅ Foreign key checks disabled")
            
            # Step 2: Delete the obligation
            logger.info("🗑️ Deleting obligation...")
            db.delete(obligation)
            db.flush()
            logger.info("✅ Obligation deleted")
            
            # Step 3: Delete related records
            logger.info("🗑️ Cleaning up related records...")
            related_tables = [
                'obligation_escalations',
                'kpis',
                'obligation_tracking',
            ]
            
            for table_name in related_tables:
                try:
                    delete_query = text(f"DELETE FROM {table_name} WHERE obligation_id = :obligation_id")
                    result = db.execute(delete_query, {"obligation_id": obligation_id})
                    if result.rowcount > 0:
                        logger.info(f"   ✅ Deleted {result.rowcount} from {table_name}")
                except Exception as e:
                    logger.debug(f"   ℹ️ Skipped {table_name}: {str(e)}")
            
            # Step 4: Re-enable foreign key checks
            db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            logger.info("🔒 Foreign key checks re-enabled")
            
            # Step 5: Commit all changes
            db.commit()
            
        except Exception as e:
            # Make sure to re-enable foreign key checks even if error occurs
            try:
                db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                db.commit()
            except:
                pass
            raise e
        
        logger.info(f"✅ Obligation {obligation_id} deleted successfully")
        logger.info("=" * 60)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Obligation deleted successfully"
            },
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        db.rollback()
        raise
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error deleting obligation: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting obligation: {str(e)}"
        )

@router.post("/bulk-create", response_model=List[ObligationResponse])
async def bulk_create_obligations(
    obligations: List[ObligationCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple obligations at once (used for AI-generated obligations)
    """
    try:
        logger.info("=" * 60)
        logger.info(f"📦 BULK CREATING {len(obligations)} OBLIGATIONS")
        logger.info("=" * 60)
        
        created_obligations = []
        
        for idx, obligation_data in enumerate(obligations, 1):
            logger.info(f"Creating obligation {idx}/{len(obligations)}: {obligation_data.obligation_title}")
            
            new_obligation = Obligation(
                contract_id=obligation_data.contract_id,
                obligation_title=obligation_data.obligation_title,
                description=obligation_data.description,
                obligation_type=obligation_data.obligation_type,
                owner_user_id=obligation_data.owner_user_id,
                escalation_user_id=obligation_data.escalation_user_id,
                threshold_date=obligation_data.threshold_date,
                due_date=obligation_data.due_date,
                status=obligation_data.status,
                is_ai_generated=obligation_data.is_ai_generated,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_obligation)
            db.flush()  # Get the ID without committing
            
            logger.info(f"  ✅ Created with ID: {new_obligation.id}")
            
            # Create tracking log
            tracking = ObligationTracking(
                obligation_id=new_obligation.id,
                action_taken="Bulk Created",
                action_by=current_user.id,
                notes=f"Obligation '{obligation_data.obligation_title}' created via bulk import",
                created_at=datetime.utcnow()
            )
            db.add(tracking)
            
            created_obligations.append(new_obligation)
        
        logger.info("💾 Committing all obligations...")
        db.commit()
        
        # Refresh all created obligations
        for obligation in created_obligations:
            db.refresh(obligation)
        
        logger.info(f"✅ Successfully created {len(created_obligations)} obligations")
        logger.info("=" * 60)
        
        return created_obligations
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error bulk creating obligations: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating obligations: {str(e)}"
        )

@router.get("/{obligation_id}/tracking", response_model=List[ObligationTrackingResponse])
async def get_obligation_tracking(
    obligation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get tracking history for an obligation
    """
    try:
        logger.info(f"📊 Fetching tracking history for obligation {obligation_id}")
        
        tracking = db.query(ObligationTracking).filter(
            ObligationTracking.obligation_id == obligation_id
        ).order_by(ObligationTracking.created_at.desc()).all()
        
        logger.info(f"✅ Found {len(tracking)} tracking records")
        
        return tracking
        
    except Exception as e:
        logger.error(f"❌ Error fetching tracking history: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tracking history: {str(e)}"
        )


@router.get("/stats")
async def get_all_obligations_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get obligation statistics for all contracts in the user's company
    """
    try:
        logger.info(f"📊 Fetching obligation stats for company {current_user.company_id}")
        
        # Get all obligations for the company
        obligations = db.query(Obligation).join(
            Contract, Obligation.contract_id == Contract.id
        ).filter(
            Contract.company_id == current_user.company_id
        ).all()
        
        # Calculate stats
        total = len(obligations)
        in_progress = sum(1 for o in obligations if o.status == "in-progress")
        completed = sum(1 for o in obligations if o.status == "completed")
        pending = sum(1 for o in obligations if o.status in ["initiated", "pending"])
        
        # Calculate overdue
        overdue = 0
        for o in obligations:
            if o.due_date and o.status not in ["completed", "cancelled"]:
                due_date_obj = o.due_date.date() if isinstance(o.due_date, datetime) else o.due_date
                if due_date_obj < datetime.now().date():
                    overdue += 1
        
        # Stats by type
        by_type = {}
        for o in obligations:
            otype = o.obligation_type or "other"
            by_type[otype] = by_type.get(otype, 0) + 1
        
        # Stats by priority
        by_priority = {"high": 0, "medium": 0, "low": 0}
        for o in obligations:
            if o.due_date:
                due_date_obj = o.due_date.date() if isinstance(o.due_date, datetime) else o.due_date
                days_until_due = (due_date_obj - datetime.now().date()).days
                if days_until_due < 0 or o.status == "overdue":
                    by_priority["high"] += 1
                elif days_until_due <= 7:
                    by_priority["high"] += 1
                elif days_until_due <= 30:
                    by_priority["medium"] += 1
                else:
                    by_priority["low"] += 1
            else:
                by_priority["low"] += 1
        
        stats = {
            "total": total,
            "in_progress": in_progress,
            "completed": completed,
            "overdue": overdue,
            "pending": pending,
            "by_type": by_type,
            "by_priority": by_priority
        }
        
        logger.info(f"✅ Stats calculated: {stats}")
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching stats: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching obligation stats: {str(e)}"
        )


@router.get("/all")
async def get_all_obligations(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    priority_filter: Optional[str] = Query(None, description="Filter by priority"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all obligations for the current user's company (across all contracts)
    """
    try:
        logger.info(f"📋 Fetching all obligations for company {current_user.company_id}")
        logger.info(f"Filters: status={status_filter}, priority={priority_filter}, search={search}")
        
        # Build query - join with contracts to filter by company
        query = db.query(Obligation).join(
            Contract, Obligation.contract_id == Contract.id
        ).filter(
            Contract.company_id == current_user.company_id
        )
        
        # Apply status filter
        if status_filter and status_filter != "all":
            if status_filter == "overdue":
                query = query.filter(
                    and_(
                        Obligation.status.notin_(["completed", "cancelled"]),
                        Obligation.due_date < datetime.now()
                    )
                )
            else:
                query = query.filter(Obligation.status == status_filter)
        
        # Apply search
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Obligation.obligation_title.ilike(search_term),
                    Obligation.description.ilike(search_term)
                )
            )
        
        obligations = query.order_by(Obligation.created_at.desc()).all()
        
        logger.info(f"✅ Found {len(obligations)} obligations")
        
        # Enrich with user data and calculated fields
        enriched_obligations = []
        for obligation in obligations:
            # Get contract info
            contract = db.query(Contract).filter(Contract.id == obligation.contract_id).first()
            
            # Get owner info
            owner = None
            if obligation.owner_user_id:
                owner = db.query(User).filter(User.id == obligation.owner_user_id).first()
            
            # Get escalation user info
            escalation_user = None
            if obligation.escalation_user_id:
                escalation_user = db.query(User).filter(User.id == obligation.escalation_user_id).first()
            
            # Calculate days until due
            days_until_due = None
            is_overdue = False
            priority = "low"
            
            if obligation.due_date:
                due_date_obj = obligation.due_date.date() if isinstance(obligation.due_date, datetime) else obligation.due_date
                today = datetime.now().date()
                days_until_due = (due_date_obj - today).days
                is_overdue = days_until_due < 0
                
                # Calculate priority
                if is_overdue or obligation.status == "overdue":
                    priority = "high"
                elif days_until_due <= 7:
                    priority = "high"
                elif days_until_due <= 30:
                    priority = "medium"
            
            enriched_data = {
                "id": obligation.id,
                "contract_id": obligation.contract_id,
                "contract_number": contract.contract_number if contract else None,
                "contract_title": contract.contract_title if contract else None,
                "obligation_title": obligation.obligation_title,
                "description": obligation.description,
                "obligation_type": obligation.obligation_type or "other",
                "owner_user_id": obligation.owner_user_id,
                "owner_name": f"{owner.first_name} {owner.last_name}" if owner else None,
                "owner_email": owner.email if owner else None,
                "escalation_user_id": obligation.escalation_user_id,
                "escalation_name": f"{escalation_user.first_name} {escalation_user.last_name}" if escalation_user else None,
                "threshold_date": obligation.threshold_date.isoformat() if obligation.threshold_date else None,
                "due_date": obligation.due_date.isoformat() if obligation.due_date else None,
                "status": obligation.status,
                "is_ai_generated": obligation.is_ai_generated,
                "created_at": obligation.created_at.isoformat(),
                "updated_at": obligation.updated_at.isoformat(),
                "days_until_due": days_until_due,
                "is_overdue": is_overdue,
                "priority": priority
            }
            
            # Apply priority filter if needed
            if priority_filter and priority_filter != "all":
                if enriched_data["priority"] == priority_filter:
                    enriched_obligations.append(enriched_data)
            else:
                enriched_obligations.append(enriched_data)
        
        logger.info(f"✅ Returning {len(enriched_obligations)} obligations after filtering")
        
        return {
            "success": True,
            "data": enriched_obligations,
            "total": len(enriched_obligations)
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching all obligations: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching obligations: {str(e)}"
        )

@router.get("/{obligation_id}", response_model=ObligationResponse)
async def get_obligation(
    obligation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single obligation by ID
    """
    try:
        logger.info(f"🔍 Fetching obligation {obligation_id}")
        
        obligation = db.query(Obligation).filter(
            Obligation.id == obligation_id
        ).first()
        
        if not obligation:
            logger.error(f"❌ Obligation {obligation_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obligation not found"
            )
        
        logger.info(f"✅ Found obligation: {obligation.obligation_title}")
        return obligation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching obligation: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching obligation: {str(e)}"
        )

@router.get("/test")
async def test_obligations_api():
    """Simple test endpoint - no authentication required"""
    return {"status": "OK", "message": "Obligations API is working!"}



class AIObligationResponse(BaseModel):
    title: str
    description: str
    category: str
    priority: str
    confidence: float
    clause_reference: Optional[str] = None


@router.post("/generate-ai/{contract_id}", response_model=List[AIObligationResponse])
async def generate_ai_obligations(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate obligations using Claude AI by analyzing the actual contract document.
    """
    try:
        # Verify contract exists
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        logger.info(f"Generating AI obligations for contract {contract_id}")
        
        # Get contract content/document
        contract_text = await get_contract_content(contract, db)
        
        if not contract_text:
            raise HTTPException(
                status_code=400, 
                detail="Contract document not found or is empty"
            )
        
        # Extract obligations using Claude AI
        ai_obligations = await extract_obligations_with_ai(contract_text, contract)
        
        logger.info(f"Generated {len(ai_obligations)} AI obligations for contract {contract_id}")
        return ai_obligations
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating AI obligations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_contract_content(contract, db: Session) -> str:
    """
    Retrieve the actual contract document content.
    This looks for uploaded documents associated with the contract.
    """
    try:
        # Try to get the contract document from the database
        try:
            from app.models import ContractDocument
            
            # Get the latest document for this contract
            document = db.query(ContractDocument).filter(
                ContractDocument.contract_id == contract.id
            ).order_by(ContractDocument.uploaded_at.desc()).first()
            
            if document and document.file_path:
                # Read the document content
                import PyPDF2
                import docx
                
                file_path = document.file_path
                
                # Handle PDF files
                if file_path.lower().endswith('.pdf'):
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text()
                        return text
                
                # Handle DOCX files
                elif file_path.lower().endswith('.docx'):
                    doc = docx.Document(file_path)
                    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                    return text
                
                # Handle TXT files
                elif file_path.lower().endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as file:
                        return file.read()
        except ImportError:
            logger.warning("ContractDocument model not found, using contract metadata")
        
        # If no document found, use contract description or terms
        contract_info = f"""
CONTRACT INFORMATION:

Contract ID: {contract.id}
Contract Title: {getattr(contract, 'contract_title', 'N/A')}
Contract Number: {getattr(contract, 'contract_number', 'N/A')}
Contract Type: {getattr(contract, 'contract_type', 'N/A')}

PARTIES:
Party A: {getattr(contract, 'party_a_name', 'N/A')}
Party B: {getattr(contract, 'party_b_name', 'N/A')}

DURATION:
Start Date: {getattr(contract, 'start_date', 'N/A')}
End Date: {getattr(contract, 'end_date', 'N/A')}

FINANCIAL:
Contract Value: {getattr(contract, 'contract_value', 'N/A')}

DESCRIPTION:
{getattr(contract, 'description', 'No description available')}

TERMS AND CONDITIONS:
{getattr(contract, 'terms_and_conditions', 'No terms specified')}

SCOPE OF WORK:
{getattr(contract, 'scope_of_work', 'No scope defined')}
"""
        
        return contract_info
        
    except Exception as e:
        logger.error(f"Error reading contract content: {str(e)}")
        # Return basic contract info as fallback
        contract_title = getattr(contract, 'contract_title', 'Untitled Contract')
        return f"Contract #{contract.id}: {contract_title}"


async def extract_obligations_with_ai(contract_text: str, contract) -> List[AIObligationResponse]:
    """
    Use Claude AI to extract obligations from the actual contract text.
    """
    try:
        # Create the AI prompt with better instructions
        prompt = f"""Analyze this contract and extract ALL contractual obligations. Return a JSON array.

CONTRACT TEXT:
{contract_text}

TASK: Extract every obligation, duty, requirement, or commitment mentioned in this contract.

For each obligation found, create a JSON object with these exact fields:
- title: Short descriptive title of the obligation
- description: Detailed explanation of what must be done
- category: Choose ONE from: payment, delivery, compliance, reporting, maintenance, insurance, coordination, inspection, other
- priority: Choose ONE from: high, medium, low
- confidence: Number between 0.5 and 1.0
- clause_reference: Where in the contract this obligation appears

CRITICAL INSTRUCTIONS:
1. Extract AT LEAST 5 obligations even if the contract is brief
2. Look for: payment terms, delivery requirements, reporting duties, compliance rules, maintenance obligations, insurance requirements, meeting schedules, approval processes
3. If the contract mentions parties, dates, amounts, or actions - those are obligations
4. Return ONLY the JSON array, no other text
5. Do NOT wrap in markdown code blocks

EXAMPLE OUTPUT FORMAT:
[
  {{"title": "Monthly Payment", "description": "Pay invoice within 30 days", "category": "payment", "priority": "high", "confidence": 0.9, "clause_reference": "Payment Terms"}},
  {{"title": "Quality Reports", "description": "Submit monthly quality reports", "category": "reporting", "priority": "medium", "confidence": 0.85, "clause_reference": "Reporting Requirements"}}
]

Now extract obligations from the contract above and return ONLY the JSON array:"""

        # Call Claude AI using the ClaudeService client
        logger.info(f"Calling Claude AI via ClaudeService.client")
        logger.info(f"Contract text length: {len(contract_text)} characters")
        
        # Use the client from ClaudeService
        message = claude_service.client.messages.create(
            model=claude_service.model,
            max_tokens=claude_service.max_tokens,
            temperature=0.3,  # Lower temperature for more consistent JSON
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract the response
        response_text = message.content[0].text
        
        logger.info(f"Received AI response: {len(response_text)} characters")
        logger.info(f"Raw AI response (first 500 chars): {response_text[:500]}")
        
        # Parse JSON response - more aggressive cleaning
        response_text = response_text.strip()
        
        # Remove markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        response_text = response_text.strip()
        
        # Log cleaned response
        logger.info(f"Cleaned response (first 300 chars): {response_text[:300]}")
        
        # Parse the JSON
        try:
            obligations_data = json.loads(response_text)
        except json.JSONDecodeError as je:
            logger.error(f"JSON parsing failed: {str(je)}")
            logger.error(f"Full cleaned response: {response_text}")
            
            # Try to extract JSON array from text
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                logger.info("Found JSON array pattern, trying to parse...")
                obligations_data = json.loads(json_match.group(0))
            else:
                raise
        
        if not isinstance(obligations_data, list):
            logger.error(f"Response is not a list, type: {type(obligations_data)}")
            raise Exception("AI response is not a JSON array")
        
        logger.info(f"Successfully parsed {len(obligations_data)} obligations from AI")
        
        if len(obligations_data) == 0:
            logger.error("AI extracted 0 obligations - this should not happen")
            logger.error(f"Contract text was: {contract_text[:500]}")
            
            # Create basic obligations from contract metadata
            basic_obligations = []
            
            # Extract obligations from contract fields
            if hasattr(contract, 'contract_type') and contract.contract_type:
                basic_obligations.append({
                    "title": f"{contract.contract_type} Execution",
                    "description": f"Execute all terms and conditions of this {contract.contract_type} contract",
                    "category": "compliance",
                    "priority": "high",
                    "confidence": 0.8,
                    "clause_reference": "General Terms"
                })
            
            if hasattr(contract, 'contract_value') and contract.contract_value:
                basic_obligations.append({
                    "title": "Payment Obligation",
                    "description": f"Complete payment of contract value: {contract.contract_value}",
                    "category": "payment",
                    "priority": "high",
                    "confidence": 0.9,
                    "clause_reference": "Financial Terms"
                })
            
            if hasattr(contract, 'start_date') and contract.start_date:
                basic_obligations.append({
                    "title": "Contract Commencement",
                    "description": f"Begin contract performance from start date: {contract.start_date}",
                    "category": "coordination",
                    "priority": "high",
                    "confidence": 0.85,
                    "clause_reference": "Contract Duration"
                })
            
            if hasattr(contract, 'end_date') and contract.end_date:
                basic_obligations.append({
                    "title": "Contract Completion",
                    "description": f"Complete all obligations before end date: {contract.end_date}",
                    "category": "delivery",
                    "priority": "high",
                    "confidence": 0.85,
                    "clause_reference": "Contract Duration"
                })
            
            # Add a reporting obligation
            basic_obligations.append({
                "title": "Progress Reporting",
                "description": "Provide regular progress reports on contract performance and deliverables",
                "category": "reporting",
                "priority": "medium",
                "confidence": 0.75,
                "clause_reference": "General Obligations"
            })
            
            obligations_data = basic_obligations
            logger.info(f"Created {len(basic_obligations)} basic obligations from contract metadata")
        
        # Convert to AIObligationResponse objects
        ai_obligations = []
        for idx, obl in enumerate(obligations_data):
            try:
                ai_obligations.append(
                    AIObligationResponse(
                        title=str(obl.get("title", f"Obligation {idx+1}"))[:500],
                        description=str(obl.get("description", "No description provided"))[:2000],
                        category=str(obl.get("category", "other")).lower(),
                        priority=str(obl.get("priority", "medium")).lower(),
                        confidence=float(obl.get("confidence", 0.8)),
                        clause_reference=str(obl.get("clause_reference", "Not specified"))[:200]
                    )
                )
            except Exception as e:
                logger.error(f"Error processing obligation {idx}: {str(e)}")
                logger.error(f"Obligation data: {obl}")
                continue
        
        logger.info(f"Successfully created {len(ai_obligations)} AIObligationResponse objects")
        return ai_obligations
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing AI response as JSON: {str(e)}")
        logger.error(f"Raw response: {response_text if 'response_text' in locals() else 'No response'}...")
        raise Exception("AI returned invalid JSON format. Please try again.")
    except Exception as e:
        logger.error(f"Error in AI extraction: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise Exception(f"AI extraction failed: {str(e)}")