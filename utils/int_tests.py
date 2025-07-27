#!/usr/bin/env python3
"""
Integration tests for OpenGameAssetLibrary API
Run with: python int_tests.py
"""

import requests
import json
import time
import sys
from datetime import datetime

API_URL = "http://localhost:5000"

# Test tracking
tests_passed = 0
tests_failed = 0
test_assets = []  # Track created assets for cleanup


def test(name, func):
    """Run a test and track results"""
    global tests_passed, tests_failed
    print(f"\n[TEST] {name}...", end=" ")
    try:
        func()
        print("✅ PASSED")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ FAILED: {e}")
        tests_failed += 1
    except Exception as e:
        print(f"❌ ERROR: {e}")
        tests_failed += 1


def assert_equals(actual, expected, message=""):
    """Assert equality with descriptive message"""
    if actual != expected:
        raise AssertionError(f"{message} Expected {expected}, got {actual}")


def assert_in(item, container, message=""):
    """Assert item is in container"""
    if item not in container:
        raise AssertionError(f"{message} {item} not found in {container}")


def assert_status(response, expected_status):
    """Assert HTTP status code"""
    if response.status_code != expected_status:
        raise AssertionError(f"Expected status {expected_status}, got {response.status_code}: {response.text}")


# ============= CORE ENDPOINT TESTS =============

def test_ping():
    """Test health check endpoint"""
    response = requests.get(f"{API_URL}/ping")
    assert_status(response, 200)
    data = response.json()
    assert_equals(data["status"], "alive")
    assert_in("timestamp", data)
    assert_equals(data["service"], "OpenGameAssetLibrary")


def test_add_asset():
    """Test adding a new asset"""
    asset_data = {
        "name": "Test Dragon",
        "type": "creature",
        "author": "test_author",
        "game_origin": "test_game",
        "description": "A test creature for integration testing",
        "attributes": {
            "power": 75,
            "defense": 60,
            "health": 150,
            "element": "fire"
        },
        "tags": ["test", "dragon", "fire"],
        "rarity": "rare"
    }
    
    response = requests.post(f"{API_URL}/add_asset", json=asset_data)
    assert_status(response, 200)
    data = response.json()
    assert_equals(data["message"], "Asset added successfully")
    assert_in("asset", data)
    
    # Verify asset properties
    asset = data["asset"]
    assert_equals(asset["name"], "Test Dragon")
    assert_equals(asset["type"], "creature")
    assert_equals(asset["available"], True)
    assert_equals(asset["attributes"]["power"], 75)
    
    # Track for cleanup
    test_assets.append(asset["id"])
    return asset["id"]


def test_browse():
    """Test browsing assets"""
    # Browse all assets
    response = requests.get(f"{API_URL}/browse")
    assert_status(response, 200)
    data = response.json()
    assert_in("assets", data)
    assert_in("total", data)
    
    # Browse with filters
    response = requests.get(f"{API_URL}/browse?type=creature&available=true")
    assert_status(response, 200)
    data = response.json()
    for asset in data["assets"]:
        assert_equals(asset["type"], "creature")
        assert_equals(asset["available"], True)


def test_checkout():
    """Test checking out an asset"""
    # First add an asset
    asset_id = test_add_asset()
    
    # Check it out
    checkout_data = {
        "asset_id": asset_id,
        "borrower": "test_player",
        "game_context": "test_session"
    }
    
    response = requests.post(f"{API_URL}/checkout", json=checkout_data)
    assert_status(response, 200)
    data = response.json()
    assert_equals(data["message"], "Asset checked out successfully")
    assert_equals(data["asset"]["id"], asset_id)
    
    # Verify asset is no longer available
    response = requests.get(f"{API_URL}/browse?available=true")
    asset_ids = [a["id"] for a in response.json()["assets"]]
    assert asset_id not in asset_ids, "Checked out asset should not be available"


def test_checkout_unavailable():
    """Test checking out an already checked out asset"""
    # Get a checked out asset
    response = requests.get(f"{API_URL}/browse?available=false")
    data = response.json()
    
    if data["total"] > 0:
        asset = data["assets"][0]
        checkout_data = {
            "asset_id": asset["id"],
            "borrower": "another_player",
            "game_context": "test"
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data)
        assert_status(response, 400)
        assert_in("already checked out", response.json()["error"])


