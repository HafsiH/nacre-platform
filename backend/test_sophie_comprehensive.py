#!/usr/bin/env python3
"""
Comprehensive test for Sophie AI functionality
"""
import asyncio
import json
from pathlib import Path
from app.services.sophie_llm import sophie_chat, sophie_status
from app.routes.sophie import sophie_train_status, _train_worker, _auto_map
from app.services.csv_io import preview_csv, count_csv_rows

async def comprehensive_test():
    print("🧪 Comprehensive Sophie AI Test")
    print("=" * 50)
    
    # Test 1: Sophie Status
    print("\n1. Testing Sophie Status...")
    try:
        status = sophie_status()
        print(f"✅ Sophie status: {status}")
    except Exception as e:
        print(f"❌ Sophie status failed: {e}")
        return
    
    # Test 2: Sophie Chat
    print("\n2. Testing Sophie Chat...")
    try:
        result = sophie_chat("Hello, how are you?")
        print(f"✅ Sophie chat response: {result.get('reply', 'No reply')[:100]}...")
    except Exception as e:
        print(f"❌ Sophie chat failed: {e}")
        return
    
    # Test 3: Training Status
    print("\n3. Testing Training Status...")
    try:
        train_status = sophie_train_status()
        print(f"✅ Training status: {train_status}")
    except Exception as e:
        print(f"❌ Training status failed: {e}")
        return
    
    # Test 4: Training with Test Data
    print("\n4. Testing Training with Test Data...")
    test_file = Path("test_training.csv")
    if test_file.exists():
        try:
            headers, rows = preview_csv(str(test_file), limit=1)
            mapping = _auto_map(headers)
            total = count_csv_rows(str(test_file))
            
            print(f"✅ File: {test_file}")
            print(f"✅ Headers: {headers}")
            print(f"✅ Mapping: {mapping}")
            print(f"✅ Total rows: {total}")
            
            # Run training
            _train_worker(str(test_file), mapping)
            
            # Check final status
            final_status = sophie_train_status()
            print(f"✅ Final training status: {final_status}")
            
            if final_status['processed'] > 0:
                print("🎉 Training successful!")
            else:
                print("⚠️ Training processed 0 rows")
                
        except Exception as e:
            print(f"❌ Training test failed: {e}")
    else:
        print("⚠️ Test file not found, skipping training test")
    
    # Test 5: Sophie Chat After Training
    print("\n5. Testing Sophie Chat After Training...")
    try:
        result = sophie_chat("What patterns have you learned?")
        print(f"✅ Sophie response after training: {result.get('reply', 'No reply')[:150]}...")
    except Exception as e:
        print(f"❌ Sophie chat after training failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Comprehensive test completed!")

if __name__ == "__main__":
    asyncio.run(comprehensive_test())
