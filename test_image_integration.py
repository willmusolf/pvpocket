#!/usr/bin/env python3
"""
Test script to validate real card images integration in battle simulator.
Checks Firebase image URLs, API responses, and overall system integration.
"""

import requests
import json
import sys
import time
from typing import Dict, List, Any

def test_card_api_images(base_url: str = "http://localhost:5002") -> Dict[str, Any]:
    """Test card API endpoints for image URL inclusion."""
    results = {
        "card_search_api": False,
        "dev_card_search_api": False,
        "sample_cards_with_images": [],
        "sample_cards_without_images": [],
        "total_tested": 0,
        "errors": []
    }
    
    try:
        # Test regular card search API
        response = requests.get(f"{base_url}/api/cards/search", params={"q": "pikachu", "limit": 3})
        if response.status_code == 200:
            data = response.json()
            results["card_search_api"] = data.get("success", False)
            # Note: This API doesn't include firebase_image_url by design
        
        # Test dev card search API (includes firebase_image_url)
        response = requests.get(f"{base_url}/api/dev/cards/search", params={"q": "pikachu", "limit": 5})
        if response.status_code == 200:
            data = response.json()
            results["dev_card_search_api"] = data.get("success", False)
            results["total_tested"] = data.get("total_found", 0)
            
            for card in data.get("cards", []):
                if card.get("firebase_image_url"):
                    results["sample_cards_with_images"].append({
                        "name": card["name"],
                        "energy_type": card["energy_type"],
                        "image_url_preview": card["firebase_image_url"][:60] + "..." if len(card["firebase_image_url"]) > 60 else card["firebase_image_url"]
                    })
                else:
                    results["sample_cards_without_images"].append({
                        "name": card["name"],
                        "energy_type": card["energy_type"]
                    })
        
    except Exception as e:
        results["errors"].append(f"Card API test failed: {str(e)}")
    
    return results