def test_return():
    """Test returning an asset"""
    # First check out an asset
    asset_id = test_add_asset()
    checkout_data = {
        "asset_id": asset_id,
        "borrower": "test_player",
        "game_context": "test_session"
    }
    requests.post(f"{API_URL}/checkout", json=checkout_data)
    
    # Return it
    return_data = {
        "asset_id": asset_id,
        "borrower": "test_player",
        "condition": "good",
        "notes": "Test return"
    }
    
    response = requests.post(f"{API_URL}/return", json=return_data)
    assert_status(response, 200)
    data = response.json()
    assert_equals(data["message"], "Asset returned successfully")
    assert_equals(data["return_details"]["condition"], "good")
    
    # Verify asset is available again
    response = requests.get(f"{API_URL}/browse?available=true")
    asset_ids = [a["id"] for a in response.json()["assets"]]
    assert asset_id in asset_ids, "Returned asset should be available"


def test_return_wrong_borrower():
    """Test returning an asset by wrong borrower"""
    # Setup
    asset_id = test_add_asset()
    checkout_data = {
        "asset_id": asset_id,
        "borrower": "player1",
        "game_context": "test"
    }
    requests.post(f"{API_URL}/checkout", json=checkout_data)
    
    # Try to return as different player
    return_data = {
        "asset_id": asset_id,
        "borrower": "player2",
        "condition": "good"
    }
    
    response = requests.post(f"{API_URL}/return", json=return_data)
    assert_status(response, 403)
    assert_in("checked out to someone else", response.json()["error"])


# ============= HISTORY TESTS =============

def test_asset_history():
    """Test getting asset history"""
    # Create asset with some history
    asset_id = test_add_asset()
    
    # Check out and return
    checkout_data = {"asset_id": asset_id, "borrower": "player1", "game_context": "game1"}
    requests.post(f"{API_URL}/checkout", json=checkout_data)
    return_data = {"asset_id": asset_id, "borrower": "player1", "condition": "good"}
    requests.post(f"{API_URL}/return", json=return_data)
    
    # Get history
    response = requests.get(f"{API_URL}/history/{asset_id}")
    assert_status(response, 200)
    data = response.json()
    
    assert_in("asset", data)
    assert_in("statistics", data)
    assert_in("checkout_history", data)
    assert_equals(data["statistics"]["total_checkouts"], 1)
    assert_equals(len(data["checkout_history"]), 1)


def test_library_history():
    """Test getting library statistics"""
    response = requests.get(f"{API_URL}/history")
    assert_status(response, 200)
    data = response.json()
    
    assert_in("library_statistics", data)
    stats = data["library_statistics"]
    assert_in("total_assets", stats)
    assert_in("by_type", stats)
    assert_in("by_rarity", stats)
    assert stats["total_assets"] >= 0


# ============= SEARCH TESTS =============

def test_search():
    """Test search functionality"""
    # Add searchable asset
    asset_data = {
        "name": "Searchable Phoenix",
        "type": "creature",
        "author": "test_author",
        "game_origin": "test_game",
        "description": "A mythical fire bird for searching",
        "tags": ["phoenix", "fire", "legendary"],
        "rarity": "legendary"
    }
    response = requests.post(f"{API_URL}/add_asset", json=asset_data)
    asset_id = response.json()["asset"]["id"]
    test_assets.append(asset_id)
    
    # Search by text
    response = requests.get(f"{API_URL}/search?q=phoenix")
    assert_status(response, 200)
    data = response.json()
    assert data["total_results"] > 0
    found = any(r["name"] == "Searchable Phoenix" for r in data["results"])
    assert found, "Should find phoenix in search results"
    
    # Search with filters
    response = requests.get(f"{API_URL}/search?type=creature&rarity=legendary")
    assert_status(response, 200)
    data = response.json()
    for result in data["results"]:
        assert_equals(result["type"], "creature")
        assert_equals(result["rarity"], "legendary")


