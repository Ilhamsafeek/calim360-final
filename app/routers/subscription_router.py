# =====================================================
# FILE: app/routers/subscription_router.py
# Subscription API Endpoints
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.subscription_service import SubscriptionService

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("/modules", response_model=List[Dict])
async def get_all_modules(
    db: Session = Depends(get_db)
):
    """Get all available modules"""
    try:
        modules = SubscriptionService.get_all_modules(db)
        return modules
    except Exception as e:
        logger.error(f"Get modules error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch modules"
        )


@router.get("/my-modules", response_model=List[Dict])
async def get_my_modules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all modules with subscription status for current user's company"""
    try:
        if not current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with any company"
            )
        
        modules = SubscriptionService.get_modules_with_access(
            current_user.company_id, 
            db
        )
        
        return modules
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get my modules error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch subscriptions"
        )


@router.get("/check/{module_code}", response_model=Dict)
async def check_module_access(
    module_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if current user's company has access to specific module"""
    try:
        if not current_user.company_id:
            return {"has_access": False, "module_code": module_code}
        
        has_access = SubscriptionService.has_module_access(
            current_user.company_id,
            module_code,
            db
        )
        
        return {
            "has_access": has_access,
            "module_code": module_code,
            "company_id": current_user.company_id
        }
        
    except Exception as e:
        logger.error(f"Check module access error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check module access"
        )


@router.post("/subscribe/{module_code}")
async def subscribe_to_module(
    module_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Subscribe current user's company to a module (Admin only)"""
    try:
        # Check if user is admin
        if current_user.user_type not in ['super_admin', 'company_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can manage subscriptions"
            )
        
        if not current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with any company"
            )
        
        success = SubscriptionService.subscribe_company_to_module(
            current_user.company_id,
            module_code,
            None,  # No expiry date for now
            db
        )
        
        if success:
            return {
                "success": True,
                "message": f"Successfully subscribed to {module_code}",
                "module_code": module_code
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to subscribe to module"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscribe to module error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to module"
        )


@router.delete("/unsubscribe/{module_code}")
async def unsubscribe_from_module(
    module_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unsubscribe current user's company from a module (Admin only)"""
    try:
        # Check if user is admin
        if current_user.user_type not in ['super_admin', 'company_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can manage subscriptions"
            )
        
        if not current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with any company"
            )
        
        success = SubscriptionService.unsubscribe_company_from_module(
            current_user.company_id,
            module_code,
            db
        )
        
        if success:
            return {
                "success": True,
                "message": f"Successfully unsubscribed from {module_code}",
                "module_code": module_code
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to unsubscribe from module"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unsubscribe from module error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe from module"
        )