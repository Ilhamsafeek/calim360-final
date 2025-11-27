"""
Authentication API Package
"""
from app.api.api_v1.auth.registration import router as registration_router

__all__ = ['registration_router']