def test_popular():
    """Test popular assets endpoint"""
    response = requests.get(f"{API_URL}/popular?limit=5&days=7")
    assert_status(response, 200)
    data = response.json()
    
    assert_in("period_days", data)
    assert_in("popular_assets", data)
    assert_equals(data["period_days"], 7)
    assert len(data["popular_assets"]) <= 5


# ============= BATCH TESTS =============

def test_batch_import():
    """Test batch import functionality"""
    batch_data = {
        "assets": [
            {
                "name": "Batch Item 1",
                "type": "item",
                "author": "test_author",
                "game_origin": "test_game",
                "attributes": {"effects": [{"type": "heal", "value": 20}]}
            },
            {
                "name": "Batch Item 2",
                "type": "item",
                "author": "test_author",
                "game_origin": "test_game",
                "attributes": {"effects": [{"type": "boost", "value": 10}]}
            }
        ]
    }
    
    response = requests.post(f"{API_URL}/batch/import", json=batch_data)
    assert_status(response, 200)
    data = response.json()
    
    assert_equals(data["success"], 2)
    assert_equals(data["failed"], 0)
    assert_equals(len(data["imported"]), 2)
    
    # Track for cleanup
    for asset in data["imported"]:
        test_assets.append(asset["id"])


def test_batch_checkout():
    """Test batch checkout functionality"""
    # Add multiple assets
    asset_ids = []
    for i in range(3):
        asset_data = {
            "name": f"Batch Checkout Item {i}",
            "type": "item",
            "author": "test_author",
            "game_origin": "test_game"
        }
        response = requests.post(f"{API_URL}/add_asset", json=asset_data)
        asset_id = response.json()["asset"]["id"]
        asset_ids.append(asset_id)
        test_assets.append(asset_id)
    
    # Batch checkout
    checkout_data = {
        "asset_ids": asset_ids,
        "borrower": "batch_player",
        "game_context": "batch_test"
    }
    
    response = requests.post(f"{API_URL}/batch/checkout", json=checkout_data)
    assert_status(response, 200)
    data = response.json()
    
    assert_equals(data["success"], 3)
    assert_equals(data["failed"], 0)


def test_export():
    """Test export functionality"""
    response = requests.get(f"{API_URL}/export?type=creature&rarity=rare")
    assert_status(response, 200)
    data = response.json()
    
    assert_in("export_timestamp", data)
    assert_in("asset_count", data)
    assert_in("assets", data)
    
    # Exported assets should not have checkout history
    for asset in data["assets"]:
        assert "checkout_history" not in asset
        assert "current_borrower" not in asset


# ============= UTILITY TESTS =============

def test_generate_test_data():
    """Test test data generation"""
    response = requests.post(f"{API_URL}/utils/generate")
    assert_status(response, 200)
    data = response.json()
    
    assert_in("Generated", data["message"])
    assert len(data["assets"]) > 0


def test_git_status():
    """Test git status endpoint"""
    response = requests.get(f"{API_URL}/utils/git-status")
    assert_status(response, 200)
    data = response.json()
    
    assert_in("branch", data)
    assert_in("current_commit", data)
    assert_in("recent_commits", data)


def test_cleanup():
    """Test cleanup functionality"""
    # First generate test data
    requests.post(f"{API_URL}/utils/generate")
    
    # Then clean it up
    response = requests.post(f"{API_URL}/utils/cleanup")
    assert_status(response, 200)
    data = response.json()
    
    assert_in("removed", data)
    assert_in("message", data)


# ============= ERROR HANDLING TESTS =============

def test_missing_required_fields():
    """Test error handling for missing fields"""
    # Missing required field
    asset_data = {
        "name": "Incomplete Asset",
        "type": "item"
        # Missing author and game_origin
    }
    
    response = requests.post(f"{API_URL}/add_asset", json=asset_data)
    assert_status(response, 400)
    assert_in("Missing required fields", response.json()["error"])


def test_invalid_asset_id():
    """Test handling of invalid asset IDs"""
    response = requests.get(f"{API_URL}/history/invalid-id-12345")
    assert_status(response, 404)
    assert_in("not found", response.json()["error"])


