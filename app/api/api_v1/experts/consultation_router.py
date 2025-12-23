# =====================================================
# FILE: app/api/api_v1/experts/consultation_router.py
# Consultation Room API Routes
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import secrets

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.consultation import (
    ExpertSession, ExpertQuery, ExpertSessionMessage, 
    ExpertSessionAttachment, ExpertActionItem, ExpertSessionFeedback,
    ExpertProfile
)
from app.api.api_v1.experts.consultation_schemas import (
    SessionCreate, SessionResponse, ActiveSessionResponse,
    MessageCreate, MessageResponse, MessageListResponse,
    AttachmentCreate, AttachmentResponse,
    ActionItemCreate, ActionItemUpdate, ActionItemResponse,
    FeedbackCreate, FeedbackResponse,
    SessionEndRequest, SessionEndResponse,
    SessionStatistics, TypingIndicator,
    MemoGenerateRequest, MemoResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/consultation", tags=["consultation"])

# =====================================================
# SESSION MANAGEMENT
# =====================================================

@router.post("/sessions", response_model=SessionResponse)
async def create_consultation_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new consultation session
    - Validates query exists and belongs to user
    - Generates unique session code
    - Sets up session with expert
    """
    try:
        # Validate query exists
        query = db.query(ExpertQuery).filter(
            ExpertQuery.id == session_data.query_id
        ).first()
        
        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        
        # Check if session already exists for this query
        existing_session = db.query(ExpertSession).filter(
            ExpertSession.query_id == session_data.query_id
        ).first()
        
        if existing_session:
            return existing_session
        
        # Generate session code
        session_code = f"SESS-{secrets.token_hex(4).upper()}"
        
        # Create session
        new_session = ExpertSession(
            query_id=session_data.query_id,
            contract_id=query.contract_id,
            user_id=current_user.id,
            expert_id=session_data.expert_id,
            session_code=session_code,
            session_type=session_data.session_type,
            query_text=query.question,
            selected_tone=session_data.selected_tone,
            status='scheduled'
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        logger.info(f" Session created: {session_code} for user {current_user.email}")
        
        return new_session
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )

@router.get("/sessions/{session_id}", response_model=ActiveSessionResponse)
async def get_session_details(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get full details of a consultation session
    - Session info
    - Query details
    - Expert details
    - Contract details
    - Participants
    - Message and attachment counts
    """
    try:
        session = db.query(ExpertSession).filter(
            ExpertSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Get query details
        query = db.query(ExpertQuery).filter(
            ExpertQuery.id == session.query_id
        ).first()
        
        query_details = {
            "id": query.id,
            "query_code": query.query_code,
            "subject": query.subject,
            "question": query.question,
            "query_type": query.query_type,
            "priority": query.priority,
            "expertise_areas": query.expertise_areas
        } if query else None
        
        # Get expert details
        expert_details = None
        if session.expert_id:
            expert = db.query(ExpertProfile).filter(
                ExpertProfile.id == session.expert_id
            ).first()
            
            if expert:
                expert_user = db.query(User).filter(User.id == expert.user_id).first()
                expert_details = {
                    "id": expert.id,
                    "name": f"{expert_user.first_name} {expert_user.last_name}",
                    "email": expert_user.email,
                    "expertise_areas": expert.expertise_areas,
                    "specialization": expert.specialization,
                    "average_rating": expert.average_rating,
                    "is_available": expert.is_available
                }
        
        # Get contract details
        contract_details = None
        if session.contract_id:
            from app.models.contract import Contract
            contract = db.query(Contract).filter(
                Contract.id == session.contract_id
            ).first()
            
            if contract:
                contract_details = {
                    "id": contract.id,
                    "contract_number": contract.contract_number,
                    "title": contract.title,
                    "contract_type": contract.contract_type,
                    "status": contract.status
                }
        
        # Get participants
        participants = []
        user = db.query(User).filter(User.id == session.user_id).first()
        if user:
            participants.append({
                "id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "role": "client"
            })
        
        if expert_details:
            participants.append({
                "id": expert_details["id"],
                "name": expert_details["name"],
                "email": expert_details["email"],
                "role": "expert"
            })
        
        # Get counts
        message_count = db.query(func.count(ExpertSessionMessage.id)).filter(
            ExpertSessionMessage.session_id == session_id
        ).scalar()
        
        attachment_count = db.query(func.count(ExpertSessionAttachment.id)).filter(
            ExpertSessionAttachment.session_id == session_id
        ).scalar()
        
        return {
            "session": session,
            "query_details": query_details,
            "expert_details": expert_details,
            "contract_details": contract_details,
            "participants": participants,
            "message_count": message_count or 0,
            "attachment_count": attachment_count or 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Error fetching session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch session details"
        )

@router.post("/sessions/{session_id}/start")
async def start_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a consultation session"""
    try:
        session = db.query(ExpertSession).filter(
            ExpertSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Update session status
        session.status = 'active'
        session.start_time = datetime.utcnow()
        
        # Update query status
        query = db.query(ExpertQuery).filter(
            ExpertQuery.id == session.query_id
        ).first()
        
        if query:
            query.status = 'in_progress'
        
        db.commit()
        
        # Create system message
        system_msg = ExpertSessionMessage(
            session_id=session_id,
            sender_id=str(current_user.id),
            sender_type='system',
            message_type='system',
            message_content=f"Session started at {session.start_time.strftime('%I:%M %p')}"
        )
        db.add(system_msg)
        db.commit()
        
        logger.info(f" Session started: {session_id}")
        
        return {
            "success": True,
            "message": "Session started successfully",
            "session_id": session_id,
            "start_time": session.start_time
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error starting session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start session"
        )

@router.post("/sessions/{session_id}/end", response_model=SessionEndResponse)
async def end_session(
    session_id: str,
    end_data: SessionEndRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    End a consultation session
    - Calculate duration
    - Generate memo if requested
    - Create action items
    - Update session status
    """
    try:
        session = db.query(ExpertSession).filter(
            ExpertSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Update session
        session.status = 'completed'
        session.end_time = datetime.utcnow()
        
        # Calculate duration
        if session.start_time:
            duration = (session.end_time - session.start_time).total_seconds() / 60
            session.session_duration_minutes = int(duration)
        
        # Generate memo placeholder
        if end_data.generate_memo:
            session.memo_file = f"/memos/session_{session.session_code}_memo.pdf"
        
        # Generate blockchain hash
        import hashlib
        hash_data = f"{session_id}{session.end_time}{current_user.id}"
        session.blockchain_hash = hashlib.sha256(hash_data.encode()).hexdigest()
        
        # Create action items
        action_items_created = 0
        if end_data.action_items:
            for task_desc in end_data.action_items:
                action_item = ExpertActionItem(
                    session_id=session_id,
                    task_description=task_desc,
                    priority='medium'
                )
                db.add(action_item)
                action_items_created += 1
        
        # Update query status
        query = db.query(ExpertQuery).filter(
            ExpertQuery.id == session.query_id
        ).first()
        
        if query:
            query.status = 'answered'
            query.responded_at = datetime.utcnow()
        
        db.commit()
        
        # Create system message
        system_msg = ExpertSessionMessage(
            session_id=session_id,
            sender_id=str(current_user.id),
            sender_type='system',
            message_type='system',
            message_content=f"Session ended. Duration: {session.session_duration_minutes} minutes"
        )
        db.add(system_msg)
        db.commit()
        
        logger.info(f" Session ended: {session_id}")
        
        return {
            "session_id": session_id,
            "end_time": session.end_time,
            "duration_minutes": session.session_duration_minutes or 0,
            "memo_file": session.memo_file,
            "action_items_created": action_items_created,
            "recording_url": session.recording_url,
            "blockchain_hash": session.blockchain_hash,
            "message": "Session ended successfully"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error ending session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end session"
        )

# =====================================================
# MESSAGES
# =====================================================

@router.post("/messages", response_model=MessageResponse)
async def send_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message in the consultation session"""
    try:
        # Create message
        new_message = ExpertSessionMessage(
            session_id=message_data.session_id,
            sender_id=str(current_user.id),
            sender_type='user',
            message_type=message_data.message_type,
            message_content=message_data.message_content,
            attachments=message_data.attachments
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        # Build response
        response = {
            "id": new_message.id,
            "session_id": new_message.session_id,
            "sender_id": new_message.sender_id,
            "sender_name": f"{current_user.first_name} {current_user.last_name}",
            "sender_type": new_message.sender_type,
            "message_type": new_message.message_type,
            "message_content": new_message.message_content,
            "attachments": new_message.attachments,
            "is_ai_generated": new_message.is_ai_generated,
            "is_read": new_message.is_read,
            "created_at": new_message.created_at
        }
        
        return response
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error sending message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages for a session with pagination"""
    try:
        # Get total count
        total_count = db.query(func.count(ExpertSessionMessage.id)).filter(
            ExpertSessionMessage.session_id == session_id
        ).scalar()
        
        # Get unread count for current user
        unread_count = db.query(func.count(ExpertSessionMessage.id)).filter(
            and_(
                ExpertSessionMessage.session_id == session_id,
                ExpertSessionMessage.sender_id != str(current_user.id),
                ExpertSessionMessage.is_read == False
            )
        ).scalar()
        
        # Get messages
        messages = db.query(ExpertSessionMessage).filter(
            ExpertSessionMessage.session_id == session_id
        ).order_by(ExpertSessionMessage.created_at.asc()).offset(skip).limit(limit).all()
        
        # Build response
        message_list = []
        for msg in messages:
            sender = db.query(User).filter(User.id == msg.sender_id).first()
            sender_name = f"{sender.first_name} {sender.last_name}" if sender else "Unknown"
            
            message_list.append({
                "id": msg.id,
                "session_id": msg.session_id,
                "sender_id": msg.sender_id,
                "sender_name": sender_name,
                "sender_type": msg.sender_type,
                "message_type": msg.message_type,
                "message_content": msg.message_content,
                "attachments": msg.attachments,
                "is_ai_generated": msg.is_ai_generated,
                "is_read": msg.is_read,
                "created_at": msg.created_at
            })
        
        return {
            "messages": message_list,
            "total_count": total_count or 0,
            "unread_count": unread_count or 0
        }
        
    except Exception as e:
        logger.error(f" Error fetching messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch messages"
        )

# =====================================================
# ACTION ITEMS
# =====================================================

@router.post("/action-items", response_model=ActionItemResponse)
async def create_action_item(
    action_data: ActionItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an action item for a session"""
    try:
        new_action = ExpertActionItem(
            session_id=action_data.session_id,
            task_description=action_data.task_description,
            assigned_to=action_data.assigned_to,
            due_date=action_data.due_date,
            priority=action_data.priority
        )
        
        db.add(new_action)
        db.commit()
        db.refresh(new_action)
        
        # Get assignee name
        assignee_name = None
        if new_action.assigned_to:
            assignee = db.query(User).filter(User.id == new_action.assigned_to).first()
            if assignee:
                assignee_name = f"{assignee.first_name} {assignee.last_name}"
        
        response = {
            "id": new_action.id,
            "session_id": new_action.session_id,
            "task_description": new_action.task_description,
            "assigned_to": new_action.assigned_to,
            "assignee_name": assignee_name,
            "due_date": new_action.due_date,
            "priority": new_action.priority,
            "status": new_action.status,
            "completed_at": new_action.completed_at,
            "completion_notes": new_action.completion_notes,
            "created_at": new_action.created_at,
            "updated_at": new_action.updated_at
        }
        
        logger.info(f" Action item created: {new_action.id}")
        return response
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error creating action item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create action item"
        )

@router.get("/sessions/{session_id}/action-items", response_model=List[ActionItemResponse])
async def get_session_action_items(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all action items for a session"""
    try:
        action_items = db.query(ExpertActionItem).filter(
            ExpertActionItem.session_id == session_id
        ).order_by(ExpertActionItem.created_at.desc()).all()
        
        result = []
        for item in action_items:
            assignee_name = None
            if item.assigned_to:
                assignee = db.query(User).filter(User.id == item.assigned_to).first()
                if assignee:
                    assignee_name = f"{assignee.first_name} {assignee.last_name}"
            
            result.append({
                "id": item.id,
                "session_id": item.session_id,
                "task_description": item.task_description,
                "assigned_to": item.assigned_to,
                "assignee_name": assignee_name,
                "due_date": item.due_date,
                "priority": item.priority,
                "status": item.status,
                "completed_at": item.completed_at,
                "completion_notes": item.completion_notes,
                "created_at": item.created_at,
                "updated_at": item.updated_at
            })
        
        return result
        
    except Exception as e:
        logger.error(f" Error fetching action items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch action items"
        )

@router.patch("/action-items/{action_id}", response_model=ActionItemResponse)
async def update_action_item(
    action_id: str,
    update_data: ActionItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an action item"""
    try:
        action_item = db.query(ExpertActionItem).filter(
            ExpertActionItem.id == action_id
        ).first()
        
        if not action_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action item not found"
            )
        
        # Update fields
        if update_data.status:
            action_item.status = update_data.status
            if update_data.status == 'completed':
                action_item.completed_at = datetime.utcnow()
        
        if update_data.completion_notes:
            action_item.completion_notes = update_data.completion_notes
        
        if update_data.due_date:
            action_item.due_date = update_data.due_date
        
        if update_data.priority:
            action_item.priority = update_data.priority
        
        action_item.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(action_item)
        
        # Get assignee name
        assignee_name = None
        if action_item.assigned_to:
            assignee = db.query(User).filter(User.id == action_item.assigned_to).first()
            if assignee:
                assignee_name = f"{assignee.first_name} {assignee.last_name}"
        
        return {
            "id": action_item.id,
            "session_id": action_item.session_id,
            "task_description": action_item.task_description,
            "assigned_to": action_item.assigned_to,
            "assignee_name": assignee_name,
            "due_date": action_item.due_date,
            "priority": action_item.priority,
            "status": action_item.status,
            "completed_at": action_item.completed_at,
            "completion_notes": action_item.completion_notes,
            "created_at": action_item.created_at,
            "updated_at": action_item.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f" Error updating action item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update action item"
        )

# =====================================================
# FEEDBACK
# =====================================================

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for a consultation session"""
    try:
        new_feedback = ExpertSessionFeedback(
            session_id=feedback_data.session_id,
            rated_by=str(current_user.id),
            rating=feedback_data.rating,
            feedback_type='user',
            communication_rating=feedback_data.communication_rating,
            expertise_rating=feedback_data.expertise_rating,
            responsiveness_rating=feedback_data.responsiveness_rating,
            overall_satisfaction=feedback_data.overall_satisfaction,
            comments=feedback_data.comments,
            would_recommend=feedback_data.would_recommend
        )
        
        db.add(new_feedback)
        
        # Update session feedback
        session = db.query(ExpertSession).filter(
            ExpertSession.id == feedback_data.session_id
        ).first()
        
        if session:
            session.feedback_rating = feedback_data.rating
            session.feedback_comment = feedback_data.comments
        
        db.commit()
        db.refresh(new_feedback)
        
        logger.info(f" Feedback submitted for session: {feedback_data.session_id}")
        
        return new_feedback
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error submitting feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )

# =====================================================
# STATISTICS
# =====================================================

@router.get("/statistics", response_model=SessionStatistics)
async def get_session_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get consultation session statistics for current user"""
    try:
        # Total sessions
        total_sessions = db.query(func.count(ExpertSession.id)).filter(
            ExpertSession.user_id == str(current_user.id)
        ).scalar() or 0
        
        # Active sessions
        active_sessions = db.query(func.count(ExpertSession.id)).filter(
            and_(
                ExpertSession.user_id == str(current_user.id),
                ExpertSession.status == 'active'
            )
        ).scalar() or 0
        
        # Completed sessions
        completed_sessions = db.query(func.count(ExpertSession.id)).filter(
            and_(
                ExpertSession.user_id == str(current_user.id),
                ExpertSession.status == 'completed'
            )
        ).scalar() or 0
        
        # Total duration
        total_duration = db.query(func.sum(ExpertSession.session_duration_minutes)).filter(
            ExpertSession.user_id == str(current_user.id)
        ).scalar() or 0
        
        # Average rating
        avg_rating = db.query(func.avg(ExpertSession.feedback_rating)).filter(
            and_(
                ExpertSession.user_id == str(current_user.id),
                ExpertSession.feedback_rating.isnot(None)
            )
        ).scalar()
        
        # Total messages
        total_messages = db.query(func.count(ExpertSessionMessage.id)).join(
            ExpertSession
        ).filter(
            ExpertSession.user_id == str(current_user.id)
        ).scalar() or 0
        
        # Total action items
        total_action_items = db.query(func.count(ExpertActionItem.id)).join(
            ExpertSession
        ).filter(
            ExpertSession.user_id == str(current_user.id)
        ).scalar() or 0
        
        # Pending action items
        pending_action_items = db.query(func.count(ExpertActionItem.id)).join(
            ExpertSession
        ).filter(
            and_(
                ExpertSession.user_id == str(current_user.id),
                or_(
                    ExpertActionItem.status == 'open',
                    ExpertActionItem.status == 'in_progress'
                )
            )
        ).scalar() or 0
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "completed_sessions": completed_sessions,
            "total_duration_minutes": total_duration,
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "total_messages": total_messages,
            "total_action_items": total_action_items,
            "pending_action_items": pending_action_items
        }
        
    except Exception as e:
        logger.error(f" Error fetching statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch statistics"
        )