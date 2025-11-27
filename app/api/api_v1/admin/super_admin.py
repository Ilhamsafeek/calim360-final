# =====================================================
# FILE: app/api/api_v1/admin/super_admin.py
# Super Admin Management API
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.middleware.rbac_middleware import require_role, get_user_roles
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Super Admin"])


# =====================================================
# SCHEMAS
# =====================================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    company_id: int
    role_name: str
    department: Optional[str] = None
    job_title: Optional[str] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class RoleCreate(BaseModel):
    role_name: str
    role_name_ar: Optional[str] = None
    description: Optional[str] = None
    company_id: Optional[int] = None
    permissions: List[str] = []


class CompanyCreate(BaseModel):
    company_name: str
    company_name_ar: Optional[str] = None
    cr_number: Optional[str] = None
    industry: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


# =====================================================
# SUPER ADMIN CHECK
# =====================================================

async def verify_super_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify user is Super Admin"""
    roles = get_user_roles(db, current_user.id)
    if "Super Admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required"
        )
    return current_user


# =====================================================
# USER MANAGEMENT (Super Admin Only)
# =====================================================

@router.get("/users")
async def list_all_users(
    company_id: Optional[int] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(verify_super_admin)
):
    """List all users across all companies (Super Admin only)"""
    offset = (page - 1) * limit
    
    # Build query
    sql = """
        SELECT u.*, c.company_name,
               GROUP_CONCAT(r.role_name) as roles
        FROM users u
        LEFT JOIN companies c ON u.company_id = c.id
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        WHERE 1=1
    """
    params = {}
    
    if company_id:
        sql += " AND u.company_id = :company_id"
        params["company_id"] = company_id
    
    if is_active is not None:
        sql += " AND u.is_active = :is_active"
        params["is_active"] = is_active
    
    sql += " GROUP BY u.id"
    
    if role:
        sql += f" HAVING roles LIKE '%{role}%'"
    
    sql += " ORDER BY u.created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    result = db.execute(text(sql), params)
    users = []
    
    for row in result:
        users.append({
            "id": row.id,
            "email": row.email,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "company_id": row.company_id,
            "company_name": row.company_name,
            "roles": row.roles.split(",") if row.roles else [],
            "department": row.department,
            "is_active": row.is_active,
            "last_login_at": row.last_login_at,
            "created_at": row.created_at
        })
    
    # Get total count
    count_sql = "SELECT COUNT(*) FROM users WHERE 1=1"
    if company_id:
        count_sql += f" AND company_id = {company_id}"
    total = db.execute(text(count_sql)).scalar()
    
    return {
        "success": True,
        "data": users,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total
        }
    }


@router.post("/users")
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_super_admin)
):
    """Create user in any company (Super Admin only)"""
    from app.core.security import get_password_hash
    
    # Check if email exists
    check = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": user_data.email}
    ).first()
    
    if check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    sql = """
        INSERT INTO users 
        (email, password_hash, first_name, last_name, company_id, 
         department, job_title, user_role, user_type, is_active, 
         is_verified, created_at, created_by)
        VALUES 
        (:email, :password_hash, :first_name, :last_name, :company_id,
         :department, :job_title, :role_name, 'internal', 1, 1, NOW(), :admin_id)
    """
    
    db.execute(text(sql), {
        "email": user_data.email,
        "password_hash": get_password_hash(user_data.password),
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "company_id": user_data.company_id,
        "department": user_data.department,
        "job_title": user_data.job_title,
        "role_name": user_data.role_name,
        "admin_id": admin.id
    })
    
    # Get new user ID
    new_user_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
    
    # Assign role
    role = db.execute(
        text("SELECT id FROM roles WHERE role_name = :role_name"),
        {"role_name": user_data.role_name}
    ).first()
    
    if role:
        db.execute(text("""
            INSERT INTO user_roles (user_id, role_id, assigned_by, assigned_at)
            VALUES (:user_id, :role_id, :admin_id, NOW())
        """), {
            "user_id": new_user_id,
            "role_id": role.id,
            "admin_id": admin.id
        })
    
    db.commit()
    
    logger.info(f"Super Admin {admin.id} created user {new_user_id}")
    
    return {
        "success": True,
        "message": "User created successfully",
        "user_id": new_user_id
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_super_admin)
):
    """Update any user (Super Admin only)"""
    updates = []
    params = {"user_id": user_id, "admin_id": admin.id}
    
    if user_data.first_name:
        updates.append("first_name = :first_name")
        params["first_name"] = user_data.first_name
    
    if user_data.last_name:
        updates.append("last_name = :last_name")
        params["last_name"] = user_data.last_name
    
    if user_data.department:
        updates.append("department = :department")
        params["department"] = user_data.department
    
    if user_data.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = user_data.is_active
    
    if user_data.role_name:
        updates.append("user_role = :role_name")
        params["role_name"] = user_data.role_name
    
    updates.append("updated_at = NOW()")
    updates.append("updated_by = :admin_id")
    
    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = :user_id"
    db.execute(text(sql), params)
    
    # Update role assignment if changed
    if user_data.role_name:
        # Remove old roles
        db.execute(text("DELETE FROM user_roles WHERE user_id = :user_id"), 
                   {"user_id": user_id})
        
        # Add new role
        role = db.execute(
            text("SELECT id FROM roles WHERE role_name = :role_name"),
            {"role_name": user_data.role_name}
        ).first()
        
        if role:
            db.execute(text("""
                INSERT INTO user_roles (user_id, role_id, assigned_by, assigned_at)
                VALUES (:user_id, :role_id, :admin_id, NOW())
            """), {
                "user_id": user_id,
                "role_id": role.id,
                "admin_id": admin.id
            })
    
    db.commit()
    
    return {"success": True, "message": "User updated"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_super_admin)
):
    """Delete any user (Super Admin only)"""
    # Prevent self-deletion
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Soft delete
    db.execute(text("""
        UPDATE users 
        SET is_active = 0, updated_at = NOW(), updated_by = :admin_id
        WHERE id = :user_id
    """), {"user_id": user_id, "admin_id": admin.id})
    
    db.commit()
    
    return {"success": True, "message": "User deactivated"}


# =====================================================
# COMPANY MANAGEMENT (Super Admin Only)
# =====================================================

@router.get("/companies")
async def list_all_companies(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(verify_super_admin)
):
    """List all companies (Super Admin only)"""
    offset = (page - 1) * limit
    
    sql = """
        SELECT c.*, 
               (SELECT COUNT(*) FROM users WHERE company_id = c.id) as user_count,
               (SELECT COUNT(*) FROM contracts WHERE company_id = c.id) as contract_count
        FROM companies c
        ORDER BY c.created_at DESC
        LIMIT :limit OFFSET :offset
    """
    
    result = db.execute(text(sql), {"limit": limit, "offset": offset})
    companies = []
    
    for row in result:
        companies.append({
            "id": row.id,
            "company_name": row.company_name,
            "cr_number": row.cr_number,
            "industry": row.industry,
            "subscription_plan": row.subscription_plan,
            "is_active": row.is_active,
            "user_count": row.user_count,
            "contract_count": row.contract_count,
            "created_at": row.created_at
        })
    
    total = db.execute(text("SELECT COUNT(*) FROM companies")).scalar()
    
    return {
        "success": True,
        "data": companies,
        "pagination": {"page": page, "limit": limit, "total": total}
    }


@router.post("/companies")
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_super_admin)
):
    """Create new company (Super Admin only)"""
    sql = """
        INSERT INTO companies 
        (company_name, company_name_ar, cr_number, industry, email, phone,
         subscription_status, is_active, created_at, created_by)
        VALUES 
        (:name, :name_ar, :cr, :industry, :email, :phone, 
         'active', 1, NOW(), :admin_id)
    """
    
    db.execute(text(sql), {
        "name": company_data.company_name,
        "name_ar": company_data.company_name_ar,
        "cr": company_data.cr_number,
        "industry": company_data.industry,
        "email": company_data.email,
        "phone": company_data.phone,
        "admin_id": admin.id
    })
    
    company_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
    db.commit()
    
    return {
        "success": True,
        "message": "Company created",
        "company_id": company_id
    }


# =====================================================
# ROLE MANAGEMENT (Super Admin Only)
# =====================================================

@router.get("/roles")
async def list_all_roles(
    db: Session = Depends(get_db),
    admin: User = Depends(verify_super_admin)
):
    """List all system roles"""
    sql = """
        SELECT r.*, 
               (SELECT COUNT(*) FROM user_roles WHERE role_id = r.id) as user_count
        FROM roles r
        ORDER BY r.is_system_role DESC, r.role_name
    """
    
    result = db.execute(text(sql))
    roles = []
    
    for row in result:
        roles.append({
            "id": row.id,
            "role_name": row.role_name,
            "description": row.description,
            "is_system_role": row.is_system_role,
            "is_active": row.is_active,
            "user_count": row.user_count
        })
    
    return {"success": True, "data": roles}


@router.post("/roles")
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(verify_super_admin)
):
    """Create custom role (Super Admin only)"""
    sql = """
        INSERT INTO roles 
        (role_name, role_name_ar, description, company_id, 
         is_system_role, is_active, created_at)
        VALUES 
        (:name, :name_ar, :desc, :company_id, 0, 1, NOW())
    """
    
    db.execute(text(sql), {
        "name": role_data.role_name,
        "name_ar": role_data.role_name_ar,
        "desc": role_data.description,
        "company_id": role_data.company_id
    })
    
    role_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()
    
    # Add permissions
    for perm_code in role_data.permissions:
        perm = db.execute(
            text("SELECT id FROM permissions WHERE permission_name = :code"),
            {"code": perm_code}
        ).first()
        
        if perm:
            db.execute(text("""
                INSERT INTO role_permissions (role_id, permission_id, granted_by, granted_at)
                VALUES (:role_id, :perm_id, :admin_id, NOW())
            """), {
                "role_id": role_id,
                "perm_id": perm.id,
                "admin_id": admin.id
            })
    
    db.commit()
    
    return {"success": True, "message": "Role created", "role_id": role_id}


# =====================================================
# SYSTEM STATISTICS (Super Admin Only)
# =====================================================

@router.get("/statistics")
async def get_system_statistics(
    db: Session = Depends(get_db),
    admin: User = Depends(verify_super_admin)
):
    """Get system-wide statistics (Super Admin only)"""
    stats = {}
    
    # User stats
    stats["total_users"] = db.execute(
        text("SELECT COUNT(*) FROM users WHERE is_active = 1")
    ).scalar()
    
    stats["total_companies"] = db.execute(
        text("SELECT COUNT(*) FROM companies WHERE is_active = 1")
    ).scalar()
    
    stats["total_contracts"] = db.execute(
        text("SELECT COUNT(*) FROM contracts WHERE is_deleted = 0 OR is_deleted IS NULL")
    ).scalar()
    
    # Contracts by status
    status_result = db.execute(text("""
        SELECT status, COUNT(*) as count 
        FROM contracts 
        WHERE is_deleted = 0 OR is_deleted IS NULL
        GROUP BY status
    """))
    stats["contracts_by_status"] = {row[0]: row[1] for row in status_result}
    
    # Active workflows
    stats["active_workflows"] = db.execute(
        text("SELECT COUNT(*) FROM workflow_instances WHERE status = 'active'")
    ).scalar()
    
    # Pending approvals
    try:
        stats["pending_approvals"] = db.execute(
            text("SELECT COUNT(*) FROM approval_requests WHERE approval_status = 'pending'")
        ).scalar() or 0
    except:
        stats["pending_approvals"] = 0
    
    # Today's activity
    stats["today_logins"] = db.execute(text("""
        SELECT COUNT(DISTINCT user_id) FROM user_sessions 
        WHERE DATE(created_at) = CURDATE()
    """)).scalar()
    
    stats["today_contracts"] = db.execute(text("""
        SELECT COUNT(*) FROM contracts 
        WHERE DATE(created_at) = CURDATE()
    """)).scalar()
    
    return {"success": True, "data": stats}