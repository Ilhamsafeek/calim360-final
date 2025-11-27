# =====================================================
# FILE: app/api/api_v1/contracts/service.py
# COMPLETE Contract Service - All Methods Included
# =====================================================

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
from fastapi import HTTPException, status

from app.models.contract import Contract, ContractVersion, ContractTemplate
from app.models.user import User


class ContractService:
    """Contract business logic service"""
    
    # =====================================================
    # CONTRACT NUMBER GENERATION
    # =====================================================
    
    @staticmethod
    def generate_contract_number(db: Session, company_id: int) -> str:
        """Generate unique contract number in format: CNT-YYYY-XXXX"""
        current_year = datetime.now().year
        prefix = f"CNT-{current_year}"
        
        last_contract = db.query(Contract).filter(
            Contract.company_id == company_id,
            Contract.contract_number.like(f"{prefix}%")
        ).order_by(desc(Contract.contract_number)).first()
        
        if last_contract:
            try:
                last_number = int(last_contract.contract_number.split('-')[-1])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
        
        return f"{prefix}-{new_number:04d}"
    
    
    # =====================================================
    # CREATE CONTRACT
    # =====================================================
    
    @staticmethod
    def create_contract(
        db: Session,
        request,
        user_id: int,
        company_id: int
    ) -> Contract:
        """Create a new contract with all required fields"""
        try:
            # Generate contract number
            contract_number = ContractService.generate_contract_number(db, company_id)
            
            # Validate project if provided
            if request.project_id:
                from app.models.project import Project
                project = db.query(Project).filter(
                    Project.id == request.project_id,
                    Project.company_id == company_id
                ).first()
                if not project:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Project not found"
                    )
            
            # Create contract
            new_contract = Contract(
                company_id=company_id,
                project_id=request.project_id,
                contract_number=contract_number,
                contract_title=request.contract_title,
                profile_type=getattr(request, 'profile_type', 'client'),
                template_id=getattr(request, 'template_id', None),
                contract_type=getattr(request, 'contract_type', None),
                contract_value=getattr(request, 'contract_value', None),
                currency=getattr(request, 'currency', 'QAR'),
                effective_date=getattr(request, 'effective_date', None),
                expiry_date=getattr(request, 'expiry_date', None),
                auto_renewal=getattr(request, 'auto_renewal', False),
                status='draft',
                current_version=1,
                confidentiality_level='STANDARD',
                language='en',
                created_by=user_id,
                updated_by=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False
            )
            
            db.add(new_contract)
            db.flush()
            
