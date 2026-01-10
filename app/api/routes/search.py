"""
Global Search API Endpoint - CORRECTED IMPORTS
File: app/api/routes/search.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.core.database import get_db
from app.models.contract import Contract
from app.models.project import Project
from app.models.user import Company, User
from app.core.dependencies import get_current_user
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter()

@router.get("/global-search")
async def global_search(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=10, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Global search across contracts, projects, and parties
    """
    try:
        search_term = f"%{query}%"
        results = {
            "contracts": [],
            "projects": [],
            "parties": [],
            "query": query
        }
        
        # Search Contracts
        contracts = db.query(Contract).filter(
            and_(
                Contract.company_id == current_user.company_id,
                or_(
                    Contract.contract_number.ilike(search_term),
                    Contract.contract_title.ilike(search_term),
                    Contract.contract_type.ilike(search_term),
                    Contract.party_b_name.ilike(search_term),
                    Contract.party_a_name.ilike(search_term)
                )
            )
        ).limit(limit).all()
        
        for contract in contracts:
            results["contracts"].append({
                "id": contract.id,
                "contract_number": contract.contract_number,
                "title": contract.contract_title,
                "type": contract.contract_type,
                "counterparty": contract.party_b_name or contract.party_a_name,
                "value": float(contract.contract_value) if contract.contract_value else None,
                "status": contract.status,
                "url": f"/contract/edit/{contract.id}"
            })
        
        # Search Projects
        projects = db.query(Project).filter(
            and_(
                Project.company_id == current_user.company_id,
                or_(
                    Project.project_code.ilike(search_term),
                    Project.project_name.ilike(search_term),
                    Project.project_type.ilike(search_term),
                    Project.description.ilike(search_term)
                )
            )
        ).limit(limit).all()
        
        for project in projects:
            results["projects"].append({
                "id": project.id,
                "project_code": project.project_code,
                "name": project.project_name,
                "type": project.project_type,
                "value": float(project.project_value) if project.project_value else None,
                "status": project.status,
                "url": "/projects/",
                # "url": f"/projects/{project.id}"
            })
        
        # Search Parties (Companies)
        parties = db.query(Company).filter(
            and_(
                Company.id != current_user.company_id,
                or_(
                    Company.company_name.ilike(search_term),
                    Company.cr_number.ilike(search_term),
                    Company.email.ilike(search_term)
                )
            )
        ).limit(limit).all()
        
        for party in parties:
            results["parties"].append({
                "id": party.id,
                "name": party.company_name,
                "cr_number": party.cr_number,
                "type": party.company_type,
                "email": party.email,
                "url": "#"
            })
        
        # Add total count
        results["total"] = (
            len(results["contracts"]) + 
            len(results["projects"]) + 
            len(results["parties"])
        )
        
        return results
        
    except Exception as e:
        print(f"❌ Error in global_search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/quick-search")
async def quick_search(
    query: str = Query(..., min_length=1),
    type: str = Query(default="all"),  # all, contracts, projects, parties
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Quick search with type filter
    """
    try:
        search_term = f"%{query}%"
        results = []
        
        if type in ["all", "contracts"]:
            contracts = db.query(Contract).filter(
                and_(
                    Contract.company_id == current_user.company_id,
                    or_(
                        Contract.contract_number.ilike(search_term),
                        Contract.contract_title.ilike(search_term)
                    )
                )
            ).limit(5).all()
            
            for c in contracts:
                results.append({
                    "type": "contract",
                    "id": c.id,
                    "title": c.contract_title,
                    "subtitle": c.contract_number,
                    "icon": "file-text",
                    "url": f"/contract/edit/{c.id}"
                })
        
        if type in ["all", "projects"]:
            projects = db.query(Project).filter(
                and_(
                    Project.company_id == current_user.company_id,
                    or_(
                        Project.project_code.ilike(search_term),
                        Project.project_name.ilike(search_term)
                    )
                )
            ).limit(5).all()
            
            for p in projects:
                results.append({
                    "type": "project",
                    "id": p.id,
                    "title": p.project_name,
                    "subtitle": p.project_code,
                    "icon": "folder",
                    "url": f"/projects/{p.id}"
                })
        
        if type in ["all", "parties"]:
            parties = db.query(Company).filter(
                and_(
                    Company.id != current_user.company_id,
                    Company.company_name.ilike(search_term)
                )
            ).limit(5).all()
            
            for party in parties:
                results.append({
                    "type": "party",
                    "id": party.id,
                    "title": party.company_name,
                    "subtitle": party.cr_number or party.company_type,
                    "icon": "building",
                    "url": f"/parties/{party.id}"
                })
        
        return {
            "results": results,
            "count": len(results),
            "query": query
        }
        
    except Exception as e:
        print(f"❌ Error in quick_search: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )