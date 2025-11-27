#!/usr/bin/env python3
"""
Test script for blockchain integration
"""

import asyncio
import sys
sys.path.append('/path/to/your/calim360/project')

from app.services.blockchain_service import blockchain_service

async def test_blockchain():
    """Test blockchain functionality"""
    
    print("🧪 Testing Blockchain Integration...")
    print("=" * 50)
    
    # Test 1: Store contract hash
    print("\n1️⃣ Testing: Store Contract Hash")
    result = await blockchain_service.store_contract_hash(
        contract_id=1,
        document_content="Test Contract Content",
        uploaded_by=1,
        company_id=1,
        contract_number="TEST-001",
        contract_type="service"
    )
    
    if result.get("success"):
        print("✅ PASS: Contract hash stored")
        print(f"   Transaction ID: {result['transaction_id']}")
        print(f"   Document Hash: {result['document_hash']}")
    else:
        print("❌ FAIL: Failed to store contract hash")
        return False
    
    # Test 2: Verify contract hash
    print("\n2️⃣ Testing: Verify Contract Hash")
    verify_result = await blockchain_service.verify_contract_hash(
        contract_id=1,
        current_document_content="Test Contract Content"
    )
    
    if verify_result.get("success") and verify_result.get("verified"):
        print("✅ PASS: Contract verification successful")
    else:
        print("❌ FAIL: Contract verification failed")
        return False
    
    # Test 3: Store audit log
    print("\n3️⃣ Testing: Store Audit Log")
    audit_result = await blockchain_service.store_audit_log(
        audit_id="test-audit-001",
        entity_type="contract",
        entity_id="1",
        action="create",
        user_id=1,
        old_values=None,
        new_values={"status": "draft"},
        ip_address="127.0.0.1"
    )
    
    if audit_result.get("success"):
        print("✅ PASS: Audit log stored on blockchain")
        print(f"   Transaction ID: {audit_result['transaction_id']}")
    else:
        print("❌ FAIL: Failed to store audit log")
        return False
    
    # Test 4: Get contract record
    print("\n4️⃣ Testing: Get Contract Record")
    record = await blockchain_service.get_contract_record(1)
    
    if record:
        print("✅ PASS: Retrieved contract record")
        print(f"   Contract ID: {record['contract_id']}")
    else:
        print("❌ FAIL: Failed to retrieve contract record")
        return False
    
    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_blockchain())
    sys.exit(0 if success else 1)