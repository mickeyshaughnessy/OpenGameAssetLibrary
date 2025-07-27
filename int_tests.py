#!/usr/bin/env python3
"""Simple test runner to check API endpoints"""
import requests
import json
import time

API_URL = "http://127.0.0.1:5000"

print("Testing OpenGameAssetLibrary API...")
print(f"API URL: {API_URL}\n")

# Test 1: Ping
print("1. Testing /ping...")
try:
    r = requests.get(f"{API_URL}/ping")
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.text}")
except Exception as e:
    print(f"   ERROR: {e}")

time.sleep(0.5)

# Test 2: Add Asset
print("\n2. Testing /add_asset...")
try:
    asset_data = {
        "name": "Test Sword",
        "type": "item",
        "author": "tester",
        "game_origin": "test_game"
    }
    r = requests.post(f"{API_URL}/add_asset", json=asset_data)
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.text[:100]}...")
    
    if r.status_code == 200:
        asset_id = r.json()["asset"]["id"]
        print(f"   Asset ID: {asset_id}")
except Exception as e:
    print(f"   ERROR: {e}")
    asset_id = None

time.sleep(0.5)

# Test 3: Browse
print("\n3. Testing /browse...")
try:
    r = requests.get(f"{API_URL}/browse")
    print(f"   Status: {r.status_code}")
    data = r.json()
    print(f"   Total assets: {data.get('total', 0)}")
except Exception as e:
    print(f"   ERROR: {e}")

time.sleep(0.5)

# Test 4: Search
print("\n4. Testing /search...")
try:
    r = requests.get(f"{API_URL}/search?q=test")
    print(f"   Status: {r.status_code}")
    data = r.json()
    print(f"   Results found: {data.get('total_results', 0)}")
except Exception as e:
    print(f"   ERROR: {e}")

time.sleep(0.5)

# Test 5: Checkout (if we have an asset)
if asset_id:
    print("\n5. Testing /checkout...")
    try:
        checkout_data = {
            "asset_id": asset_id,
            "borrower": "player1"
        }
        r = requests.post(f"{API_URL}/checkout", json=checkout_data)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.text[:100]}...")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    time.sleep(0.5)
    
    # Test 6: Return
    print("\n6. Testing /return...")
    try:
        return_data = {
            "asset_id": asset_id,
            "borrower": "player1"
        }
        r = requests.post(f"{API_URL}/return", json=return_data)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.text}")
    except Exception as e:
        print(f"   ERROR: {e}")

print("\n✓ Basic tests completed!")
print("\nTo run full integration tests: python int_tests.py")