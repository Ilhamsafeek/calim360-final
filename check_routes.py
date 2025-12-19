import sys
from app.main import app

print("\n🔍 Checking Obligations Routes...")
obligations_routes = [r for r in app.routes if hasattr(r, 'path') and '/obligations' in r.path.lower()]

if obligations_routes:
    print(f"✅ Found {len(obligations_routes)} routes:")
    for route in obligations_routes:
        if hasattr(route, 'methods'):
            print(f"   {list(route.methods)[0]:7s} {route.path}")
else:
    print("❌ NO OBLIGATIONS ROUTES FOUND!")
    print("   Router is NOT registered in main.py")
