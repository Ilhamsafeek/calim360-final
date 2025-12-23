# =====================================================
# FILE: app/api/api_v1/correspondence/crud.py
# Database CRUD Operations for Correspondence
# =====================================================

from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


# =====================================================
# CREATE OPERATIONS
# =====================================================

def create_correspondence(
    db: Session,
    correspondence_data: Dict[str, Any],
    sender_id: str
) -> Optional[Dict[str, Any]]:
    """Create new correspondence record"""
    
    try:
        # Generate UUID for the new record
        import uuid
        correspondence_id = str(uuid.uuid4())
        
        query = text("""
            INSERT INTO correspondence (
                id, contract_id, correspondence_type, subject, content,
                sender_id, recipient_ids, cc_ids, priority, status,
                is_ai_generated, ai_tone, sent_at, created_at
            ) VALUES (
                :id, :contract_id, :correspondence_type, :subject, :content,
                :sender_id, :recipient_ids, :cc_ids, :priority, :status,
                :is_ai_generated, :ai_tone, :sent_at, NOW()
            )
        """)
        
        db.execute(query, {
            "id": correspondence_id,
            "contract_id": correspondence_data.get("contract_id"),
            "correspondence_type": correspondence_data["correspondence_type"],
            "subject": correspondence_data["subject"],
            "content": correspondence_data["content"],
            "sender_id": sender_id,
            "recipient_ids": json.dumps(correspondence_data.get("recipient_ids", [])),
            "cc_ids": json.dumps(correspondence_data.get("cc_ids", [])),
            "priority": correspondence_data.get("priority", "normal"),
            "status": correspondence_data.get("status", "draft"),
            "is_ai_generated": correspondence_data.get("is_ai_generated", False),
            "ai_tone": correspondence_data.get("ai_tone"),
            "sent_at": datetime.utcnow() if correspondence_data.get("status") == "sent" else None
        })
        
        db.commit()
        
        # Get the created record
        result = db.execute(text("""
            SELECT c.*, 
                   CONCAT(u.first_name, ' ', u.last_name) as sender_name,
                   u.email as sender_email,
                   (SELECT COUNT(*) FROM correspondence_attachments WHERE correspondence_id = c.id) as attachments_count
            FROM correspondence c
            LEFT JOIN users u ON c.sender_id = u.id
            WHERE c.id = :correspondence_id
        """), {"correspondence_id": correspondence_id})
        
        row = result.fetchone()
        if row:
            item = dict(row._mapping)
            item['recipient_ids'] = json.loads(item.get('recipient_ids', '[]') or '[]')
            item['cc_ids'] = json.loads(item.get('cc_ids', '[]') or '[]')
            return item
        
        return None
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error creating correspondence: {str(e)}")
        raise


# =====================================================
# READ OPERATIONS
# =====================================================

