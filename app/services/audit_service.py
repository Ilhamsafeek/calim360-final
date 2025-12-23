# =====================================================
# FILE: app/services/audit_service.py
# Service Layer for Audit Trail (Using Raw SQL)
# =====================================================

from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib
import json
import logging
import uuid

logger = logging.getLogger(__name__)

class AuditService:
    """
    Service for creating and managing audit logs using raw SQL
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_action(
        self,
        action_type: str,
        user_id: Optional[int] = None,
        contract_id: Optional[int] = None,
        action_details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        create_blockchain_record: bool = False
    ) -> int:
        """
        Create an audit log entry
        
        Returns:
            ID of created audit log
        """
        try:
            # Prepare action details
            if action_details is None:
                action_details = {}
            
            # Add entity info to action details
            if entity_type:
                action_details["entity_type"] = entity_type
            if entity_id:
                action_details["entity_id"] = entity_id
            
            # Insert audit log using raw SQL
            sql = """
                INSERT INTO audit_logs 
                (user_id, contract_id, action_type, action_details, ip_address, user_agent, created_at)
                VALUES (:user_id, :contract_id, :action_type, :action_details, :ip_address, :user_agent, :created_at)
            """
            
            params = {
                'user_id': user_id,
                'contract_id': contract_id,
                'action_type': action_type,
                'action_details': json.dumps(action_details),
                'ip_address': ip_address,
                'user_agent': user_agent,
                'created_at': datetime.utcnow()
            }
            
            result = self.db.execute(text(sql), params)
            self.db.commit()
            
            # Get the inserted ID
            log_id = result.lastrowid
            
            logger.info(f" Audit log created: {action_type} by user {user_id}")
            return log_id
            
        except Exception as e:
            self.db.rollback()
            logger.error(f" Error creating audit log: {str(e)}")
            raise

# =====================================================
# CONVENIENCE FUNCTIONS FOR COMMON ACTIONS
# =====================================================

def log_contract_action(
    db: Session,
    action_type: str,
    contract_id: int,
    user_id: Optional[int],
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> int:
    """Convenience function to log contract-related actions"""
    service = AuditService(db)
    return service.log_action(
        action_type=action_type,
        user_id=user_id,
        contract_id=contract_id,
        action_details=details,
        ip_address=ip_address,
        entity_type="contract",
        entity_id=str(contract_id)
    )

def log_user_action(
    db: Session,
    action_type: str,
    user_id: int,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> int:
    """Convenience function to log user-related actions"""
    service = AuditService(db)
    return service.log_action(
        action_type=action_type,
        user_id=user_id,
        action_details=details,
        ip_address=ip_address,
        entity_type="user",
        entity_id=str(user_id)
    )

def log_system_action(
    db: Session,
    action_type: str,
    details: Optional[Dict[str, Any]] = None
) -> int:
    """Convenience function to log system-level actions"""
    service = AuditService(db)
    return service.log_action(
        action_type=action_type,
        action_details=details,
        entity_type="system",
        entity_id="system"
    )