def test_empty_batch():
    """Test empty batch operations"""
    response = requests.post(f"{API_URL}/batch/import", json={"assets": []})
    assert_status(response, 400)
    assert_in("No assets provided", response.json()["error"])


# ============= MULTIMEDIA ASSET TESTS =============

def test_multimedia_assets():
    """Test adding various multimedia asset types"""
    multimedia_assets = [
        {
            "name": "Test Character Background",
            "type": "text",
            "author": "test_author",
            "game_origin": "test_game",
            "description": "A character's backstory",
            "media": {
                "full_text": "https://mithrilmedia.s3.amazonaws.com/text/test_background.md"
            },
            "tags": ["backstory", "text"]
        },
        {
            "name": "Test NPC",
            "type": "npc",
            "author": "test_author",
            "game_origin": "test_game",
            "description": "A friendly merchant",
            "attributes": {
                "personality": "friendly",
                "services": ["trade", "quest"]
            },
            "media": {
                "portrait": "https://mithrilmedia.s3.amazonaws.com/images/npc_merchant.jpg",
                "dialogue": "https://mithrilmedia.s3.amazonaws.com/dialogue/merchant.json"
            }
        },
        {
            "name": "Test Battle Music",
            "type": "audio",
            "author": "test_author",
            "game_origin": "test_game",
            "attributes": {
                "format": "ogg",
                "duration": 180,
                "loop_points": {"start": 10, "end": 170}
            },
            "media": {
                "track": "https://mithrilmedia.s3.amazonaws.com/audio/battle_theme.ogg"
            }
        }
    ]
    
    for asset_data in multimedia_assets:
        response = requests.post(f"{API_URL}/add_asset", json=asset_data)
        assert_status(response, 200)
        asset = response.json()["asset"]
        test_assets.append(asset["id"])
        
        # Verify media URLs are preserved
        assert_equals(asset["media"], asset_data["media"])


# ============= MAIN TEST RUNNER =============

def cleanup_test_assets():
    """Clean up all test assets created during tests"""
    print("\nCleaning up test assets...")
    for asset_id in test_assets:
        try:
            # Try to return if checked out
            requests.post(f"{API_URL}/return", json={
                "asset_id": asset_id,
                "borrower": "test_player",
                "condition": "good"
            })
        except:
            pass
    
    # Use cleanup endpoint for test authors
    requests.post(f"{API_URL}/utils/cleanup")


def run_all_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("OpenGameAssetLibrary Integration Tests")
    print("=" * 60)
    
    # Check if API is running
    try:
        requests.get(f"{API_URL}/ping", timeout=2)
    except:
        print(f"\n❌ ERROR: API server not running at {API_URL}")
        print("Please start the server with: python api_server.py")
        sys.exit(1)
    
    # Core tests
    test("Ping endpoint", test_ping)
    test("Add asset", test_add_asset)
    test("Browse assets", test_browse)
    test("Checkout asset", test_checkout)
    test("Checkout unavailable asset", test_checkout_unavailable)
    test("Return asset", test_return)
    test("Return wrong borrower", test_return_wrong_borrower)
    
    # History tests
    test("Asset history", test_asset_history)
    test("Library history", test_library_history)
    
    # Search tests
    test("Search functionality", test_search)
    test("Popular assets", test_popular)
    
    # Batch tests
    test("Batch import", test_batch_import)
    test("Batch checkout", test_batch_checkout)
    test("Export collection", test_export)
    
    # Utility tests
    test("Generate test data", test_generate_test_data)
    test("Git status", test_git_status)
    test("Cleanup", test_cleanup)
    
    # Error handling tests
    test("Missing required fields", test_missing_required_fields)
    test("Invalid asset ID", test_invalid_asset_id)
    test("Empty batch", test_empty_batch)
    
    # Multimedia tests
    test("Multimedia assets", test_multimedia_assets)
    
    # Cleanup
    cleanup_test_assets()
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests completed: {tests_passed + tests_failed}")
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    print("=" * 60)
    
    return tests_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)