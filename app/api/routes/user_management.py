# =====================================================
# FILE: app/api/routes/user_management.py
# FIXED - User Management API Routes (No Auth Required for Testing)
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime
import bcrypt
import secrets
import string

from app.core.database import get_db
from app.models.user import User, Company

router = APIRouter(prefix="/api/users", tags=["User Management"])

# =====================================================
# TEMPORARY: GET COMPANY ID FOR TESTING
# =====================================================
def get_test_company_id(db: Session = Depends(get_db)) -> int:
    """Get first company ID for testing purposes."""
    company = db.query(Company).first()
    if not company:
        # Create a test company if none exists
        test_company = Company(
            id=1,
            company_name="Test Company",
            email="test@company.com",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(test_company)
        db.commit()
        return 1
    return company.id

# =====================================================
# GET ALL COMPANY USERS
# =====================================================
@router.get("/company")
async def get_company_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    role_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all users for the company with filtering and pagination."""
    
    try:
        # Get company ID for testing
        company_id = get_test_company_id(db)
        
        # Build base query
        query = db.query(User).filter(User.company_id == company_id)
        
        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term),
                    User.job_title.ilike(search_term),
                    User.username.ilike(search_term)
                )
            )
        
        # Apply status filter
        if status_filter:
            if status_filter == "active":
                query = query.filter(and_(User.is_active == True, User.is_verified == True))
            elif status_filter == "inactive":
                query = query.filter(or_(User.is_active == False, User.is_verified == False))
            elif status_filter == "pending":
                query = query.filter(User.is_verified == False)
        
        # Apply role filter
        if role_filter:
            query = query.filter(User.user_role == role_filter)
        
        # Get total count for pagination
        total_users = query.count()
        
        # Apply pagination and get results
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        # Convert to response format
        user_list = []
        for user in users:
            user_data = {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "username": user.username or "",
                "user_role": user.user_role or "user",
                "department": user.department or "",
                "job_title": user.job_title or "",
                "mobile_number": user.mobile_number or "",
                "qid_number": user.qid_number or "",
                "user_type": user.user_type or "client",
                "language_preference": user.language_preference or "en",
                "timezone": user.timezone or "Asia/Qatar",
                "is_active": bool(user.is_active) if user.is_active is not None else True,
                "is_verified": bool(user.is_verified) if user.is_verified is not None else True,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            user_list.append(user_data)
        
        return {
            "users": user_list,
            "total": total_users,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        print(f"Error in get_company_users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )

# =====================================================
# GET SINGLE USER
# =====================================================
@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific user by ID."""
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "id": user.id,
            "company_id": user.company_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "username": user.username or "",
            "user_role": user.user_role or "user",
            "department": user.department or "",
            "job_title": user.job_title or "",
            "mobile_number": user.mobile_number or "",
            "qid_number": user.qid_number or "",
            "user_type": user.user_type or "client",
            "language_preference": user.language_preference or "en",
            "timezone": user.timezone or "Asia/Qatar",
            "is_active": bool(user.is_active) if user.is_active is not None else True,
            "is_verified": bool(user.is_verified) if user.is_verified is not None else True,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user: {str(e)}"
        )

