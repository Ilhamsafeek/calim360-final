# =====================================================
# File: app/api/api_v1/auth/logout.py
# Fixed Logout Backend API with Cookie Clearing
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# =====================================================
# LOGOUT ENDPOINT - FIXED WITH COOKIE CLEARING
# =====================================================

@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user - Update last activity and clear session cookie
    """
    try:
        # Update user's last activity
        current_user.last_activity = datetime.utcnow()
        db.commit()
        
        # Clear the session cookie
        response.delete_cookie(
            key="session_token",
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        logger.info(f"✅ User logged out: {current_user.email} - Session cookie cleared")
        
        return {
            "success": True,
            "message": "Logged out successfully",
            "redirect_url": "/login"
        }
        
    except Exception as e:
        logger.error(f"❌ Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

# =====================================================
# LOGOUT PAGE ENDPOINT (for web navigation)
# =====================================================

@router.get("/logout")
async def logout_page(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout via GET request - for web navigation
    """
    try:
        # Update user's last activity
        current_user.last_activity = datetime.utcnow()
        db.commit()
        
        # Clear the session cookie
        response.delete_cookie(
            key="session_token",
            httponly=True,
            secure=False,
            samesite="lax"
        )
        
        logger.info(f"✅ User logged out via GET: {current_user.email}")
        
        # Return redirect response for web
        from fastapi.responses import RedirectResponse
        redirect_response = RedirectResponse(url="/login", status_code=302)
        redirect_response.delete_cookie(
            key="session_token",
            httponly=True,
            secure=False,
            samesite="lax"
        )
        return redirect_response
        
    except Exception as e:
        logger.error(f"❌ Logout error: {str(e)}")
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=302)