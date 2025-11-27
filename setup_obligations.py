# setup_obligations.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import engine

def setup_tables():
    print("=" * 60)
    print("SETTING UP OBLIGATIONS TABLES")
    print("=" * 60)
    
    try:
        with engine.connect() as conn:
            # Create obligations table
            print("\n1. Creating obligations table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS obligations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    contract_id INT NOT NULL,
                    obligation_title VARCHAR(500) NOT NULL,
                    description TEXT,
                    obligation_type VARCHAR(100),
                    owner_user_id INT,
                    escalation_user_id INT,
                    threshold_date DATETIME,
                    due_date DATETIME,
                    status VARCHAR(50) DEFAULT 'initiated',
                    is_ai_generated TINYINT(1) DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_contract_id (contract_id),
                    INDEX idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.commit()
            print("✅ Obligations table created")
            
            # Create tracking table
            print("\n2. Creating obligation_tracking table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS obligation_tracking (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    obligation_id INT NOT NULL,
                    action_taken VARCHAR(255),
                    action_by INT,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_obligation_id (obligation_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.commit()
            print("✅ Obligation tracking table created")
            
            # Verify tables exist
            print("\n3. Verifying tables...")
            result = conn.execute(text("SHOW TABLES LIKE 'obligations'"))
            if result.fetchone():
                print("✅ obligations table exists")
                
                # Show structure
                result = conn.execute(text("DESCRIBE obligations"))
                print("\nTable structure:")
                for row in result:
                    print(f"  - {row[0]}: {row[1]}")
            else:
                print("❌ obligations table NOT found!")
            
            result = conn.execute(text("SHOW TABLES LIKE 'obligation_tracking'"))
            if result.fetchone():
                print("✅ obligation_tracking table exists")
            else:
                print("❌ obligation_tracking table NOT found!")
            
            # Check current data
            print("\n4. Checking existing data...")
            result = conn.execute(text("SELECT COUNT(*) as count FROM obligations"))
            count = result.fetchone()[0]
            print(f"   Current obligations in database: {count}")
            
            if count > 0:
                print("\n   Recent obligations:")
                result = conn.execute(text("""
                    SELECT id, obligation_title, status, created_at 
                    FROM obligations 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """))
                for row in result:
                    print(f"   - ID {row[0]}: {row[1]} ({row[2]}) - {row[3]}")
            
            print("\n" + "=" * 60)
            print("✅ SETUP COMPLETE!")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_tables()