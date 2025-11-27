# app/api/api_v1/correspondence/__init__.py
"""
Correspondence API Package
"""
from fastapi import APIRouter

# Create main router
router = APIRouter()

# Import and include sub-routers
try:
    from app.api.api_v1.correspondence.upload import router as upload_router
    router.include_router(upload_router, prefix="/documents", tags=["correspondence-documents"])
except ImportError as e:
    print(f"⚠️ Warning: Could not import upload router: {e}")

# Try to import analyze router if it exists
try:
    from app.api.api_v1.correspondence.analyze import router as analyze_router
    router.include_router(analyze_router, tags=["correspondence-analysis"])
except ImportError:
    print("⚠️ Warning: analyze router not found, skipping...")

__all__ = ['router']