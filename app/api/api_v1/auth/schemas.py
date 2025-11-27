"""
Registration Schemas - Fixed to match frontend field names
File: app/api/api_v1/auth/schemas.py
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict
from datetime import date, datetime
import re

class UserRegistration(BaseModel):
    # User Information
    firstName: str = Field(..., min_length=1, max_length=50)
    lastName: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirmPassword: str
    
    # Company Information
    companyName: str = Field(..., min_length=1, max_length=100)
    industry: str
    companySize: str
    website: Optional[str] = None  # Changed from companyWebsite
    country: str
    
    # Authorized Representative - match frontend field names
    authRepName: Optional[str] = None  # Changed from authorizedRep
    authRepQID: Optional[str] = None
    crNumber: str = Field(..., min_length=1, max_length=30)
    crExpiryDate: date
    
    # Contact Information
    phoneNumber: Optional[str] = None
    jobTitle: str
    
    # Account Preferences
    userType: str
    timeZone: str
    languagePreference: str = "en"
    licenseType: str
    numberOfUsers: str
    
    # Security Information
    securityQuestion: str
    securityAnswer: str
    
    # Terms and Conditions - match frontend field names
    terms: Optional[bool] = False  # Changed from acceptTerms
    privacy: Optional[bool] = False
    dataConsent: Optional[bool] = False
    newsletter: Optional[bool] = False  # Changed from subscribeNewsletter
    enable2FA: Optional[bool] = False
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('confirmPassword')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('crExpiryDate')
    def cr_not_expired(cls, v):
        if v < date.today():
            raise ValueError('CR has expired. Please renew before registration.')
        return v
    
    @validator('terms')
    def terms_must_be_accepted(cls, v):
        # Frontend sends "on" for checked checkboxes, need to handle this
        if v == "on" or v is True:
            return True
        if not v:
            raise ValueError('You must accept the terms and conditions')
        return v
    
    @validator('privacy')
    def privacy_must_be_accepted(cls, v):
        # Frontend sends "on" for checked checkboxes
        if v == "on" or v is True:
            return True
        if not v:
            raise ValueError('You must accept the privacy policy')
        return v
    
    @validator('newsletter', 'dataConsent', 'enable2FA', pre=True)
    def convert_checkbox(cls, v):
        # Convert "on" to True, None/False to False
        if v == "on":
            return True
        return bool(v) if v else False
    
    @validator('email')
    def email_lowercase(cls, v):
        return v.lower()
    
    @validator('website')
    def validate_website(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            return f'https://{v}'
        return v

class EmailVerificationRequest(BaseModel):
    token: str

class ResendVerificationEmail(BaseModel):
    email: EmailStr

class RegistrationResponse(BaseModel):
    success: bool
    message: str
    userId: Optional[int] = None
    email: str
    verificationRequired: bool = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    rememberMe: bool = False

class LoginResponse(BaseModel):
    success: bool
    message: str
    requires_2fa: bool = False
    requires_security_question: bool = False
    security_question: Optional[str] = None
    user: Optional[Dict] = None
    access_token: Optional[str] = None
    redirect_url: Optional[str] = None

class TwoFactorVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str

class SecurityQuestionVerifyRequest(BaseModel):
    email: EmailStr
    security_answer: str