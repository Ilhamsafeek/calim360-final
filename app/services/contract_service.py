# =====================================================
# FILE: app/services/contract_service.py
# Contract Service - Enhanced with Database Integration
# =====================================================

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid
import json

from app.models.contract import Contract, ContractTemplate, ContractVersion
from app.models.user import User, Company

class ContractService:
    """Contract business logic and utilities"""
    
    @staticmethod
    def generate_contract_number(
        db: Session, 
        company_id: int, 
        contract_type: str = "GENERAL"
    ) -> str:
        """Generate unique contract number based on company and type"""
        try:
            # Get company details
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError("Company not found")
            
            # Get current year
            current_year = datetime.now().year
            
            # Create prefix from company name and type
            company_prefix = ''.join([c for c in company.company_name if c.isalpha()])[:3].upper()
            type_prefix = contract_type[:3].upper()
            
            # Get next sequence number for this year and company
            last_contract = db.query(Contract).filter(
                Contract.company_id == company_id,
                Contract.contract_number.like(f"{company_prefix}-{type_prefix}-{current_year}-%")
            ).order_by(desc(Contract.created_at)).first()
            
            if last_contract and last_contract.contract_number:
                # Extract sequence number from last contract
                parts = last_contract.contract_number.split('-')
                if len(parts) >= 4:
                    try:
                        last_seq = int(parts[-1])
                        next_seq = last_seq + 1
                    except ValueError:
                        next_seq = 1
                else:
                    next_seq = 1
            else:
                next_seq = 1
            
            # Format: COMP-TYPE-YYYY-NNNN
            contract_number = f"{company_prefix}-{type_prefix}-{current_year}-{next_seq:04d}"
            
            return contract_number
            
        except Exception as e:
            # Fallback to UUID-based number
            return f"CNT-{str(uuid.uuid4())[:8].upper()}"
    
    @staticmethod
    def get_contract_templates(
        db: Session,
        company_id: Optional[int] = None,
        profile_type: Optional[str] = None,
        category: Optional[str] = None,
        include_system: bool = True
    ) -> List[ContractTemplate]:
        """Get available contract templates"""
        query = db.query(ContractTemplate).filter(
            ContractTemplate.is_active == True
        )
        
        if company_id:
            # Include company-specific and system templates
            if include_system:
                query = query.filter(
                    or_(
                        ContractTemplate.company_id == company_id,
                        ContractTemplate.company_id.is_(None)  # System templates
                    )
                )
            else:
                query = query.filter(ContractTemplate.company_id == company_id)
        
        if profile_type:
            query = query.filter(ContractTemplate.template_category == profile_type)
        
        if category:
            query = query.filter(ContractTemplate.template_type == category)
        
        return query.order_by(ContractTemplate.template_name).all()
    
    @staticmethod
    def create_contract_from_template(
        db: Session,
        template_id: int,
        contract_data: Dict[str, Any],
        user_id: int,
        ai_content: Optional[Dict[str, Any]] = None
    ) -> Contract:
        """Create a new contract from template"""
        try:
            # Get template
            template = db.query(ContractTemplate).filter(
                ContractTemplate.id == template_id,
                ContractTemplate.is_active == True
            ).first()
            
            if not template:
                raise ValueError("Template not found or inactive")
            
            # Get user for company context
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Generate contract number
            contract_number = ContractService.generate_contract_number(
                db, user.company_id, contract_data.get('contract_type', template.template_type)
            )
            
            # Create contract
            new_contract = Contract(
                company_id=user.company_id,
                contract_number=contract_number,
                contract_title=contract_data.get('contract_title', f"{template.template_name} - {contract_number}"),
                contract_type=template.template_type,
                contract_category=template.template_category,
                template_id=template_id,
                profile_type=contract_data.get('profile_type', 'client'),
                contract_value=contract_data.get('contract_value'),
                currency=contract_data.get('currency', 'QAR'),
                start_date=contract_data.get('start_date'),
                end_date=contract_data.get('end_date'),
                effective_date=contract_data.get('effective_date'),
                auto_renewal=contract_data.get('auto_renewal', False),
                renewal_period_months=contract_data.get('renewal_period_months'),
                renewal_notice_days=contract_data.get('renewal_notice_days'),
                status='draft',
                workflow_status='created',
                current_version=1,
                tags=contract_data.get('tags'),
                metadata=contract_data.get('metadata'),
                created_by=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_contract)
            db.flush()  # Get the ID without committing
            
            # Create initial version
            initial_content = ai_content.get('content') if ai_content else template.template_content
            
            initial_version = ContractVersion(
                contract_id=new_contract.id,
                version_number=1,
                version_type='draft',
                contract_content=initial_content,
                contract_content_ar=ai_content.get('content_ar') if ai_content else template.template_content_ar,
                change_summary="Initial contract creation from template",
                is_major_version=True,
                created_by=user_id,
                created_at=datetime.utcnow()
            )
            
            db.add(initial_version)
            
            return new_contract
            
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create contract from template: {str(e)}")
    
    @staticmethod
    def get_user_contracts(
        db: Session,
        user_id: int,
        status_filter: Optional[str] = None,
        profile_filter: Optional[str] = None,
        search_term: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get contracts for a user with filtering and pagination"""
        
        # Get user and company
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Base query for user's company contracts
        query = db.query(Contract).filter(
            Contract.company_id == user.company_id,
            Contract.is_deleted != True
        )
        
        # Apply filters
        if status_filter:
            query = query.filter(Contract.status == status_filter)
        
        if profile_filter:
            query = query.filter(Contract.profile_type == profile_filter)
        
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                or_(
                    Contract.contract_title.ilike(search_pattern),
                    Contract.contract_number.ilike(search_pattern),
                    Contract.description.ilike(search_pattern)
                )
            )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and get results
        contracts = query.order_by(desc(Contract.created_at)).offset(offset).limit(limit).all()
        
        return {
            "contracts": contracts,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
    
    @staticmethod
    def get_contract_statistics(db: Session, company_id: int) -> Dict[str, Any]:
        """Get contract statistics for dashboard"""
        try:
            # Base query for company contracts
            base_query = db.query(Contract).filter(
                Contract.company_id == company_id,
                Contract.is_deleted != True
            )
            
            # Total contracts
            total_contracts = base_query.count()
            
            # Status breakdown
            status_stats = db.query(
                Contract.status,
                func.count(Contract.id).label('count')
            ).filter(
                Contract.company_id == company_id,
                Contract.is_deleted != True
            ).group_by(Contract.status).all()
            
            # Profile type breakdown
            profile_stats = db.query(
                Contract.profile_type,
                func.count(Contract.id).label('count')
            ).filter(
                Contract.company_id == company_id,
                Contract.is_deleted != True
            ).group_by(Contract.profile_type).all()
            
            # Recent contracts (last 30 days)
            from datetime import timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_contracts = base_query.filter(
                Contract.created_at >= thirty_days_ago
            ).count()
            
            # Contracts by value ranges
            value_ranges = [
                ("0-10K", 0, 10000),
                ("10K-100K", 10001, 100000),
                ("100K-1M", 100001, 1000000),
                ("1M+", 1000001, None)
            ]
            
            value_stats = []
            for range_name, min_val, max_val in value_ranges:
                query = base_query.filter(Contract.contract_value >= min_val)
                if max_val:
                    query = query.filter(Contract.contract_value <= max_val)
                count = query.count()
                value_stats.append({"range": range_name, "count": count})
            
            return {
                "total_contracts": total_contracts,
                "recent_contracts": recent_contracts,
                "status_breakdown": [{"status": s.status, "count": s.count} for s in status_stats],
                "profile_breakdown": [{"profile": p.profile_type, "count": p.count} for p in profile_stats],
                "value_breakdown": value_stats,
                "calculated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Failed to get contract statistics: {str(e)}")
    
    @staticmethod
    def validate_contract_data(contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contract data before creation"""
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['contract_title', 'profile_type']
        for field in required_fields:
            if not contract_data.get(field):
                errors.append(f"{field} is required")
        
        # Date validations
        start_date = contract_data.get('start_date')
        end_date = contract_data.get('end_date')
        
        if start_date and end_date:
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            if start_date >= end_date:
                errors.append("End date must be after start date")
        
        # Contract value validation
        contract_value = contract_data.get('contract_value')
        if contract_value is not None:
            try:
                float(contract_value)
                if float(contract_value) < 0:
                    errors.append("Contract value cannot be negative")
            except (ValueError, TypeError):
                errors.append("Contract value must be a valid number")
        
        # Profile type validation
        valid_profiles = ['client', 'consultant', 'contractor', 'sub_contractor']
        if contract_data.get('profile_type') not in valid_profiles:
            errors.append(f"Profile type must be one of: {', '.join(valid_profiles)}")
        
        # Currency validation
        valid_currencies = ['QAR', 'USD', 'EUR', 'GBP', 'AED', 'SAR']
        currency = contract_data.get('currency', 'QAR')
        if currency not in valid_currencies:
            warnings.append(f"Currency {currency} may not be commonly used. Supported: {', '.join(valid_currencies)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @staticmethod
    def search_contracts(
        db: Session,
        company_id: int,
        search_params: Dict[str, Any]
    ) -> List[Contract]:
        """Advanced contract search"""
        
        query = db.query(Contract).filter(
            Contract.company_id == company_id,
            Contract.is_deleted != True
        )
        
        # Text search
        if search_params.get('text'):
            text_pattern = f"%{search_params['text']}%"
            query = query.filter(
                or_(
                    Contract.contract_title.ilike(text_pattern),
                    Contract.contract_number.ilike(text_pattern),
                    Contract.description.ilike(text_pattern),
                    Contract.contract_type.ilike(text_pattern)
                )
            )
        
        # Status filter
        if search_params.get('status'):
            if isinstance(search_params['status'], list):
                query = query.filter(Contract.status.in_(search_params['status']))
            else:
                query = query.filter(Contract.status == search_params['status'])
        
        # Date range filters
        if search_params.get('created_after'):
            query = query.filter(Contract.created_at >= search_params['created_after'])
        
        if search_params.get('created_before'):
            query = query.filter(Contract.created_at <= search_params['created_before'])
        
        # Value range filters
        if search_params.get('min_value'):
            query = query.filter(Contract.contract_value >= search_params['min_value'])
        
        if search_params.get('max_value'):
            query = query.filter(Contract.contract_value <= search_params['max_value'])
        
        # Profile type filter
        if search_params.get('profile_type'):
            query = query.filter(Contract.profile_type == search_params['profile_type'])
        
        # Contract type filter
        if search_params.get('contract_type'):
            query = query.filter(Contract.contract_type == search_params['contract_type'])
        
        # Sort by
        sort_by = search_params.get('sort_by', 'created_at')
        sort_order = search_params.get('sort_order', 'desc')
        
        if hasattr(Contract, sort_by):
            order_field = getattr(Contract, sort_by)
            if sort_order.lower() == 'asc':
                query = query.order_by(order_field.asc())
            else:
                query = query.order_by(order_field.desc())
        
        # Pagination
        limit = search_params.get('limit', 50)
        offset = search_params.get('offset', 0)
        
        return query.offset(offset).limit(limit).all()