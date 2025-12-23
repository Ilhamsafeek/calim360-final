# =====================================================
# EXPERTS API ROUTER - FIXED VERSION
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from fastapi import Body

from app.api.api_v1.experts.schemas import (
    ExpertQueryCreate,
    ExpertQueryResponse,  # Make sure this is imported
    ExpertListResponse,
    QueryUpdateRequest,
    QueryDetailResponse,
    ConsultationSessionCreate,
    ConsultationSessionResponse,
    ExpertProfileResponse,
    ExpertAvailabilityResponse,
    ExpertStatsResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

def generate_query_code() -> str:
    """Generate unique query code: EXQ-YYYYMMDD-XXXXXXXX"""
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = str(uuid.uuid4())[:8].upper()
    return f"EXQ-{date_part}-{random_part}"

# =====================================================
# ASK AN EXPERT - CREATE QUERY - FIXED
# =====================================================
from fastapi import Body

@router.post("/queries")
async def create_expert_query(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create expert query - ACCEPTS ANY JSON"""
    try:
        query_id = str(uuid.uuid4())
        query_code = f"EXQ-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        logger.info(f" Creating query: {query_code}")
        logger.info(f" Data received: {data}")
        
        # Get values from dict
        query_type = data.get("query_type", "general")
        subject = data.get("subject", "No subject")
        question = data.get("question", "")
        priority = data.get("priority", "normal")
        
        # Get user info
        user_name = f"{current_user.first_name} {current_user.last_name}" if hasattr(current_user, 'first_name') else "User"
        user_email = current_user.email if hasattr(current_user, 'email') else "unknown"
        
        # Enhanced question
        enhanced_question = f"[User: {user_name} ({user_email})]\n\n{question}"
        
        # INSERT
        insert_sql = text("""
        INSERT INTO queries (
            id, query_code, query_type, subject, question,
            priority, status, asked_at
        ) VALUES (
            :id, :query_code, :query_type, :subject, :question,
            :priority, 'open', NOW()
        )
        """)
        
        db.execute(insert_sql, {
            "id": query_id,
            "query_code": query_code,
            "query_type": query_type,
            "subject": subject,
            "question": enhanced_question,
            "priority": priority
        })
        
        db.commit()
        
        logger.info(f" Query created: {query_code}")
        
        return {
            "success": True,
            "message": "Query submitted successfully",
            "query_id": query_id,
            "query_code": query_code,
            "status": "open",
            "asked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f" Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# EXPERT DIRECTORY - GET EXPERT LIST
# =====================================================
@router.get("/directory")
async def get_expert_directory(
    search: Optional[str] = None,
    expertise_area: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get expert directory with search and filters"""
    try:
        where_conditions = [
            "u.is_active = 1 AND COALESCE(LOWER(TRIM(u.user_type)), '') = 'expert'"
            ]
        params = {}
        
        # Search
        if search:
            where_conditions.append("""
                (LOWER(u.first_name) LIKE LOWER(:search) 
                OR LOWER(u.last_name) LIKE LOWER(:search)
                OR LOWER(u.email) LIKE LOWER(:search)
                OR LOWER(u.department) LIKE LOWER(:search)
                OR LOWER(ep.expertise_areas) LIKE LOWER(:search))
            """)
            params["search"] = f"%{search}%"
        
        # Filter by expertise area - Search in BOTH department AND expertise_areas
        if expertise_area and expertise_area != "all":
            where_conditions.append("""
                (LOWER(u.department) LIKE LOWER(:expertise_area) 
                OR LOWER(ep.expertise_areas) LIKE LOWER(:expertise_area))
            """)
            params["expertise_area"] = f"%{expertise_area}%"
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get total count
        count_sql = text(f"""
            SELECT COUNT(DISTINCT u.id)
            FROM users u
            LEFT JOIN expert_profiles ep ON u.id = ep.user_id
            {where_clause}
        """)
        
        total_result = db.execute(count_sql, params)
        total_count = total_result.scalar()
        
        # Get experts with details
        query_sql = text(f"""
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                u.email,
                u.mobile_number,
                u.profile_picture_url,
                u.department,
                u.job_title,
                ep.expertise_areas,
                ep.specialization,
                ep.license_number,
                ep.license_authority,
                ep.years_of_experience,
                ep.bio,
                ep.is_available,
                ep.hourly_rate,
                ep.total_consultations,
                ep.average_rating,
                ep.qfcra_certified,
                ep.qid_verified,
                (SELECT COUNT(*) FROM expert_queries 
                 WHERE user_id = u.id AND status IN ('open', 'in_progress')) as active_consultations
            FROM users u
            LEFT JOIN expert_profiles ep ON u.id = ep.user_id
            {where_clause}
            ORDER BY u.first_name ASC
            LIMIT :limit OFFSET :offset
        """)
        
        params["limit"] = limit
        params["offset"] = offset
        
        result = db.execute(query_sql, params)
        rows = result.fetchall()
        
        experts = []
        for row in rows:
            # Parse expertise areas
            expertise_areas = []
            if row[8]:  # expertise_areas from expert_profiles
                expertise_areas = [area.strip() for area in row[8].split(',')]
            elif row[6]:  # department from users
                expertise_areas = [row[6]]
            else:
                expertise_areas = ["General Consultation"]
            
            expert_data = {
                "expert_id": str(row[0]),
                "first_name": row[1] or "",
                "last_name": row[2] or "",
                "full_name": f"{row[1] or ''} {row[2] or ''}".strip(),
                "email": row[3],
                "phone": row[4],
                "profile_picture": row[5] or "/static/assets/images/default-avatar.png",
                "department": row[6],
                "job_title": row[7] or "Legal Expert",
                "expertise_areas": expertise_areas,
                "specialization": row[9] or row[7],
                "license_number": row[10],
                "license_authority": row[11],
                "years_of_experience": row[12] or 0,
                "bio": row[13],
                "is_available": bool(row[14]) if row[14] is not None else True,
                "hourly_rate": float(row[15]) if row[15] else 0.0,
                "total_consultations": row[16] or 0,
                "average_rating": float(row[17]) if row[17] else 4.5,
                "qfcra_certified": bool(row[18]) if row[18] is not None else False,
                "qid_verified": bool(row[19]) if row[19] is not None else False,
                "active_sessions": row[20] or 0,
                "availability_status": "available" if (row[14] if row[14] is not None else True) and (row[20] or 0) < 5 else "busy"
            }
            experts.append(expert_data)
        
        logger.info(f" Retrieved {len(experts)} experts (Total: {total_count}, Filter: {expertise_area})")
        
        return {
            "success": True,
            "experts": experts,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
        
    except Exception as e:
        logger.error(f" Error fetching expert directory: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch expert directory: {str(e)}"
        )

# =====================================================
# EXPERT DIRECTORY - GET STATISTICS
# =====================================================
@router.get("/stats")
async def get_expert_statistics(db: Session = Depends(get_db)):
    """Get statistics for expert directory dashboard"""
    try:
        stats_sql = text("""
            SELECT 
                COUNT(DISTINCT u.id) as total_experts,
                COUNT(DISTINCT CASE 
                    WHEN COALESCE(ep.is_available, 1) = 1 THEN u.id 
                END) as available_experts,
                AVG(CASE 
                    WHEN ep.average_rating > 0 THEN ep.average_rating 
                    ELSE 4.5 
                END) as avg_platform_rating,
                SUM(COALESCE(ep.total_consultations, 0)) as total_consultations
            FROM users u
            LEFT JOIN expert_profiles ep ON u.id = ep.user_id
            WHERE u.is_active = 1 
            AND COALESCE(LOWER(TRIM(u.user_type)), '') = 'expert'
        """)
        
        result = db.execute(stats_sql)
        row = result.fetchone()
        
        return {
            "total_experts": row[0] or 0,
            "available_now": row[1] or 0,
            "avg_response_time": "< 5 min",
            "platform_rating": round(row[2] or 4.5, 1),
            "total_consultations": row[3] or 0
        }
        
    except Exception as e:
        logger.error(f" Error fetching expert stats: {str(e)}")
        return {
            "total_experts": 0,
            "available_now": 0,
            "avg_response_time": "< 5 min",
            "platform_rating": 4.5,
            "total_consultations": 0
        }

# =====================================================
# EXPERT DIRECTORY - GET EXPERT PROFILE
# =====================================================
@router.get("/profile/{expert_id}")
async def get_expert_profile(
    expert_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed profile for a specific expert"""
    try:
        profile_sql = text("""
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                u.email,
                u.mobile_number,
                u.profile_picture_url,
                u.department,
                u.job_title,
                ep.expertise_areas,
                ep.specialization,
                ep.license_number,
                ep.license_authority,
                ep.years_of_experience,
                ep.bio,
                ep.is_available,
                ep.hourly_rate,
                ep.total_consultations,
                ep.average_rating,
                ep.qfcra_certified,
                ep.qid_verified
            FROM users u
            LEFT JOIN expert_profiles ep ON u.id = ep.user_id
            WHERE u.id = :expert_id AND u.is_active = 1
        """)
        
        result = db.execute(profile_sql, {"expert_id": int(expert_id)})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expert not found"
            )
        
        # Parse expertise areas
        expertise_areas = []
        if row[8]:
            expertise_areas = [area.strip() for area in row[8].split(',')]
        elif row[6]:
            expertise_areas = [row[6]]
        
        return {
            "expert_id": str(row[0]),
            "first_name": row[1],
            "last_name": row[2],
            "full_name": f"{row[1]} {row[2]}",
            "email": row[3],
            "phone": row[4],
            "profile_picture": row[5] or "/static/assets/images/default-avatar.png",
            "department": row[6],
            "job_title": row[7],
            "expertise_areas": expertise_areas,
            "specialization": row[9] or row[7],
            "license_number": row[10],
            "license_authority": row[11],
            "years_of_experience": row[12] or 0,
            "bio": row[13],
            "is_available": bool(row[14]) if row[14] is not None else True,
            "hourly_rate": float(row[15]) if row[15] else 0.0,
            "total_consultations": row[16] or 0,
            "average_rating": float(row[17]) if row[17] else 4.5,
            "qfcra_certified": bool(row[18]) if row[18] is not None else False,
            "qid_verified": bool(row[19]) if row[19] is not None else False,
            "recent_reviews": []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Error fetching expert profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch expert profile: {str(e)}"
        )

# Keep all your other endpoints exactly as they are...
# (get_my_queries, get_all_queries, get_available_experts, etc.)

# =====================================================
# FIXED: GET AVAILABLE EXPERTS WITH PROPER FILTERING
# =====================================================
@router.get("/available")
async def get_available_experts(
    expertise_area: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of available experts with proper expertise area filtering"""
    try:
        where_clause = """
        WHERE (u.user_role LIKE '%expert%' OR u.user_role LIKE '%legal%' OR u.user_type = 'expert') 
        AND u.is_active = 1
        """
        params = {}
        
        if expertise_area:
            where_clause += """ AND (
                LOWER(u.department) LIKE LOWER(:expertise_area) 
                OR LOWER(ep.expertise_areas) LIKE LOWER(:expertise_area)
            )"""
            params["expertise_area"] = f"%{expertise_area}%"
        
        query_sql = text(f"""
        SELECT DISTINCT
               u.id, 
               u.first_name, 
               u.last_name, 
               u.email,
               COALESCE(u.department, 'General') as department,
               u.profile_picture_url,
               COUNT(DISTINCT q.id) as active_consultations,
               ep.expertise_areas,
               ep.average_rating,
               ep.total_consultations,
               ep.is_available
        FROM users u
        LEFT JOIN expert_profiles ep ON ep.user_id = u.id
        LEFT JOIN queries q ON q.assigned_to = u.id AND q.status = 'open'
        {where_clause}
        GROUP BY u.id, u.first_name, u.last_name, u.email, u.department, 
                 u.profile_picture_url, ep.expertise_areas, ep.average_rating, 
                 ep.total_consultations, ep.is_available
        ORDER BY active_consultations ASC, u.first_name ASC
        """)
        
        result = db.execute(query_sql, params)
        rows = result.fetchall()
        
        experts = []
        for row in rows:
            expertise_list = []
            if row[7]:
                try:
                    import json
                    expertise_list = json.loads(row[7]) if isinstance(row[7], str) else row[7]
                except:
                    expertise_list = [e.strip() for e in row[7].split(',') if e.strip()]
            
            if not expertise_list and row[4]:
                expertise_list = [row[4]]
            
            if not expertise_list:
                expertise_list = ["General"]
            
            expert = {
                "expert_id": str(row[0]),
                "name": f"{row[1]} {row[2]}",
                "email": row[3],
                "expertise_areas": expertise_list,
                "profile_picture": row[5],
                "active_consultations": row[6],
                "availability_status": "available" if row[6] < 5 and (row[10] is None or row[10]) else "busy",
                "rating": float(row[8]) if row[8] else 4.5,
                "total_consultations": int(row[9]) if row[9] else 0
            }
            experts.append(expert)
        
        logger.info(f" Found {len(experts)} available experts" + 
                   (f" for expertise area: {expertise_area}" if expertise_area else ""))
        return experts
        
    except Exception as e:
        logger.error(f" Error fetching experts: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch experts: {str(e)}"
        )

# ... keep all your other endpoints (get_my_queries, get_query_details, update_query, assign_expert_to_query) ...
# =====================================================
# GET QUERY DETAILS
# =====================================================
@router.get("/queries/{query_id}")
async def get_query_details(
    query_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get query details"""
    try:
        query_sql = text("""
        SELECT q.id, q.query_code, q.query_type, q.subject, 
               q.question, q.response, q.priority, q.status,
               q.asked_at, q.responded_at, q.closed_at,
               e.first_name AS expert_first_name,
               e.last_name AS expert_last_name,
               e.email AS expert_email
        FROM queries q
        LEFT JOIN users e ON q.assigned_to = e.id
        WHERE q.id = :query_id
        """)
        
        result = db.execute(query_sql, {"query_id": query_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        
        question = row[4]
        contract_name = None
        user_name = "Unknown"
        user_email = ""
        
        if question:
            lines = question.split('\n')
            clean_lines = []
            
            for line in lines:
                if line.startswith("[User:"):
                    try:
                        user_end = line.index("]")
                        user_part = line[7:user_end]
                        if "(" in user_part:
                            user_name = user_part.split("(")[0].strip()
                            user_email = user_part.split("(")[1].strip(")")
                        else:
                            user_name = user_part
                    except:
                        pass
                elif line.startswith("[Contract:"):
                    try:
                        contract_end = line.index("]")
                        contract_name = line[11:contract_end]
                    except:
                        pass
                elif line.strip() and not line.startswith("["):
                    clean_lines.append(line)
            
            question = '\n'.join(clean_lines).strip()
        
        return {
            "query_id": str(row[0]),
            "query_code": row[1],
            "query_type": row[2],
            "subject": row[3],
            "question": question,
            "response": row[5],
            "priority": row[6],
            "status": row[7],
            "asked_at": row[8],
            "responded_at": row[9],
            "closed_at": row[10],
            "asked_by": {
                "name": user_name,
                "email": user_email
            },
            "contract": {
                "title": contract_name
            } if contract_name else None,
            "expert": {
                "name": f"{row[11]} {row[12]}" if row[11] else None,
                "email": row[13]
            } if row[11] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# UPDATE QUERY STATUS
# =====================================================
@router.patch("/queries/{query_id}")
async def update_query(
    query_id: str,
    update_data: QueryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update query status and response"""
    try:
        check_sql = text("SELECT id, status FROM queries WHERE id = :query_id")
        result = db.execute(check_sql, {"query_id": query_id})
        query = result.fetchone()
        
        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        
        update_fields = ["status = :status"]
        params = {"query_id": query_id, "status": update_data.status}
        
        if update_data.response:
            update_fields.append("response = :response")
            update_fields.append("responded_at = NOW()")
            params["response"] = update_data.response
        
        if update_data.status == "closed":
            update_fields.append("closed_at = NOW()")
        
        update_sql = text(f"""
        UPDATE queries 
        SET {', '.join(update_fields)}
        WHERE id = :query_id
        """)
        
        db.execute(update_sql, params)
        db.commit()
        
        logger.info(f" Query {query_id} updated to status: {update_data.status}")
        
        return {
            "success": True,
            "message": "Query updated successfully",
            "query_id": query_id,
            "status": update_data.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update query: {str(e)}"
        )

# =====================================================
# ASSIGN EXPERT TO QUERY
# =====================================================
@router.post("/queries/{query_id}/assign/{expert_id}")
async def assign_expert_to_query(
    query_id: str,
    expert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign an expert to a query"""
    try:
        check_sql = text("SELECT id, status FROM queries WHERE id = :query_id")
        result = db.execute(check_sql, {"query_id": query_id})
        query = result.fetchone()
        
        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        
        if query[1] not in ("open", "in_progress"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot assign expert to query with status: {query[1]}"
            )
        
        expert_id_int = int(expert_id) if isinstance(expert_id, str) else expert_id
        
        expert_check_sql = text("SELECT id FROM users WHERE id = :expert_id AND is_active = 1")
        expert_result = db.execute(expert_check_sql, {"expert_id": expert_id_int})
        expert = expert_result.fetchone()
        
        if not expert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expert not found or inactive"
            )
        
        assign_sql = text("""
        UPDATE queries 
        SET assigned_to = :expert_id, status = 'in_progress'
        WHERE id = :query_id
        """)
        
        db.execute(assign_sql, {"query_id": query_id, "expert_id": expert_id_int})
        db.commit()
        
        logger.info(f" Expert {expert_id} assigned to query {query_id}")
        
        return {
            "success": True,
            "message": "Expert assigned successfully",
            "query_id": query_id,
            "expert_id": expert_id,
            "status": "in_progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Error assigning expert: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign expert: {str(e)}"
        )