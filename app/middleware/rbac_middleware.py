# =====================================================
# FILE: app/middleware/rbac_middleware.py
# Role-Based Access Control Middleware
# =====================================================

from functools import wraps
from typing import List, Union
from fastapi import HTTPException, status, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.core.database import get_db
from app.core.permissions import Permission, has_permission
from app.core.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)


def get_user_roles(db: Session, user_id: int) -> List[str]:
    """Fetch user roles from database"""
    try:
        query = text("""
            SELECT r.role_name 
            FROM roles r
            JOIN user_roles ur ON r.id = ur.role_id
            WHERE ur.user_id = :user_id
            AND r.is_active = 1
        """)
        result = db.execute(query, {"user_id": user_id})
        roles = [row.role_name for row in result]
        
        # Also check user_role column in users table as fallback
        if not roles:
            user_query = text("SELECT user_role FROM users WHERE id = :user_id")
            user_result = db.execute(user_query, {"user_id": user_id}).first()
            if user_result and user_result.user_role:
                roles = [user_result.user_role]
        
        return roles if roles else ["Viewer"]  # Default to Viewer
        
    except Exception as e:
        logger.error(f"Error fetching user roles: {e}")
        return ["Viewer"]


def require_permission(*permissions: Permission):
    """
    Decorator to require specific permissions for an endpoint
    Usage: @require_permission(Permission.CONTRACT_CREATE)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies
            request: Request = kwargs.get('request')
            db: Session = kwargs.get('db')
            current_user: User = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get user roles
            user_roles = get_user_roles(db, current_user.id)
            
            # Super Admin bypasses all checks
            if "Super Admin" in user_roles:
                return await func(*args, **kwargs)
            
            # Check if user has any of the required permissions
            has_required = any(
                has_permission(user_roles, perm) 
                for perm in permissions
            )
            
            if not has_required:
                logger.warning(
                    f"Access denied for user {current_user.id} "
                    f"to {func.__name__}. Required: {permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {[p.value for p in permissions]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: str):
    """
    Decorator to require specific roles for an endpoint
    Usage: @require_role("Super Admin", "Company Admin")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get('request')
            db: Session = kwargs.get('db')
            current_user: User = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_roles = get_user_roles(db, current_user.id)
            
            # Check if user has any required role
            if not any(role in user_roles for role in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {roles}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_company_access(func):
    """
    Decorator to ensure user can only access their company's data
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user: User = kwargs.get('current_user')
        db: Session = kwargs.get('db')
        
        user_roles = get_user_roles(db, current_user.id)
        
        # Super Admin can access all companies
        if "Super Admin" in user_roles:
            return await func(*args, **kwargs)
        
        # For other users, inject company filter
        kwargs['_company_filter'] = current_user.company_id
        return await func(*args, **kwargs)
    
    return wrapper


class RBACDependency:
    """
    Dependency class for RBAC checks in FastAPI
    Usage: Depends(RBACDependency(Permission.CONTRACT_CREATE))
    """
    def __init__(self, *permissions: Permission):
        self.permissions = permissions
    
    async def __call__(
        self,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> User:
        user_roles = get_user_roles(db, current_user.id)
        
        # Super Admin bypass
        if "Super Admin" in user_roles:
            return current_user
        
        # Check permissions
        has_required = any(
            has_permission(user_roles, perm) 
            for perm in self.permissions
        )
        
        if not has_required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user