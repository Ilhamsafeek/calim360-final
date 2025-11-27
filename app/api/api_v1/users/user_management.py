# =====================================================
# FILE: app/api/api_v1/users/user_management.py
# User Management API Endpoints
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
import secrets

from app.core.database import get_db
from app.models.user import User, Company
from app.core.security import hash_password
from app.core.dependencies import get_current_user
from app.core.email import send_welcome_email

router = APIRouter()

# =====================================================
# PYDANTIC SCHEMAS
# =====================================================

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    mobile_number: str
    qid_number: Optional[str] = None
    job_title: Optional[str] = None
    username: str
    password: str
    user_role: Optional[str] = None
    department: Optional[str] = None
    user_type: Optional[str] = None
    language_preference: str = "en"
    timezone: str = "Asia/Qatar"
    is_active: bool = True
    send_welcome_email: bool = True

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

    @validator('mobile_number')
    def validate_mobile(cls, v):
        # Remove spaces and dashes
        v = v.replace(' ', '').replace('-', '')
        if not v.isdigit():
            raise ValueError('Mobile number must contain only digits')
        if len(v) < 8 or len(v) > 15:
            raise ValueError('Mobile number must be 8-15 digits')
        return v


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
    qid_number: Optional[str] = None
    job_title: Optional[str] = None
    user_role: Optional[str] = None
    department: Optional[str] = None
    user_type: Optional[str] = None
    language_preference: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    company_id: int
    first_name: str
    last_name: str
    email: str
    username: str
    mobile_number: Optional[str]
    qid_number: Optional[str]
    job_title: Optional[str]
    user_role: Optional[str]
    department: Optional[str]
    user_type: Optional[str]
    language_preference: str
    timezone: str
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# API ENDPOINTS
# =====================================================

@router.get("/health")
async def health_check():
    """
    Health check endpoint - no authentication required
    """
    return {"status": "ok", "message": "User management API is running"}


@router.get("/debug/current-user")
async def debug_current_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Debug endpoint to check current logged-in user
    """
    return {
        "status": "authenticated",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "company_id": current_user.company_id,
            "user_role": current_user.user_role,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified
        }
    }


@router.post("/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new user in the same company as the current user
    """
    
    # Verify current user has permission (admin or manager)
    if current_user.user_role not in ['admin', 'manager']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and managers can create users"
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )
    
    # Check QID if provided
    if user_data.qid_number:
        existing_qid = db.query(User).filter(User.qid_number == user_data.qid_number).first()
        if existing_qid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QID Number is already registered"
            )
    
    # Hash password
    password_hash = hash_password(user_data.password)
    
    # Create new user with same company_id as current user
    new_user = User(
        company_id=current_user.company_id,  # CRITICAL: Use same company
        email=user_data.email.lower(),
        username=user_data.username,
        password_hash=password_hash,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        mobile_number=user_data.mobile_number,
        mobile_country_code='+974',
        qid_number=user_data.qid_number,
        job_title=user_data.job_title,
        user_role=user_data.user_role,
        department=user_data.department,
        user_type=user_data.user_type,
        language_preference=user_data.language_preference,
        timezone=user_data.timezone,
        is_active=user_data.is_active,
        is_verified=True,  # Auto-verify for admin-created users
        email_verified_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send welcome email if requested
    if user_data.send_welcome_email:
        try:
            await send_welcome_email(
                new_user.email,
                new_user.first_name
            )
        except Exception as e:
            # Log error but don't fail the user creation
            print(f"Failed to send welcome email: {e}")
    
    return new_user


@router.get("/company", response_model=dict)
async def get_company_users(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all users in the current user's company
    """
    
    # Query all users from the same company
    users = db.query(User).filter(
        User.company_id == current_user.company_id
    ).order_by(User.created_at.desc()).all()
    
    return {
        "users": users,
        "total": len(users)
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific user by ID (must be in same company)
    """
    
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id  # Security: Same company only
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a user (must be in same company)
    """
    
    # Verify permission
    if current_user.user_role not in ['admin', 'manager'] and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this user"
        )
    
    # Get user to update
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id  # Security: Same company only
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    update_data = user_data.dict(exclude_unset=True)
    
    # Handle email uniqueness
    if 'email' in update_data and update_data['email'] != user.email:
        existing = db.query(User).filter(User.email == update_data['email'].lower()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already in use"
            )
        update_data['email'] = update_data['email'].lower()
    
    # Handle password update
    if 'password' in update_data:
        update_data['password_hash'] = hash_password(update_data.pop('password'))
    
    # Update user
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a user (must be admin and in same company)
    """
    
    # Only admins can delete users
    if current_user.user_role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete users"
        )
    
    # Can't delete yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    
    # Get user to delete
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id  # Security: Same company only
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete (set is_active to False) or hard delete
    # For security, we'll do soft delete
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    
    # For hard delete, uncomment below:
    # db.delete(user)
    # db.commit()
    
    return None


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Activate a deactivated user
    """
    
    if current_user.user_role not in ['admin', 'manager']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and managers can activate users"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/{user_id}/resend-welcome", status_code=status.HTTP_200_OK)
async def resend_welcome_email(
    user_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resend welcome email to a user
    """
    
    if current_user.user_role not in ['admin', 'manager']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and managers can resend welcome emails"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        await send_welcome_email(user.email, user.first_name)
        
        return {"message": "Welcome email sent successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


# =====================================================
# ROUTER REGISTRATION
# Add this router to your main app with:
# app.include_router(user_management.router, prefix="/api/users", tags=["users"])
# =====================================================