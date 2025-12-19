import sys
sys.path.insert(0, '/var/www/calim360')

from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("DESCRIBE obligations"))
    print("Current columns in obligations table:")
    for row in result:
        print(f"  {row[0]:30s} {row[1]:20s} {row[2]:5s} {row[3]:5s}")
