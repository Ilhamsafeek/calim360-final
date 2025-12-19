content = open('app/api/api_v1/obligations/obligations.py', 'r').read()

# Find and replace the entire delete section
old_delete = '''            # 1. Delete from obligation_updates
            db.execute(
                text("DELETE FROM obligation_updates WHERE obligation_id = :id"),
                {"id": obligation_id}
            )
            
            # 2. Delete from obligation_escalations
            db.execute(
                text("DELETE FROM obligation_escalations WHERE obligation_id = :id"),
                {"id": obligation_id}
            )
            
            # 3. Delete from obligation_tracking
            db.execute(
                text("DELETE FROM obligation_tracking WHERE obligation_id = :id"),
                {"id": obligation_id}
            )
            
            # 4. Delete from kpis table
            db.execute(
                text("DELETE FROM kpis WHERE obligation_id = :id"),
                {"id": obligation_id}
            )
            
            # ✅ COMMIT THE MANUAL DELETES FIRST
            db.commit()
            logger.info(f"✅ Deleted related records for obligation {obligation_id}")
            
            # 5. Finally, delete the obligation itself
            db.delete(obligation)
            db.commit()'''

new_delete = '''            # Use raw SQL to delete everything in one transaction
            # This bypasses SQLAlchemy's session tracking issues
            
            # 1. Delete from obligation_updates
            result1 = db.execute(
                text("DELETE FROM obligation_updates WHERE obligation_id = :id"),
                {"id": obligation_id}
            )
            logger.info(f"   Deleted {result1.rowcount} from obligation_updates")
            
            # 2. Delete from obligation_escalations
            result2 = db.execute(
                text("DELETE FROM obligation_escalations WHERE obligation_id = :id"),
                {"id": obligation_id}
            )
            logger.info(f"   Deleted {result2.rowcount} from obligation_escalations")
            
            # 3. Delete from obligation_tracking
            result3 = db.execute(
                text("DELETE FROM obligation_tracking WHERE obligation_id = :id"),
                {"id": obligation_id}
            )
            logger.info(f"   Deleted {result3.rowcount} from obligation_tracking")
            
            # 4. Delete from kpis
            result4 = db.execute(
                text("DELETE FROM kpis WHERE obligation_id = :id"),
                {"id": obligation_id}
            )
            logger.info(f"   Deleted {result4.rowcount} from kpis")
            
            # 5. Delete the obligation itself using raw SQL
            result5 = db.execute(
                text("DELETE FROM obligations WHERE id = :id"),
                {"id": obligation_id}
            )
            logger.info(f"   Deleted {result5.rowcount} from obligations")
            
            # Commit everything at once
            db.commit()'''

content = content.replace(old_delete, new_delete)

with open('app/api/api_v1/obligations/obligations.py', 'w') as f:
    f.write(content)

print("✅ Fixed delete function to use raw SQL")
