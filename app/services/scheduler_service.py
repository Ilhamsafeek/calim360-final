# =====================================================
# FILE: app/services/scheduler_service.py
# Background Job Scheduler for SLA, Notifications, Cleanup
# =====================================================

import asyncio
from datetime import datetime, timedelta
from typing import Callable, List
import logging
from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.workflow_enforcement_service import WorkflowEnforcementService
from app.services.notification_service import NotificationService, NotificationTemplates

logger = logging.getLogger(__name__)


class SchedulerService:
    """Background job scheduler"""
    
    def __init__(self):
        self.jobs: List[dict] = []
        self.running = False
    
    def add_job(self, name: str, func: Callable, interval_minutes: int):
        """Add a scheduled job"""
        self.jobs.append({
            "name": name,
            "func": func,
            "interval": interval_minutes,
            "last_run": None
        })
        logger.info(f"Scheduled job '{name}' every {interval_minutes} minutes")
    
    async def start(self):
        """Start the scheduler"""
        self.running = True
        logger.info("🚀 Background scheduler started")
        
        while self.running:
            for job in self.jobs:
                now = datetime.utcnow()
                should_run = (
                    job["last_run"] is None or
                    (now - job["last_run"]).total_seconds() >= job["interval"] * 60
                )
                
                if should_run:
                    try:
                        logger.info(f"⏱️ Running job: {job['name']}")
                        if asyncio.iscoroutinefunction(job["func"]):
                            await job["func"]()
                        else:
                            job["func"]()
                        job["last_run"] = now
                        logger.info(f" Job completed: {job['name']}")
                    except Exception as e:
                        logger.error(f" Job failed: {job['name']} - {e}")
            
            # Sleep for 1 minute before checking again
            await asyncio.sleep(60)
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Scheduler stopped")


# =====================================================
# SCHEDULED JOB FUNCTIONS
# =====================================================

def check_sla_breaches():
    """Check for SLA breaches and send escalations"""
    db = SessionLocal()
    try:
        breaches = WorkflowEnforcementService.check_sla_breaches(db)
        
        for breach in breaches:
            # Send urgent notification
            notification = NotificationTemplates.sla_breach(
                breach["contract_number"],
                breach["stage"]
            )
            
            # Get contract owner
            owner = db.execute(text("""
                SELECT created_by FROM contracts WHERE id = :id
            """), {"id": breach["contract_id"]}).scalar()
            
            if owner:
                NotificationService.create_notification(
                    db, owner,
                    notification["title"],
                    notification["message"],
                    notification["type"],
                    notification["priority"],
                    "contract",
                    breach["contract_id"],
                    send_email=True
                )
        
        logger.info(f"SLA check complete. {len(breaches)} breaches found.")
        
    finally:
        db.close()


def check_sla_warnings():
    """Check for approaching SLA deadlines (24hr warning)"""
    db = SessionLocal()
    try:
        # Find stages with SLA deadline in next 24 hours
        query = text("""
            SELECT ws.id, ws.sla_deadline, ws.approver_user_id,
                   c.contract_number, c.id as contract_id,
                   TIMESTAMPDIFF(HOUR, NOW(), ws.sla_deadline) as hours_remaining
            FROM workflow_stages ws
            JOIN workflow_instances wi ON ws.workflow_instance_id = wi.id
            JOIN contracts c ON wi.contract_id = c.id
            WHERE ws.status = 'pending'
            AND ws.sla_deadline BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
            AND (ws.warning_sent = 0 OR ws.warning_sent IS NULL)
        """)
        
        results = db.execute(query).fetchall()
        
        for row in results:
            if row.approver_user_id:
                notification = NotificationTemplates.sla_warning(
                    row.contract_number,
                    row.hours_remaining
                )
                
                NotificationService.create_notification(
                    db, row.approver_user_id,
                    notification["title"],
                    notification["message"],
                    notification["type"],
                    notification["priority"],
                    "contract",
                    row.contract_id,
                    send_email=True
                )
            
            # Mark warning as sent
            db.execute(text("""
                UPDATE workflow_stages SET warning_sent = 1 WHERE id = :id
            """), {"id": row.id})
        
        db.commit()
        logger.info(f"SLA warning check complete. {len(results)} warnings sent.")
        
    finally:
        db.close()