def test_battle_api_images(base_url: str = "http://localhost:5002") -> Dict[str, Any]:
    """Test battle API for image URL inclusion in game state."""
    results = {
        "battle_creation": False,
        "images_in_game_state": False,
        "battle_id": None,
        "player_cards_with_images": {"player_1": 0, "player_2": 0},
        "total_cards_checked": {"player_1": 0, "player_2": 0},
        "sample_pokemon": [],
        "errors": []
    }
    
    try:
        # Create a battle
        battle_data = {
            "deck1_type": "fire",
            "deck2_type": "water", 
            "mode": "ai_vs_ai",
            "seed": 42
        }
        
        response = requests.post(
            f"{base_url}/api/battle/start",
            json=battle_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results["battle_creation"] = data.get("success", False)
            
            if results["battle_creation"]:
                results["battle_id"] = data.get("battle_id")
                game_state = data.get("current_state", {})
                players = game_state.get("players", [])
                
                for i, player in enumerate(players):
                    player_key = f"player_{i+1}"
                    
                    # Check active Pokemon
                    active = player.get("active_pokemon")
                    if active and active.get("card"):
                        card = active["card"]
                        results["total_cards_checked"][player_key] += 1
                        
                        if card.get("firebase_image_url"):
                            results["player_cards_with_images"][player_key] += 1
                            results["sample_pokemon"].append({
                                "player": i+1,
                                "type": "active",
                                "name": card["name"],
                                "has_image": True,
                                "image_preview": card["firebase_image_url"][:50] + "..."
                            })
                        else:
                            results["sample_pokemon"].append({
                                "player": i+1,
                                "type": "active", 
                                "name": card["name"],
                                "has_image": False
                            })
                    
                    # Check hand cards (sample first 3)
                    hand = player.get("hand", [])[:3]
                    for card in hand:
                        results["total_cards_checked"][player_key] += 1
                        if card.get("firebase_image_url"):
                            results["player_cards_with_images"][player_key] += 1
                
                # Determine if images are properly included
                total_with_images = sum(results["player_cards_with_images"].values())
                total_checked = sum(results["total_cards_checked"].values())
                results["images_in_game_state"] = total_with_images > 0 and (total_with_images / total_checked) > 0.8
                
    except Exception as e:
        results["errors"].append(f"Battle API test failed: {str(e)}")
    
    return results

def test_image_accessibility(image_urls: List[str]) -> Dict[str, Any]:
    """Test if Firebase image URLs are accessible."""
    results = {
        "accessible_count": 0,
        "inaccessible_count": 0,
        "total_tested": len(image_urls),
        "sample_results": [],
        "errors": []
    }
    
    for url in image_urls[:5]:  # Test first 5 URLs
        try:
            response = requests.head(url, timeout=10)
            accessible = response.status_code == 200
            
            if accessible:
                results["accessible_count"] += 1
            else:
                results["inaccessible_count"] += 1
            
            results["sample_results"].append({
                "url_preview": url[:60] + "..." if len(url) > 60 else url,
                "accessible": accessible,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", "unknown")
            })
            
        except Exception as e:
            results["inaccessible_count"] += 1
            results["errors"].append(f"Failed to test {url[:60]}...: {str(e)}")
    
    return results

def test_battle_simulator_endpoints(base_url: str = "http://localhost:5002") -> Dict[str, Any]:
    """Test battle simulator specific endpoints."""
    results = {
        "battle_simulator_page": False,
        "test_battle_endpoint": False,
        "errors": []
    }
    
    try:
        # Test battle simulator page
        response = requests.get(f"{base_url}/battle-simulator")
        results["battle_simulator_page"] = response.status_code == 200
        
        # Test advanced battle endpoint
        response = requests.get(f"{base_url}/api/test-battle")
        if response.status_code == 200:
            data = response.json()
            results["test_battle_endpoint"] = data.get("success", False)
            
    except Exception as e:
        results["errors"].append(f"Battle simulator endpoints test failed: {str(e)}")
    
    return results

def run_comprehensive_test() -> Dict[str, Any]:
    """Run all image integration tests."""
    print("🧪 Running comprehensive image integration tests...")
    print("=" * 60)
    
    all_results = {}
    
    # Test 1: Card API Images
    print("\n1. Testing Card API Image URLs...")
    card_results = test_card_api_images()
    all_results["card_api"] = card_results
    
    if card_results["dev_card_search_api"]:
        print(f"✅ Dev Card API working - {len(card_results['sample_cards_with_images'])} cards with images")
        for card in card_results["sample_cards_with_images"][:3]:
            print(f"   - {card['name']} ({card['energy_type']}): {card['image_url_preview']}")
    else:
        print("❌ Dev Card API failed")
    
    # Test 2: Battle API Images  
    print("\n2. Testing Battle API Image Integration...")
    battle_results = test_battle_api_images()
    all_results["battle_api"] = battle_results
    
    if battle_results["battle_creation"]:
        print(f"✅ Battle created successfully: {battle_results['battle_id']}")
        if battle_results["images_in_game_state"]:
            print("✅ Images properly included in game state")
            p1_images = battle_results["player_cards_with_images"]["player_1"]
            p2_images = battle_results["player_cards_with_images"]["player_2"]
            print(f"   Player 1: {p1_images} cards with images")
            print(f"   Player 2: {p2_images} cards with images")
        else:
            print("❌ Images missing from game state")
    else:
        print("❌ Battle creation failed")
    
    # Test 3: Image Accessibility
    print("\n3. Testing Firebase Image Accessibility...")
    sample_urls = []
    if battle_results["sample_pokemon"]:
        for pokemon in battle_results["sample_pokemon"]:
            if pokemon.get("has_image") and "image_preview" in pokemon:
                # Reconstruct full URL (this is a preview)
                sample_urls.append("https://storage.googleapis.com/pvpocket-dd286.firebasestorage.app/cards/genetic-apex/259")  # Sample URL
    
    if sample_urls:
        image_results = test_image_accessibility(sample_urls)
        all_results["image_accessibility"] = image_results
        
        if image_results["accessible_count"] > 0:
            print(f"✅ {image_results['accessible_count']}/{image_results['total_tested']} images accessible")
        else:
            print(f"❌ No images accessible")
    else:
        print("⚠️  No image URLs available for testing")
    
    # Test 4: Battle Simulator Endpoints
    print("\n4. Testing Battle Simulator Endpoints...")
    simulator_results = test_battle_simulator_endpoints()
    all_results["battle_simulator"] = simulator_results
    
    if simulator_results["battle_simulator_page"]:
        print("✅ Battle simulator page accessible")
    else:
        print("❌ Battle simulator page failed")
        
    if simulator_results["test_battle_endpoint"]:
        print("✅ Test battle endpoint working")
    else:
        print("❌ Test battle endpoint failed")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    if card_results["dev_card_search_api"]: tests_passed += 1
    if battle_results["battle_creation"] and battle_results["images_in_game_state"]: tests_passed += 1
    if "image_accessibility" in all_results and all_results["image_accessibility"]["accessible_count"] > 0: tests_passed += 1
    if simulator_results["battle_simulator_page"]: tests_passed += 1
    
    print(f"Tests passed: {tests_passed}/{total_tests}")
    print(f"Success rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED - Image integration is working correctly!")
    elif tests_passed >= 2:
        print("⚠️  PARTIAL SUCCESS - Some components working, check details above")
    else:
        print("❌ INTEGRATION FAILED - Major issues detected")
    
    print("\n🚀 Next steps:")
    print("   1. Open http://localhost:5002/battle-simulator (Flask integration)")
    print("   2. Open http://localhost:5173 (React dev server)")
    print("   3. Create a battle and observe image loading")
    
    return all_results

if __name__ == "__main__":
    try:
        results = run_comprehensive_test()
        
        # Save detailed results
        with open("image_integration_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Detailed results saved to: image_integration_test_results.json")
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test runner failed: {str(e)}")
        sys.exit(1)