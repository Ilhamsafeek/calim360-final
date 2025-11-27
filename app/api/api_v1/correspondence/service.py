# =====================================================
# FILE: app/api/api_v1/correspondence/service.py
# Business Logic for Correspondence with AI Integration
# FIXED: All queries now properly join contract_versions for contract_content
# =====================================================

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime

from app.api.api_v1.correspondence.crud import (
    get_documents_by_ids,
    create_correspondence,
    get_correspondence_list,
    get_correspondence_by_id
)

logger = logging.getLogger(__name__)

class CorrespondenceService:
    """Service layer for correspondence management"""
    
    @staticmethod
    async def generate_ai_correspondence(
        db: Session,
        query: str,
        document_ids: List[str],
        tone: str,
        correspondence_type: str,
        contract_id: Optional[str] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered correspondence using Claude API
        """
        
        try:
            # Get reference documents
            documents = get_documents_by_ids(db, document_ids)
            
            # Get contract context if contract_id provided
            context = None
            if contract_id:
                context = CorrespondenceService._get_contract_context(db, contract_id)
            
            # Try to use Claude API if available
            try:
                from app.core.claude_client import claude_client
                
                if claude_client and hasattr(claude_client, 'api_key') and claude_client.api_key:
                    # Call Claude API
                    result = await claude_client.generate_correspondence(
                        query=query,
                        documents=documents,
                        tone=tone,
                        correspondence_type=correspondence_type,
                        context=context
                    )
                    
                    if result["success"]:
                        logger.info(f"✅ AI correspondence generated successfully using Claude API")
                    else:
                        logger.warning(f"⚠️ AI generation failed: {result.get('error')}")
                    
                    return result
                else:
                    raise Exception("Claude API key not configured")
                    
            except Exception as claude_error:
                logger.warning(f"⚠️ Claude API not available: {str(claude_error)}, using mock response")
                # Fallback to mock response
                return CorrespondenceService._generate_mock_response(
                    query=query,
                    tone=tone,
                    correspondence_type=correspondence_type,
                    documents=documents,
                    context=context
                )
            
        except Exception as e:
            logger.error(f"❌ Error in AI correspondence generation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content": CorrespondenceService._get_fallback_content(query, tone, correspondence_type)
            }
    
    @staticmethod
    async def analyze_documents(
        db: Session,
        document_ids: List[str],
        query: str
    ) -> Dict[str, Any]:
        """
        Analyze documents for correspondence insights
        """
        
        try:
            documents = get_documents_by_ids(db, document_ids)
            
            # Try to use Claude API if available
            try:
                from app.core.claude_client import claude_client
                
                if claude_client and hasattr(claude_client, 'api_key') and claude_client.api_key:
                    result = await claude_client.analyze_documents(
                        documents=documents,
                        query=query
                    )
                    
                    logger.info(f"✅ Document analysis completed using Claude API")
                    return result
                else:
                    raise Exception("Claude API key not configured")
                    
            except Exception as claude_error:
                logger.warning(f"⚠️ Claude API not available: {str(claude_error)}, using mock analysis")
                # Fallback to mock analysis
                return CorrespondenceService._generate_mock_analysis(documents, query)
            
        except Exception as e:
            logger.error(f"❌ Error in document analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _get_contract_context(db: Session, contract_id: str) -> Dict[str, Any]:
        """
        Get contract details for context
        FIXED: Now joins with contract_versions to get contract_content
        """
        
        try:
            # ✅ FIXED: Added JOIN with contract_versions table
            query = text("""
                SELECT 
                    c.id,
                    c.contract_number,
                    c.contract_title,
                    c.contract_type,
                    c.contract_value,
                    c.currency,
                    c.start_date,
                    c.end_date,
                    c.status,
                    c.current_version,
                    cv.contract_content,
                    cv.contract_content_ar,
                    cv.version_number
                FROM contracts c
                LEFT JOIN contract_versions cv ON c.id = cv.contract_id 
                    AND cv.version_number = c.current_version
                WHERE c.id = :contract_id
            """)
            
            result = db.execute(query, {"contract_id": contract_id}).fetchone()
            
            if result:
                return {
                    "id": str(result.id),
                    "contract_number": result.contract_number,
                    "contract_title": result.contract_title,
                    "contract_type": result.contract_type,
                    "contract_value": float(result.contract_value) if result.contract_value else None,
                    "currency": result.currency,
                    "start_date": result.start_date.isoformat() if result.start_date else None,
                    "end_date": result.end_date.isoformat() if result.end_date else None,
                    "status": result.status,
                    "current_version": result.current_version,
                    "contract_content": result.contract_content,
                    "contract_content_ar": result.contract_content_ar,
                    "version_number": result.version_number
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error fetching contract context: {str(e)}")
            return {}
    
    @staticmethod
    def _generate_mock_response(
        query: str,
        tone: str,
        correspondence_type: str,
        documents: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate mock response when Claude API is not available
        """
        
        contract_info = ""
        if context:
            contract_info = f"""
Contract: {context.get('contract_number', 'N/A')}
Title: {context.get('contract_title', 'N/A')}
Version: {context.get('version_number', 'N/A')}
"""
        
        documents_info = ""
        if documents:
            documents_info = "\n".join([f"- {doc.get('document_name', 'Unknown')}" for doc in documents[:3]])
        
        content = f"""Dear Sir/Madam,

RE: {query}

{contract_info}

We acknowledge receipt of your correspondence regarding the above matter.

After careful review of the relevant documentation:
{documents_info}

We respectfully submit the following response:

1. OVERVIEW
   We have thoroughly reviewed the matter and the contractual obligations as outlined in the agreement.

2. CONTRACTUAL POSITION
   Based on our analysis of the contract terms and conditions, we note the following key provisions:
   - Dispute resolution procedures as outlined in the contract
   - Notification requirements and timelines
   - Remedial action provisions

3. OUR POSITION
   We maintain that proper procedures must be followed in accordance with the contract terms.

4. PROPOSED RESOLUTION
   We propose the following course of action:
   - Immediate discussion to resolve the matter amicably
   - Review of all relevant documentation
   - Agreement on next steps within the contractual framework

We remain committed to the successful completion of this project and look forward to resolving this matter in a timely manner.

Yours faithfully,

[Authorized Signatory]

---
Note: This is a demonstration response generated with {tone} tone.
For production use, please configure the Claude API key to enable AI-powered correspondence generation.
"""
        
        return {
            "success": True,
            "content": content,
            "tone": tone,
            "type": correspondence_type,
            "tokens_used": 0,
            "model": "mock-fallback",
            "generated_at": datetime.utcnow().isoformat(),
            "warning": "Claude API not configured - using mock response"
        }
    
    @staticmethod
    def _generate_mock_analysis(
        documents: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        Generate mock analysis when Claude API is not available
        """
        
        return {
            "success": True,
            "analysis": f"Mock analysis of {len(documents)} documents regarding: {query}",
            "key_findings": [
                "Contract contains standard dispute resolution clauses",
                "Force Majeure provisions are outlined in the agreement",
                "Payment terms and penalty clauses are defined",
                "Document review indicates compliance requirements"
            ],
            "risks": [
                "Timeline requirements must be strictly followed",
                "Failure to notify within specified periods may impact claims",
                "Documentation requirements must be met"
            ],
            "opportunities": [
                "Contract allows for negotiation and discussion",
                "Provisions exist for contract amendments",
                "Alternative dispute resolution mechanisms available"
            ],
            "recommended_actions": [
                "Gather all supporting documentation",
                "Submit formal notification within required timeframe",
                "Schedule meeting to discuss resolution options",
                "Review contract clauses carefully before proceeding"
            ],
            "confidence_score": 75.0,
            "warning": "Claude API not configured - using mock analysis"
        }
    
    @staticmethod
    def _get_fallback_content(query: str, tone: str, correspondence_type: str) -> str:
        """
        Simple fallback content when everything fails
        """
        return f"""Dear Sir/Madam,

RE: {query}

This is an automatically generated placeholder correspondence.

To enable AI-powered correspondence generation, please configure the Claude API key in your environment settings.

Yours faithfully,
[Authorized Signatory]

Type: {correspondence_type} | Tone: {tone}
"""