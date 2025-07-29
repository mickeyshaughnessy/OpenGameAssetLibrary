#!/usr/bin/env python3
"""
Integration tests for Simple Asset Library API
Tests the simplified API endpoints
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
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            print(f"📌 Version: {data.get('version', 'unknown')}")
            # Check for database status if available (enhanced version)
            db_status = data.get('database_status')
            if db_status:
                print(f"🗄️  Database Status: {db_status.get('status', 'unknown')}")
                print(f"📊 Candles Count: {db_status.get('candles_count', 0)}")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_browse_initial():
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
    print_test("Add New Asset (/add)")
    try:
        asset_data = {
            "name": "Test 3D Model Pack",
            "type": "3d_models",
            "author": "test_creator",
            "description": "A collection of test 3D models",
            "attributes": {
                "file_count": 25,
                "total_size": "150MB",
                "format": "FBX"
            },
            "tags": ["3d", "models", "test"],
            "rarity": "uncommon",
            "file_extension": "zip"
        }
        
        r = requests.post(f"{API_URL}/add", json=asset_data)
        success = print_result(r.status_code, 200, r.text)
        
        asset_id = None
        if success:
            response_data = r.json()
            asset_id = response_data.get("asset", {}).get("id")
            s3_url = response_data.get("asset", {}).get("s3_url")
            indexed = response_data.get("indexed", False)
            print(f"🆔 Asset ID: {asset_id}")
            print(f"🔗 S3 URL: {s3_url}")
            if 'indexed' in response_data:
                print(f"🔍 Indexed for search: {indexed}")
        
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
            for asset in data.get('assets', [])[:5]:  # Show first 5
                checkout_count = asset.get('checkout_count', 0)
                print(f"   - {asset.get('name')} ({asset.get('type')}) - Checkouts: {checkout_count}")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_search():
    print_test("Search Assets - Text Mode (/search)")
    try:
        # Test text search
        r = requests.get(f"{API_URL}/search?q=test")
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            print(f"🔍 Search mode: {data.get('mode', 'text')}")
            print(f"🔍 Search results for 'test': {data.get('total_results', 0)}")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False





def test_get_asset(asset_id):
    if not asset_id:
        print("⏭️  Skipping get asset test - no asset ID")
        return False
        
    print_test(f"Get Asset Details (/asset/{asset_id})")
    try:
        r = requests.get(f"{API_URL}/asset/{asset_id}")
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            asset = data.get('asset', {})
            # Show checkout count if available
            if 'checkout_count' in asset:
                print(f"📊 Total checkouts: {asset.get('checkout_count', 0)}")
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
            "borrower": "test_user_123"
        }
        
        r = requests.post(f"{API_URL}/checkout", json=checkout_data)
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            checkout = data.get('checkout', {})
            print(f"📦 Checked out by: {checkout.get('user')}")
            print(f"🔗 Download URL: {checkout.get('s3_url')}")
            print(f"🆔 Checkout ID: {checkout.get('checkout_id')}")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_multiple_checkouts(asset_id):
    if not asset_id:
        print("⏭️  Skipping multiple checkout test - no asset ID")
        return False
        
    print_test("Multiple Users Checkout Same Asset (/checkout)")
    try:
        # Second user checkouts the same asset
        checkout_data = {
            "asset_id": asset_id,
            "borrower": "another_user_456"
        }
        
        r = requests.post(f"{API_URL}/checkout", json=checkout_data)
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            checkout = data.get('checkout', {})
            print(f"📦 Also checked out by: {checkout.get('user')}")
            print(f"✅ Multiple checkouts allowed!")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False



def test_stats():
    print_test("Library Statistics (/stats)")
    try:
        r = requests.get(f"{API_URL}/stats")
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            stats = data.get('library_stats', {})
            print(f"📈 Total assets: {stats.get('total_assets', 0)}")
            print(f"📈 Total checkouts: {stats.get('total_checkouts', 0)}")
            
            # Type breakdown
            by_type = stats.get('by_type', {})
            if by_type:
                print(f"📊 Assets by type:")
                for asset_type, count in by_type.items():
                    print(f"   - {asset_type}: {count}")
            
            # Database stats (if available in enhanced version)
            db_stats = stats.get('database_stats')
            if db_stats:
                print(f"🗄️  Database: {db_stats.get('status', 'unknown')}")
                print(f"📊 Indexed items: {db_stats.get('candles_count', 0)}")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_filtered_browse():
    print_test("Browse with Filters (/browse?type=3d_models)")
    try:
        r = requests.get(f"{API_URL}/browse?type=3d_models")
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            print(f"📊 3D Models found: {data.get('total', 0)}")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_search_with_filters():
    print_test("Search with Filters (/search?type=3d_models&rarity=uncommon)")
    try:
        r = requests.get(f"{API_URL}/search?type=3d_models&rarity=uncommon")
        success = print_result(r.status_code, 200, r.text)
        if success:
            data = r.json()
            print(f"🔍 Filtered results: {data.get('total_results', 0)}")
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False



def main():
    print("🚀 Starting Simple Asset Library Integration Tests")
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
        result = test_func(*args)
        if result is True:
            tests_passed += 1
        elif isinstance(result, tuple) and result[0] is True:
            tests_passed += 1
            return result[1] if len(result) > 1 else None
        return result
    
    # Run all tests
    run_test(test_ping)
    run_test(test_browse_initial)
    
    # Add an asset and get its ID
    asset_id = run_test(test_add_asset)
    
    run_test(test_browse_with_assets)
    run_test(test_search)
    run_test(test_get_asset, asset_id)
    run_test(test_stats)
    run_test(test_filtered_browse)
    run_test(test_search_with_filters)
    run_test(test_checkout, asset_id)
    run_test(test_multiple_checkouts, asset_id)
    
    # Test get asset again to see checkout count
    run_test(test_get_asset, asset_id)
    
    # Test browse again to see updated checkout count
    run_test(test_browse_with_assets)
    run_test(test_stats)
    
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
        print("\n✨ Your Simple Asset Library is working perfectly!")
        print("👥 Multiple users can now checkout the same asset simultaneously!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()