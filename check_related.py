import sys
sys.path.insert(0, '/var/www/calim360')
from app.core.database import engine
from sqlalchemy import text

obligation_id = 199

with engine.connect() as conn:
    # Check each related table
    tables = ['obligation_updates', 'obligation_escalations', 'obligation_tracking', 'kpis']
    
    for table in tables:
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE obligation_id = :id"), {"id": obligation_id})
            count = result.scalar()
            print(f"{table:30s} {count} records")
        except Exception as e:
            print(f"{table:30s} Error: {e}")
