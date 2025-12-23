"""
Registration Backend - Fixed response format
File: app/api/api_v1/auth/registration.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import secrets
from datetime import datetime

from app.core.database import get_db
from app.models.user import User, Company
from app.api.api_v1.auth.schemas import UserRegistration, RegistrationResponse
from app.core.email import send_verification_email
from app.core.security import hash_password
import logging

from app.models.subscription import CompanyModuleSubscription


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=RegistrationResponse)
async def register_user(
    user_data: UserRegistration,
    db: Session = Depends(get_db)
):
    """Register new user with automatic CLM module subscription"""
    try:
        logger.info(f" Starting registration for: {user_data.email}")
        
        # VALIDATION - Check existing user
        existing_user = db.query(User).filter(
            User.email == user_data.email.lower()
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered."
            )
        
        # VALIDATION - Check existing CR Number (only if provided)
        if user_data.crNumber and user_data.crNumber.strip():
            existing_cr = db.query(Company).filter(
                Company.cr_number == user_data.crNumber
            ).first()
            
            if existing_cr:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CR Number is already registered."
                )
        
        # VALIDATION - Check existing QID (only if provided)
        if user_data.authRepQID and user_data.authRepQID.strip():
            existing_qid = db.query(User).filter(
                User.qid_number == user_data.authRepQID
            ).first()
            
            if existing_qid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="QID Number is already registered."
                )
        
        # CREATE COMPANY - EXACT field names from Company model
        new_company = Company(
            company_name=user_data.companyName,
            cr_number=user_data.crNumber if user_data.crNumber else None,
            cr_expiry_date=user_data.crExpiryDate,
            authorized_rep_name=user_data.authRepName if user_data.authRepName else None,
            authorized_rep_qid=user_data.authRepQID if user_data.authRepQID else None,
            license_type=user_data.licenseType,
            number_of_users=user_data.numberOfUsers,
            industry=user_data.industry,
            company_size=user_data.companySize,
            company_website=user_data.website if user_data.website else None,
            phone=user_data.phoneNumber if user_data.phoneNumber else None,
            country=user_data.country,
            timezone=user_data.timeZone,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(new_company)
        db.flush()  # Get company ID
        
        logger.info(f" Company created: {new_company.company_name} (ID: {new_company.id})")
        
        # CREATE USER - EXACT field names from User model
        verification_token = secrets.token_urlsafe(32)
        
        new_user = User(
            company_id=new_company.id,
            email=user_data.email.lower(),
            password_hash=hash_password(user_data.password),
            first_name=user_data.firstName,
            last_name=user_data.lastName,
            job_title=user_data.jobTitle,
            qid_number=user_data.authRepQID if user_data.authRepQID else None,  #  Convert empty to None
            mobile_number=user_data.phoneNumber if user_data.phoneNumber else None,  #  Convert empty to None
            user_type=user_data.userType,
            language_preference=user_data.languagePreference,
            timezone=user_data.timeZone,
            is_active=False,  # Activate after email verification
            is_verified=False,
            email_verification_token=verification_token,
            two_factor_enabled=user_data.enable2FA if user_data.enable2FA else False,
            terms_accepted=user_data.terms if hasattr(user_data, 'terms') else False,
            privacy_accepted=user_data.privacy if hasattr(user_data, 'privacy') else False,
            data_consent=user_data.dataConsent if hasattr(user_data, 'dataConsent') else False,
            newsletter_subscribed=user_data.newsletter if hasattr(user_data, 'newsletter') else False,
            created_at=datetime.utcnow()
        )
        db.add(new_user)
        db.flush()  # Get user ID
        
        logger.info(f" User created: {new_user.email} (ID: {new_user.id})")
        
        # CREATE DEFAULT CLM MODULE SUBSCRIPTION
        subscription = CompanyModuleSubscription(
            company_id=new_company.id,
            module_code='clm',
            is_active=True,
            subscribed_date=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        db.add(subscription)
        
        logger.info(f" CLM module subscription created for company: {new_company.id}")
        
        # COMMIT ALL CHANGES
        db.commit()
        
        # SEND VERIFICATION EMAIL
        try:
            send_verification_email(
                email=new_user.email,
                first_name=new_user.first_name,
                verification_token=verification_token
            )
            logger.info(f" Verification email sent to: {new_user.email}")
        except Exception as email_error:
            logger.error(f" Failed to send verification email: {str(email_error)}")
            # Don't fail registration if email fails
        
        return RegistrationResponse(
            success=True,
            message="Registration successful! Please check your email to verify your account.",
            user_id=new_user.id,
            company_id=new_company.id,
            email=new_user.email,
            redirect_url="/login"
        )
        
    except HTTPException:
        db.rollback()
        raise
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f" Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed due to duplicate data."
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f" Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

        
@router.get("/check-availability")
async def check_availability(
    email: str = None,
    cr_number: str = None,
    qid_number: str = None,
    db: Session = Depends(get_db)
):
    """Check availability"""
    result = {
        "email_available": True,
        "cr_available": True,
        "qid_available": True
    }
    
    try:
        if email:
            exists = db.query(User).filter(User.email == email.lower()).first()
            result["email_available"] = exists is None
        
        if cr_number:
            exists = db.query(Company).filter(Company.cr_number == cr_number).first()
            result["cr_available"] = exists is None
        
        if qid_number:
            exists = db.query(User).filter(User.qid_number == qid_number).first()
            result["qid_available"] = exists is None
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check"
        )