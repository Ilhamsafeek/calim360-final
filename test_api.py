# test_api.py
import requests
import json

BASE_URL = "http://localhost:8000"
CONTRACT_ID = 4649  # Change to your contract ID

def test_create_obligation():
    print("=" * 60)
    print("TESTING OBLIGATION CREATION")
    print("=" * 60)
    
    # Test data
    data = {
        "contract_id": CONTRACT_ID,
        "obligation_title": "API Test Obligation",
        "description": "Testing from Python script",
        "obligation_type": "testing",
        "status": "initiated",
        "is_ai_generated": False
    }
    
    print("\n1. Sending POST request...")
    print(f"URL: {BASE_URL}/api/obligations/")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/obligations/",
            json=data
        )
        
        print(f"\n2. Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 201:
            result = response.json()
            print("\n SUCCESS! Obligation created:")
            print(json.dumps(result, indent=2))
            
            obligation_id = result['id']
            
            # Verify by fetching
            print(f"\n3. Verifying by fetching obligation {obligation_id}...")
            verify_response = requests.get(f"{BASE_URL}/api/obligations/{obligation_id}")
            
            if verify_response.status_code == 200:
                print(" Verification successful! Obligation exists in database.")
            else:
                print(" Verification failed!")
                
        else:
            print("\n FAILED!")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"\n ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

def test_fetch_obligations():
    print("\n" + "=" * 60)
    print("TESTING FETCH OBLIGATIONS")
    print("=" * 60)
    
    try:
        print(f"\nFetching obligations for contract {CONTRACT_ID}...")
        response = requests.get(f"{BASE_URL}/api/obligations/contract/{CONTRACT_ID}")
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            obligations = response.json()
            print(f"\n Found {len(obligations)} obligations")
            
            if obligations:
                print("\nObligations:")
                for ob in obligations:
                    print(f"  - ID {ob['id']}: {ob['obligation_title']} ({ob['status']})")
            else:
                print("  (No obligations found)")
        else:
            print(f" Failed: {response.text}")
            
    except Exception as e:
        print(f" ERROR: {str(e)}")

if __name__ == "__main__":
    # Make sure your FastAPI server is running first!
    print("\n  Make sure your FastAPI server is running on port 8000!\n")
    input("Press Enter to continue...")
    
    test_create_obligation()
    test_fetch_obligations()
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)