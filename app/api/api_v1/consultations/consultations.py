"""
app/api/api_v1/endpoints/consultations.py
FastAPI Backend for My Consultations Page - FIXED FOR ACTUAL DATABASE SCHEMA
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Create router WITHOUT prefix (we'll add it in main.py)
router = APIRouter()


# =====================================================
# PYDANTIC SCHEMAS
# =====================================================

class ConsultationResponse(BaseModel):
    consultation_id: str
    consultation_code: str
    subject: str
    query_text: str
    consultation_date: Optional[datetime]
    duration_minutes: Optional[int]
    session_type: Optional[str]
    status: str
    priority: str
    
    expert_id: Optional[str]
    expert_name: Optional[str]
    expert_specialty: Optional[str]
    expert_picture: Optional[str]
    expert_rating: Optional[float]
    
    session_status: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    memo_file: Optional[str]
    recording_url: Optional[str]
    transcript_url: Optional[str]
    
    contract_id: Optional[str]
    contract_name: Optional[str]
    contract_number: Optional[str]
    
    action_items_count: int
    
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ConsultationStatsResponse(BaseModel):
    total_consultations: int
    scheduled_count: int
    completed_count: int
    cancelled_count: int
    pending_action_items: int
    average_rating: Optional[float]


class ActionItemResponse(BaseModel):
    action_id: str
    session_id: str
    task_description: str
    due_date: Optional[datetime]
    priority: Optional[str]
    status: Optional[str]
    completed_at: Optional[datetime]
    completion_notes: Optional[str]

    class Config:
        from_attributes = True


# =====================================================
# GET MY CONSULTATIONS - LIST VIEW
# =====================================================

@router.get("/my-consultations", response_model=List[ConsultationResponse])
async def get_my_consultations(
    status_filter: Optional[str] = Query(None, description="scheduled, completed, cancelled, all"),
    search: Optional[str] = Query(None, description="Search by subject, expert name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all consultations for the current user
    FIXED: Uses actual database column names (asked_at instead of created_at)
    """
    try:
        user_id = str(current_user.id)
        
        # Build WHERE conditions
        where_conditions = ["CAST(q.asked_by AS CHAR) = :user_id"]
        params = {"user_id": user_id}
        
        # Status filter
        if status_filter and status_filter != "all":
            if status_filter == "scheduled":
                where_conditions.append(
                    "(es.session_time IS NOT NULL AND es.session_time > NOW() AND es.start_time IS NULL)"
                )
            elif status_filter == "completed":
                where_conditions.append("(es.end_time IS NOT NULL)")
            elif status_filter == "cancelled":
                where_conditions.append(
                    "(es.session_time IS NOT NULL AND es.session_time <= NOW() "
                    "AND es.start_time IS NULL AND es.end_time IS NULL)"
                )
        
        # Search filter
        if search:
            where_conditions.append(
                "(q.subject LIKE :search OR q.question LIKE :search OR "
                "CONCAT(eu.first_name, ' ', eu.last_name) LIKE :search)"
            )
            params["search"] = f"%{search}%"
        
        where_clause = " AND ".join(where_conditions)
        
        # Main query - FIXED column names
        query = text(f"""
            SELECT 
                q.id AS consultation_id,
                q.query_code AS consultation_code,
                q.subject,
                q.question AS query_text,
                q.priority,
                q.status AS query_status,
                q.asked_at AS created_at,
                q.responded_at AS updated_at,
                
                -- Session Info
                es.id AS session_id,
                es.session_code,
                es.session_type,
                es.session_time AS consultation_date,
                es.session_duration_minutes AS duration_minutes,
                es.start_time,
                es.end_time,
                es.memo_file,
                es.recording_url,
                
                -- Expert Info
                es.expert_id,
                CONCAT(eu.first_name, ' ', eu.last_name) AS expert_name,
                ep.specialization AS expert_specialty,
                NULL AS expert_picture,
                ep.average_rating AS expert_rating,
                
                -- Contract Info
                es.contract_id,
                c.contract_title AS contract_name,
                c.contract_number,
                
                -- Action Items Count
                (SELECT COUNT(*) FROM expert_action_items eai 
                 WHERE eai.session_id = es.id) AS action_items_count,
                
                -- Determine overall status
                CASE
                    WHEN es.end_time IS NOT NULL THEN 'completed'
                    WHEN es.session_time IS NOT NULL AND es.session_time > NOW() 
                         AND es.start_time IS NULL THEN 'scheduled'
                    WHEN es.session_time IS NOT NULL AND es.session_time <= NOW() 
                         AND es.start_time IS NULL AND es.end_time IS NULL THEN 'cancelled'
                    ELSE q.status
                END AS status
                
            FROM queries q
            LEFT JOIN expert_sessions es ON q.id = es.query_id
            LEFT JOIN users eu ON es.expert_id = eu.id
            LEFT JOIN expert_profiles ep ON eu.id = ep.user_id
            LEFT JOIN contracts c ON es.contract_id = c.id
            WHERE {where_clause}
            ORDER BY 
                CASE 
                    WHEN es.session_time IS NOT NULL AND es.session_time > NOW() 
                         AND es.start_time IS NULL THEN 1
                    WHEN es.end_time IS NOT NULL THEN 2
                    ELSE 3
                END,
                es.session_time DESC,
                q.asked_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        params["limit"] = limit
        params["offset"] = offset
        
        result = db.execute(query, params)
        rows = result.fetchall()
        
        # Convert to response model
        consultations = []
        for row in rows:
            consultation = ConsultationResponse(
                consultation_id=str(row.consultation_id),
                consultation_code=row.consultation_code or "",
                subject=row.subject or "",
                query_text=row.query_text or "",
                consultation_date=row.consultation_date,
                duration_minutes=row.duration_minutes or 0,
                session_type=row.session_type,
                status=row.status or "pending",
                priority=row.priority or "standard",
                expert_id=str(row.expert_id) if row.expert_id else None,
                expert_name=row.expert_name,
                expert_specialty=row.expert_specialty,
                expert_picture=row.expert_picture,
                expert_rating=float(row.expert_rating) if row.expert_rating else None,
                session_status=None,  # Column doesn't exist in database
                start_time=row.start_time,
                end_time=row.end_time,
                memo_file=row.memo_file,
                recording_url=row.recording_url,
                transcript_url=None,
                contract_id=str(row.contract_id) if row.contract_id else None,
                contract_name=row.contract_name,
                contract_number=row.contract_number,
                action_items_count=row.action_items_count or 0,
                created_at=row.created_at,
                updated_at=row.updated_at
            )
            consultations.append(consultation)
        
        return consultations
        
    except Exception as e:
        logger.error(f"Error fetching consultations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# GET CONSULTATION STATISTICS
# =====================================================

@router.get("/my-consultations/stats", response_model=ConsultationStatsResponse)
async def get_consultation_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics for user's consultations"""
    try:
        user_id = str(current_user.id)
        
        query = text("""
            SELECT 
                COUNT(DISTINCT q.id) AS total_consultations,
                SUM(CASE 
                    WHEN es.session_time IS NOT NULL AND es.session_time > NOW() 
                         AND es.start_time IS NULL THEN 1 
                    ELSE 0 
                END) AS scheduled_count,
                SUM(CASE WHEN es.end_time IS NOT NULL THEN 1 ELSE 0 END) AS completed_count,
                SUM(CASE 
                    WHEN es.session_time IS NOT NULL AND es.session_time <= NOW() 
                         AND es.start_time IS NULL AND es.end_time IS NULL THEN 1 
                    ELSE 0 
                END) AS cancelled_count,
                (SELECT COUNT(*) FROM expert_action_items eai
                 JOIN expert_sessions es2 ON eai.session_id = es2.id
                 JOIN queries q2 ON es2.query_id = q2.id
                 WHERE CAST(q2.asked_by AS CHAR) = :user_id 
                 AND eai.status != 'completed') AS pending_action_items,
                AVG(es.feedback_rating) AS average_rating
            FROM queries q
            LEFT JOIN expert_sessions es ON q.id = es.query_id
            WHERE CAST(q.asked_by AS CHAR) = :user_id
        """)
        
        result = db.execute(query, {"user_id": user_id})
        row = result.fetchone()
        
        return ConsultationStatsResponse(
            total_consultations=row.total_consultations or 0,
            scheduled_count=row.scheduled_count or 0,
            completed_count=row.completed_count or 0,
            cancelled_count=row.cancelled_count or 0,
            pending_action_items=row.pending_action_items or 0,
            average_rating=float(row.average_rating) if row.average_rating else None
        )
        
    except Exception as e:
        logger.error(f"Error fetching consultation stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# GET ACTION ITEMS FOR A SESSION
# =====================================================

@router.get("/sessions/{session_id}/action-items", response_model=List[ActionItemResponse])
async def get_session_action_items(
    session_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get action items for a specific consultation session"""
    try:
        query = text("""
            SELECT 
                eai.id AS action_id,
                eai.session_id,
                eai.task_description,
                eai.due_date,
                eai.priority,
                eai.status,
                eai.completed_at,
                eai.completion_notes
            FROM expert_action_items eai
            JOIN expert_sessions es ON eai.session_id = es.id
            JOIN queries q ON es.query_id = q.id
            WHERE eai.session_id = :session_id
            AND CAST(q.asked_by AS CHAR) = :user_id
            ORDER BY 
                CASE eai.priority
                    WHEN 'urgent' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    ELSE 4
                END,
                eai.due_date ASC
        """)
        
        result = db.execute(query, {
            "session_id": session_id,
            "user_id": str(current_user.id)
        })
        rows = result.fetchall()
        
        action_items = []
        for row in rows:
            action_items.append(ActionItemResponse(
                action_id=str(row.action_id),
                session_id=str(row.session_id),
                task_description=row.task_description,
                due_date=row.due_date,
                priority=row.priority,
                status=row.status,
                completed_at=row.completed_at,
                completion_notes=row.completion_notes
            ))
        
        return action_items
        
    except Exception as e:
        logger.error(f"Error fetching action items: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# DOWNLOAD ENDPOINTS
# =====================================================

@router.get("/sessions/{session_id}/download/memo")
async def download_memo(
    session_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download consultation memo"""
    try:
        query = text("""
            SELECT es.memo_file 
            FROM expert_sessions es
            JOIN queries q ON es.query_id = q.id
            WHERE es.id = :session_id
            AND CAST(q.asked_by AS CHAR) = :user_id
        """)
        
        result = db.execute(query, {
            "session_id": session_id,
            "user_id": str(current_user.id)
        })
        row = result.fetchone()
        
        if not row or not row.memo_file:
            raise HTTPException(status_code=404, detail="Memo not found")
        
        return {"file_url": row.memo_file}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading memo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/download/recording")
async def download_recording(
    session_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download consultation recording"""
    try:
        query = text("""
            SELECT es.recording_url 
            FROM expert_sessions es
            JOIN queries q ON es.query_id = q.id
            WHERE es.id = :session_id
            AND CAST(q.asked_by AS CHAR) = :user_id
        """)
        
        result = db.execute(query, {
            "session_id": session_id,
            "user_id": str(current_user.id)
        })
        row = result.fetchone()
        
        if not row or not row.recording_url:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        return {"file_url": row.recording_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading recording: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))