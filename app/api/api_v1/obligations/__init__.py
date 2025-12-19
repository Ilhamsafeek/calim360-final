"""
Obligations API Package
"""
from fastapi import APIRouter

# Create main router with prefix
router = APIRouter(prefix="/api/obligations", tags=["obligations"])

# Import and include the obligations endpoints router
from app.api.api_v1.obligations.obligations import router as obligations_endpoints
router.include_router(obligations_endpoints)

__all__ = ["router"]