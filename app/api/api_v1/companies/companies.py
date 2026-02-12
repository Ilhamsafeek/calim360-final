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
        
        # Filter by active status -  FIXED: Use 'status' column
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
from sqlalchemy import text

@router.get("/{company_id}")
async def get_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific company"""
    try:
        query = text("SELECT * FROM companies WHERE id = :company_id")
        result = db.execute(query, {"company_id": company_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Return EVERYTHING as-is
        return dict(result._mapping)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))