# =====================================================
# CREATE NEW USER
# =====================================================
@router.post("/create")
async def create_user(
    user_data: dict,  # Accept plain dict for now
    db: Session = Depends(get_db)
):
    """Create a new user."""
    
    try:
        # Get company ID for testing
        company_id = get_test_company_id(db)
        
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already exists"
            )
        
        # Check if username already exists
        username = user_data.get("username") or user_data["email"].split('@')[0]
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            username = f"{username}_{secrets.randbelow(1000)}"
        
        # Hash the password
        password = user_data["password"]
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        # Create new user object
        new_user = User(
            company_id=company_id,
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            email=user_data["email"],
            username=username,
            password_hash=hashed_password,
            user_role=user_data.get("user_role", "user"),
            department=user_data.get("department"),
            job_title=user_data.get("job_title"),
            mobile_number=user_data.get("mobile_number"),
            mobile_country_code="+974",
            qid_number=user_data.get("qid_number"),
            user_type=user_data.get("user_type", "client"),
            language_preference=user_data.get("language_preference", "en"),
            timezone=user_data.get("timezone", "Asia/Qatar"),
            is_active=user_data.get("is_active", True),
            is_verified=True,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"✅ User created successfully: {new_user.email}")
        
        return {
            "id": new_user.id,
            "company_id": new_user.company_id,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "email": new_user.email,
            "username": new_user.username,
            "user_role": new_user.user_role,
            "department": new_user.department,
            "job_title": new_user.job_title,
            "mobile_number": new_user.mobile_number,
            "qid_number": new_user.qid_number,
            "user_type": new_user.user_type,
            "language_preference": new_user.language_preference,
            "timezone": new_user.timezone,
            "is_active": bool(new_user.is_active),
            "is_verified": bool(new_user.is_verified),
            "created_at": new_user.created_at,
            "updated_at": new_user.updated_at
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in create_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

# =====================================================
# UPDATE USER
# =====================================================
@router.put("/{user_id}")
async def update_user(
    user_id: int,
    user_data: dict,  # Accept plain dict for now
    db: Session = Depends(get_db)
):
    """Update an existing user."""
    
    try:
        # Get the user to update
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check email uniqueness if changed
        if user_data.get("email") and user_data["email"] != user.email:
            existing_email = db.query(User).filter(
                and_(
                    User.email == user_data["email"],
                    User.id != user_id
                )
            ).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email address already exists"
                )
            user.email = user_data["email"]
        
        # Check username uniqueness if changed
        if user_data.get("username") and user_data["username"] != user.username:
            existing_username = db.query(User).filter(
                and_(
                    User.username == user_data["username"],
                    User.id != user_id
                )
            ).first()
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )
            user.username = user_data["username"]
        
        # Update user fields
        update_fields = [
            'first_name', 'last_name', 'user_role', 'department', 
            'job_title', 'mobile_number', 'qid_number', 'user_type',
            'language_preference', 'timezone'
        ]
        
        for field in update_fields:
            if field in user_data and user_data[field] is not None:
                setattr(user, field, user_data[field])
        
        if 'is_active' in user_data:
            user.is_active = user_data['is_active']
        
        # Update password if provided
        if user_data.get("password"):
            password_bytes = user_data["password"].encode('utf-8')
            salt = bcrypt.gensalt()
            user.password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        # Update metadata
        user.updated_at = datetime.utcnow()
        
        # Save changes
        db.commit()
        db.refresh(user)
        
        print(f"✅ User updated successfully: {user.email}")
        
        return {
            "id": user.id,
            "company_id": user.company_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "username": user.username,
            "user_role": user.user_role,
            "department": user.department,
            "job_title": user.job_title,
            "mobile_number": user.mobile_number,
            "qid_number": user.qid_number,
            "user_type": user.user_type,
            "language_preference": user.language_preference,
            "timezone": user.timezone,
            "is_active": bool(user.is_active),
            "is_verified": bool(user.is_verified),
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in update_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )

# =====================================================
# DELETE USER
# =====================================================
@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Delete a user (soft delete by deactivating)."""
    
    try:
        # Get the user to delete
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Soft delete by deactivating the user
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        # Optionally add deletion marker to email
        if not user.email.endswith('.deleted'):
            user.email = f"{user.email}.deleted.{int(datetime.utcnow().timestamp())}"
        
        db.commit()
        
        print(f"✅ User deleted successfully: {user.first_name} {user.last_name}")
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in delete_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )

# =====================================================
# BULK OPERATIONS
# =====================================================
@router.post("/bulk-activate")
async def bulk_activate_users(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Activate multiple users at once."""
    
    try:
        user_ids = request_data.get("user_ids", [])
        
        updated_count = db.query(User).filter(
            User.id.in_(user_ids)
        ).update(
            {
                "is_active": True,
                "updated_at": datetime.utcnow()
            },
            synchronize_session=False
        )
        
        db.commit()
        
        return {"message": f"Activated {updated_count} users successfully"}
        
    except Exception as e:
        db.rollback()
        print(f"Error in bulk_activate_users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate users: {str(e)}"
        )

@router.post("/bulk-deactivate")
async def bulk_deactivate_users(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Deactivate multiple users at once."""
    
    try:
        user_ids = request_data.get("user_ids", [])
        
        updated_count = db.query(User).filter(
            User.id.in_(user_ids)
        ).update(
            {
                "is_active": False,
                "updated_at": datetime.utcnow()
            },
            synchronize_session=False
        )
        
        db.commit()
        
        return {"message": f"Deactivated {updated_count} users successfully"}
        
    except Exception as e:
        db.rollback()
        print(f"Error in bulk_deactivate_users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate users: {str(e)}"
        )