# =====================================================
# FILE: app/api/api_v1/blockchain/router.py
# Blockchain API Routes - FIXED IMPORT
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
import uuid
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.blockchain import BlockchainRecord, DocumentIntegrity
from app.services.blockchain_service import blockchain_service  # IMPORT AT TOP
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/blockchain", tags=["blockchain"])

# =====================================================
# SCHEMAS
# =====================================================

class StoreContractHashRequest(BaseModel):
    contract_id: int
    document_content: str
    contract_number: str
    contract_type: str

class VerifyContractHashRequest(BaseModel):
    contract_id: int
    document_content: str

# =====================================================
# ENDPOINTS
# =====================================================

@router.post("/store-contract-hash")
async def store_contract_hash(
    request: StoreContractHashRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Store contract hash on blockchain"""
    try:
        result = await blockchain_service.store_contract_hash(
            contract_id=request.contract_id,
            document_content=request.document_content,
            uploaded_by=current_user.id,
            company_id=current_user.company_id,
            contract_number=request.contract_number,
            contract_type=request.contract_type
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store hash on blockchain"
            )
        
        # Store in database
        blockchain_record = BlockchainRecord(
            id=str(uuid.uuid4()),
            entity_type="contract",
            entity_id=str(request.contract_id),
            transaction_hash=result["transaction_id"],
            block_number=result["block_number"],
            blockchain_network="hyperledger-fabric",
            status="confirmed",
            created_at=datetime.utcnow()
        )
        db.add(blockchain_record)
        
        integrity_record = DocumentIntegrity(
            id=str(uuid.uuid4()),
            document_id=str(request.contract_id),
            hash_algorithm="SHA-256",
            document_hash=result["document_hash"],
            blockchain_hash=result["transaction_id"],
            verification_status="verified",
            last_verified_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        db.add(integrity_record)
        
        db.commit()
        
        logger.info(f"✅ Contract hash stored: {request.contract_id}")
        
        return {
            "success": True,
            "message": "Contract hash stored on blockchain",
            "transaction_id": result["transaction_id"],
            "block_number": result["block_number"],
            "document_hash": result["document_hash"]
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error storing contract hash: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/verify-contract-hash")
async def verify_contract_hash(
    request: VerifyContractHashRequest,
    db: Session = Depends(get_db)
):
    """Verify contract hash against blockchain"""
    try:
        # First, check if record exists in database
        integrity_record = db.query(DocumentIntegrity).filter(
            DocumentIntegrity.document_id == str(request.contract_id)
        ).first()
        
        # If no record exists, create one first
        if not integrity_record:
            logger.info(f"📝 Creating initial record for contract {request.contract_id}")
            
            # Store on blockchain first
            store_result = await blockchain_service.store_contract_hash(
                contract_id=request.contract_id,
                document_content=request.document_content,
                uploaded_by=1,  # System user
                company_id=1,
                contract_number=f"CNT-{request.contract_id}",
                contract_type="unknown"
            )
            
            if store_result.get("success"):
                # Create database records
                blockchain_record = BlockchainRecord(
                    id=str(uuid.uuid4()),
                    entity_type="contract",
                    entity_id=str(request.contract_id),
                    transaction_hash=store_result["transaction_id"],
                    block_number=store_result["block_number"],
                    blockchain_network="hyperledger-fabric",
                    status="confirmed",
                    created_at=datetime.utcnow()
                )
                db.add(blockchain_record)
                
                integrity_record = DocumentIntegrity(
                    id=str(uuid.uuid4()),
                    document_id=str(request.contract_id),
                    hash_algorithm="SHA-256",
                    document_hash=store_result["document_hash"],
                    blockchain_hash=store_result["transaction_id"],
                    verification_status="verified",
                    last_verified_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                db.add(integrity_record)
                db.commit()
        
        # Now verify
        result = await blockchain_service.verify_contract_hash(
            contract_id=request.contract_id,
            current_document_content=request.document_content
        )
        
        # Update verification status
        if integrity_record:
            integrity_record.verification_status = "verified" if result["verified"] else "tampered"
            integrity_record.last_verified_at = datetime.utcnow()
            db.commit()
        
        logger.info(f"✅ Contract verification: {request.contract_id}")
        
        return {
            "success": True,
            "verified": result["verified"],
            "message": result["message"],
            "current_hash": result["current_hash"],
            "stored_hash": result["stored_hash"],
            "verification_timestamp": result["verification_timestamp"]
        }
        
    except Exception as e:
        logger.error(f"❌ Verification error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "verified": False,
            "message": str(e)
        }

@router.get("/contract-record/{contract_id}")
async def get_contract_record(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """Get contract blockchain record"""
    try:
        logger.info(f"📖 Getting record for contract {contract_id}")
        
        blockchain_record = db.query(BlockchainRecord).filter(
            BlockchainRecord.entity_type == "contract",
            BlockchainRecord.entity_id == str(contract_id)
        ).first()
        
        integrity_record = db.query(DocumentIntegrity).filter(
            DocumentIntegrity.document_id == str(contract_id)
        ).first()
        
        # If no records found, try to get from blockchain service
        if not blockchain_record and not integrity_record:
            logger.warning(f"⚠️ No database record found for contract {contract_id}")
            
            # Check blockchain mock ledger
            blockchain_data = await blockchain_service.get_contract_record(contract_id)
            
            if blockchain_data:
                # Return data from blockchain mock ledger
                return {
                    "success": True,
                    "blockchain_record": {
                        "transaction_hash": blockchain_data.get("transaction_id", "N/A"),
                        "block_number": blockchain_data.get("block_number", "N/A"),
                        "network": "hyperledger-fabric",
                        "status": "confirmed",
                        "created_at": blockchain_data.get("timestamp", datetime.utcnow().isoformat())
                    },
                    "integrity_record": {
                        "document_hash": blockchain_data.get("document_hash", "N/A"),
                        "verification_status": "verified",
                        "last_verified_at": datetime.utcnow().isoformat()
                    },
                    "mode": "mock",
                    "source": "blockchain_memory"
                }
            
            # No record found anywhere
            return {
                "success": False,
                "message": "Blockchain record not found. Please save the contract first.",
                "blockchain_record": None,
                "integrity_record": None
            }
        
        # Return database records
        return {
            "success": True,
            "blockchain_record": {
                "transaction_hash": blockchain_record.transaction_hash if blockchain_record else "N/A",
                "block_number": blockchain_record.block_number if blockchain_record else "N/A",
                "network": blockchain_record.blockchain_network if blockchain_record else "hyperledger-fabric",
                "status": blockchain_record.status if blockchain_record else "N/A",
                "created_at": blockchain_record.created_at.isoformat() if blockchain_record else None
            },
            "integrity_record": {
                "document_hash": integrity_record.document_hash if integrity_record else "N/A",
                "verification_status": integrity_record.verification_status if integrity_record else "N/A",
                "last_verified_at": integrity_record.last_verified_at.isoformat() if integrity_record and integrity_record.last_verified_at else None
            },
            "mode": "database",
            "source": "mysql_database"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting record: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": str(e),
            "blockchain_record": None,
            "integrity_record": None
        }

@router.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok", 
        "service": "blockchain",
        "network_status": blockchain_service.get_network_status()
    }
