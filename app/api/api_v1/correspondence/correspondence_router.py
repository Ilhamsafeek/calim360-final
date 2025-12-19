# =====================================================
# FILE: app/api/api_v1/correspondence/correspondence_router.py
# Correspondence Management API Router
# Includes Document Upload, AI Analysis, and CRUD operations
# =====================================================

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import logging
import os
import json
import uuid
import hashlib

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.claude_service import claude_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/correspondence", tags=["Correspondence"])


# =====================================================
# UPLOAD CONFIGURATION
# =====================================================
ALLOWED_EXTENSIONS = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'txt': 'text/plain',
    'rtf': 'application/rtf',
    'eml': 'message/rfc822',
    'msg': 'application/vnd.ms-outlook',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png'
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_BATCH_SIZE = 10
UPLOAD_BASE_DIR = Path("app/uploads/correspondence")


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
# HELPER FUNCTIONS
# =====================================================
def validate_upload_file(file: UploadFile) -> tuple:
    """Validate uploaded file"""
    file_ext = Path(file.filename).suffix.lower().replace('.', '')
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type .{file_ext} not allowed"
    return True, "Valid"


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


# =====================================================
# DOCUMENT UPLOAD ENDPOINT
# =====================================================
@router.post("/upload")
async def upload_correspondence_documents(
    files: List[UploadFile] = File(...),
    project_id: int = Form(...),
    document_type: str = Form(default="correspondence"),
    notes: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload documents with FK-safe handling"""
    try:
        logger.info(f"📤 Upload request: {len(files)} files for project {project_id} by user {current_user.email}")
        
        if len(files) > MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {MAX_BATCH_SIZE} files allowed per upload"
            )
        
        # Verify project exists
        project_query = text("SELECT id, company_id FROM projects WHERE id = :project_id")
        project_result = db.execute(project_query, {"project_id": project_id}).fetchone()
        
        if not project_result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")
        
        # Get the actual user ID from the database to ensure it exists
        user_check = text("SELECT id FROM users WHERE id = :user_id")
        user_result = db.execute(user_check, {"user_id": current_user.id}).fetchone()
        
        if not user_result:
            logger.error(f"❌ User {current_user.id} not found in database!")
            # Try to find user by email
            email_check = text("SELECT id FROM users WHERE email = :email")
            email_result = db.execute(email_check, {"email": current_user.email}).fetchone()
            if email_result:
                actual_user_id = email_result.id
                logger.info(f"✅ Found user by email, actual id: {actual_user_id}")
            else:
                actual_user_id = None
                logger.warning("⚠️ User not found, will set uploaded_by to NULL")
        else:
            actual_user_id = user_result.id
        
        uploaded_files = []
        failed_files = []
        
        for file in files:
            try:
                # Validate file
                is_valid, message = validate_upload_file(file)
                if not is_valid:
                    failed_files.append({"filename": file.filename, "error": message})
                    continue
                
                content = await file.read()
                file_size = len(content)
                
                if file_size > MAX_FILE_SIZE:
                    failed_files.append({"filename": file.filename, "error": "File size exceeds 50MB limit"})
                    continue
                
                file_hash = calculate_file_hash(content)
                
                # Create directory
                save_dir = UPLOAD_BASE_DIR / str(current_user.company_id) / str(project_id)
                save_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_ext = Path(file.filename).suffix
                base_name = Path(file.filename).stem[:50]
                unique_filename = f"{base_name}_{timestamp}{file_ext}"
                file_path = save_dir / unique_filename
                
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                doc_id = str(uuid.uuid4())
                file_ext_lower = file_ext.lower().replace('.', '')
                mime_type = ALLOWED_EXTENSIONS.get(file_ext_lower, file.content_type or 'application/octet-stream')
                
                metadata = json.dumps({
                    "project_id": project_id,
                    "original_filename": file.filename,
                    "notes": notes,
                    "upload_source": "correspondence_management",
                    "uploader_email": current_user.email  # Store email as backup
                })
                
                # Insert with proper handling for uploaded_by
                # If user FK is problematic, set to NULL
                if actual_user_id is not None:
                    insert_query = text("""
                        INSERT INTO documents (
                            id, company_id, document_name, document_type, 
                            file_path, file_size, mime_type, hash_value, 
                            uploaded_by, uploaded_at, version, access_count, metadata
                        ) VALUES (
                            :id, :company_id, :document_name, :document_type,
                            :file_path, :file_size, :mime_type, :hash_value,
                            :uploaded_by, :uploaded_at, 1, 0, :metadata
                        )
                    """)
                    params = {
                        "id": doc_id,
                        "company_id": current_user.company_id,
                        "document_name": file.filename,
                        "document_type": document_type,
                        "file_path": str(file_path),
                        "file_size": file_size,
                        "mime_type": mime_type,
                        "hash_value": file_hash,
                        "uploaded_by": actual_user_id,
                        "uploaded_at": datetime.utcnow(),
                        "metadata": metadata
                    }
                else:
                    # Skip uploaded_by if user doesn't exist
                    insert_query = text("""
                        INSERT INTO documents (
                            id, company_id, document_name, document_type, 
                            file_path, file_size, mime_type, hash_value, 
                            uploaded_at, version, access_count, metadata
                        ) VALUES (
                            :id, :company_id, :document_name, :document_type,
                            :file_path, :file_size, :mime_type, :hash_value,
                            :uploaded_at, 1, 0, :metadata
                        )
                    """)
                    params = {
                        "id": doc_id,
                        "company_id": current_user.company_id,
                        "document_name": file.filename,
                        "document_type": document_type,
                        "file_path": str(file_path),
                        "file_size": file_size,
                        "mime_type": mime_type,
                        "hash_value": file_hash,
                        "uploaded_at": datetime.utcnow(),
                        "metadata": metadata
                    }
                
                db.execute(insert_query, params)
                
                uploaded_files.append({
                    "id": doc_id,
                    "filename": file.filename,
                    "file_size": file_size,
                    "document_type": document_type,
                    "mime_type": mime_type,
                    "uploaded_at": datetime.utcnow().isoformat()
                })
                
                logger.info(f"✅ Uploaded: {file.filename} ({file_size} bytes) -> {doc_id}")
                
            except Exception as file_error:
                logger.error(f"❌ Error uploading {file.filename}: {str(file_error)}")
                failed_files.append({"filename": file.filename, "error": str(file_error)})
        
        db.commit()
        
        return {
            "success": len(uploaded_files) > 0,
            "message": f"Uploaded {len(uploaded_files)} file(s) successfully",
            "uploaded": uploaded_files,
            "failed": failed_files,
            "total_uploaded": len(uploaded_files),
            "total_failed": len(failed_files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {str(e)}"
        )

        
# =====================================================
# GET PROJECT DOCUMENTS ENDPOINT
# =====================================================
@router.get("/documents/{project_id}")
async def get_project_documents_for_correspondence(
    project_id: int,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all documents for a project"""
    try:
        logger.info(f"📂 Fetching documents for project {project_id}")
        
        query_str = """
            SELECT 
                id, document_name, document_type, file_path,
                file_size, mime_type, uploaded_by, uploaded_at,
                metadata
            FROM documents
            WHERE JSON_EXTRACT(metadata, '$.project_id') = :project_id
        """
        params = {"project_id": project_id}
        
        if document_type:
            query_str += " AND document_type = :document_type"
            params["document_type"] = document_type
        
        query_str += " ORDER BY uploaded_at DESC"
        
        result = db.execute(text(query_str), params).fetchall()
        
        documents = []
        for row in result:
            documents.append({
                "id": row.id,
                "document_name": row.document_name,
                "document_type": row.document_type,
                "file_size": row.file_size,
                "mime_type": row.mime_type,
                "uploaded_by": row.uploaded_by,
                "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None
            })
        
        return {
            "success": True,
            "project_id": project_id,
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch documents: {str(e)}"
        )


# =====================================================
# GET PROJECTS WITH DOCUMENTS (FIXED)
# =====================================================
@router.get("/projects")
async def get_projects_with_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects with their documents for correspondence management"""
    try:
        company_id = current_user.company_id
        logger.info(f"📁 Loading projects for user {current_user.id}, company_id={company_id}")
        
        # Get ALL projects for the company (removed status filter)
        projects_query = text("""
            SELECT 
                p.id,
                p.project_code,
                p.project_name,
                p.status,
                p.description,
                p.created_at
            FROM projects p
            WHERE p.company_id = :company_id
            ORDER BY p.project_name ASC
        """)
        
        projects_result = db.execute(projects_query, {"company_id": company_id}).fetchall()
        
        logger.info(f"📊 Found {len(projects_result)} projects for company {company_id}")
        
        projects = []
        for proj in projects_result:
            # Method 1: Get documents directly linked via project_documents table
            direct_docs_query = text("""
                SELECT 
                    d.id, d.document_name, d.document_type, d.file_path,
                    d.file_size, d.mime_type, d.uploaded_at,
                    NULL as contract_number, NULL as contract_title
                FROM documents d
                INNER JOIN project_documents pd ON d.id = pd.document_id
                WHERE pd.project_id = :project_id
            """)
            
            # Method 2: Get documents linked via contracts
            contract_docs_query = text("""
                SELECT 
                    d.id, d.document_name, d.document_type, d.file_path,
                    d.file_size, d.mime_type, d.uploaded_at,
                    c.contract_number, c.contract_title
                FROM documents d
                INNER JOIN contracts c ON d.contract_id = c.id
                WHERE c.project_id = :project_id
            """)
            
            # Method 3: Get documents with project_id in metadata (from upload)
            metadata_docs_query = text("""
                SELECT 
                    d.id, d.document_name, d.document_type, d.file_path,
                    d.file_size, d.mime_type, d.uploaded_at,
                    NULL as contract_number, NULL as contract_title
                FROM documents d
                WHERE JSON_EXTRACT(d.metadata, '$.project_id') = :project_id
            """)
            
            # Combine all document sources
            all_docs = []
            seen_doc_ids = set()
            
            # Try each query method
            for query, name in [
                (direct_docs_query, "direct"), 
                (contract_docs_query, "contract"), 
                (metadata_docs_query, "metadata")
            ]:
                try:
                    docs = db.execute(query, {"project_id": proj.id}).fetchall()
                    for doc in docs:
                        if doc.id not in seen_doc_ids:
                            seen_doc_ids.add(doc.id)
                            all_docs.append(doc)
                except Exception as e:
                    logger.warning(f"{name} docs query error: {e}")
            
            documents = []
            for doc in all_docs:
                documents.append({
                    "id": str(doc.id),
                    "document_name": doc.document_name,
                    "document_type": doc.document_type,
                    "file_path": doc.file_path,
                    "file_size": doc.file_size,
                    "mime_type": doc.mime_type,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    "contract_number": doc.contract_number,
                    "contract_title": doc.contract_title
                })
            
            projects.append({
                "id": proj.id,
                "project_code": proj.project_code,
                "project_name": proj.project_name,
                "status": proj.status,
                "description": proj.description,
                "document_count": len(documents),
                "documents": documents
            })
        
        logger.info(f"✅ Returning {len(projects)} projects with documents")
        
        return {
            "success": True,
            "data": projects,
            "total": len(projects)
        }
        
    except Exception as e:
        logger.error(f"❌ Error loading projects: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load projects: {str(e)}"
        )


# =====================================================
# FALLBACK ANALYSIS FUNCTION
# =====================================================
def generate_fallback_analysis(query: str, documents: List[Dict]) -> str:
    """Generate fallback analysis when AI service is unavailable"""
    
    doc_names = ", ".join([d.get("name", "Unknown") for d in documents[:5]])
    doc_count = len(documents)
    
    return f"""## Correspondence Analysis Report

### Query
{query}

### Documents Analyzed
- **Total Documents:** {doc_count}
- **Documents:** {doc_names}

### Analysis Summary
Based on the {doc_count} document(s) provided, the following preliminary analysis has been conducted:

1. **Document Review Status:** All {doc_count} document(s) have been received and catalogued for analysis.

2. **Key Observations:**
   - Documents require detailed manual review
   - Cross-reference with contract terms is recommended
   - Timeline and deadline implications should be verified

3. **Initial Assessment:**
   The documents appear to relate to the query regarding "{query[:100]}..."
   Further detailed analysis is recommended to provide specific guidance.

### Recommendations
1. Review each document individually for specific clauses relevant to the query
2. Cross-reference with the main contract terms
3. Consult with legal counsel for complex matters
4. Document all findings and decisions for audit trail

### Next Steps
- Schedule a detailed review meeting
- Prepare a formal response if required
- Update relevant stakeholders

---
*Note: This is an automated preliminary analysis. For comprehensive guidance, please ensure AI services are properly configured or consult with your legal team.*
"""


# =====================================================
# AI ANALYSIS ENDPOINT (FIXED)
# =====================================================
@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_correspondence_documents(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze correspondence documents using AI
    
    **Features:**
    - AI-generated analysis and recommendations
    - Confidence scoring
    - Source references
    - Suggested actions
    """
    import time
    start_time = time.time()
    
    try:
        logger.info(f"📧 Analysis request from user {current_user.email}")
        logger.info(f"   Mode: {request.mode}, Documents: {len(request.document_ids)}")
        
        # Fetch document contents
        doc_contents = []
        sources = []
        
        for doc_id in request.document_ids:
            doc_query = text("""
                SELECT 
                    d.id, d.document_name, d.document_type, 
                    d.file_path, d.mime_type, d.uploaded_at,
                    c.contract_number, c.contract_title
                FROM documents d
                LEFT JOIN contracts c ON d.contract_id = c.id
                WHERE d.id = :doc_id
            """)
            doc = db.execute(doc_query, {"doc_id": doc_id}).fetchone()
            
            if doc:
                # Try to read file content for text files
                content_preview = "Document content not available for preview"
                try:
                    if doc.file_path and os.path.exists(doc.file_path):
                        if doc.mime_type in ['text/plain', 'application/rtf'] or \
                           doc.file_path.endswith(('.txt', '.md', '.rtf')):
                            with open(doc.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content_preview = f.read()[:5000]
                except Exception as e:
                    logger.warning(f"Could not read file {doc.file_path}: {e}")
                
                doc_contents.append({
                    "id": str(doc.id),
                    "name": doc.document_name,
                    "type": doc.document_type,
                    "content_preview": content_preview,
                    "contract_number": doc.contract_number,
                    "contract_title": doc.contract_title,
                    "date": doc.uploaded_at.isoformat() if doc.uploaded_at else None
                })
                
                sources.append({
                    "document_id": str(doc.id),
                    "document_name": doc.document_name,
                    "document_type": doc.document_type
                })
        
        if not doc_contents:
            logger.warning("No documents found for analysis")
            return AnalysisResponse(
                success=False,
                content="No documents found for analysis. Please select valid documents.",
                confidence=0.0,
                processing_time=time.time() - start_time,
                sources=[],
                recommendations=[],
                key_points=[],
                suggested_actions=[],
                tokens_used=0,
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Call ClaudeService.analyze_correspondence (the correct method)
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
            
            # Extract values from the AI result
            content = ai_result.get("analysis_text") or ai_result.get("content") or "Analysis completed."
            confidence = ai_result.get("confidence_score", 75.0)
            tokens_used = ai_result.get("tokens_used", 0)
            key_points = ai_result.get("key_points", ["Document review completed"])
            recommendations = ai_result.get("recommendations", ["Review analysis results"])
            suggested_actions = ai_result.get("suggested_actions", ["Follow up on findings"])
            
        except Exception as claude_error:
            logger.error(f"❌ Claude service error: {str(claude_error)}")
            
            # Generate fallback response
            content = generate_fallback_analysis(request.query, doc_contents)
            confidence = 65.0
            tokens_used = 0
            key_points = ["Document review completed", "Manual analysis recommended"]
            recommendations = ["Consult with legal team", "Review all referenced clauses"]
            suggested_actions = ["Schedule follow-up meeting", "Document all decisions"]
        
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            success=True,
            content=content,
            confidence=confidence,
            processing_time=processing_time,
            sources=sources,
            recommendations=recommendations,
            key_points=key_points,
            suggested_actions=suggested_actions,
            tokens_used=tokens_used,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Analysis error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            success=False,
            content=f"Analysis failed: {str(e)}",
            confidence=0.0,
            processing_time=processing_time,
            sources=[],
            recommendations=[],
            key_points=[],
            suggested_actions=[],
            tokens_used=0,
            timestamp=datetime.utcnow().isoformat()
        )


# =====================================================
# CREATE CORRESPONDENCE
# =====================================================
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_correspondence(
    correspondence: CorrespondenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new correspondence record"""
    try:
        corr_id = str(uuid.uuid4())
        
        insert_query = text("""
            INSERT INTO correspondence (
                id, contract_id, correspondence_type, subject, content,
                sender_id, priority, status, is_ai_generated, ai_tone, created_at
            ) VALUES (
                :id, :contract_id, :type, :subject, :content,
                :sender_id, :priority, 'draft', :is_ai, :tone, :created_at
            )
        """)
        
        db.execute(insert_query, {
            "id": corr_id,
            "contract_id": correspondence.contract_id,
            "type": correspondence.correspondence_type,
            "subject": correspondence.subject,
            "content": correspondence.content,
            "sender_id": str(current_user.id),
            "priority": correspondence.priority,
            "is_ai": correspondence.tone is not None,
            "tone": correspondence.tone,
            "created_at": datetime.utcnow()
        })
        
        db.commit()
        
        logger.info(f"✅ Created correspondence: {corr_id}")
        
        return {
            "success": True,
            "id": corr_id,
            "message": "Correspondence created successfully"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating correspondence: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create correspondence: {str(e)}"
        )


# =====================================================
# LIST CORRESPONDENCE
# =====================================================
@router.get("/")
async def list_correspondence(
    contract_id: Optional[str] = None,
    status: Optional[str] = None,
    correspondence_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all correspondence with optional filters"""
    try:
        query_str = """
            SELECT 
                c.id, c.contract_id, c.correspondence_type, c.subject,
                c.content, c.sender_id, c.priority, c.status,
                c.is_ai_generated, c.ai_tone, c.created_at,
                u.first_name, u.last_name, u.email as sender_email
            FROM correspondence c
            LEFT JOIN users u ON c.sender_id = u.id
            WHERE c.sender_id = :user_id
        """
        params = {"user_id": str(current_user.id)}
        
        if contract_id:
            query_str += " AND c.contract_id = :contract_id"
            params["contract_id"] = contract_id
            
        if status:
            query_str += " AND c.status = :status"
            params["status"] = status
            
        if correspondence_type:
            query_str += " AND c.correspondence_type = :type"
            params["type"] = correspondence_type
        
        query_str += " ORDER BY c.created_at DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        result = db.execute(text(query_str), params).fetchall()
        
        items = []
        for row in result:
            items.append({
                "id": row.id,
                "contract_id": row.contract_id,
                "correspondence_type": row.correspondence_type,
                "subject": row.subject,
                "content": row.content[:200] + "..." if len(row.content or "") > 200 else row.content,
                "sender_name": f"{row.first_name} {row.last_name}",
                "sender_email": row.sender_email,
                "priority": row.priority,
                "status": row.status,
                "is_ai_generated": row.is_ai_generated,
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        return {
            "success": True,
            "items": items,
            "total": len(items),
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing correspondence: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list correspondence: {str(e)}"
        )


# =====================================================
# DELETE DOCUMENT
# =====================================================
@router.delete("/documents/{document_id}")
async def delete_correspondence_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document"""
    try:
        # Check document exists
        check_query = text("""
            SELECT id, file_path, document_name
            FROM documents
            WHERE id = :document_id
        """)
        result = db.execute(check_query, {"document_id": document_id}).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete file from disk
        try:
            if result.file_path and os.path.exists(result.file_path):
                os.remove(result.file_path)
                logger.info(f"🗑️ Deleted file: {result.file_path}")
        except Exception as file_error:
            logger.warning(f"⚠️ Could not delete file: {file_error}")
        
        # Delete from database
        delete_query = text("DELETE FROM documents WHERE id = :document_id")
        db.execute(delete_query, {"document_id": document_id})
        db.commit()
        
        logger.info(f"✅ Document deleted: {document_id}")
        
        return {
            "success": True,
            "message": f"Document '{result.document_name}' deleted successfully",
            "document_id": document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )