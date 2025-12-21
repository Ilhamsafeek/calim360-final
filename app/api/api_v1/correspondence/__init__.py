from fastapi import APIRouter
from .router import router as correspondence_router

router = APIRouter()

router.include_router(correspondence_router, tags=["Correspondence"])

__all__ = ["router"]