# app/api/api_v1/correspondence/upload.py
"""
Document Upload API for Correspondence Management
Handles file uploads with validation, storage, and database integration
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import hashlib
import json
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
    'eml': 'message/rfc822'
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_BATCH_SIZE = 10
UPLOAD_BASE_DIR = Path("app/uploads/correspondence")


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower().replace('.', '')
    
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type .{file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS.keys())}"
    
    # Check content type
    expected_mime = ALLOWED_EXTENSIONS.get(file_ext)
    if file.content_type != expected_mime and not file.content_type.startswith(expected_mime.split('/')[0]):
        return False, f"Invalid content type for .{file_ext} file"
    
    return True, "Valid"


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


def save_file_to_disk(
    content: bytes,
    filename: str,
    project_id: int,
    company_id: int
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
    return str(file_path.relative_to(Path("app")))


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
    - **notes**: Optional notes about the upload
    """
    
    try:
        # Validate batch size
        if len(files) > MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {MAX_BATCH_SIZE} files allowed per upload"
            )
        
        # Verify project exists and user has access
        from sqlalchemy import text
        
        project_query = text("""
            SELECT id, company_id, title 
            FROM projects 
            WHERE id = :project_id AND company_id = :company_id
        """)
        
        project = db.execute(project_query, {
            "project_id": project_id,
            "company_id": current_user.company_id
        }).fetchone()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        uploaded_documents = []
        errors = []
        
        for file in files:
            try:
                # Read file content
                content = await file.read()
                file_size = len(content)
                
                # Validate file size
                if file_size > MAX_FILE_SIZE:
                    errors.append({
                        "filename": file.filename,
                        "error": f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size (50MB)"
                    })
                    continue
                
                # Validate file type
                is_valid, message = validate_file(file)
                if not is_valid:
                    errors.append({
                        "filename": file.filename,
                        "error": message
                    })
                    continue
                
                # Calculate file hash for integrity
                file_hash = calculate_file_hash(content)
                
                # Check for duplicate files
                duplicate_query = text("""
                    SELECT id, name FROM project_documents 
                    WHERE project_id = :project_id 
                    AND file_hash = :file_hash
                    LIMIT 1
                """)
                
                duplicate = db.execute(duplicate_query, {
                    "project_id": project_id,
                    "file_hash": file_hash
                }).fetchone()
                
                if duplicate:
                    errors.append({
                        "filename": file.filename,
                        "error": f"Duplicate file already exists: {duplicate.name}"
                    })
                    continue
                
                # Save file to disk
                file_path = save_file_to_disk(
                    content,
                    file.filename,
                    project_id,
                    current_user.company_id
                )
                
                # Insert into database
                insert_query = text("""
                    INSERT INTO project_documents (
                        project_id,
                        company_id,
                        name,
                        type,
                        file_path,
                        file_size,
                        file_hash,
                        mime_type,
                        document_type,
                        notes,
                        uploaded_by,
                        uploaded_at,
                        status
                    ) VALUES (
                        :project_id,
                        :company_id,
                        :name,
                        :type,
                        :file_path,
                        :file_size,
                        :file_hash,
                        :mime_type,
                        :document_type,
                        :notes,
                        :uploaded_by,
                        :uploaded_at,
                        :status
                    )
                """)
                
                result = db.execute(insert_query, {
                    "project_id": project_id,
                    "company_id": current_user.company_id,
                    "name": file.filename,
                    "type": Path(file.filename).suffix.lower().replace('.', ''),
                    "file_path": file_path,
                    "file_size": file_size,
                    "file_hash": file_hash,
                    "mime_type": file.content_type,
                    "document_type": document_type,
                    "notes": notes,
                    "uploaded_by": current_user.id,
                    "uploaded_at": datetime.utcnow(),
                    "status": "active"
                })
                
                db.commit()
                document_id = result.lastrowid
                
                # Create audit log
                audit_query = text("""
                    INSERT INTO audit_logs (
                        event_type, user_id, project_id, document_id, 
                        note, event_time
                    ) VALUES (
                        :event_type, :user_id, :project_id, :document_id,
                        :note, :event_time
                    )
                """)
                
                db.execute(audit_query, {
                    "event_type": "document_uploaded",
                    "user_id": current_user.id,
                    "project_id": project_id,
                    "document_id": document_id,
                    "note": f"Document '{file.filename}' uploaded to project",
                    "event_time": datetime.utcnow()
                })
                
                db.commit()
                
                uploaded_documents.append({
                    "id": document_id,
                    "name": file.filename,
                    "type": Path(file.filename).suffix.lower().replace('.', ''),
                    "size": file_size,
                    "size_formatted": f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / 1024 / 1024:.1f} MB",
                    "uploaded_at": datetime.utcnow().isoformat()
                })
                
                logger.info(f"Document uploaded: {file.filename} (ID: {document_id}) by user {current_user.email}")
                
            except Exception as e:
                logger.error(f"Error uploading file {file.filename}: {str(e)}")
                errors.append({
                    "filename": file.filename,
                    "error": f"Upload failed: {str(e)}"
                })
                db.rollback()
        
        # Prepare response
        response = {
            "success": True,
            "message": f"Successfully uploaded {len(uploaded_documents)} of {len(files)} files",
            "data": {
                "uploaded": uploaded_documents,
                "errors": errors,
                "project_id": project_id,
                "project_title": project.title
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload failed: {str(e)}"
        )


@router.get("/upload-limits")
async def get_upload_limits():
    """Get upload limits and allowed file types"""
    return {
        "success": True,
        "data": {
            "max_file_size": MAX_FILE_SIZE,
            "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
            "max_batch_size": MAX_BATCH_SIZE,
            "allowed_extensions": list(ALLOWED_EXTENSIONS.keys()),
            "allowed_mime_types": list(ALLOWED_EXTENSIONS.values())
        }
    }