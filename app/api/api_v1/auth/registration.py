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
    module: str = Query(default="clm", description="Module to subscribe to"),  # ✅ ADDED
    db: Session = Depends(get_db)
):
    """Register new user with automatic module subscription"""
    try:
        logger.info(f"📝 Starting registration for: {user_data.email} with module: {module}")
        
        # VALIDATION
        existing_user = db.query(User).filter(
            User.email == user_data.email.lower()
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered."
            )
        
        if user_data.crNumber:
            existing_cr = db.query(Company).filter(
                Company.cr_number == user_data.crNumber
            ).first()
            
            if existing_cr:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CR Number is already registered."
                )
        
        if user_data.authRepQID:
            existing_qid = db.query(User).filter(
                User.qid_number == user_data.authRepQID
            ).first()
            
            if existing_qid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="QID Number is already registered."
                )
        
        logger.info("✅ Validation passed")
        
        # CREATE COMPANY
        new_company = Company(
            company_name=user_data.companyName,
            company_name_ar=None,
            cr_number=user_data.crNumber,
            cr_expiry_date=user_data.crExpiryDate,
            authorized_rep_name=getattr(user_data, 'authRepName', None),
            authorized_rep_qid=user_data.authRepQID if user_data.authRepQID else None,
            license_type=user_data.licenseType,
            number_of_users=user_data.numberOfUsers,
            qid_number=user_data.authRepQID if user_data.authRepQID else None,
            company_type=user_data.userType,
            industry=user_data.industry,
            company_size=user_data.companySize,
            company_website=user_data.website if user_data.website else None,
            phone=user_data.phoneNumber if user_data.phoneNumber else None,
            email=user_data.email.lower(),
            website=user_data.website if user_data.website else None,
            country=user_data.country,
            city=None,
            address=None,
            address_ar=None,
            postal_code=None,
            logo_url=None,
            status='PENDING',
            registration_status='pending',
            subscription_plan=user_data.licenseType,
            subscription_expiry=None,
            timezone=user_data.timeZone,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=None,
            updated_by=None
        )
        
        db.add(new_company)
        db.flush()
        
        logger.info(f"✅ Company: ID={new_company.id}, Type={new_company.company_type}")
        
        # HASH PASSWORD
        password_hash = hash_password(user_data.password)
        
        # CREATE USER
        current_time = datetime.utcnow()
        
        new_user = User(
            company_id=new_company.id,
            email=user_data.email.lower(),
            username=user_data.email.lower(),
            password_hash=password_hash,
            first_name=user_data.firstName,
            last_name=user_data.lastName,
            first_name_ar=None,
            last_name_ar=None,
            qid_number=user_data.authRepQID if user_data.authRepQID else None,
            mobile_number=user_data.phoneNumber if user_data.phoneNumber else None,
            mobile_country_code='+974',
            user_type=user_data.userType,
            user_role=None,
            department=None,
            job_title=user_data.jobTitle,
            profile_picture_url=None,
            language_preference=user_data.languagePreference,
            timezone=user_data.timeZone,
            is_active=True,
            is_verified=False,
            email_verified_at=None,
            email_verification_token=secrets.token_urlsafe(32),
            email_verification_expires=datetime.utcnow(),
            two_factor_enabled=bool(getattr(user_data, 'enable2FA', False)),
            two_factor_secret=None,
            last_login_at=None,
            last_login_ip=None,
            failed_login_attempts=0,
            account_locked_until=None,
            password_reset_token=None,
            password_reset_expires=None,
            terms_accepted=bool(getattr(user_data, 'terms', False)),
            terms_accepted_at=current_time if getattr(user_data, 'terms', False) else None,
            privacy_accepted=bool(getattr(user_data, 'privacy', False)),
            data_consent=bool(getattr(user_data, 'dataConsent', False)),
            newsletter_subscribed=bool(getattr(user_data, 'newsletter', False)),
            created_at=current_time,
            created_by=None,
            updated_at=current_time,
            updated_by=None
        )
        
        db.add(new_user)
        new_company.created_by = new_user.id
        
        # =====================================================
        # ✅ CREATE MODULE SUBSCRIPTION (AUTOMATIC)
        # =====================================================
        valid_modules = [
            'clm', 'correspondence', 'risk', 'obligations', 
            'reports', 'blockchain', 'expert'
        ]
        
        # Validate module code and default to CLM if invalid
        if module not in valid_modules:
            logger.warning(f"⚠️ Invalid module '{module}', defaulting to 'clm'")
            module = 'clm'
        
        subscription = CompanyModuleSubscription(
            company_id=new_company.id,
            module_code=module,
            is_active=True,
            subscribed_date=datetime.utcnow(),
            expiry_date=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(subscription)
        
        logger.info(f"📦 Subscribed company {new_company.id} to module: {module}")
        # =====================================================
        
        # COMMIT
        try:
            db.commit()
            db.refresh(new_user)
            db.refresh(new_company)
            
            logger.info(f"✅ User: {new_user.id}, Email: {new_user.email}")
            logger.info(f"✅ Company: {new_company.id}, Type: {new_company.company_type}")
            logger.info(f"✅ Subscription: Module={module}")
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"❌ Integrity: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Duplicate data."
            )
        except Exception as e:
            db.rollback()
            logger.error(f"❌ DB error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error."
            )
        
        # SEND EMAIL
        verification_link = f"http://localhost:8000/verify-email?token={new_user.email_verification_token}"
        
        try:
            await send_verification_email(
                email=new_user.email,
                first_name=new_user.first_name,
                verification_link=verification_link
            )
            logger.info("✅ Email sent")
        except Exception as e:
            logger.warning(f"⚠️ Email failed: {str(e)}")
        
        logger.info("🎉 Registration complete!")
        
        # RETURN RESPONSE - Match schema format!
        return RegistrationResponse(
            success=True,
            message="Registration successful! Please check your email to verify your account.",
            userId=new_user.id,
            email=new_user.email,
            verificationRequired=True
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed."
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