def get_correspondence_list(
    db: Session,
    company_id: int,
    page: int = 1,
    page_size: int = 20,
    correspondence_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    contract_id: Optional[str] = None,
    is_ai_generated: Optional[bool] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get correspondence list with filters"""
    
    try:
        # Build WHERE clause
        where_clauses = ["u.company_id = :company_id"]
        params = {
            "company_id": company_id, 
            "offset": (page - 1) * page_size, 
            "limit": page_size
        }
        
        if correspondence_type:
            where_clauses.append("c.correspondence_type = :correspondence_type")
            params["correspondence_type"] = correspondence_type
            
        if status:
            where_clauses.append("c.status = :status")
            params["status"] = status
            
        if priority:
            where_clauses.append("c.priority = :priority")
            params["priority"] = priority
        
        if contract_id:
            where_clauses.append("c.contract_id = :contract_id")
            params["contract_id"] = contract_id
        
        if is_ai_generated is not None:
            where_clauses.append("c.is_ai_generated = :is_ai_generated")
            params["is_ai_generated"] = is_ai_generated
        
        if date_from:
            where_clauses.append("c.created_at >= :date_from")
            params["date_from"] = date_from
        
        if date_to:
            where_clauses.append("c.created_at <= :date_to")
            params["date_to"] = date_to
            
        if search:
            where_clauses.append("(c.subject LIKE :search OR c.content LIKE :search)")
            params["search"] = f"%{search}%"
        
        where_sql = " AND ".join(where_clauses)
        
        # Get total count
        count_query = text(f"""
            SELECT COUNT(*) as total
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            WHERE {where_sql}
        """)
        
        total = db.execute(count_query, params).fetchone()[0]
        
        # Get correspondence list
        list_query = text(f"""
            SELECT c.*,
                   CONCAT(u.first_name, ' ', u.last_name) as sender_name,
                   u.email as sender_email,
                   (SELECT COUNT(*) FROM correspondence_attachments WHERE correspondence_id = c.id) as attachments_count,
                   con.contract_number,
                   con.contract_title
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            LEFT JOIN contracts con ON c.contract_id = con.id
            WHERE {where_sql}
            ORDER BY c.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        results = db.execute(list_query, params).fetchall()
        
        items = []
        for row in results:
            item = dict(row._mapping)
            # Parse JSON fields
            item['recipient_ids'] = json.loads(item.get('recipient_ids', '[]') or '[]')
            item['cc_ids'] = json.loads(item.get('cc_ids', '[]') or '[]')
            items.append(item)
        
        return {
            "total": total,
            "items": items,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        logger.error(f" Error fetching correspondence list: {str(e)}")
        raise


def get_correspondence_by_id(
    db: Session,
    correspondence_id: str
) -> Optional[Dict[str, Any]]:
    """Get single correspondence by ID with full details"""
    
    try:
        query = text("""
            SELECT c.*,
                   CONCAT(u.first_name, ' ', u.last_name) as sender_name,
                   u.email as sender_email,
                   con.contract_number,
                   con.contract_title
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            LEFT JOIN contracts con ON c.contract_id = con.id
            WHERE c.id = :correspondence_id
        """)
        
        result = db.execute(query, {"correspondence_id": correspondence_id}).fetchone()
        
        if result:
            item = dict(result._mapping)
            # Parse JSON fields
            item['recipient_ids'] = json.loads(item.get('recipient_ids', '[]') or '[]')
            item['cc_ids'] = json.loads(item.get('cc_ids', '[]') or '[]')
            
            # Get attachments
            attachments_query = text("""
                SELECT 
                    ca.id,
                    ca.attachment_name,
                    ca.attachment_type,
                    ca.file_size,
                    ca.uploaded_at,
                    d.file_path as file_url
                FROM correspondence_attachments ca
                LEFT JOIN documents d ON ca.document_id = d.id
                WHERE ca.correspondence_id = :correspondence_id
                ORDER BY ca.uploaded_at DESC
            """)
            
            attachments_result = db.execute(
                attachments_query, 
                {"correspondence_id": correspondence_id}
            ).fetchall()
            
            item['attachments'] = [dict(row._mapping) for row in attachments_result]
            item['attachments_count'] = len(item['attachments'])
            
            return item
        
        return None
        
    except Exception as e:
        logger.error(f" Error fetching correspondence by ID: {str(e)}")
        raise


def get_documents_by_ids(
    db: Session,
    document_ids: List[str]
) -> List[Dict[str, Any]]:
    """Get documents by IDs for AI processing"""
    
    if not document_ids:
        return []
    
    try:
        # Use proper parameterized query for IN clause
        placeholders = ','.join([f":doc_id_{i}" for i in range(len(document_ids))])
        params = {f"doc_id_{i}": doc_id for i, doc_id in enumerate(document_ids)}
        
        query = text(f"""
            SELECT 
                id, 
                document_name, 
                document_type, 
                file_path, 
                mime_type,
                extracted_text,
                file_size
            FROM documents
            WHERE id IN ({placeholders})
        """)
        
        results = db.execute(query, params).fetchall()
        return [dict(row._mapping) for row in results]
        
    except Exception as e:
        logger.error(f" Error fetching documents by IDs: {str(e)}")
        return []


# =====================================================
# UPDATE OPERATIONS
# =====================================================

def update_correspondence(
    db: Session,
    correspondence_id: str,
    update_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Update correspondence record"""
    
    try:
        # Build dynamic update query
        update_fields = []
        params = {"correspondence_id": correspondence_id}
        
        if "subject" in update_data:
            update_fields.append("subject = :subject")
            params["subject"] = update_data["subject"]
        
        if "content" in update_data:
            update_fields.append("content = :content")
            params["content"] = update_data["content"]
        
        if "status" in update_data:
            update_fields.append("status = :status")
            params["status"] = update_data["status"]
            
            # Auto-set sent_at when status changes to 'sent'
            if update_data["status"] == "sent":
                update_fields.append("sent_at = NOW()")
        
        if "priority" in update_data:
            update_fields.append("priority = :priority")
            params["priority"] = update_data["priority"]
        
        if "recipient_ids" in update_data:
            update_fields.append("recipient_ids = :recipient_ids")
            params["recipient_ids"] = json.dumps(update_data["recipient_ids"])
        
        if "cc_ids" in update_data:
            update_fields.append("cc_ids = :cc_ids")
            params["cc_ids"] = json.dumps(update_data["cc_ids"])
        
        if not update_fields:
            # No fields to update
            return get_correspondence_by_id(db, correspondence_id)
        
        update_query = text(f"""
            UPDATE correspondence
            SET {', '.join(update_fields)}
            WHERE id = :correspondence_id
        """)
        
        db.execute(update_query, params)
        db.commit()
        
        # Return updated record
        return get_correspondence_by_id(db, correspondence_id)
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error updating correspondence: {str(e)}")
        raise


def update_correspondence_status(
    db: Session,
    correspondence_id: str,
    status: str
) -> bool:
    """Update correspondence status"""
    
    try:
        query = text("""
            UPDATE correspondence
            SET status = :status,
                sent_at = CASE 
                    WHEN :status = 'sent' AND sent_at IS NULL THEN NOW() 
                    ELSE sent_at 
                END,
                read_at = CASE 
                    WHEN :status = 'read' AND read_at IS NULL THEN NOW() 
                    ELSE read_at 
                END
            WHERE id = :correspondence_id
        """)
        
        result = db.execute(query, {
            "correspondence_id": correspondence_id,
            "status": status
        })
        
        db.commit()
        
        return result.rowcount > 0
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error updating correspondence status: {str(e)}")
        return False


# =====================================================
# DELETE OPERATIONS
# =====================================================

def delete_correspondence_record(
    db: Session,
    correspondence_id: str
) -> bool:
    """Delete correspondence record (hard delete)"""
    
    try:
        # Delete attachments first (foreign key constraint)
        delete_attachments = text("""
            DELETE FROM correspondence_attachments
            WHERE correspondence_id = :correspondence_id
        """)
        db.execute(delete_attachments, {"correspondence_id": correspondence_id})
        
        # Delete correspondence
        delete_corr = text("""
            DELETE FROM correspondence
            WHERE id = :correspondence_id
        """)
        result = db.execute(delete_corr, {"correspondence_id": correspondence_id})
        
        db.commit()
        
        return result.rowcount > 0
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error deleting correspondence: {str(e)}")
        return False


def archive_correspondence(
    db: Session,
    correspondence_id: str
) -> bool:
    """Archive correspondence (soft delete)"""
    
    try:
        query = text("""
            UPDATE correspondence
            SET status = 'archived'
            WHERE id = :correspondence_id
        """)
        
        result = db.execute(query, {"correspondence_id": correspondence_id})
        db.commit()
        
        return result.rowcount > 0
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error archiving correspondence: {str(e)}")
        return False


# =====================================================
# ATTACHMENT OPERATIONS
# =====================================================

def create_correspondence_attachment(
    db: Session,
    correspondence_id: str,
    document_id: Optional[str] = None,
    attachment_name: str = None,
    attachment_type: Optional[str] = None,
    file_size: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Create correspondence attachment record"""
    
    try:
        import uuid
        attachment_id = str(uuid.uuid4())
        
        query = text("""
            INSERT INTO correspondence_attachments (
                id, correspondence_id, document_id, 
                attachment_name, attachment_type, file_size, uploaded_at
            ) VALUES (
                :id, :correspondence_id, :document_id,
                :attachment_name, :attachment_type, :file_size, NOW()
            )
        """)
        
        db.execute(query, {
            "id": attachment_id,
            "correspondence_id": correspondence_id,
            "document_id": document_id,
            "attachment_name": attachment_name,
            "attachment_type": attachment_type,
            "file_size": file_size
        })
        
        db.commit()
        
        # Return created attachment
        result = db.execute(text("""
            SELECT * FROM correspondence_attachments
            WHERE id = :attachment_id
        """), {"attachment_id": attachment_id}).fetchone()
        
        return dict(result._mapping) if result else None
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error creating attachment: {str(e)}")
        raise


def get_correspondence_attachments(
    db: Session,
    correspondence_id: str
) -> List[Dict[str, Any]]:
    """Get all attachments for a correspondence"""
    
    try:
        query = text("""
            SELECT 
                ca.id,
                ca.attachment_name,
                ca.attachment_type,
                ca.file_size,
                ca.uploaded_at,
                d.file_path as file_url,
                d.document_name
            FROM correspondence_attachments ca
            LEFT JOIN documents d ON ca.document_id = d.id
            WHERE ca.correspondence_id = :correspondence_id
            ORDER BY ca.uploaded_at DESC
        """)
        
        results = db.execute(query, {"correspondence_id": correspondence_id}).fetchall()
        return [dict(row._mapping) for row in results]
        
    except Exception as e:
        logger.error(f" Error fetching attachments: {str(e)}")
        return []


def delete_correspondence_attachment(
    db: Session,
    attachment_id: str
) -> bool:
    """Delete correspondence attachment"""
    
    try:
        query = text("""
            DELETE FROM correspondence_attachments
            WHERE id = :attachment_id
        """)
        
        result = db.execute(query, {"attachment_id": attachment_id})
        db.commit()
        
        return result.rowcount > 0
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error deleting attachment: {str(e)}")
        return False


# =====================================================
# STATISTICS & ANALYTICS
# =====================================================

def get_correspondence_statistics(
    db: Session,
    company_id: int,
    contract_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get correspondence statistics"""
    
    try:
        # Build WHERE clause
        where_clauses = ["u.company_id = :company_id"]
        params = {"company_id": company_id}
        
        if contract_id:
            where_clauses.append("c.contract_id = :contract_id")
            params["contract_id"] = contract_id
        
        if date_from:
            where_clauses.append("c.created_at >= :date_from")
            params["date_from"] = date_from
        
        if date_to:
            where_clauses.append("c.created_at <= :date_to")
            params["date_to"] = date_to
        
        where_sql = " AND ".join(where_clauses)
        
        # Total count
        total_query = text(f"""
            SELECT COUNT(*) as total
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            WHERE {where_sql}
        """)
        total = db.execute(total_query, params).fetchone()[0]
        
        # By status
        status_query = text(f"""
            SELECT c.status, COUNT(*) as count
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            WHERE {where_sql}
            GROUP BY c.status
        """)
        status_results = db.execute(status_query, params).fetchall()
        by_status = {row.status: row.count for row in status_results}
        
        # By type
        type_query = text(f"""
            SELECT c.correspondence_type, COUNT(*) as count
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            WHERE {where_sql}
            GROUP BY c.correspondence_type
        """)
        type_results = db.execute(type_query, params).fetchall()
        by_type = {row.correspondence_type: row.count for row in type_results}
        
        # By priority
        priority_query = text(f"""
            SELECT c.priority, COUNT(*) as count
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            WHERE {where_sql}
            GROUP BY c.priority
        """)
        priority_results = db.execute(priority_query, params).fetchall()
        by_priority = {row.priority: row.count for row in priority_results}
        
        # AI generated count
        ai_query = text(f"""
            SELECT COUNT(*) as count
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            WHERE {where_sql} AND c.is_ai_generated = 1
        """)
        ai_count = db.execute(ai_query, params).fetchone()[0]
        
        # Pending (draft status)
        pending = by_status.get('draft', 0)
        
        # Overdue (high/urgent priority drafts older than 24 hours)
        overdue_query = text(f"""
            SELECT COUNT(*) as count
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            WHERE {where_sql}
            AND c.status = 'draft'
            AND c.priority IN ('high', 'urgent')
            AND c.created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        overdue = db.execute(overdue_query, params).fetchone()[0]
        
        # Calculate percentages
        ai_percentage = (ai_count / total * 100) if total > 0 else 0.0
        
        return {
            "total_count": total,
            "by_status": by_status,
            "by_type": by_type,
            "by_priority": by_priority,
            "ai_generated_count": ai_count,
            "ai_generated_percentage": round(ai_percentage, 2),
            "avg_response_time": None,  # TODO: Calculate from actual data
            "pending_responses": pending,
            "overdue_count": overdue
        }
        
    except Exception as e:
        logger.error(f" Error generating statistics: {str(e)}")
        raise


def get_correspondence_trends(
    db: Session,
    company_id: int,
    period: str = "daily",  # daily, weekly, monthly
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get correspondence trends over time"""
    
    try:
        # Determine date grouping
        date_format = {
            "daily": "%Y-%m-%d",
            "weekly": "%Y-%U",
            "monthly": "%Y-%m"
        }.get(period, "%Y-%m-%d")
        
        where_clauses = ["u.company_id = :company_id"]
        params = {"company_id": company_id}
        
        if date_from:
            where_clauses.append("c.created_at >= :date_from")
            params["date_from"] = date_from
        
        if date_to:
            where_clauses.append("c.created_at <= :date_to")
            params["date_to"] = date_to
        
        where_sql = " AND ".join(where_clauses)
        
        query = text(f"""
            SELECT 
                DATE_FORMAT(c.created_at, :date_format) as date,
                COUNT(*) as count
            FROM correspondence c
            JOIN users u ON c.sender_id = u.id
            WHERE {where_sql}
            GROUP BY DATE_FORMAT(c.created_at, :date_format)
            ORDER BY date ASC
        """)
        
        params["date_format"] = date_format
        
        results = db.execute(query, params).fetchall()
        
        data_points = [
            {"date": row.date, "count": row.count}
            for row in results
        ]
        
        total_in_period = sum(point["count"] for point in data_points)
        
        # Calculate growth (compare with previous period)
        # TODO: Implement growth calculation
        growth_percentage = 0.0
        
        return {
            "period": period,
            "data_points": data_points,
            "total_in_period": total_in_period,
            "growth_percentage": growth_percentage
        }
        
    except Exception as e:
        logger.error(f" Error generating trends: {str(e)}")
        raise


# =====================================================
# BULK OPERATIONS
# =====================================================

def bulk_update_correspondence_status(
    db: Session,
    correspondence_ids: List[str],
    status: str
) -> int:
    """Bulk update correspondence status"""
    
    try:
        if not correspondence_ids:
            return 0
        
        placeholders = ','.join([f":corr_id_{i}" for i in range(len(correspondence_ids))])
        params = {f"corr_id_{i}": corr_id for i, corr_id in enumerate(correspondence_ids)}
        params["status"] = status
        
        query = text(f"""
            UPDATE correspondence
            SET status = :status,
                sent_at = CASE 
                    WHEN :status = 'sent' AND sent_at IS NULL THEN NOW() 
                    ELSE sent_at 
                END
            WHERE id IN ({placeholders})
        """)
        
        result = db.execute(query, params)
        db.commit()
        
        return result.rowcount
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error bulk updating status: {str(e)}")
        return 0


def bulk_delete_correspondence(
    db: Session,
    correspondence_ids: List[str]
) -> int:
    """Bulk delete correspondence"""
    
    try:
        if not correspondence_ids:
            return 0
        
        placeholders = ','.join([f":corr_id_{i}" for i in range(len(correspondence_ids))])
        params = {f"corr_id_{i}": corr_id for i, corr_id in enumerate(correspondence_ids)}
        
        # Delete attachments first
        delete_attach = text(f"""
            DELETE FROM correspondence_attachments
            WHERE correspondence_id IN ({placeholders})
        """)
        db.execute(delete_attach, params)
        
        # Delete correspondence
        delete_corr = text(f"""
            DELETE FROM correspondence
            WHERE id IN ({placeholders})
        """)
        result = db.execute(delete_corr, params)
        
        db.commit()
        
        return result.rowcount
        
    except Exception as e:
        db.rollback()
        logger.error(f" Error bulk deleting correspondence: {str(e)}")
        return 0