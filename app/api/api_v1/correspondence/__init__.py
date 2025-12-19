# =====================================================
# FILE: app/api/api_v1/correspondence/__init__.py
# Correspondence Module Initialization
# =====================================================

from fastapi import APIRouter
from .correspondence_router import router as correspondence_router

# Create main correspondence router
router = APIRouter()

# Include sub-routers
router.include_router(correspondence_router)

__all__ = ["router"]