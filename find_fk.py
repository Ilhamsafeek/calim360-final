import sys
sys.path.insert(0, '/var/www/calim360')
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Find all foreign keys pointing to obligations
    result = conn.execute(text("""
        SELECT 
            TABLE_NAME,
            COLUMN_NAME,
            CONSTRAINT_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM
            INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE
            REFERENCED_TABLE_SCHEMA = 'lpeclk_smart_clm'
            AND REFERENCED_TABLE_NAME = 'obligations'
        ORDER BY TABLE_NAME
    """))
    
    print("Tables with foreign keys to 'obligations':")
    print("=" * 80)
    for row in result:
        print(f"Table: {row[0]:30s} Column: {row[1]:25s} FK: {row[2]}")
    
    print("\n" + "=" * 80)
    
    # Check if obligation 199 has records in any of these tables
    obligation_id = 199
    
    # Get all table names
    result = conn.execute(text("""
        SELECT DISTINCT TABLE_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE REFERENCED_TABLE_SCHEMA = 'lpeclk_smart_clm'
            AND REFERENCED_TABLE_NAME = 'obligations'
    """))
    
    tables = [row[0] for row in result]
    
    print(f"\nChecking for obligation_id {obligation_id} in all related tables:")
    print("=" * 80)
    
    for table in tables:
        try:
            check_result = conn.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE obligation_id = :id"),
                {"id": obligation_id}
            )
            count = check_result.scalar()
            if count > 0:
                print(f"❌ {table:30s} {count} records (BLOCKING DELETE!)")
            else:
                print(f"✅ {table:30s} {count} records")
        except Exception as e:
            print(f"⚠️  {table:30s} Error: {str(e)[:50]}")
