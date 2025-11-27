"""
User Settings API Router - FIXED VERSION
File: app/api/api_v1/user/settings.py
Matches actual MySQL database schema
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import logging
import os
from pathlib import Path

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User, Company

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/user", tags=["user-settings"])

# =====================================================
# Pydantic Schemas
# =====================================================

class PersonalInfoUpdate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    job_title: Optional[str] = None
    country: Optional[str] = None

class CompanyInfoUpdate(BaseModel):
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    authorized_representative: Optional[str] = None
    authorized_rep_qid: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class SecuritySettingsUpdate(BaseModel):
    two_factor_enabled: bool
    security_question: Optional[str] = None
    security_answer: Optional[str] = None

class PreferencesUpdate(BaseModel):
    language_preference: str
    timezone: str
    email_notifications: bool
    newsletter: bool
    sms_notifications: bool

class UserSettingsResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# =====================================================
# Get User Settings
# =====================================================

@router.get("/settings")
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete user settings including personal, company, and preferences
    """
    try:
        # Get company info if exists
        company_info = None
        if current_user.company_id:
            company = db.query(Company).filter(Company.id == current_user.company_id).first()
            if company:
                company_info = {
                    "id": company.id,
                    "company_name": company.company_name,
                    "cr_number": company.cr_number,
                    "qid_number": company.qid_number,
                    "industry": company.industry,
                    "company_type": company.company_type,
                    "address": company.address,
                    "city": company.city,
                    "country": company.country,
                    "postal_code": company.postal_code,
                    "phone": company.phone,
                    "email": company.email,
                    "website": company.website,
                    "subscription_plan": company.subscription_plan,
                    "subscription_expiry": company.subscription_expiry.isoformat() if company.subscription_expiry else None
                }
        
        # Build user settings response - ONLY use fields that exist in DB
        settings = {
            "personal": {
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "email": current_user.email,
                "phone": current_user.mobile_number,
                "mobile_country_code": getattr(current_user, 'mobile_country_code', '+974'),
                "job_title": current_user.job_title,
                "department": current_user.department,
                "country": "Qatar",  # Default
                "qid_number": current_user.qid_number
            },
            "company": company_info,
            "security": {
                "two_factor_enabled": current_user.two_factor_enabled,
                "email_verified": current_user.is_verified,
                "last_login": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
                # Note: last_password_change doesn't exist in this DB schema
            },
            "preferences": {
                "user_type": current_user.user_type,
                "language_preference": current_user.language_preference,
                "timezone": current_user.timezone,
                "email_notifications": True,  # Default - can be extended
                "newsletter": False,
                "sms_notifications": False
            },
            "license": {
                "type": company_info.get("subscription_plan", "Corporate") if company_info else "Individual",
                "expiry": company_info.get("subscription_expiry") if company_info else None,
                "max_contracts": "Unlimited" if company_info else "10",
                "max_users": "10" if company_info else "1",
                "active_users": 1  # TODO: Calculate actual count
            }
        }
        
        return {
            "success": True,
            "data": settings
        }
        
    except Exception as e:
        logger.error(f"Error fetching user settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user settings"
        )

# =====================================================
# Update Personal Information
# =====================================================

@router.put("/settings/personal")
async def update_personal_info(
    data: PersonalInfoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's personal information
    """
    try:
        # Update user fields
        current_user.first_name = data.first_name
        current_user.last_name = data.last_name
        
        if data.phone:
            current_user.mobile_number = data.phone
        
        if data.job_title:
            current_user.job_title = data.job_title
        
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Personal info updated for user: {current_user.email}")
        
        return {
            "success": True,
            "message": "Personal information updated successfully",
            "data": {
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "phone": current_user.mobile_number,
                "job_title": current_user.job_title
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating personal info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update personal information"
        )

# =====================================================
# Update Company Information
# =====================================================

@router.put("/settings/company")
async def update_company_info(
    data: CompanyInfoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update company information (requires company association)
    """
    try:
        if not current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with a company"
            )
        
        company = db.query(Company).filter(Company.id == current_user.company_id).first()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        
        # Update company fields
        if data.industry:
            company.industry = data.industry
        
        if data.website:
            company.website = data.website
        
        company.updated_at = datetime.utcnow()
        company.updated_by = current_user.id
        
        db.commit()
        db.refresh(company)
        
        logger.info(f"Company info updated for company: {company.id}")
        
        return {
            "success": True,
            "message": "Company information updated successfully",
            "data": {
                "industry": company.industry,
                "website": company.website
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating company info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company information"
        )

# =====================================================
# Change Password
# =====================================================

@router.post("/settings/password")
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    """
    try:
        # Validate new password matches confirmation
        if data.new_password != data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match"
            )
        
        # Validate password length
        if len(data.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Verify current password
        if not verify_password(data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Hash and update new password
        current_user.password_hash = hash_password(data.new_password)
        # Note: last_password_change field doesn't exist in this DB schema
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Password changed for user: {current_user.email}")
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

# =====================================================
# Update Security Settings
# =====================================================

@router.put("/settings/security")
async def update_security_settings(
    data: SecuritySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update security settings including 2FA
    """
    try:
        current_user.two_factor_enabled = data.two_factor_enabled
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Security settings updated for user: {current_user.email}")
        
        return {
            "success": True,
            "message": "Security settings updated successfully",
            "data": {
                "two_factor_enabled": current_user.two_factor_enabled
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating security settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update security settings"
        )

# =====================================================
# Update Preferences
# =====================================================

@router.put("/settings/preferences")
async def update_preferences(
    data: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user preferences
    """
    try:
        current_user.language_preference = data.language_preference
        current_user.timezone = data.timezone
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Preferences updated for user: {current_user.email}")
        
        return {
            "success": True,
            "message": "Preferences updated successfully",
            "data": {
                "language_preference": current_user.language_preference,
                "timezone": current_user.timezone
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )

# =====================================================
# Document Upload (CR/QID)
# =====================================================

@router.post("/settings/upload-document")
async def upload_document(
    document_type: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload CR or QID documents
    """
    try:
        # Validate document type
        if document_type not in ["cr", "qid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document type. Must be 'cr' or 'qid'"
            )
        
        # Validate file extension
        allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Create upload directory if not exists
        upload_dir = Path("app/uploads/documents") / str(current_user.id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{document_type}_{timestamp}{file_ext}"
        file_path = upload_dir / filename
        
        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Update database (store relative path)
        relative_path = f"uploads/documents/{current_user.id}/{filename}"
        
        # Store in user or company record based on document type
        if document_type == "qid":
            # Store in user record
            current_user.updated_at = datetime.utcnow()
            db.commit()
        elif document_type == "cr" and current_user.company_id:
            # Store in company record
            company = db.query(Company).filter(Company.id == current_user.company_id).first()
            if company:
                company.updated_at = datetime.utcnow()
                db.commit()
        
        logger.info(f"Document uploaded: {filename} for user: {current_user.email}")
        
        return {
            "success": True,
            "message": f"{document_type.upper()} document uploaded successfully",
            "data": {
                "filename": filename,
                "path": relative_path,
                "type": document_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )