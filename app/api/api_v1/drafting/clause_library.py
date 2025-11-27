from fastapi import APIRouter, Depends, HTTPException, status, Query 
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from sqlalchemy.exc import IntegrityError
import logging
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.clause_library import ClauseLibrary  # Your model

logger = logging.getLogger(__name__)

router = APIRouter()

# =====================================================
# CREATE CLAUSE
# =====================================================
@router.post("/clauses", status_code=status.HTTP_201_CREATED)
async def create_clause(
    clause_data: dict,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a new clause in the library."""
    try:
        logger.info(f"Creating new clause: {clause_data.get('clause_title')}")

        # Ensure created_by is a valid UUID string
        created_by_user_id = None
        if current_user and getattr(current_user, "id", None):
            # Make sure it's a string (UUID)
            created_by_user_id = str(current_user.id)

            # Optional: check that the user exists in the database
            user_exists = db.query(User).filter(User.id == created_by_user_id).first()
            if not user_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current user not found in the database."
                )

        new_clause = ClauseLibrary(
            id=str(uuid.uuid4()),
            company_id=current_user.company_id if current_user else None,
            clause_code=generate_clause_code(db),
            clause_title=clause_data.get('clause_title'),
            clause_title_ar=clause_data.get('clause_title_ar'),
            clause_text=clause_data.get('clause_text'),
            clause_text_ar=clause_data.get('clause_text_ar'),
            category=clause_data.get('category', 'general'),
            sub_category=clause_data.get('sub_category', 'general'),
            clause_type=clause_data.get('clause_type', 'standard'),
            risk_level=clause_data.get('risk_level', 'low'),
            tags=clause_data.get('tags', []),
            is_active=True,
            usage_count=0,
            created_by=created_by_user_id,  # must match users.id CHAR(36)
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_clause)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clause code or foreign key constraint violated."
            )

        db.refresh(new_clause)
        logger.info(f"✅ Clause created successfully: {new_clause.id}")

        return {
            "success": True,
            "message": "Clause created successfully",
            "clause": {
                "id": new_clause.id,
                "clause_code": new_clause.clause_code,
                "clause_title": new_clause.clause_title,
                "category": new_clause.category,
                "created_at": new_clause.created_at.isoformat()
            }
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating clause: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create clause: {str(e)}"
        )

def generate_clause_code(db: Session) -> str:
    """Generate a globally unique clause code."""
    last_clause = db.query(ClauseLibrary).order_by(ClauseLibrary.id.desc()).first()
    next_number = 1
    if last_clause and last_clause.clause_code:
        digits = ''.join(filter(str.isdigit, last_clause.clause_code))
        if digits.isdigit():
            next_number = int(digits) + 1
    return f"CL{str(next_number).zfill(4)}"


# =====================================================
# GET CLAUSES
# =====================================================
@router.get("/clauses")
async def get_clauses(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    sort_by: str = Query("recent", regex="^(recent|alphabetical|usage)$"),
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get clauses for current user's company"""
    try:
        logger.info(f"Fetching clauses for user: {current_user.email}")
        query = db.query(ClauseLibrary).filter(
            ClauseLibrary.company_id == current_user.company_id,
            ClauseLibrary.is_active == True
        )
        
        if category:
            query = query.filter(ClauseLibrary.category == category)
        
        if search:
            query = query.filter(
                (ClauseLibrary.clause_title.contains(search)) |
                (ClauseLibrary.clause_text.contains(search))
            )
        
        if sort_by == "recent":
            query = query.order_by(ClauseLibrary.created_at.desc())
        elif sort_by == "alphabetical":
            query = query.order_by(ClauseLibrary.clause_title.asc())
        elif sort_by == "usage":
            query = query.order_by(ClauseLibrary.usage_count.desc())
        
        total = query.count()
        offset = (page - 1) * page_size
        clauses = query.offset(offset).limit(page_size).all()
        
        return {
            "success": True,
            "total": total,
            "page": page,
            "page_size": page_size,
            "clauses": [
                {
                    "id": c.id,
                    "clause_code": c.clause_code,
                    "clause_title": c.clause_title,
                    "clause_text": c.clause_text,
                    "category": c.category,
                    "sub_category": c.sub_category,
                    "clause_type": c.clause_type,
                    "risk_level": c.risk_level,
                    "tags": c.tags,
                    "usage_count": c.usage_count,
                    "created_at": c.created_at.isoformat()
                }
                for c in clauses
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching clauses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch clauses: {str(e)}"
        )


# =====================================================
# GET STATISTICS
# =====================================================
@router.get("/statistics")
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get clause library statistics"""
    try:
        total_clauses = db.query(ClauseLibrary).filter(
            ClauseLibrary.company_id == current_user.company_id,
            ClauseLibrary.is_active == True
        ).count()
        
        categories = db.query(
            ClauseLibrary.category,
            func.count(ClauseLibrary.id)
        ).filter(
            ClauseLibrary.company_id == current_user.company_id,
            ClauseLibrary.is_active == True
        ).group_by(ClauseLibrary.category).all()
        
        return {
            "success": True,
            "statistics": {
                "total_clauses": total_clauses,
                "categories": {cat: count for cat, count in categories}
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}"
        )
