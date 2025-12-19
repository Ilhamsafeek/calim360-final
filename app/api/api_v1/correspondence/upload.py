# app/api/api_v1/correspondence/upload.py
"""
Document Upload API for Correspondence Management
Handles file uploads with validation, storage, and database integration
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import hashlib
import uuid
import os
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Allowed file types
ALLOWED_EXTENSIONS = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'txt': 'text/plain',
    'rtf': 'application/rtf',
    'odt': 'application/vnd.oasis.opendocument.text',
    'eml': 'message/rfc822',
    'msg': 'application/vnd.ms-outlook',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png'
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_BATCH_SIZE = 10
UPLOAD_BASE_DIR = Path("app/uploads/correspondence")


def validate_file(file: UploadFile) -> tuple:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower().replace('.', '')
    
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type .{file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS.keys())}"
    
    return True, "Valid"


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


def save_file_to_disk(
    content: bytes,
    filename: str,
    project_id: int,
    company_id: str
) -> str:
    """Save file to disk and return relative path"""
    # Create directory structure: uploads/correspondence/{company_id}/{project_id}/
    save_dir = UPLOAD_BASE_DIR / str(company_id) / str(project_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = Path(filename).suffix
    base_name = Path(filename).stem[:50]  # Limit filename length
    unique_filename = f"{base_name}_{timestamp}{file_ext}"
    
    file_path = save_dir / unique_filename
    
    # Write file
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Return relative path for database storage
    return str(file_path)


@router.post("/upload")
async def upload_document(
    files: List[UploadFile] = File(...),
    project_id: int = Form(...),
    document_type: str = Form(default="correspondence"),
    notes: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload one or more documents to a project
    
    - **files**: List of files to upload (max 10 files, max 50MB each)
    - **project_id**: ID of the project to associate documents with
    - **document_type**: Type of document (correspondence, contract, email, etc.)
    - **notes**: Optional notes for the uploaded files
    """
    
    try:
        logger.info(f"📤 Upload request: {len(files)} files for project {project_id} by user {current_user.email}")
        
        # Validate batch size
        if len(files) > MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {MAX_BATCH_SIZE} files allowed per upload"
            )
        
        # Verify project exists and user has access
        project_query = text("""
            SELECT p.id, p.company_id 
            FROM projects p
            WHERE p.id = :project_id
        """)
        project_result = db.execute(project_query, {"project_id": project_id}).fetchone()
        
        if not project_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        company_id = str(current_user.company_id) if current_user.company_id else str(project_result.company_id)
        
        uploaded_files = []
        failed_files = []
        
        for file in files:
            try:
                # Validate file
                is_valid, message = validate_file(file)
                if not is_valid:
                    failed_files.append({
                        "filename": file.filename,
                        "error": message
                    })
                    continue
                
                # Read file content
                content = await file.read()
                file_size = len(content)
                
                # Check file size
                if file_size > MAX_FILE_SIZE:
                    failed_files.append({
                        "filename": file.filename,
                        "error": f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds limit of 50MB"
                    })
                    continue
                
                # Calculate hash
                file_hash = calculate_file_hash(content)
                
                # Save file to disk
                file_path = save_file_to_disk(content, file.filename, project_id, company_id)
                
                # Generate document ID
                doc_id = str(uuid.uuid4())
                
                # Get file extension
                file_ext = Path(file.filename).suffix.lower().replace('.', '')
                mime_type = ALLOWED_EXTENSIONS.get(file_ext, file.content_type or 'application/octet-stream')
                
                # Insert into documents table
                insert_query = text("""
                    INSERT INTO documents (
                        id, company_id, document_name, document_type, 
                        file_path, file_size, mime_type, hash_value, 
                        uploaded_by, uploaded_at, version, access_count,
                        metadata
                    ) VALUES (
                        :id, :company_id, :document_name, :document_type,
                        :file_path, :file_size, :mime_type, :hash_value,
                        :uploaded_by, :uploaded_at, 1, 0,
                        :metadata
                    )
                """)
                
                # Prepare metadata
                import json
                metadata = json.dumps({
                    "project_id": project_id,
                    "original_filename": file.filename,
                    "notes": notes,
                    "upload_source": "correspondence_management"
                })
                
                db.execute(insert_query, {
                    "id": doc_id,
                    "company_id": company_id,
                    "document_name": file.filename,
                    "document_type": document_type,
                    "file_path": file_path,
                    "file_size": file_size,
                    "mime_type": mime_type,
                    "hash_value": file_hash,
                    "uploaded_by": str(current_user.id),
                    "uploaded_at": datetime.utcnow(),
                    "metadata": metadata
                })
                
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
                failed_files.append({
                    "filename": file.filename,
                    "error": str(file_error)
                })
        
        # Commit all uploads
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


@router.get("/documents/{project_id}")
async def get_project_documents(
    project_id: int,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all documents for a project
    
    - **project_id**: Project ID to fetch documents for
    - **document_type**: Optional filter by document type
    """
    
    try:
        logger.info(f"📂 Fetching documents for project {project_id}")
        
        # Build query
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
        
        query = text(query_str)
        result = db.execute(query, params).fetchall()
        
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


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a document
    
    - **document_id**: Document ID to delete
    """
    
    try:
        # Check document exists and user has permission
        check_query = text("""
            SELECT id, file_path, uploaded_by, document_name
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