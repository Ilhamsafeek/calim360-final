import sys
sys.path.insert(0, '/var/www/calim360')
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Get detailed FK info
    result = conn.execute(text("""
        SELECT 
            CONSTRAINT_NAME,
            TABLE_NAME,
            COLUMN_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME,
            DELETE_RULE,
            UPDATE_RULE
        FROM 
            INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
                ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE 
            rc.CONSTRAINT_SCHEMA = 'lpeclk_smart_clm'
            AND rc.REFERENCED_TABLE_NAME = 'obligations'
    """))
    
    print("Foreign Key Constraints on 'obligations':")
    print("=" * 80)
    for row in result:
        print(f"FK: {row[0]}")
        print(f"  Table: {row[1]}.{row[2]} -> {row[3]}.{row[4]}")
        print(f"  ON DELETE: {row[5]}, ON UPDATE: {row[6]}")
        print()
    
    # Force check obligation_updates with explicit lock
    print("Checking obligation_updates with different approach:")
    result = conn.execute(text("""
        SELECT obligation_id, COUNT(*) 
        FROM obligation_updates 
        WHERE obligation_id = 199
        GROUP BY obligation_id
    """))
    
    rows = result.fetchall()
    if rows:
        print(f"❌ Found records: {rows}")
    else:
        print("✅ No records found")
        
    # Try to count ALL records in obligation_updates
    result = conn.execute(text("SELECT COUNT(*) FROM obligation_updates"))
    total = result.scalar()
    print(f"Total records in obligation_updates: {total}")
    
    # If there are records, show them
    if total > 0:
        result = conn.execute(text("""
            SELECT id, obligation_id, update_type 
            FROM obligation_updates 
            LIMIT 10
        """))
        print("\nSample records:")
        for row in result:
            print(f"  ID: {row[0]}, obligation_id: {row[1]}, type: {row[2]}")