# Around line 110-135, REPLACE this section:

            # Get template content if creating from template
            initial_content = "<h1>New Contract</h1><p>Contract content will be added...</p>"
            initial_content_ar = None
            
            if request.template_id:
                template = db.query(ContractTemplate).filter(
                    ContractTemplate.id == request.template_id
                ).first()
                if template:
                    # Copy template content to contract ✅
                    initial_content = template.template_content or f"<h1>{template.template_name}</h1><p>Template loaded.</p>"
                    initial_content_ar = template.template_content_ar
            
            # Create initial version WITH CONTENT ✅
            initial_version = ContractVersion(
                contract_id=new_contract.id,
                version_number=1,
                version_type='draft',
                contract_content=initial_content,
                contract_content_ar=initial_content_ar,
                change_summary='Initial contract creation',
                is_major_version=False,
                created_by=user_id,
                created_at=datetime.utcnow()
            )
                        
            db.add(initial_version)
            
            # Log audit trail
            ContractService._log_audit(
                db=db,
                contract_id=new_contract.id,
                user_id=user_id,
                action='contract_created',
                details={
                    'contract_number': contract_number,
                    'template_id': getattr(request, 'template_id', None)
                }
            )
            
            db.commit()
            db.refresh(new_contract)
            
            return new_contract
            
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create contract: {str(e)}"
            )
    
    
    # =====================================================
    # GET CONTRACT
    # =====================================================
    
    @staticmethod
    def get_contract_by_id(
        db: Session,
        contract_id: int,
        company_id: int
    ) -> Optional[Contract]:
        """Get contract by ID with company validation"""
        return db.query(Contract).filter(
            Contract.id == contract_id,
            Contract.company_id == company_id,
            Contract.is_deleted == False
        ).first()
    
    
    # =====================================================
    # LIST CONTRACTS
    # =====================================================
    
    @staticmethod
    def list_contracts(
        db: Session,
        company_id: int,
        status: Optional[str] = None,
        profile_type: Optional[str] = None,
        project_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Contract], int]:
        """List contracts with filters"""
        query = db.query(Contract).filter(
            Contract.company_id == company_id,
            Contract.is_deleted == False
        )
        
        if status:
            query = query.filter(Contract.status == status)
        
        if profile_type:
            query = query.filter(Contract.profile_type == profile_type)
        
        if project_id:
            query = query.filter(Contract.project_id == project_id)
        
        total = query.count()
        contracts = query.order_by(desc(Contract.created_at)).offset(skip).limit(limit).all()
        
        return contracts, total
    
    
    # =====================================================
    # UPDATE CONTRACT
    # =====================================================
    
    @staticmethod
    def update_contract(
        db: Session,
        contract_id: int,
        request,
        user_id: int,
        company_id: int
    ) -> Contract:
        """Update contract details"""
        contract = ContractService.get_contract_by_id(db, contract_id, company_id)
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        # Update fields
        if hasattr(request, 'contract_title') and request.contract_title:
            contract.contract_title = request.contract_title
        
        if hasattr(request, 'status') and request.status:
            contract.status = request.status
        
        contract.updated_by = user_id
        contract.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(contract)
        
        return contract
    
    
    # =====================================================
    # DELETE CONTRACT
    # =====================================================
    
    @staticmethod
    def delete_contract(
        db: Session,
        contract_id: int,
        user_id: int,
        company_id: int
    ):
        """Soft delete a contract"""
        contract = ContractService.get_contract_by_id(db, contract_id, company_id)
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        contract.is_deleted = True
        contract.deleted_at = datetime.utcnow()
        contract.updated_by = user_id
        
        db.commit()
    
    
    # =====================================================
    # CONTRACT LOCKING
    # =====================================================
    
    @staticmethod
    def lock_contract(
        db: Session,
        contract_id: int,
        user_id: int,
        company_id: int
    ) -> Contract:
        """Lock contract for editing"""
        contract = ContractService.get_contract_by_id(db, contract_id, company_id)
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        if contract.is_locked and contract.locked_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Contract is locked by another user"
            )
        
        contract.is_locked = True
        contract.locked_by = user_id
        contract.locked_at = datetime.utcnow()
        
        db.commit()
        db.refresh(contract)
        
        return contract
    
    
    @staticmethod
    def unlock_contract(
        db: Session,
        contract_id: int,
        user_id: int,
        company_id: int
    ) -> Contract:
        """Unlock contract"""
        contract = ContractService.get_contract_by_id(db, contract_id, company_id)
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        contract.is_locked = False
        contract.locked_by = None
        contract.locked_at = None
        
        db.commit()
        db.refresh(contract)
        
        return contract
    
    
    # =====================================================
    # VERSION MANAGEMENT
    # =====================================================
    
    @staticmethod
    def save_contract_version(
        db: Session,
        contract_id: int,
        contract_content: str,
        user_id: int,
        version_type: str = 'draft',
        change_summary: Optional[str] = None
    ) -> ContractVersion:
        """Save a new version of contract content"""
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        # Get next version number
        last_version = db.query(ContractVersion).filter(
            ContractVersion.contract_id == contract_id
        ).order_by(desc(ContractVersion.version_number)).first()
        
        next_version_number = (last_version.version_number + 1) if last_version else 1
        
        # Create new version
        new_version = ContractVersion(
            contract_id=contract_id,
            version_number=next_version_number,
            version_type=version_type,
            contract_content=contract_content,
            change_summary=change_summary,
            created_by=user_id,
            created_at=datetime.utcnow()
        )
        
        db.add(new_version)
        
        # Update contract version
        contract.current_version = next_version_number
        contract.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(new_version)
        
        return new_version
    
    
    @staticmethod
    def get_contract_content(
        db: Session,
        contract_id: int,
        version_number: Optional[int] = None
    ) -> Optional[str]:
        """Get contract content for a specific version"""
        query = db.query(ContractVersion).filter(
            ContractVersion.contract_id == contract_id
        )
        
        if version_number:
            version = query.filter(ContractVersion.version_number == version_number).first()
        else:
            version = query.order_by(desc(ContractVersion.version_number)).first()
        
        return version.contract_content if version else None
    
    
    # =====================================================
    # HELPER METHODS
    # =====================================================
    
    @staticmethod
    def _log_audit(db: Session, contract_id: int, user_id: int, action: str, details: dict):
        """Log audit trail for contract actions"""
        try:
            from app.models.audit import AuditLog
            
            # Use correct field names from AuditLog model
            audit_log = AuditLog(
                user_id=user_id,
                contract_id=contract_id,
                action_type=action,
                action_details=details,
                created_at=datetime.utcnow()
            )
            db.add(audit_log)
        except (ImportError, Exception) as e:
            # Don't fail the main operation if audit logging fails
            print(f"Audit logging skipped: {str(e)}")
    
    
    # =====================================================
    # CLAUSE MANAGEMENT (Stubs)
    # =====================================================
    
    @staticmethod
    def add_clause(db: Session, request, user_id: int):
        """Add clause - stub for now"""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Clause management not yet implemented"
        )
    
    
    @staticmethod
    def get_contract_clauses(db: Session, contract_id: int):
        """Get contract clauses - stub for now"""
        return []
    
    
    @staticmethod
    def update_clause(db: Session, clause_id: int, request, user_id: int):
        """Update clause - stub for now"""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Clause management not yet implemented"
        )
    
    
    @staticmethod
    def delete_clause(db: Session, clause_id: int, user_id: int):
        """Delete clause - stub for now"""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Clause management not yet implemented"
        )