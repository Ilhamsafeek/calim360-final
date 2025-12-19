# =====================================================
# FILE: app/api/api_v1/correspondence/correspondence_router.py
# Correspondence Management API Router
# Uses existing ClaudeService for AI analysis
# =====================================================

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os
import json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.claude_service import claude_service  # Use existing service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/correspondence", tags=["Correspondence"])

# =====================================================
# SCHEMAS
# =====================================================
class AnalysisRequest(BaseModel):
    query: str
    mode: str = "project"  # 'project' or 'document'
    document_ids: List[str]
    project_id: Optional[int] = None
    tone: str = "formal"
    language: str = "en"
    priority: str = "normal"

class AnalysisResponse(BaseModel):
    success: bool
    content: str
    confidence: float
    processing_time: float
    sources: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    key_points: List[str] = []
    suggested_actions: List[str] = []
    tokens_used: int = 0
    timestamp: str

class CorrespondenceCreate(BaseModel):
    contract_id: Optional[str] = None
    correspondence_type: str = "query"
    subject: str
    content: str
    priority: str = "normal"
    tone: Optional[str] = None

class CorrespondenceResponse(BaseModel):
    id: str
    subject: str
    content: str
    correspondence_type: str
    status: str
    created_at: str

# =====================================================
# GET PROJECTS WITH DOCUMENTS
# =====================================================
@router.get("/projects")
async def get_projects_with_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects with their documents for correspondence management"""
    try:
        logger.info(f"📁 Loading projects for user {current_user.id}, company {current_user.company_id}")
        
        # Get projects
        projects_query = text("""
            SELECT 
                p.id,
                p.project_code,
                p.project_name,
                p.status,
                p.created_at,
                COUNT(DISTINCT c.id) as contract_count
            FROM projects p
            LEFT JOIN contracts c ON c.project_id = p.id
            WHERE p.company_id = :company_id
            AND p.status = 'active'
            GROUP BY p.id
            ORDER BY p.project_name ASC
        """)
        
        projects_result = db.execute(projects_query, {"company_id": current_user.company_id}).fetchall()
        
        projects = []
        for proj in projects_result:
            # Get documents for each project
            docs_query = text("""
                SELECT 
                    d.id,
                    d.document_name,
                    d.document_type,
                    d.file_path,
                    d.file_size,
                    d.uploaded_at,
                    c.contract_number,
                    c.contract_title
                FROM documents d
                INNER JOIN contracts c ON d.contract_id = c.id
                WHERE c.project_id = :project_id
                AND c.company_id = :company_id
                ORDER BY d.uploaded_at DESC
            """)
            
            docs_result = db.execute(docs_query, {
                "project_id": proj.id,
                "company_id": current_user.company_id
            }).fetchall()
            
            documents = []
            for doc in docs_result:
                documents.append({
                    "id": str(doc.id),
                    "document_name": doc.document_name,
                    "document_type": doc.document_type,
                    "file_path": doc.file_path,
                    "file_size": doc.file_size,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    "contract_number": doc.contract_number,
                    "contract_title": doc.contract_title
                })
            
            projects.append({
                "id": proj.id,
                "project_code": proj.project_code,
                "project_name": proj.project_name,
                "status": proj.status,
                "contract_count": proj.contract_count,
                "document_count": len(documents),
                "documents": documents,
                "created_at": proj.created_at.isoformat() if proj.created_at else None
            })
        
        logger.info(f"✅ Found {len(projects)} projects")
        return {"success": True, "data": projects, "count": len(projects)}
        
    except Exception as e:
        logger.error(f"❌ Error loading projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# GET STATISTICS
# =====================================================
@router.get("/stats")
async def get_correspondence_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get correspondence statistics for the dashboard"""
    try:
        # Count active projects
        projects_query = text("""
            SELECT COUNT(*) as count FROM projects 
            WHERE company_id = :company_id AND status = 'active'
        """)
        projects_count = db.execute(projects_query, {"company_id": current_user.company_id}).scalar() or 0
        
        # Count documents
        docs_query = text("""
            SELECT COUNT(*) as count FROM documents d
            INNER JOIN contracts c ON d.contract_id = c.id
            WHERE c.company_id = :company_id
        """)
        docs_count = db.execute(docs_query, {"company_id": current_user.company_id}).scalar() or 0
        
        # Count correspondence/queries
        corr_query = text("""
            SELECT COUNT(*) as count FROM correspondence c
            INNER JOIN contracts ct ON c.contract_id = ct.id
            WHERE ct.company_id = :company_id
        """)
        try:
            corr_count = db.execute(corr_query, {"company_id": current_user.company_id}).scalar() or 0
        except:
            corr_count = 0
        
        # Count AI responses
        ai_query = text("""
            SELECT COUNT(*) as count FROM correspondence c
            INNER JOIN contracts ct ON c.contract_id = ct.id
            WHERE ct.company_id = :company_id AND c.is_ai_generated = 1
        """)
        try:
            ai_count = db.execute(ai_query, {"company_id": current_user.company_id}).scalar() or 0
        except:
            ai_count = 0
        
        return {
            "projects": projects_count,
            "documents": docs_count,
            "queries": corr_count,
            "ai_responses": ai_count
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting stats: {str(e)}")
        return {"projects": 0, "documents": 0, "queries": 0, "ai_responses": 0}

# =====================================================
# ANALYZE CORRESPONDENCE (AI) - Uses existing ClaudeService
# =====================================================
@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_correspondence(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze correspondence documents using AI"""
    import time
    start_time = time.time()
    
    try:
        logger.info(f"🤖 AI Analysis request from user {current_user.email}")
        logger.info(f"   Query: {request.query[:100]}...")
        logger.info(f"   Documents: {len(request.document_ids)}")
        
        # Validate documents access
        if not request.document_ids:
            raise HTTPException(status_code=400, detail="No documents selected")
        
        # Fetch document contents for AI analysis
        doc_contents = []
        valid_contract_id = None  # Store a valid UUID contract_id
        
        for doc_id in request.document_ids:
            doc_query = text("""
                SELECT 
                    d.id, 
                    d.document_name, 
                    d.file_path, 
                    d.document_type, 
                    d.file_size,
                    d.uploaded_at,
                    d.contract_id,
                    c.contract_title,
                    c.contract_number
                FROM documents d
                INNER JOIN contracts c ON d.contract_id = c.id
                WHERE d.id = :doc_id AND c.company_id = :company_id
            """)
            
            doc = db.execute(doc_query, {
                "doc_id": doc_id,
                "company_id": current_user.company_id
            }).fetchone()
            
            if doc:
                # Store first valid contract_id for saving correspondence
                if not valid_contract_id and doc.contract_id:
                    valid_contract_id = doc.contract_id
                
                # Build document info for AI
                content_preview = f"Document: {doc.document_name}\nType: {doc.document_type or 'Unknown'}"
                
                # Try to read actual file content if available
                if doc.file_path and os.path.exists(doc.file_path):
                    try:
                        if doc.file_path.endswith(('.txt', '.md')):
                            with open(doc.file_path, 'r', encoding='utf-8') as f:
                                content_preview = f.read()[:30000]
                    except Exception as e:
                        logger.warning(f"Could not read file {doc.file_path}: {e}")
                
                doc_contents.append({
                    "id": str(doc.id),
                    "name": doc.document_name,
                    "type": doc.document_type,
                    "content_preview": content_preview,
                    "contract_title": doc.contract_title,
                    "contract_number": doc.contract_number,
                    "date": doc.uploaded_at.isoformat() if doc.uploaded_at else None
                })
        
        if not doc_contents:
            raise HTTPException(status_code=404, detail="No accessible documents found")
        
        # Call existing ClaudeService.analyze_correspondence method
        # The service ALWAYS returns a dict (either AI response or fallback)
        try:
            ai_result = claude_service.analyze_correspondence(
                query=request.query,
                documents=doc_contents,
                analysis_mode=request.mode,
                tone=request.tone,
                urgency=request.priority,
                language=request.language,
                jurisdiction="Qatar"
            )
            logger.info(f"✅ Claude analysis completed - Confidence: {ai_result.get('confidence_score', 0)}%")
        except Exception as claude_error:
            logger.error(f"❌ Claude service error: {str(claude_error)}")
            # Generate fallback response manually
            ai_result = {
                "analysis_text": generate_fallback_analysis(request.query, doc_contents),
                "confidence_score": 65.0,
                "tokens_used": 0,
                "key_points": ["Document review completed", "Manual analysis recommended"],
                "recommendations": ["Consult with legal team", "Review all referenced clauses"],
                "suggested_actions": ["Schedule follow-up meeting", "Document all decisions"]
            }
        
        processing_time = time.time() - start_time
        
        # Save to correspondence table (handle int vs UUID mismatch)
        if valid_contract_id:
            try:
                # Check if correspondence table exists and get contract_id type
                # The contracts.id is INT but correspondence.contract_id might be char(36)
                # We need to handle this carefully
                
                # First, verify the contract exists in contracts table
                verify_contract = text("""
                    SELECT id FROM contracts WHERE id = :contract_id LIMIT 1
                """)
                contract_exists = db.execute(verify_contract, {"contract_id": valid_contract_id}).fetchone()
                
                if contract_exists:
                    save_query = text("""
                        INSERT INTO correspondence (
                            contract_id, correspondence_type, subject, content,
                            sender_id, priority, status, is_ai_generated, ai_tone, created_at
                        ) VALUES (
                            :contract_id, 'query', :subject, :content,
                            :sender_id, :priority, 'completed', 1, :tone, NOW()
                        )
                    """)
                    
                    db.execute(save_query, {
                        "contract_id": valid_contract_id,
                        "subject": request.query[:500],
                        "content": ai_result.get("analysis_text", "")[:10000],
                        "sender_id": current_user.id,  # Keep as int since users.id is int
                        "priority": request.priority,
                        "tone": request.tone
                    })
                    db.commit()
                    logger.info(f"✅ Correspondence saved for contract {valid_contract_id}")
                else:
                    logger.warning(f"⚠️ Contract {valid_contract_id} not found in contracts table")
                
            except Exception as e:
                db.rollback()
                logger.warning(f"⚠️ Could not save correspondence (non-critical): {str(e)}")
        else:
            logger.warning("⚠️ No valid contract_id found, skipping correspondence save")
        
        return AnalysisResponse(
            success=True,
            content=ai_result.get("analysis_text", "Analysis completed."),
            confidence=ai_result.get("confidence_score", 85.0) / 100.0,  # Convert to 0-1 scale
            processing_time=round(processing_time, 2),
            sources=[{"id": d["id"], "name": d["name"]} for d in doc_contents],
            recommendations=ai_result.get("recommendations", []),
            key_points=ai_result.get("key_points", []),
            suggested_actions=ai_result.get("suggested_actions", []),
            tokens_used=ai_result.get("tokens_used", 0),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_fallback_analysis(query: str, documents: List[Dict]) -> str:
    """Generate fallback analysis when Claude is unavailable"""
    doc_names = "\n".join([f"• {d['name']}" for d in documents[:10]])
    
    return f"""## Correspondence Analysis

**Query:** {query[:200]}...

### Documents Analyzed
{doc_names}

### Analysis Summary
The selected documents have been reviewed. Due to AI service limitations, a comprehensive automated analysis could not be completed at this time.

### Key Observations
1. **Document Review Required**: Manual review of the documents is recommended for detailed analysis.
2. **Contractual Context**: Consider the contractual relationships and obligations referenced in these documents.
3. **Timeline Awareness**: Note any time-sensitive matters or deadlines mentioned.

### Recommendations
1. Review all documents thoroughly with relevant stakeholders
2. Identify and document key obligations and deadlines
3. Consult with legal counsel for complex contractual matters
4. Maintain detailed records of all correspondence and decisions

### Next Steps
- Schedule a review meeting with the project team
- Create a checklist of action items from the documents
- Set up reminders for any identified deadlines
- Document all decisions and their rationale

---
*Note: For enhanced AI-powered analysis, please ensure the Claude API service is properly configured. For critical legal or financial matters, always consult with qualified professionals.*
"""

# =====================================================
# GET CORRESPONDENCE LIST
# =====================================================
@router.get("/list")
async def get_correspondence_list(
    project_id: Optional[int] = None,
    contract_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of correspondence records"""
    try:
        where_clauses = ["ct.company_id = :company_id"]
        params = {"company_id": current_user.company_id, "limit": limit, "offset": offset}
        
        if project_id:
            where_clauses.append("ct.project_id = :project_id")
            params["project_id"] = project_id
        
        if contract_id:
            where_clauses.append("c.contract_id = :contract_id")
            params["contract_id"] = contract_id
        
        where_sql = " AND ".join(where_clauses)
        
        query = text(f"""
            SELECT 
                c.id,
                c.subject,
                c.correspondence_type,
                c.priority,
                c.status,
                c.is_ai_generated,
                c.created_at,
                ct.contract_number,
                ct.contract_title
            FROM correspondence c
            INNER JOIN contracts ct ON c.contract_id = ct.id
            WHERE {where_sql}
            ORDER BY c.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        results = db.execute(query, params).fetchall()
        
        items = []
        for row in results:
            items.append({
                "id": str(row.id),
                "subject": row.subject,
                "correspondence_type": row.correspondence_type,
                "priority": row.priority,
                "status": row.status,
                "is_ai_generated": bool(row.is_ai_generated),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "contract_number": row.contract_number,
                "contract_title": row.contract_title
            })
        
        return {"success": True, "data": items, "count": len(items)}
        
    except Exception as e:
        logger.error(f"❌ Error fetching correspondence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# GET SINGLE CORRESPONDENCE
# =====================================================
@router.get("/{correspondence_id}")
async def get_correspondence(
    correspondence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single correspondence record"""
    try:
        query = text("""
            SELECT 
                c.*,
                ct.contract_number,
                ct.contract_title,
                u.first_name,
                u.last_name
            FROM correspondence c
            INNER JOIN contracts ct ON c.contract_id = ct.id
            LEFT JOIN users u ON c.sender_id = u.id
            WHERE c.id = :corr_id AND ct.company_id = :company_id
        """)
        
        result = db.execute(query, {
            "corr_id": correspondence_id,
            "company_id": current_user.company_id
        }).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Correspondence not found")
        
        return {
            "success": True,
            "data": {
                "id": str(result.id),
                "subject": result.subject,
                "content": result.content,
                "correspondence_type": result.correspondence_type,
                "priority": result.priority,
                "status": result.status,
                "is_ai_generated": bool(result.is_ai_generated),
                "ai_tone": result.ai_tone,
                "created_at": result.created_at.isoformat() if result.created_at else None,
                "contract_number": result.contract_number,
                "contract_title": result.contract_title,
                "sender_name": f"{result.first_name} {result.last_name}" if result.first_name else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching correspondence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# DELETE CORRESPONDENCE
# =====================================================
@router.delete("/{correspondence_id}")
async def delete_correspondence(
    correspondence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a correspondence record"""
    try:
        # Verify access
        verify_query = text("""
            SELECT c.id FROM correspondence c
            INNER JOIN contracts ct ON c.contract_id = ct.id
            WHERE c.id = :corr_id AND ct.company_id = :company_id
        """)
        
        exists = db.execute(verify_query, {
            "corr_id": correspondence_id,
            "company_id": current_user.company_id
        }).fetchone()
        
        if not exists:
            raise HTTPException(status_code=404, detail="Correspondence not found")
        
        # Delete
        delete_query = text("DELETE FROM correspondence WHERE id = :corr_id")
        db.execute(delete_query, {"corr_id": correspondence_id})
        db.commit()
        
        return {"success": True, "message": "Correspondence deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error deleting correspondence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def format_file_size(bytes_size: int) -> str:
    """Format file size for display"""
    if not bytes_size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"