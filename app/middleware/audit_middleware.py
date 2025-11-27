# =====================================================
# FILE: app/middleware/audit_middleware.py
# Middleware for Automatic Audit Logging (Using Raw SQL)
# =====================================================

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy import text
import time
import logging
import json
from typing import Callable
from datetime import datetime

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log API requests to audit trail
    """
    
    # Endpoints to exclude from logging
    EXCLUDED_ENDPOINTS = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/static/",
        "/api/reports/audit-trail/"  # Don't log audit trail queries
    ]
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request and log to audit trail
        """
        start_time = time.time()
        
        # Check if endpoint should be logged
        should_log = self._should_log_request(request)
        
        # Process request
        response = await call_next(request)
        
        # Log to audit trail if needed
        if should_log and response.status_code < 400:
            try:
                await self._log_request(request, response, start_time)
            except Exception as e:
                logger.error(f"❌ Failed to log audit trail: {str(e)}")
        
        return response
    
    def _should_log_request(self, request: Request) -> bool:
        """
        Determine if request should be logged
        """
        path = request.url.path
        method = request.method
        
        # Exclude certain endpoints
        for excluded in self.EXCLUDED_ENDPOINTS:
            if path.startswith(excluded):
                return False
        
        # Log POST, PUT, PATCH, DELETE by default
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return True
        
        return False
    
    async def _log_request(self, request: Request, response, start_time: float):
        """
        Log request to audit trail using raw SQL
        """
        try:
            # Create database session
            db = SessionLocal()
            
            try:
                # Extract user ID from request state
                user_id = None
                if hasattr(request.state, "user"):
                    user_id = request.state.user.id
                
                # Determine action type
                action_type = self._get_action_type(request)
                
                # Extract entity information
                entity_type, entity_id = self._extract_entity_info(request)
                
                # Get IP address
                ip_address = self._get_client_ip(request)
                
                # Get user agent
                user_agent = request.headers.get("user-agent", "")
                
                # Prepare action details
                action_details = {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "status_code": response.status_code,
                    "response_time_ms": round((time.time() - start_time) * 1000, 2),
                    "entity_type": entity_type,
                    "entity_id": entity_id
                }
                
                # Insert log using raw SQL
                sql = """
                    INSERT INTO audit_logs 
                    (user_id, action_type, action_details, ip_address, user_agent, created_at)
                    VALUES (:user_id, :action_type, :action_details, :ip_address, :user_agent, :created_at)
                """
                
                db.execute(text(sql), {
                    'user_id': user_id,
                    'action_type': action_type,
                    'action_details': json.dumps(action_details),
                    'ip_address': ip_address,
                    'user_agent': user_agent[:500] if user_agent else None,  # Limit length
                    'created_at': datetime.utcnow()
                })
                
                db.commit()
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error in audit logging: {str(e)}")
    
    def _get_action_type(self, request: Request) -> str:
        """
        Determine action type from request method and path
        """
        method = request.method
        path = request.url.path.lower()
        
        # Map common patterns to action types
        if "create" in path or method == "POST":
            return "create"
        elif "update" in path or "edit" in path or method in ["PUT", "PATCH"]:
            return "update"
        elif "delete" in path or "remove" in path or method == "DELETE":
            return "delete"
        elif "approve" in path:
            return "approve"
        elif "reject" in path:
            return "reject"
        elif "sign" in path:
            return "sign"
        elif "upload" in path:
            return "upload"
        elif "download" in path or "export" in path:
            return "download"
        elif method == "GET":
            return "view"
        else:
            return "access"
    
    def _extract_entity_info(self, request: Request) -> tuple:
        """
        Extract entity type and ID from request path
        """
        path = request.url.path
        parts = path.split("/")
        
        # Common patterns
        entity_type = "unknown"
        entity_id = None
        
        if "contracts" in path:
            entity_type = "contract"
        elif "documents" in path:
            entity_type = "document"
        elif "projects" in path:
            entity_type = "project"
        elif "workflow" in path:
            entity_type = "workflow"
        elif "obligations" in path:
            entity_type = "obligation"
        elif "users" in path:
            entity_type = "user"
        
        # Try to extract ID
        for i, part in enumerate(parts):
            if part.isdigit() and i > 0:
                entity_id = part
                break
        
        return entity_type, entity_id
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request
        """
        # Check for forwarded IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"