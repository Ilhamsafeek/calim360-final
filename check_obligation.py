import sys
sys.path.insert(0, '/var/www/calim360')
from app.core.database import engine
from sqlalchemy import text

obligation_id = 199

with engine.connect() as conn:
    # Check if obligation exists
    result = conn.execute(
        text("SELECT id, obligation_title, contract_id FROM obligations WHERE id = :id"),
        {"id": obligation_id}
    )
    obligation = result.fetchone()
    
    if obligation:
        print(f"✅ Obligation {obligation_id} EXISTS:")
        print(f"   Title: {obligation[1]}")
        print(f"   Contract ID: {obligation[2]}")
        
        # Try to delete directly with SQL
        print(f"\n🔧 Attempting direct SQL delete...")
        try:
            result = conn.execute(
                text("DELETE FROM obligations WHERE id = :id"),
                {"id": obligation_id}
            )
            conn.commit()
            print(f"✅ Successfully deleted! Rows affected: {result.rowcount}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            conn.rollback()
    else:
        print(f"❌ Obligation {obligation_id} does NOT exist")