def check_contract_expiry():
    """Check for expiring contracts and send reminders"""
    db = SessionLocal()
    try:
        # Check for 90, 60, 30, 7 day warnings
        for days in [90, 60, 30, 7]:
            query = text(f"""
                SELECT c.id, c.contract_number, c.contract_title,
                       c.expiry_date, c.created_by
                FROM contracts c
                WHERE c.expiry_date = DATE_ADD(CURDATE(), INTERVAL :days DAY)
                AND c.status NOT IN ('Cancelled', 'Expired', 'Renewed')
                AND NOT EXISTS (
                    SELECT 1 FROM notifications n 
                    WHERE n.entity_id = c.id 
                    AND n.entity_type = 'contract'
                    AND n.title LIKE '%Expiring in {days}%'
                )
            """)
            
            results = db.execute(query, {"days": days}).fetchall()
            
            for row in results:
                notification = NotificationTemplates.contract_expiring(
                    row.contract_number, days
                )
                
                NotificationService.create_notification(
                    db, row.created_by,
                    notification["title"],
                    notification["message"],
                    notification["type"],
                    notification["priority"],
                    "contract",
                    row.id,
                    send_email=True
                )
        
        db.commit()
        logger.info("Contract expiry check complete.")
        
    finally:
        db.close()


def check_obligation_due_dates():
    """Check for upcoming obligation due dates"""
    db = SessionLocal()
    try:
        # Check for obligations due in 7, 3, 1 days
        for days in [7, 3, 1]:
            query = text(f"""
                SELECT o.id, o.obligation_title, o.due_date,
                       o.owner_user_id, c.contract_number
                FROM obligations o
                JOIN contracts c ON o.contract_id = c.id
                WHERE DATE(o.due_date) = DATE_ADD(CURDATE(), INTERVAL :days DAY)
                AND o.status NOT IN ('completed', 'cancelled')
            """)
            
            results = db.execute(query, {"days": days}).fetchall()
            
            for row in results:
                notification = NotificationTemplates.obligation_due(
                    row.obligation_title,
                    row.due_date.strftime('%Y-%m-%d')
                )
                
                if row.owner_user_id:
                    NotificationService.create_notification(
                        db, row.owner_user_id,
                        notification["title"],
                        notification["message"],
                        notification["type"],
                        "high" if days <= 3 else "normal",
                        "obligation",
                        row.id,
                        send_email=True
                    )
        
        db.commit()
        logger.info("Obligation due date check complete.")
        
    finally:
        db.close()


def cleanup_expired_sessions():
    """Clean up expired user sessions"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            DELETE FROM user_sessions 
            WHERE expires_at < NOW() OR
                  (is_active = 0 AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY))
        """))
        
        db.commit()
        logger.info(f"Session cleanup complete. {result.rowcount} sessions removed.")
        
    finally:
        db.close()


def update_overdue_obligations():
    """Mark overdue obligations"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            UPDATE obligations 
            SET status = 'overdue'
            WHERE due_date < NOW()
            AND status NOT IN ('completed', 'cancelled', 'overdue')
        """))
        
        db.commit()
        logger.info(f"Updated {result.rowcount} overdue obligations.")
        
    finally:
        db.close()


# =====================================================
# SCHEDULER INITIALIZATION
# =====================================================

scheduler = SchedulerService()

def setup_scheduler():
    """Configure all scheduled jobs"""
    scheduler.add_job("SLA Breach Check", check_sla_breaches, 15)
    scheduler.add_job("SLA Warning Check", check_sla_warnings, 60)
    scheduler.add_job("Contract Expiry Check", check_contract_expiry, 1440)  # Daily
    scheduler.add_job("Obligation Due Check", check_obligation_due_dates, 1440)
    scheduler.add_job("Session Cleanup", cleanup_expired_sessions, 60)
    scheduler.add_job("Overdue Obligations", update_overdue_obligations, 60)
    
    return scheduler