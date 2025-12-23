# =====================================================
# FILE: app/api/api_v1/reports/audit_trail.py
# Fixed - Avoiding duplicate model imports
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from typing import Optional, List
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import csv
import logging
import hashlib
import json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

# Import blockchain model only
try:
    from app.models.blockchain_record import BlockchainRecord
except ImportError:
    BlockchainRecord = None

from app.schemas.audit_trail import (
    AuditLogResponse, 
    AuditLogListResponse, 
    AuditStatistics,
    BlockchainVerificationResponse,
    ExportFormat
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports/audit-trail", tags=["reports", "audit-trail"])

# =====================================================
# GET AUDIT LOGS WITH FILTERS
# =====================================================

@router.get("/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (contract, project, etc)"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    entity_id: Optional[str] = Query(None, description="Filter by contract/project ID"),
    search: Optional[str] = Query(None, description="Search in action details"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit logs with comprehensive filtering and pagination
    """
    try:
        # Build raw SQL query to avoid model import issues
        sql = """
            SELECT 
                id, user_id, contract_id, action_type, action_details,
                ip_address, user_agent, created_at
            FROM audit_logs
            WHERE 1=1
        """
        params = {}
        
        # Apply filters
        if start_date:
            sql += " AND created_at >= :start_date"
            params['start_date'] = start_date
        
        if end_date:
            sql += " AND created_at <= :end_date"
            params['end_date'] = end_date
        
        if action_type:
            sql += " AND action_type = :action_type"
            params['action_type'] = action_type
        
        if user_id:
            sql += " AND user_id = :user_id"
            params['user_id'] = user_id
        
        if entity_id:
            # Search in both contract_id and action_details JSON
            sql += " AND (CAST(contract_id AS CHAR) LIKE :entity_search OR action_details LIKE :entity_search)"
            params['entity_search'] = f'%{entity_id}%'
        
        if search:
            sql += " AND (action_type LIKE :search OR action_details LIKE :search)"
            params['search'] = f'%{search}%'
        
        # Get total count
        count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as subquery"
        total = db.execute(text(count_sql), params).scalar()
        
        # Add pagination
        sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = (page - 1) * limit
        
        # Execute query
        result = db.execute(text(sql), params)
        rows = result.fetchall()
        
        # Format response
        audit_logs = []
        for row in rows:
            # Get user info
            user_name = "System"
            if row.user_id:
                user = db.query(User).filter(User.id == row.user_id).first()
                if user:
                    user_name = f"{user.first_name} {user.last_name}"
            
            # Parse action_details
            action_details = {}
            if row.action_details:
                try:
                    action_details = json.loads(row.action_details)
                except:
                    action_details = {"raw": row.action_details}
            
            audit_logs.append({
                "id": row.id,
                "timestamp": row.created_at.isoformat() if row.created_at else None,
                "action_type": row.action_type,
                "action_details": action_details,
                "user_id": row.user_id,
                "user_name": user_name,
                "contract_id": row.contract_id,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "entity_type": action_details.get("entity_type", "unknown"),
                "entity_id": action_details.get("entity_id"),
                "blockchain_verified": False,
                "blockchain_hash": None
            })
        
        logger.info(f" Retrieved {len(audit_logs)} audit logs for user {current_user.email}")
        
        return {
            "success": True,
            "data": audit_logs,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f" Error fetching audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching audit logs: {str(e)}"
        )

# =====================================================
# GET AUDIT STATISTICS
# =====================================================

@router.get("/statistics", response_model=AuditStatistics)
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit trail statistics for the dashboard
    """
    try:
        # Build base query
        sql = "SELECT COUNT(*) as count FROM audit_logs WHERE 1=1"
        params = {}
        
        if start_date:
            sql += " AND created_at >= :start_date"
            params['start_date'] = start_date
        if end_date:
            sql += " AND created_at <= :end_date"
            params['end_date'] = end_date
        
        # Total events
        total_events = db.execute(text(sql), params).scalar()
        
        # Unique users
        user_sql = "SELECT COUNT(DISTINCT user_id) as count FROM audit_logs WHERE user_id IS NOT NULL"
        if start_date:
            user_sql += " AND created_at >= :start_date"
        if end_date:
            user_sql += " AND created_at <= :end_date"
        unique_users = db.execute(text(user_sql), params).scalar()
        
        # Action breakdown
        action_sql = "SELECT action_type, COUNT(*) as count FROM audit_logs WHERE 1=1"
        if start_date:
            action_sql += " AND created_at >= :start_date"
        if end_date:
            action_sql += " AND created_at <= :end_date"
        action_sql += " GROUP BY action_type"
        
        action_result = db.execute(text(action_sql), params)
        action_breakdown = {row.action_type: row.count for row in action_result}
        
        logger.info(f" Retrieved audit statistics for user {current_user.email}")
        
        return {
            "success": True,
            "total_events": total_events or 0,
            "unique_users": unique_users or 0,
            "blockchain_verified": 0,
            "action_breakdown": action_breakdown,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }
        
    except Exception as e:
        logger.error(f" Error fetching statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching statistics: {str(e)}"
        )

# =====================================================
# VERIFY BLOCKCHAIN RECORD
# =====================================================

@router.get("/verify/{log_id}", response_model=BlockchainVerificationResponse)
async def verify_blockchain_record(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verify the blockchain integrity of a specific audit log entry
    """
    try:
        # Query audit log directly with SQL
        sql = "SELECT * FROM audit_logs WHERE id = :log_id"
        result = db.execute(text(sql), {"log_id": log_id})
        log = result.fetchone()
        
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit log not found"
            )
        
        return {
            "success": True,
            "verified": False,
            "message": "Blockchain verification not yet implemented",
            "blockchain_hash": None,
            "verification_timestamp": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Error verifying blockchain record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying blockchain record: {str(e)}"
        )

# =====================================================
# EXPORT AUDIT LOGS
# =====================================================

@router.get("/export")
async def export_audit_logs(
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    action_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export audit logs in CSV or JSON format
    """
    try:
        # Build query
        sql = "SELECT * FROM audit_logs WHERE 1=1"
        params = {}
        
        if start_date:
            sql += " AND created_at >= :start_date"
            params['start_date'] = start_date
        if end_date:
            sql += " AND created_at <= :end_date"
            params['end_date'] = end_date
        if action_type:
            sql += " AND action_type = :action_type"
            params['action_type'] = action_type
        
        sql += " ORDER BY created_at DESC LIMIT 10000"
        
        result = db.execute(text(sql), params)
        logs = result.fetchall()
        
        if format == ExportFormat.CSV:
            # Create CSV
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "ID", "Timestamp", "Action Type", "User ID", "Contract ID", 
                "IP Address", "Details"
            ])
            
            # Write data
            for log in logs:
                writer.writerow([
                    log.id,
                    log.created_at.isoformat() if log.created_at else "",
                    log.action_type,
                    log.user_id,
                    log.contract_id,
                    log.ip_address,
                    log.action_details or ""
                ])
            
            output.seek(0)
            filename = f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
        else:  # JSON format
            audit_data = []
            for log in logs:
                audit_data.append({
                    "id": log.id,
                    "timestamp": log.created_at.isoformat() if log.created_at else None,
                    "action_type": log.action_type,
                    "user_id": log.user_id,
                    "contract_id": log.contract_id,
                    "ip_address": log.ip_address,
                    "action_details": log.action_details
                })
            
            json_data = json.dumps(audit_data, indent=2)
            filename = f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            return StreamingResponse(
                iter([json_data]),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
    except Exception as e:
        logger.error(f" Error exporting audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting audit logs: {str(e)}"
        )

# =====================================================
# GET AVAILABLE ACTION TYPES
# =====================================================

@router.get("/action-types")
async def get_action_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of all available action types for filtering
    """
    try:
        sql = "SELECT DISTINCT action_type FROM audit_logs WHERE action_type IS NOT NULL ORDER BY action_type"
        result = db.execute(text(sql))
        action_types = [row.action_type for row in result]
        
        return {
            "success": True,
            "action_types": action_types
        }
        
    except Exception as e:
        logger.error(f" Error fetching action types: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching action types: {str(e)}"
        )

# =====================================================
# GET USERS FOR FILTER
# =====================================================

@router.get("/users")
async def get_users_for_filter(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of all active users for filtering (not just those with audit logs)
    """
    try:
        sql = """
            SELECT id, first_name, last_name, email
            FROM users
            WHERE is_active = 1
            ORDER BY first_name, last_name
        """
        result = db.execute(text(sql))
        
        users_list = [
            {
                "id": row.id,
                "name": f"{row.first_name} {row.last_name}",
                "email": row.email
            }
            for row in result
        ]
        
        return {
            "success": True,
            "users": users_list
        }
        
    except Exception as e:
        logger.error(f" Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}"
        )