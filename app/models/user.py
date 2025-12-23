# =====================================================
# FILE: app/models/user.py  
# CLEANED - Removed duplicate definitions
# =====================================================

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.orm import relationship


from app.core.database import Base

class Company(Base):
    __tablename__ = "companies"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    company_name_ar = Column(String(255))
    cr_number = Column(String(100), unique=True)
    cr_expiry_date = Column(Date)
    authorized_rep_name = Column(String(255))
    authorized_rep_qid = Column(String(20))
    license_type = Column(String(50))
    number_of_users = Column(String(50))
    qid_number = Column(String(20))
    company_type = Column(String(50))
    industry = Column(String(100))
    company_size = Column(String(50))
    company_website = Column(String(255))
    address = Column(Text)
    address_ar = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    phone = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))
    logo_url = Column(Text)
    status = Column(String(50))
    registration_status = Column(String(50))
    subscription_plan = Column(String(50))
    subscription_expiry = Column(DateTime)
    timezone = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    created_by = Column(Integer)
    updated_by = Column(Integer)
    module_subscriptions = relationship(
        "CompanyModuleSubscription", 
        back_populates="company",
        cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    first_name_ar = Column(String(100))
    last_name_ar = Column(String(100))
    qid_number = Column(String(20), unique=True)
    mobile_number = Column(String(50))
    mobile_country_code = Column(String(10))
    user_type = Column(String(50), nullable=False)
    user_role = Column(String(100))
    department = Column(String(100))
    job_title = Column(String(100))
    profile_picture_url = Column(Text)
    language_preference = Column(String(10))
    timezone = Column(String(50))
    is_active = Column(Boolean)
    is_verified = Column(Boolean)
    email_verified_at = Column(DateTime)
    email_verification_token = Column(String(255))
    email_verification_expires = Column(DateTime)
    two_factor_enabled = Column(Boolean)
    two_factor_secret = Column(String(255))
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(45))
    failed_login_attempts = Column(Integer)
    account_locked_until = Column(DateTime)
    password_reset_token = Column(String(255))
    password_reset_expires = Column(DateTime)
    terms_accepted = Column(Boolean)
    terms_accepted_at = Column(DateTime)
    privacy_accepted = Column(Boolean)
    data_consent = Column(Boolean, default=False)
    newsletter_subscribed = Column(Boolean, default=False)
    created_at = Column(DateTime)
    created_by = Column(Integer)
    updated_at = Column(DateTime)

    updated_by = Column(Integer)  #  Your actual column
    expert_profile = relationship("ExpertProfile", back_populates="user", uselist=False)

    updated_by = Column(Integer)



class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    role_name = Column(String(100), nullable=False)
    role_name_ar = Column(String(100))
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    permission_name = Column(String(100), unique=True, nullable=False)
    permission_category = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime)