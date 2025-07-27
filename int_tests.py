#!/usr/bin/env python3
"""
Integration tests for OpenGameAssetLibrary API
Tests all major API endpoints to ensure they're working correctly
"""

import requests
import json
import time
import sys

API_URL = "http://127.0.0.1:5000"

def print_test(test_name):
    print(f"\n{'='*50}")
    print(f"Testing: {test_name}")
    print('='*50)

def print_result(status_code, expected, response_text):
    success = status_code == expected
    status_emoji = "✅" if success else "❌"
    print(f"{status_emoji} Status: {status_code} (expected {expected})")
    
    try:
        response_json = json.loads(response_text)
        print(f"📝 Response: {json.dumps(response_json, indent=2)}")
    except:
        print(f"📝 Response: {response_text[:200]}...")
    
    return success

def test_ping():
    print_test("Health Check (/ping)")
    try:
        r = requests.get(f"{API_URL}/ping")
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_browse_empty():
    print_test("Browse Assets - Initial State (/browse)")
    try:
        r = requests.get(f"{API_URL}/browse")
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            print(f"📊 Found {data.get('total', 0)} assets")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_add_asset():
    print_test("Add New Asset (/add_asset)")
    try:
        asset_data = {
            "name": "Test Magical Sword",
            "type": "item",
            "author": "test_user",
            "game_origin": "test_rpg",
            "description": "A powerful sword for testing",
            "attributes": {
                "damage": 50,
                "durability": 100
            },
            "tags": ["weapon", "magic", "test"],
            "rarity": "rare"
        }
        
        r = requests.post(f"{API_URL}/add_asset", json=asset_data)
        success = print_result(r.status_code, 200, r.text)
        
        asset_id = None
        if success:
            response_data = r.json()
            asset_id = response_data.get("asset", {}).get("id")
            print(f"🆔 Asset ID: {asset_id}")
        
        return success, asset_id
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, None

def test_browse_with_assets():
    print_test("Browse Assets - After Adding (/browse)")
    try:
        r = requests.get(f"{API_URL}/browse")
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            print(f"📊 Total assets: {data.get('total', 0)}")
            for asset in data.get('assets', [])[:3]:  # Show first 3
                print(f"   - {asset.get('name')} ({asset.get('type')})")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_search():
    print_test("Search Assets (/search)")
    try:
        r = requests.get(f"{API_URL}/search?q=test")
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            print(f"🔍 Search results: {data.get('total_results', 0)}")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_checkout(asset_id):
    if not asset_id:
        print("⏭️  Skipping checkout test - no asset ID")
        return False
        
    print_test("Checkout Asset (/checkout)")
    try:
        checkout_data = {
            "asset_id": asset_id,
            "borrower": "test_player",
            "game_context": "testing session"
        }
        
        r = requests.post(f"{API_URL}/checkout", json=checkout_data)
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_return_asset(asset_id):
    if not asset_id:
        print("⏭️  Skipping return test - no asset ID")
        return False
        
    print_test("Return Asset (/return)")
    try:
        return_data = {
            "asset_id": asset_id,
            "borrower": "test_player",
            "condition": "good"
        }
        
        r = requests.post(f"{API_URL}/return", json=return_data)
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_asset_history(asset_id):
    if not asset_id:
        print("⏭️  Skipping history test - no asset ID")
        return False
        
    print_test(f"Asset History (/history/{asset_id})")
    try:
        r = requests.get(f"{API_URL}/history/{asset_id}")
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_library_history():
    print_test("Library Statistics (/history)")
    try:
        r = requests.get(f"{API_URL}/history")
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_generate_test_data():
    print_test("Generate Test Data (/utils/generate)")
    try:
        r = requests.post(f"{API_URL}/utils/generate?count=3")
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_batch_import():
    print_test("Batch Import (/batch/import)")
    try:
        batch_data = {
            "assets": [
                {
                    "name": "Batch Asset 1",
                    "type": "creature",
                    "author": "batch_test",
                    "game_origin": "batch_game"
                },
                {
                    "name": "Batch Asset 2", 
                    "type": "spell",
                    "author": "batch_test",
                    "game_origin": "batch_game"
                }
            ]
        }
        
        r = requests.post(f"{API_URL}/batch/import", json=batch_data)
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_export():
    print_test("Export Collection (/export)")
    try:
        r = requests.get(f"{API_URL}/export?type=item")
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_git_status():
    print_test("Git Status (/utils/git-status)")
    try:
        r = requests.get(f"{API_URL}/utils/git-status")
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_cleanup():
    print_test("Cleanup Test Data (/utils/cleanup)")
    try:
        r = requests.post(f"{API_URL}/utils/cleanup")
        return print_result(r.status_code, 200, r.text)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("🚀 Starting OpenGameAssetLibrary Integration Tests")
    print(f"🌐 API URL: {API_URL}")
    
    # Check if server is running
    try:
        requests.get(f"{API_URL}/ping", timeout=5)
    except:
        print("\n❌ ERROR: Cannot connect to API server!")
        print("Make sure the server is running with: python api_server.py")
        sys.exit(1)
    
    # Track test results
    tests_run = 0
    tests_passed = 0
    
    def run_test(test_func, *args):
        nonlocal tests_run, tests_passed
        tests_run += 1
        time.sleep(0.5)  # Brief pause between tests
        if test_func(*args):
            tests_passed += 1
    
    # Run all tests
    run_test(test_ping)
    run_test(test_browse_empty)
    
    # Add an asset and get its ID
    success, asset_id = test_add_asset()
    tests_run += 1
    if success:
        tests_passed += 1
    
    run_test(test_browse_with_assets)
    run_test(test_search)
    run_test(test_checkout, asset_id)
    run_test(test_return_asset, asset_id)
    run_test(test_asset_history, asset_id)
    run_test(test_library_history)
    run_test(test_generate_test_data)
    run_test(test_batch_import)
    run_test(test_export)
    run_test(test_git_status)
    run_test(test_cleanup)
    
    # Final results
    print(f"\n{'='*60}")
    print("🏁 TEST RESULTS")
    print('='*60)
    print(f"Tests Run: {tests_run}")
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_run - tests_passed}")
    print(f"Success Rate: {(tests_passed/tests_run*100):.1f}%")
    
    if tests_passed == tests_run:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()