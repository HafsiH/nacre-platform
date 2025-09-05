#!/usr/bin/env python3
"""
Test script for Sophie training functionality
"""
import asyncio
import json
from pathlib import Path
from app.routes.sophie import sophie_train_status, _train_worker, _auto_map
from app.services.csv_io import preview_csv, count_csv_rows

async def test_training():
    print("Testing Sophie training functionality...")
    
    # Test file path
    test_file = Path("test_training.csv")
    if not test_file.exists():
        print("❌ Test file not found")
        return
    
    print(f"✅ Test file found: {test_file}")
    
    # Test preview
    try:
        headers, rows = preview_csv(str(test_file), limit=1)
        print(f"✅ Headers detected: {headers}")
    except Exception as e:
        print(f"❌ Preview failed: {e}")
        return
    
    # Test mapping
    try:
        mapping = _auto_map(headers)
        print(f"✅ Auto mapping: {mapping}")
    except Exception as e:
        print(f"❌ Mapping failed: {e}")
        return
    
    # Test row count
    try:
        total = count_csv_rows(str(test_file))
        print(f"✅ Total rows: {total}")
    except Exception as e:
        print(f"❌ Row count failed: {e}")
        return
    
    # Test training worker
    print("\nStarting training worker...")
    try:
        _train_worker(str(test_file), mapping)
        print("✅ Training worker completed")
    except Exception as e:
        print(f"❌ Training worker failed: {e}")
        return
    
    # Check final status
    status = sophie_train_status()
    print(f"✅ Final status: {status}")
    
    if status['processed'] > 0:
        print("🎉 Training test successful!")
    else:
        print("⚠️ Training processed 0 rows")

if __name__ == "__main__":
    asyncio.run(test_training())
