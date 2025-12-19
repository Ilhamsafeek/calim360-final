# Read the file
with open('app/api/api_v1/obligations/obligations.py', 'r') as f:
    lines = f.readlines()

# Find the delete function and replace it
new_delete = '''# =====================================================
# DELETE OBLIGATION
# =====================================================
@router.delete("/{obligation_id}")
async def delete_obligation(
    obligation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an obligation with proper cascading and UI refresh
    """
    try:
        logger.info(f"🗑️ Deleting obligation {obligation_id}")
        
        # Get the obligation first
        obligation = db.query(Obligation).filter(Obligation.id == obligation_id).first()
        
        if not obligation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Obligation not found"
            )
        
        # Verify user has access
        contract = db.query(Contract).filter(Contract.id == obligation.contract_id).first()
        if contract and contract.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # ✅ DELETE WITH FK CHECKS DISABLED
        try:
            # Disable foreign key checks to force delete
            db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            
            # Delete related records
            db.execute(text("DELETE FROM obligation_updates WHERE obligation_id = :id"), {"id": obligation_id})
            db.execute(text("DELETE FROM obligation_escalations WHERE obligation_id = :id"), {"id": obligation_id})
            db.execute(text("DELETE FROM obligation_tracking WHERE obligation_id = :id"), {"id": obligation_id})
            db.execute(text("DELETE FROM kpis WHERE obligation_id = :id"), {"id": obligation_id})
            
            # Delete the obligation itself using RAW SQL (not ORM)
            result = db.execute(text("DELETE FROM obligations WHERE id = :id"), {"id": obligation_id})
            
            # Re-enable foreign key checks
            db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            
            # Commit everything
            db.commit()
            
            logger.info(f"✅ Obligation {obligation_id} deleted successfully (rows: {result.rowcount})")
            
            return {
                "success": True,
                "message": "Obligation deleted successfully",
                "id": obligation_id
            }
            
        except Exception as e:
            db.rollback()
            db.execute(text("SET FOREIGN_KEY_CHECKS=1"))  # Re-enable on error
            logger.error(f"❌ Error during cascading delete: {str(e)}")
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error deleting obligation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete obligation: {str(e)}"
        )

'''

# Find where the delete function starts and ends
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if '@router.delete("/{obligation_id}")' in line:
        start_idx = i
    if start_idx and i > start_idx and (line.startswith('@router.') or line.startswith('# =====')):
        end_idx = i
        break

if start_idx and end_idx:
    # Replace the function
    new_lines = lines[:start_idx] + [new_delete + '\n'] + lines[end_idx:]
    
    with open('app/api/api_v1/obligations/obligations.py', 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ Replaced delete function (lines {start_idx}-{end_idx})")
else:
    print("❌ Could not find delete function boundaries")
