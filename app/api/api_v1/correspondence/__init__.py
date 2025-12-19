# =====================================================
# FILE: app/api/api_v1/correspondence/__init__.py
# Correspondence Module Initialization
# =====================================================

from fastapi import APIRouter

# Create main correspondence router
router = APIRouter()

# Import and include sub-routers with error handling
try:
    from .correspondence_router import router as correspondence_router
    router.include_router(correspondence_router)
    print("✅ Correspondence router loaded")
except ImportError as e:
    print(f"⚠️ Could not import correspondence_router: {e}")

try:
    from .upload import router as upload_router
    # Include upload router with /correspondence prefix to match other endpoints
    router.include_router(upload_router, prefix="/correspondence", tags=["Correspondence Upload"])
    print("✅ Upload router loaded at /correspondence/upload")
except ImportError as e:
    print(f"⚠️ Could not import upload router: {e}")

try:
    from .analyze import router as analyze_router
    router.include_router(analyze_router, prefix="/correspondence", tags=["Correspondence Analysis"])
    print("✅ Analyze router loaded")
except ImportError as e:
    print(f"⚠️ Could not import analyze router: {e}")

__all__ = ["router"]