"""
CALIM 360 RBAC Test Suite - Fixed Version
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Test users
TEST_USERS = {
    "super_admin": {
        "email": "superadmin@calim360.qa",
        "password": "SuperAdmin@123"
    },
    "admin": {
        "email": "admin@testcompany.qa",
        "password": "Admin@123"
    },
    "viewer": {
        "email": "viewer@testcompany.qa",
        "password": "Viewer@123"
    }
}

class RBACTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.base_url = BASE_URL
    
    def login(self, email, password):
        """Login and store token"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"email": email, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.token = data.get("access_token")
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                    return True
            print(f" Login failed for {email}: {response.text[:200]}")
            return False
        except Exception as e:
            print(f" Login error: {e}")
            return False
    
    def logout(self):
        """Clear session"""
        self.token = None
        self.session = requests.Session()
    
    def make_request(self, method, endpoint, data=None):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            elif method == "PUT":
                response = self.session.put(url, json=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                return {"status": 0, "data": {"error": f"Unknown method: {method}"}}
            
            # Handle response
            try:
                json_data = response.json() if response.text else None
            except:
                json_data = {"raw_response": response.text[:200] if response.text else "Empty"}
            
            return {
                "status": response.status_code,
                "data": json_data
            }
        except Exception as e:
            return {
                "status": 0,
                "data": {"error": str(e)}
            }
    
    def test_endpoint(self, name, method, endpoint, expected_status, data=None):
        """Test an endpoint and check expected status"""
        result = self.make_request(method, endpoint, data)
        actual_status = result["status"]
        
        if actual_status == expected_status:
            print(f"   PASS: {name}")
            print(f"         Status: {actual_status}")
            return True
        else:
            print(f"   FAIL: {name}")
            print(f"         Expected: {expected_status}, Got: {actual_status}")
            response_preview = str(result.get("data", {}))[:150]
            print(f"         Response: {response_preview}")
            return False


def run_rbac_tests():
    """Run all RBAC tests"""
    print("=" * 60)
    print("CALIM 360 RBAC TEST SUITE")
    print("=" * 60)
    
    passed = 0
    failed = 0
    tester = RBACTester()
    
    # ========================================
    # TEST 1: Super Admin Access
    # ========================================
    print("\n📌 TEST 1: Super Admin Access")
    print("-" * 40)
    
    if tester.login(TEST_USERS["super_admin"]["email"], TEST_USERS["super_admin"]["password"]):
        print(f" Logged in as {TEST_USERS['super_admin']['email']}")
        
        tests = [
            ("Access system statistics", "GET", "/api/admin/statistics", 200),
            ("List all companies", "GET", "/api/admin/companies", 200),
            ("List all users", "GET", "/api/admin/users", 200),
            ("List all roles", "GET", "/api/admin/roles", 200),
            ("List contracts", "GET", "/api/contracts", 200),
            ("Create contract", "POST", "/api/contracts/", 201, {
                "contract_title": "Test Contract",
                "contract_type": "general",
                "profile_type": "contractor"
            }),
        ]
        
        for test in tests:
            name, method, endpoint, expected = test[0], test[1], test[2], test[3]
            data = test[4] if len(test) > 4 else None
            if tester.test_endpoint(name, method, endpoint, expected, data):
                passed += 1
            else:
                failed += 1
    else:
        failed += 6
    
    tester.logout()
    
    # ========================================
    # TEST 2: Company Admin Restrictions
    # ========================================
    print("\n📌 TEST 2: Company Admin Access")
    print("-" * 40)
    
    if tester.login(TEST_USERS["admin"]["email"], TEST_USERS["admin"]["password"]):
        print(f" Logged in as {TEST_USERS['admin']['email']}")
        
        tests = [
            ("List contracts (allowed)", "GET", "/api/contracts", 200),
            ("Access admin stats (denied)", "GET", "/api/admin/statistics", 403),
            ("List all companies (denied)", "GET", "/api/admin/companies", 403),
        ]
        
        for test in tests:
            name, method, endpoint, expected = test[0], test[1], test[2], test[3]
            data = test[4] if len(test) > 4 else None
            if tester.test_endpoint(name, method, endpoint, expected, data):
                passed += 1
            else:
                failed += 1
    else:
        print("  Skipping admin tests (user doesn't exist)")
        failed += 3
    
    tester.logout()
    
    # ========================================
    # TEST 3: Viewer Restrictions
    # ========================================
    print("\n📌 TEST 3: Viewer Restrictions")
    print("-" * 40)
    
    if tester.login(TEST_USERS["viewer"]["email"], TEST_USERS["viewer"]["password"]):
        print(f" Logged in as {TEST_USERS['viewer']['email']}")
        
        tests = [
            ("List contracts (allowed)", "GET", "/api/contracts", 200),
            ("Create contract (denied)", "POST", "/api/contracts/", 403, {
                "contract_title": "Viewer Test",
                "contract_type": "general",
                "profile_type": "contractor"
            }),
            ("Access admin (denied)", "GET", "/api/admin/users", 403),
        ]
        
        for test in tests:
            name, method, endpoint, expected = test[0], test[1], test[2], test[3]
            data = test[4] if len(test) > 4 else None
            if tester.test_endpoint(name, method, endpoint, expected, data):
                passed += 1
            else:
                failed += 1
    else:
        print("  Skipping viewer tests (user doesn't exist)")
        failed += 3
    
    tester.logout()
    
    # ========================================
    # TEST 4: Unauthenticated Access
    # ========================================
    print("\n📌 TEST 4: Unauthenticated Access")
    print("-" * 40)
    
    tests = [
        ("Contracts requires auth", "GET", "/api/contracts", 401),
        ("Admin requires auth", "GET", "/api/admin/users", 401),
        ("Create requires auth", "POST", "/api/contracts/", 401, {}),
    ]
    
    for test in tests:
        name, method, endpoint, expected = test[0], test[1], test[2], test[3]
        data = test[4] if len(test) > 4 else None
        if tester.test_endpoint(name, method, endpoint, expected, data):
            passed += 1
        else:
            failed += 1
    
    # ========================================
    # RESULTS
    # ========================================
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f" Passed: {passed}")
    print(f" Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")
    
    success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
    print(f" Success Rate: {success_rate:.1f}%")
    
    return passed, failed


if __name__ == "__main__":
    run_rbac_tests()