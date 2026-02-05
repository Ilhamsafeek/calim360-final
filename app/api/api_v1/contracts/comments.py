# =====================================================
# FILE: app/api/api_v1/contracts/comments.py
# SIMPLIFIED BUBBLE COMMENTS API WITH EXACT POSITIONING
# =====================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_user
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)


class CommentCreate(BaseModel):
    contract_id: int
    comment_text: str
    selected_text: str
    anchor: Optional[Dict[str, Any]] = None  # ← NEW: Anchor object
    position_start: Optional[int] = 0  # Keep for backward compatibility
    position_end: Optional[int] = 0
    start_xpath: Optional[str] = ''
    change_type: Optional[str] = 'comment'
    original_text: Optional[str] = None
    new_text: Optional[str] = None


class CommentUpdate(BaseModel):
    comment_text: str


class CommentResponse(BaseModel):
    id: int
    contract_id: int
    user_id: int
    user_name: str
    comment_text: str
    selected_text: str
    position_start: int
    position_end: int
    change_type: str
    original_text: Optional[str]
    new_text: Optional[str]
    created_at: str
    updated_at: str
    can_delete: bool


class TrackChangeUpdate(BaseModel):
    original_text: str
    new_text: str
    change_type: str = 'insert'


@router.post("/comments/add")
async def add_comment(
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add a new bubble comment with anchor-based tracking"""
    try:
        logger.info(f"📝 Adding comment by user {current_user.id}")
        
        # Build position_info with anchor if available
        position_info = {
            'start': data.position_start,
            'end': data.position_end,
            'start_xpath': data.start_xpath or '',
            'change_type': data.change_type,
            'original_text': data.original_text,
            'new_text': data.new_text
        }
        
        # ← NEW: Add anchor if provided
        if data.anchor:
            position_info['anchor'] = data.anchor
            logger.info(f"📍 Anchor fingerprint: {data.anchor.get('fingerprint', 'N/A')}")
        
        insert_query = text("""
            INSERT INTO contract_comments 
            (contract_id, user_id, comment_text, selected_text, position_info, created_at)
            VALUES 
            (:contract_id, :user_id, :comment_text, :selected_text, :position_info, NOW())
        """)
        
        result = db.execute(insert_query, {
            'contract_id': data.contract_id,
            'user_id': current_user.id,
            'comment_text': data.comment_text,
            'selected_text': data.selected_text,
            'position_info': json.dumps(position_info)
        })
        db.commit()
        
        comment_id = result.lastrowid
        
        # Get user name
        user_query = text("""
            SELECT CONCAT(first_name, ' ', last_name) as full_name
            FROM users WHERE id = :user_id
        """)
        user_result = db.execute(user_query, {'user_id': current_user.id}).fetchone()
        user_name = user_result[0] if user_result else "Unknown User"
        
        return {
            'success': True,
            'message': 'Comment added successfully',
            'comment': {
                'id': comment_id,
                'contract_id': data.contract_id,
                'user_id': current_user.id,
                'user_name': user_name,
                'comment_text': data.comment_text,
                'selected_text': data.selected_text,
                'anchor': data.anchor,  # ← NEW: Return anchor
                'position_start': data.position_start,
                'position_end': data.position_end,
                'change_type': data.change_type,
                'original_text': data.original_text,
                'new_text': data.new_text,
                'created_at': datetime.now().isoformat(),
                'can_delete': True
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error adding comment: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comments/{contract_id}")
async def get_comments(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all comments for a contract with anchor data"""
    try:
        query = text("""
            SELECT 
                cc.id,
                cc.contract_id,
                cc.user_id,
                CONCAT(u.first_name, ' ', u.last_name) as user_name,
                cc.comment_text,
                cc.selected_text,
                cc.position_info,
                cc.created_at,
                cc.updated_at
            FROM contract_comments cc
            LEFT JOIN users u ON cc.user_id = u.id
            WHERE cc.contract_id = :contract_id
            ORDER BY cc.created_at ASC
        """)
        
        results = db.execute(query, {'contract_id': contract_id}).fetchall()
        
        comments = []
        for row in results:
            position_info = json.loads(row.position_info) if row.position_info else {}
            
            # Extract anchor if available
            anchor = position_info.get('anchor')
            
            comment = {
                'id': row.id,
                'contract_id': row.contract_id,
                'user_id': row.user_id,
                'user_name': row.user_name,
                'comment_text': row.comment_text,
                'selected_text': row.selected_text,
                'anchor': anchor,  # ← NEW: Include anchor
                'position_start': position_info.get('start', 0),
                'position_end': position_info.get('end', 0),
                'change_type': position_info.get('change_type', 'comment'),
                'original_text': position_info.get('original_text'),
                'new_text': position_info.get('new_text'),
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                'can_delete': row.user_id == current_user.id
            }
            comments.append(comment)
        
        return {
            'success': True,
            'comments': comments,
            'current_user_id': current_user.id
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching comments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a comment (only by creator)"""
    try:
        # Check if comment belongs to current user
        check_query = text("""
            SELECT user_id FROM contract_comments WHERE id = :comment_id
        """)
        result = db.execute(check_query, {'comment_id': comment_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        if result[0] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only delete your own comments")
        
        # Delete comment
        delete_query = text("""
            DELETE FROM contract_comments WHERE id = :comment_id
        """)
        db.execute(delete_query, {'comment_id': comment_id})
        db.commit()
        
        logger.info(f" Comment {comment_id} deleted successfully")
        
        return {
            'success': True,
            'message': 'Comment deleted successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting comment: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/comments/{comment_id}")
async def update_comment(
    comment_id: int,
    data: CommentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a comment (only by creator)"""
    try:
        # Check ownership
        check_query = text("""
            SELECT user_id FROM contract_comments WHERE id = :comment_id
        """)
        result = db.execute(check_query, {'comment_id': comment_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        if result[0] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only edit your own comments")
        
        # Update comment
        update_query = text("""
            UPDATE contract_comments 
            SET comment_text = :comment_text, updated_at = NOW()
            WHERE id = :comment_id
        """)
        db.execute(update_query, {
            'comment_id': comment_id,
            'comment_text': data.comment_text
        })
        db.commit()
        
        return {
            'success': True,
            'message': 'Comment updated successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating comment: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



# =====================================================
# API endpoint to track changes automatically
# =====================================================

@router.put("/comments/{comment_id}/track-change")
async def track_comment_change(
    comment_id: int,
    data: TrackChangeUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Track when commented text is edited"""
    try:
        # Get existing comment
        check_query = text("SELECT position_info FROM contract_comments WHERE id = :id")
        result = db.execute(check_query, {'id': comment_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Parse existing position_info
        pos_info = {}
        if result[0]:
            try:
                pos_info = json.loads(result[0]) if isinstance(result[0], str) else result[0]
            except:
                pass
        
        # Update with change tracking
        pos_info['change_type'] = data.change_type
        pos_info['original_text'] = data.original_text
        pos_info['new_text'] = data.new_text
        
        # Save
        update_query = text("""
            UPDATE contract_comments 
            SET position_info = :pos_info, updated_at = NOW()
            WHERE id = :id
        """)
        db.execute(update_query, {'id': comment_id, 'pos_info': json.dumps(pos_info)})
        db.commit()
        
        return {'success': True, 'message': 'Change tracked'}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))