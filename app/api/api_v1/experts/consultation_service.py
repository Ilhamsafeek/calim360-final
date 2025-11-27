# =====================================================
# FILE: app/api/api_v1/experts/consultation_service.py
# Business Logic Layer for Consultation Room
# =====================================================

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import secrets
import hashlib
import logging

from app.models.consultation import (
    ExpertSession, ExpertQuery, ExpertProfile, ExpertAvailability,
    ExpertSessionMessage, ExpertSessionAttachment, ExpertActionItem,
    ExpertSessionFeedback
)
from app.models.user import User
from app.models.contract import Contract

logger = logging.getLogger(__name__)

class ConsultationService:
    """Service layer for consultation room business logic"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # =====================================================
    # SESSION MANAGEMENT
    # =====================================================
    
    def generate_session_code(self) -> str:
        """Generate unique session code"""
        while True:
            code = f"SESS-{secrets.token_hex(4).upper()}"
            exists = self.db.query(ExpertSession).filter(
                ExpertSession.session_code == code
            ).first()
            if not exists:
                return code
    
    def create_session(
        self,
        query_id: str,
        user_id: str,
        expert_id: Optional[str] = None,
        session_type: str = "chat",
        selected_tone: str = "professional"
    ) -> ExpertSession:
        """Create a new consultation session"""
        
        # Get query details
        query = self.db.query(ExpertQuery).filter(
            ExpertQuery.id == query_id
        ).first()
        
        if not query:
            raise ValueError("Query not found")
        
        # Check if session already exists
        existing = self.db.query(ExpertSession).filter(
            ExpertSession.query_id == query_id
        ).first()
        
        if existing:
            return existing
        
        # Auto-assign expert if not provided
        if not expert_id:
            expert_id = self._auto_assign_expert(query)
        
        # Create session
        session = ExpertSession(
            query_id=query_id,
            contract_id=query.contract_id,
            user_id=user_id,
            expert_id=expert_id,
            session_code=self.generate_session_code(),
            session_type=session_type,
            query_text=query.question,
            selected_tone=selected_tone,
            status='scheduled'
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        # Update query status
        query.status = 'assigned'
        self.db.commit()
        
        logger.info(f"✅ Session created: {session.session_code}")
        return session
    
    def _auto_assign_expert(self, query: ExpertQuery) -> Optional[str]:
        """
        Auto-assign expert based on expertise areas and availability
        Returns expert_id or None
        """
        try:
            # Get available experts
            available_experts = self.db.query(ExpertProfile).filter(
                ExpertProfile.is_available == True,
                ExpertProfile.qfcra_certified == True
            ).all()
            
            if not available_experts:
                return None
            
            # Score experts based on match
            best_expert = None
            best_score = 0
            
            for expert in available_experts:
                score = 0
                
                # Check expertise match
                if query.expertise_areas:
                    expert_areas = expert.expertise_areas.lower().split(',') if expert.expertise_areas else []
                    for area in query.expertise_areas:
                        if area.lower() in expert_areas:
                            score += 10
                
                # Prefer experts with lower current load
                active_sessions = self.db.query(func.count(ExpertSession.id)).filter(
                    and_(
                        ExpertSession.expert_id == str(expert.id),
                        ExpertSession.status == 'active'
                    )
                ).scalar()
                
                score -= active_sessions * 2
                
                # Bonus for high ratings
                if expert.average_rating:
                    score += expert.average_rating
                
                if score > best_score:
                    best_score = score
                    best_expert = expert
            
            return str(best_expert.id) if best_expert else None
            
        except Exception as e:
            logger.error(f"Error auto-assigning expert: {str(e)}")
            return None
    
    def start_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Start a consultation session"""
        
        session = self.db.query(ExpertSession).filter(
            ExpertSession.id == session_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        # Update session
        session.status = 'active'
        session.start_time = datetime.utcnow()
        
        # Update query
        query = self.db.query(ExpertQuery).filter(
            ExpertQuery.id == session.query_id
        ).first()
        
        if query:
            query.status = 'in_progress'
        
        # Create system message
        system_msg = ExpertSessionMessage(
            session_id=session_id,
            sender_id=user_id,
            sender_type='system',
            message_type='system',
            message_content=f"Session started at {session.start_time.strftime('%I:%M %p')}"
        )
        self.db.add(system_msg)
        
        self.db.commit()
        
        return {
            "success": True,
            "session_id": session_id,
            "start_time": session.start_time,
            "message": "Session started successfully"
        }
    
    def end_session(
        self,
        session_id: str,
        user_id: str,
        generate_memo: bool = True,
        action_items: Optional[List[str]] = None,
        summary_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """End a consultation session"""
        
        session = self.db.query(ExpertSession).filter(
            ExpertSession.id == session_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        # Calculate duration
        session.status = 'completed'
        session.end_time = datetime.utcnow()
        
        if session.start_time:
            duration = (session.end_time - session.start_time).total_seconds() / 60
            session.session_duration_minutes = int(duration)
        
        # Generate blockchain hash for audit trail
        hash_data = f"{session_id}{session.end_time}{user_id}"
        session.blockchain_hash = hashlib.sha256(hash_data.encode()).hexdigest()
        
        # Generate memo
        if generate_memo:
            memo_path = self._generate_memo(session, summary_notes)
            session.memo_file = memo_path
        
        # Create action items
        action_items_created = 0
        if action_items:
            for task_desc in action_items:
                action_item = ExpertActionItem(
                    session_id=session_id,
                    task_description=task_desc,
                    priority='medium',
                    status='open'
                )
                self.db.add(action_item)
                action_items_created += 1
        
        # Update query status
        query = self.db.query(ExpertQuery).filter(
            ExpertQuery.id == session.query_id
        ).first()
        
        if query:
            query.status = 'answered'
            query.responded_at = datetime.utcnow()
        
        # Update expert statistics
        if session.expert_id:
            self._update_expert_stats(session.expert_id)
        
        # System message
        system_msg = ExpertSessionMessage(
            session_id=session_id,
            sender_id=user_id,
            sender_type='system',
            message_type='system',
            message_content=f"Session ended. Duration: {session.session_duration_minutes} minutes"
        )
        self.db.add(system_msg)
        
        self.db.commit()
        
        return {
            "session_id": session_id,
            "end_time": session.end_time,
            "duration_minutes": session.session_duration_minutes,
            "memo_file": session.memo_file,
            "action_items_created": action_items_created,
            "blockchain_hash": session.blockchain_hash
        }
    
    def _generate_memo(self, session: ExpertSession, summary_notes: Optional[str]) -> str:
        """
        Generate session memo/summary document
        Returns file path
        """
        # In production, this would generate a PDF with:
        # - Session details
        # - Participants
        # - Messages/transcript
        # - Action items
        # - Expert recommendations
        # - Compliance disclaimer
        
        memo_filename = f"session_{session.session_code}_memo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        memo_path = f"/memos/{memo_filename}"
        
        # TODO: Implement actual PDF generation using reportlab or similar
        logger.info(f"Memo generated: {memo_path}")
        
        return memo_path
    
    def _update_expert_stats(self, expert_id: str):
        """Update expert consultation statistics"""
        try:
            expert = self.db.query(ExpertProfile).filter(
                ExpertProfile.id == expert_id
            ).first()
            
            if expert:
                # Update total consultations
                total = self.db.query(func.count(ExpertSession.id)).filter(
                    and_(
                        ExpertSession.expert_id == expert_id,
                        ExpertSession.status == 'completed'
                    )
                ).scalar()
                
                expert.total_consultations = total or 0
                
                # Update average rating
                avg_rating = self.db.query(func.avg(ExpertSession.feedback_rating)).filter(
                    and_(
                        ExpertSession.expert_id == expert_id,
                        ExpertSession.feedback_rating.isnot(None)
                    )
                ).scalar()
                
                if avg_rating:
                    expert.average_rating = round(float(avg_rating), 2)
                
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error updating expert stats: {str(e)}")
    
    # =====================================================
    # MESSAGING
    # =====================================================
    
    def send_message(
        self,
        session_id: str,
        sender_id: str,
        message_content: str,
        message_type: str = "text",
        attachments: Optional[List[Dict]] = None
    ) -> ExpertSessionMessage:
        """Send a message in the session"""
        
        message = ExpertSessionMessage(
            session_id=session_id,
            sender_id=sender_id,
            sender_type='user',
            message_type=message_type,
            message_content=message_content,
            attachments=attachments
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_session_messages(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[ExpertSessionMessage]:
        """Get messages for a session with pagination"""
        
        messages = self.db.query(ExpertSessionMessage).filter(
            ExpertSessionMessage.session_id == session_id
        ).order_by(
            ExpertSessionMessage.created_at.asc()
        ).offset(skip).limit(limit).all()
        
        return messages
    
    def mark_messages_as_read(self, session_id: str, user_id: str):
        """Mark all messages as read for a user"""
        
        self.db.query(ExpertSessionMessage).filter(
            and_(
                ExpertSessionMessage.session_id == session_id,
                ExpertSessionMessage.sender_id != user_id,
                ExpertSessionMessage.is_read == False
            )
        ).update({"is_read": True})
        
        self.db.commit()
    
    # =====================================================
    # ATTACHMENTS
    # =====================================================
    
    def add_attachment(
        self,
        session_id: str,
        attachment_type: str,
        file_name: str,
        file_url: str,
        uploaded_by: str,
        reference_id: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None
    ) -> ExpertSessionAttachment:
        """Add an attachment to the session"""
        
        attachment = ExpertSessionAttachment(
            session_id=session_id,
            attachment_type=attachment_type,
            reference_id=reference_id,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=uploaded_by
        )
        
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        
        return attachment
    
    def get_session_attachments(self, session_id: str) -> List[ExpertSessionAttachment]:
        """Get all attachments for a session"""
        
        return self.db.query(ExpertSessionAttachment).filter(
            ExpertSessionAttachment.session_id == session_id
        ).order_by(
            ExpertSessionAttachment.created_at.desc()
        ).all()
    
    # =====================================================
    # ACTION ITEMS
    # =====================================================
    
    def create_action_item(
        self,
        session_id: str,
        task_description: str,
        assigned_to: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: str = "medium"
    ) -> ExpertActionItem:
        """Create an action item"""
        
        action_item = ExpertActionItem(
            session_id=session_id,
            task_description=task_description,
            assigned_to=assigned_to,
            due_date=due_date,
            priority=priority,
            status='open'
        )
        
        self.db.add(action_item)
        self.db.commit()
        self.db.refresh(action_item)
        
        return action_item
    
    def update_action_item(
        self,
        action_id: str,
        status: Optional[str] = None,
        completion_notes: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: Optional[str] = None
    ) -> ExpertActionItem:
        """Update an action item"""
        
        action_item = self.db.query(ExpertActionItem).filter(
            ExpertActionItem.id == action_id
        ).first()
        
        if not action_item:
            raise ValueError("Action item not found")
        
        if status:
            action_item.status = status
            if status == 'completed':
                action_item.completed_at = datetime.utcnow()
        
        if completion_notes:
            action_item.completion_notes = completion_notes
        
        if due_date:
            action_item.due_date = due_date
        
        if priority:
            action_item.priority = priority
        
        action_item.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(action_item)
        
        return action_item
    
    def get_session_action_items(self, session_id: str) -> List[ExpertActionItem]:
        """Get all action items for a session"""
        
        return self.db.query(ExpertActionItem).filter(
            ExpertActionItem.session_id == session_id
        ).order_by(
            ExpertActionItem.created_at.desc()
        ).all()
    
    def get_user_action_items(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ExpertActionItem]:
        """Get action items assigned to a user"""
        
        query = self.db.query(ExpertActionItem).filter(
            ExpertActionItem.assigned_to == user_id
        )
        
        if status:
            query = query.filter(ExpertActionItem.status == status)
        
        return query.order_by(
            ExpertActionItem.due_date.asc()
        ).limit(limit).all()
    
    # =====================================================
    # FEEDBACK
    # =====================================================
    
    def submit_feedback(
        self,
        session_id: str,
        rated_by: str,
        rating: int,
        communication_rating: Optional[int] = None,
        expertise_rating: Optional[int] = None,
        responsiveness_rating: Optional[int] = None,
        overall_satisfaction: Optional[int] = None,
        comments: Optional[str] = None,
        would_recommend: Optional[bool] = None
    ) -> ExpertSessionFeedback:
        """Submit feedback for a session"""
        
        feedback = ExpertSessionFeedback(
            session_id=session_id,
            rated_by=rated_by,
            rating=rating,
            feedback_type='user',
            communication_rating=communication_rating,
            expertise_rating=expertise_rating,
            responsiveness_rating=responsiveness_rating,
            overall_satisfaction=overall_satisfaction,
            comments=comments,
            would_recommend=would_recommend
        )
        
        self.db.add(feedback)
        
        # Update session feedback
        session = self.db.query(ExpertSession).filter(
            ExpertSession.id == session_id
        ).first()
        
        if session:
            session.feedback_rating = rating
            session.feedback_comment = comments
        
        self.db.commit()
        
        # Update expert statistics
        if session and session.expert_id:
            self._update_expert_stats(session.expert_id)
        
        self.db.refresh(feedback)
        return feedback
    
    # =====================================================
    # STATISTICS & REPORTS
    # =====================================================
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get consultation statistics for a user"""
        
        stats = {}
        
        # Total sessions
        stats['total_sessions'] = self.db.query(func.count(ExpertSession.id)).filter(
            ExpertSession.user_id == user_id
        ).scalar() or 0
        
        # Active sessions
        stats['active_sessions'] = self.db.query(func.count(ExpertSession.id)).filter(
            and_(
                ExpertSession.user_id == user_id,
                ExpertSession.status == 'active'
            )
        ).scalar() or 0
        
        # Completed sessions
        stats['completed_sessions'] = self.db.query(func.count(ExpertSession.id)).filter(
            and_(
                ExpertSession.user_id == user_id,
                ExpertSession.status == 'completed'
            )
        ).scalar() or 0
        
        # Total duration
        stats['total_duration_minutes'] = self.db.query(
            func.sum(ExpertSession.session_duration_minutes)
        ).filter(
            ExpertSession.user_id == user_id
        ).scalar() or 0
        
        # Average rating
        avg_rating = self.db.query(
            func.avg(ExpertSession.feedback_rating)
        ).filter(
            and_(
                ExpertSession.user_id == user_id,
                ExpertSession.feedback_rating.isnot(None)
            )
        ).scalar()
        
        stats['average_rating'] = round(float(avg_rating), 2) if avg_rating else None
        
        # Message count
        stats['total_messages'] = self.db.query(
            func.count(ExpertSessionMessage.id)
        ).join(ExpertSession).filter(
            ExpertSession.user_id == user_id
        ).scalar() or 0
        
        # Action items
        stats['total_action_items'] = self.db.query(
            func.count(ExpertActionItem.id)
        ).join(ExpertSession).filter(
            ExpertSession.user_id == user_id
        ).scalar() or 0
        
        stats['pending_action_items'] = self.db.query(
            func.count(ExpertActionItem.id)
        ).join(ExpertSession).filter(
            and_(
                ExpertSession.user_id == user_id,
                or_(
                    ExpertActionItem.status == 'open',
                    ExpertActionItem.status == 'in_progress'
                )
            )
        ).scalar() or 0
        
        return stats
    
    def get_expert_statistics(self, expert_id: str) -> Dict[str, Any]:
        """Get statistics for an expert"""
        
        expert = self.db.query(ExpertProfile).filter(
            ExpertProfile.id == expert_id
        ).first()
        
        if not expert:
            raise ValueError("Expert not found")
        
        user = self.db.query(User).filter(User.id == expert.user_id).first()
        
        # Total consultations
        total = self.db.query(func.count(ExpertSession.id)).filter(
            and_(
                ExpertSession.expert_id == expert_id,
                ExpertSession.status == 'completed'
            )
        ).scalar() or 0
        
        # Average rating
        avg_rating = self.db.query(
            func.avg(ExpertSession.feedback_rating)
        ).filter(
            and_(
                ExpertSession.expert_id == expert_id,
                ExpertSession.feedback_rating.isnot(None)
            )
        ).scalar()
        
        # Total duration in hours
        total_minutes = self.db.query(
            func.sum(ExpertSession.session_duration_minutes)
        ).filter(
            ExpertSession.expert_id == expert_id
        ).scalar() or 0
        
        total_hours = round(total_minutes / 60, 2)
        
        return {
            "expert_id": expert_id,
            "expert_name": f"{user.first_name} {user.last_name}" if user else "Unknown",
            "total_consultations": total,
            "average_rating": round(float(avg_rating), 2) if avg_rating else None,
            "total_duration_hours": total_hours,
            "specializations": expert.expertise_areas.split(',') if expert.expertise_areas else [],
            "availability_status": "available" if expert.is_available else "unavailable"
        }