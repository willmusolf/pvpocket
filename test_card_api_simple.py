#!/usr/bin/env python3
"""
Simple test script to verify card API is working after diagnostic fixes.
This runs the same test that's failing in pytest but in isolation.
"""

import os
import sys
import json
import requests
from app import create_app

def test_card_api():
    """Test the card API endpoint that's failing in pytest."""
    print("🧪 TESTING CARD API ENDPOINT")
    print("="*50)
    
    # Create Flask app with testing config and force emulator mode
    os.environ['FLASK_CONFIG'] = 'testing'
    os.environ['RUN_INTEGRATION_TESTS'] = '1'
    os.environ['FORCE_EMULATOR_MODE'] = '1'
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    app = create_app('testing')
    
    with app.test_client() as client:
        print("📡 Making request to /api/cards...")
        response = client.get('/api/cards')
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Content Type: {response.content_type}")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            card_count = len(data.get('cards', []))
            print(f"✅ SUCCESS: Found {card_count} cards")
            
            if card_count >= 10:
                print("🎉 Test PASSED - API returned expected number of cards")
                return True
            else:
                print(f"⚠️ Test PARTIAL - Expected ≥10 cards, got {card_count}")
                return False
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            try:
                error_data = response.get_json()
                print(f"📄 Error: {error_data}")
            except:
                print(f"📄 Raw response: {response.data.decode()[:200]}")
            return False

def test_card_paginated_api():
    """Test the paginated card API endpoint."""
    print("\n🧪 TESTING PAGINATED CARD API ENDPOINT")
    print("="*50)
    
    # Create Flask app with testing config and force emulator mode  
    os.environ['FLASK_CONFIG'] = 'testing'
    os.environ['RUN_INTEGRATION_TESTS'] = '1'
    os.environ['FORCE_EMULATOR_MODE'] = '1'
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    app = create_app('testing')
    
    with app.test_client() as client:
        print("📡 Making request to /api/cards/paginated?limit=10...")
        response = client.get('/api/cards/paginated?limit=10')
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            card_count = len(data.get('cards', []))
            total_count = data.get('pagination', {}).get('total_count', 0)
            print(f"✅ SUCCESS: Found {card_count} cards (total: {total_count})")
            
            if total_count >= 10:
                print("🎉 Test PASSED - Paginated API returned expected total")
                return True
            else:
                print(f"⚠️ Test PARTIAL - Expected total ≥10 cards, got {total_count}")
                return False
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False

def main():
    """Run both API tests."""
    print("🚀 SIMPLE CARD API TEST")
    print("This tests the same endpoints that are failing in pytest")
    print()
    
    test1_passed = test_card_api()
    test2_passed = test_card_paginated_api()
    
    print("\n" + "="*50)
    print("📊 FINAL RESULTS")
    print("="*50)
    print(f"Card API test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Paginated API test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED - Integration tests should now work!")
        return True
    else:
        print("❌ TESTS FAILED - Issue still exists")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)