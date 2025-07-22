#!/usr/bin/env python3
"""Quick test to verify both issues are fixed"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_import():
    try:
        from app import create_app
        print("✅ App imports successfully!")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_cache_serialization():
    try:
        from app.cache_manager import CacheManager
        from datetime import datetime
        
        # Test the cache manager
        cache = CacheManager()
        
        # Test data with datetime (simulating Firestore data)
        test_data = {
            "username": "test_user",
            "created_at": datetime.now(),
            "profile_icon": "test.png"
        }
        
        # This should work now
        success = cache.set_user_data("test123", test_data)
        print(f"✅ Cache serialization works: {success}")
        
        # Test retrieval
        cached = cache.get_user_data("test123")
        print(f"✅ Cache retrieval works: {cached is not None}")
        
        return True
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running quick tests...")
    
    import_ok = test_import()
    cache_ok = test_cache_serialization()
    
    if import_ok and cache_ok:
        print("\n🎉 All tests passed! Your app should work now.")
        print("Run: python run.py")
    else:
        print("\n❌ Some tests failed. Check the errors above.")