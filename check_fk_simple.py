import sys
sys.path.insert(0, '/var/www/calim360')
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Simpler FK check
    result = conn.execute(text("""
        SELECT 
            rc.CONSTRAINT_NAME,
            kcu.TABLE_NAME,
            kcu.COLUMN_NAME,
            rc.DELETE_RULE
        FROM 
            INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
                ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
        WHERE 
            rc.CONSTRAINT_SCHEMA = 'lpeclk_smart_clm'
            AND rc.REFERENCED_TABLE_NAME = 'obligations'
    """))
    
    print("Foreign Keys on 'obligations':")
    print("=" * 80)
    for row in result:
        print(f"Constraint: {row[0]}")
        print(f"  Table.Column: {row[1]}.{row[2]}")
        print(f"  ON DELETE: {row[3]}")
        print()
