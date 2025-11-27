# =====================================================
# File: app/api/api_v1/companies/companies.py
# Companies API Router - Get companies (clients, contractors, etc.)
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, Company  # Import Company from user.py where it's defined

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/companies", tags=["companies"])

# =====================================================
# GET COMPANIES ENDPOINT
# =====================================================
@router.get("/")
async def get_companies(
    type: Optional[str] = Query(None, description="Filter by company type: client, consultant, contractor, sub_contractor"),
    search: Optional[str] = Query(None, description="Search by company name or CR number"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of companies with filtering options
    """
    try:
        logger.info(f"Fetching companies for user: {current_user.email}, type: {type}")
        
        # Build filters
        filters = []
        
        # Filter by company type
        if type:
            filters.append(Company.company_type == type)
        
        # Filter by active status - ✅ FIXED: Use 'status' column
        if is_active is not None:
            if is_active:
                filters.append(Company.status.in_(['ACTIVE', 'active']))
            else:
                filters.append(Company.status.notin_(['ACTIVE', 'active']))
        
        # Search filter
        if search:
            search_filter = or_(
                Company.company_name.ilike(f"%{search}%"),
                Company.cr_number.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        # Build query
        query = db.query(Company)
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        companies = query.offset(offset).limit(limit).all()
        
        # Convert to dict
        result = []
        for company in companies:
            result.append({
                "id": company.id,
                "company_name": company.company_name,
                "company_name_ar": company.company_name_ar,
                "cr_number": company.cr_number,
                "qid_number": company.qid_number,
                "company_type": company.company_type,
                "industry": company.industry,
                "phone": company.phone,
                "email": company.email,
                "website": company.website,
                "status": company.status,
                "city": company.city,
                "country": company.country
            })
        
        return {
            "success": True,
            "total": total,
            "offset": offset,
            "limit": limit,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error fetching companies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch companies: {str(e)}"
        )

# =====================================================
# GET SINGLE COMPANY ENDPOINT
# =====================================================
@router.get("/{company_id}")
async def get_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific company
    """
    try:
        logger.info(f"Fetching company: {company_id}")
        
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company not found with ID: {company_id}"
            )
        
        return {
            "success": True,
            "data": {
                "id": company.id,
                "company_name": company.company_name,
                "company_name_ar": company.company_name_ar,
                "cr_number": company.cr_number,
                "qid": company.qid,
                "company_type": company.company_type,
                "industry": company.industry,
                "company_size": company.company_size,
                "address": company.address,
                "city": company.city,
                "country": company.country,
                "postal_code": company.postal_code,
                "phone": company.phone,
                "email": company.email,
                "website": company.website,
                "logo_url": company.logo_url,
                "subscription_plan": company.subscription_plan,
                "subscription_status": company.subscription_status,
                "is_active": company.is_active,
                "created_at": company.created_at.isoformat() if company.created_at else None,
                "updated_at": company.updated_at.isoformat() if company.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching company: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch company: {str(e)}"
        )