#!/usr/bin/env python3
"""
Test script to verify the NACRE server can start without errors
"""

import sys
import os
import traceback

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported successfully"""
    print("Testing imports...")
    
    try:
        from app.main import app
        print("✓ FastAPI app imported successfully")
    except Exception as e:
        print(f"✗ Failed to import FastAPI app: {e}")
        traceback.print_exc()
        return False
    
    try:
        from app.config import settings
        print("✓ Settings imported successfully")
        print(f"  - Storage dir: {settings.storage_dir}")
        print(f"  - OpenAI API key configured: {'Yes' if settings.openai_api_key else 'No'}")
    except Exception as e:
        print(f"✗ Failed to import settings: {e}")
        traceback.print_exc()
        return False
    
    try:
        from app.services.nacre_dict import get_nacre_dict
        nacre_dict = get_nacre_dict()
        print(f"✓ NACRE dictionary loaded with {len(nacre_dict.entries)} entries")
    except Exception as e:
        print(f"✗ Failed to load NACRE dictionary: {e}")
        traceback.print_exc()
        return False
    
    try:
        from app.services.co2_analyzer import co2_analyzer
        status = co2_analyzer.get_status()
        print(f"✓ CO2 analyzer initialized")
        print(f"  - Status: {status.get('status', 'unknown')}")
        print(f"  - NACRE codes loaded: {status.get('total_nacre_codes', 0)}")
    except Exception as e:
        print(f"✗ Failed to initialize CO2 analyzer: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_server_creation():
    """Test that the FastAPI server can be created"""
    print("\nTesting server creation...")
    
    try:
        from app.main import app
        
        # Check if app has routes
        routes = [route.path for route in app.routes]
        print(f"✓ Server created with {len(routes)} routes")
        print("  Key routes:")
        for route in routes[:10]:  # Show first 10 routes
            print(f"    - {route}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to create server: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("=== NACRE Server Test ===")
    print()
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed")
        return 1
    
    # Test server creation
    if not test_server_creation():
        print("\n❌ Server creation tests failed")
        return 1
    
    print("\n✅ All tests passed! Server should start without errors.")
    print("\nTo start the server, run:")
    print("  python -m uvicorn app.main:app --host 127.0.0.1 --port 8123 --reload")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
