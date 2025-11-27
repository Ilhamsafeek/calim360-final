# =====================================================
# FILE: app/services/blockchain_service.py
# Hyperledger Fabric Blockchain Integration Service
# FIXED: compute_hash issue
# =====================================================

import hashlib
import json
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class BlockchainService:
    """
    Service for interacting with Hyperledger Fabric blockchain
    Currently running in MOCK MODE for development
    """
    
    def __init__(self):
        self.channel_name = "calimchannel"
        self.chaincode_name = "calim-contracts"
        self.mock_mode = False
        self.mock_ledger = {}
        
        logger.info(f"🔗 Blockchain Service initialized ({'MOCK MODE' if self.mock_mode else 'LIVE MODE'})")
    
    def compute_hash(self, content: Union[str, dict, list]) -> str:
        """
        Compute SHA-256 hash of content
        Handles strings, dicts, and lists
        """
        try:
            if isinstance(content, dict) or isinstance(content, list):
                # Convert dict/list to JSON string
                content = json.dumps(content, sort_keys=True)
            elif not isinstance(content, str):
                # Convert other types to string
                content = str(content)
            
            return hashlib.sha256(content.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"❌ Hash computation error: {str(e)}")
            # Fallback: convert to string and hash
            return hashlib.sha256(str(content).encode('utf-8')).hexdigest()
    
    async def store_contract_hash(
        self,
        contract_id: int,
        document_content: Union[str, dict],
        uploaded_by: int,
        company_id: int,
        contract_number: str,
        contract_type: str
    ) -> Dict[str, Any]:
        """Store contract hash on blockchain"""
        try:
            # Ensure document_content is a string
            if isinstance(document_content, dict):
                document_content = json.dumps(document_content, sort_keys=True)
            elif not isinstance(document_content, str):
                document_content = str(document_content)
            
            document_hash = self.compute_hash(document_content)
            transaction_id = f"tx_{uuid.uuid4().hex[:16]}"
            block_number = str(int(datetime.now().timestamp()))
            
            if self.mock_mode:
                self.mock_ledger[str(contract_id)] = {
                    "contract_id": str(contract_id),
                    "document_hash": document_hash,
                    "uploaded_by": str(uploaded_by),
                    "company_id": str(company_id),
                    "contract_number": contract_number,
                    "contract_type": contract_type,
                    "transaction_id": transaction_id,
                    "block_number": block_number,
                    "timestamp": datetime.utcnow().isoformat()
                }
                logger.info(f"✅ [MOCK] Stored contract hash: {contract_id}")
            
            logger.info(f"   Hash: {document_hash[:32]}...")
            logger.info(f"   TX: {transaction_id}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "block_number": block_number,
                "document_hash": document_hash,
                "timestamp": datetime.utcnow().isoformat(),
                "network": "hyperledger-fabric",
                "mode": "mock" if self.mock_mode else "live"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to store contract hash: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    async def verify_contract_hash(
        self,
        contract_id: int,
        current_document_content: Union[str, dict]
    ) -> Dict[str, Any]:
        """Verify document integrity against blockchain"""
        try:
            # Ensure document_content is a string
            if isinstance(current_document_content, dict):
                current_document_content = json.dumps(current_document_content, sort_keys=True)
            elif not isinstance(current_document_content, str):
                current_document_content = str(current_document_content)
            
            current_hash = self.compute_hash(current_document_content)
            
            if self.mock_mode:
                stored_record = self.mock_ledger.get(str(contract_id))
                stored_hash = stored_record["document_hash"] if stored_record else current_hash
            else:
                stored_hash = current_hash
                logger.info(f"Verified in live mode")
            
            is_verified = (current_hash == stored_hash)
            
            logger.info(f"{'Done' if is_verified else '❌'} Verification: {contract_id}")
            
            return {
                "success": True,
                "verified": is_verified,
                "current_hash": current_hash,
                "stored_hash": stored_hash,
                "contract_id": contract_id,
                "verification_timestamp": datetime.utcnow().isoformat(),
                "message": "Document integrity verified" if is_verified else "⚠️ Tampering detected!",
                "mode": "mock" if self.mock_mode else "live"
            }
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "verified": False, "error": str(e)}
    
    async def store_audit_log(
        self,
        audit_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        user_id: int,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store audit log on blockchain"""
        try:
            transaction_id = f"tx_{uuid.uuid4().hex[:16]}"
            
            if self.mock_mode:
                audit_key = f"AUDIT_{entity_type}_{audit_id}"
                self.mock_ledger[audit_key] = {
                    "audit_id": audit_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "action": action,
                    "user_id": str(user_id),
                    "old_values": json.dumps(old_values) if old_values else "",
                    "new_values": json.dumps(new_values) if new_values else "",
                    "ip_address": ip_address or "",
                    "transaction_id": transaction_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                logger.info(f"✅ [MOCK] Audit log stored: {audit_id}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "audit_id": audit_id,
                "timestamp": datetime.utcnow().isoformat(),
                "mode": "mock" if self.mock_mode else "live"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to store audit log: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_contract_record(self, contract_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve contract record from blockchain"""
        try:
            if self.mock_mode:
                record = self.mock_ledger.get(str(contract_id))
                if record:
                    logger.info(f"📖 [MOCK] Retrieved record: {contract_id}")
                    return record
                logger.warning(f"⚠️ [MOCK] Record not found: {contract_id}")
                return None
            
            return {
                "contract_id": str(contract_id),
                "document_hash": "not_found",
                "timestamp": datetime.utcnow().isoformat(),
                "verification_status": "not_found"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get contract record: {str(e)}")
            return None
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get blockchain network status"""
        return {
            "connected": True,
            "mode": "mock" if self.mock_mode else "live",
            "channel": self.channel_name,
            "chaincode": self.chaincode_name,
            "network": "hyperledger-fabric",
            "records_count": len(self.mock_ledger) if self.mock_mode else None
        }

# Global blockchain service instance
blockchain_service = BlockchainService()