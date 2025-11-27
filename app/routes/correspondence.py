# =====================================================
# FILE: app/routes/correspondence.py (FIXED)
# Fix for contract_content column error
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any
import json
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/correspondence", tags=["correspondence"])
ai_service = AIService()

@router.post("/analyze/{doc_id}")
async def analyze_correspondence(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze correspondence against contract using AI
    FIXED: Query contract_versions table for content instead of contracts table
    """
    try:
        # FIXED QUERY: Join with contract_versions to get contract_content
        query = text("""
            SELECT 
                d.id,
                d.document_name,
                d.document_type,
                d.file_path,
                d.uploaded_at,
                c.id as contract_id,
                c.contract_title,
                c.contract_type,
                c.contract_number,
                c.status as contract_status,
                c.current_version,
                cv.contract_content,
                cv.contract_content_ar,
                cv.version_number,
                cv.change_summary
            FROM documents d
            LEFT JOIN contracts c ON d.contract_id = c.id
            LEFT JOIN contract_versions cv ON c.id = cv.contract_id 
                AND cv.version_number = c.current_version
            WHERE d.id = :doc_id 
                AND c.company_id = :company_id
                AND d.is_deleted = 0
        """)
        
        result = db.execute(
            query, 
            {"doc_id": doc_id, "company_id": current_user.company_id}
        ).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or not associated with a contract"
            )
        
        # Read document content
        try:
            with open(result.file_path, 'r', encoding='utf-8') as f:
                correspondence_content = f.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read document file: {str(e)}"
            )
        
        # Prepare analysis prompt
        contract_content = result.contract_content or ""
        
        analysis_prompt = f"""
You are a legal contract expert. Analyze this correspondence against the contract.

CONTRACT DETAILS:
- Title: {result.contract_title}
- Type: {result.contract_type}
- Number: {result.contract_number}
- Version: {result.version_number}

CONTRACT CONTENT:
{contract_content[:5000]}  # Limit to prevent token overflow

CORRESPONDENCE TO ANALYZE:
{correspondence_content[:3000]}

Please provide a structured analysis in JSON format with:
{{
    "summary": "Brief summary of the correspondence",
    "correspondence_type": "Type (e.g., Notice, Request, Response, Claim)",
    "key_points": ["List of key points"],
    "contract_references": ["Referenced contract clauses/sections"],
    "obligations_mentioned": ["Any obligations mentioned"],
    "action_required": "What action is needed",
    "urgency": "Low/Medium/High",
    "risk_assessment": {{
        "level": "Low/Medium/High",
        "factors": ["Risk factors identified"]
    }},
    "recommendations": ["Recommended actions"],
    "deadline": "Any deadline mentioned (YYYY-MM-DD or null)",
    "compliance_status": "Compliant/Non-compliant/Unclear"
}}
"""
        
        # Get AI analysis
        ai_response = await ai_service.analyze_text(analysis_prompt)
        
        # Parse AI response
        try:
            # Try to extract JSON from response
            response_text = ai_response.get('analysis', '') or ai_response.get('result', '')
            
            # Handle markdown code blocks
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback to structured response if JSON parsing fails
            analysis_data = {
                "summary": response_text[:500],
                "correspondence_type": "Unknown",
                "key_points": [],
                "contract_references": [],
                "obligations_mentioned": [],
                "action_required": "Manual review required",
                "urgency": "Medium",
                "risk_assessment": {
                    "level": "Medium",
                    "factors": ["Unable to parse AI response"]
                },
                "recommendations": ["Manual review by legal team"],
                "deadline": None,
                "compliance_status": "Unclear"
            }
        
        # Save analysis to database
        save_query = text("""
            INSERT INTO correspondence_analysis 
                (id, correspondence_id, contract_id, analysis_type, analysis_data, 
                 summary, compliance_status, risk_level, action_required, 
                 analyzed_by, analyzed_at)
            VALUES 
                (UUID(), :correspondence_id, :contract_id, 'ai_analysis', :analysis_data,
                 :summary, :compliance_status, :risk_level, :action_required,
                 :analyzed_by, NOW())
        """)
        
        db.execute(save_query, {
            "correspondence_id": doc_id,
            "contract_id": result.contract_id,
            "analysis_data": json.dumps(analysis_data),
            "summary": analysis_data.get("summary", ""),
            "compliance_status": analysis_data.get("compliance_status", "Unclear"),
            "risk_level": analysis_data.get("risk_assessment", {}).get("level", "Medium"),
            "action_required": analysis_data.get("action_required", ""),
            "analyzed_by": current_user.id
        })
        db.commit()
        
        # Create obligations if mentioned
        obligations = analysis_data.get("obligations_mentioned", [])
        if obligations:
            for obligation_text in obligations:
                obligation_query = text("""
                    INSERT INTO obligations 
                        (id, contract_id, obligation_title, description, 
                         obligation_type, due_date, status, is_ai_generated,
                         created_at, updated_at)
                    VALUES 
                        (UUID(), :contract_id, :title, :description,
                         'correspondence_derived', :due_date, 'pending', 1,
                         NOW(), NOW())
                """)
                
                db.execute(obligation_query, {
                    "contract_id": result.contract_id,
                    "title": f"Obligation from {result.document_name}",
                    "description": obligation_text,
                    "due_date": analysis_data.get("deadline")
                })
        
        db.commit()
        
        return {
            "success": True,
            "document_id": doc_id,
            "contract_id": result.contract_id,
            "contract_title": result.contract_title,
            "analysis": analysis_data,
            "obligations_created": len(obligations),
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error analyzing correspondence: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze correspondence: {str(e)}"
        )


@router.get("/analysis/{doc_id}")
async def get_correspondence_analysis(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get existing analysis for a correspondence document"""
    try:
        query = text("""
            SELECT 
                ca.*,
                c.contract_title,
                c.contract_number,
                u.first_name,
                u.last_name
            FROM correspondence_analysis ca
            JOIN contracts c ON ca.contract_id = c.id
            LEFT JOIN users u ON ca.analyzed_by = u.id
            WHERE ca.correspondence_id = :doc_id
                AND c.company_id = :company_id
            ORDER BY ca.analyzed_at DESC
            LIMIT 1
        """)
        
        result = db.execute(
            query,
            {"doc_id": doc_id, "company_id": current_user.company_id}
        ).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No analysis found for this document"
            )
        
        return {
            "success": True,
            "analysis_id": result.id,
            "contract_title": result.contract_title,
            "contract_number": result.contract_number,
            "analysis_type": result.analysis_type,
            "analysis_data": json.loads(result.analysis_data) if result.analysis_data else {},
            "summary": result.summary,
            "compliance_status": result.compliance_status,
            "risk_level": result.risk_level,
            "action_required": result.action_required,
            "analyzed_by": f"{result.first_name} {result.last_name}",
            "analyzed_at": result.analyzed_at.isoformat() if result.analyzed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analysis: {str(e)}"
        )