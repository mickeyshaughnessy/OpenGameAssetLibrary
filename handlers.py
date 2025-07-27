"""
OpenGameAssetLibrary - All API Handlers
Consolidated handler module for asset library management
"""

from flask import jsonify, request
import os
import json
import uuid
import random
from datetime import datetime, timedelta
from utils.git_wrapper import run_git, get_file_history

LIBRARY_PATH = "./library-repo"
S3_BUCKET = "https://mithrilmedia.s3.amazonaws.com"


# ============= CORE HANDLERS =============

def ping():
    """Health check endpoint"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "OpenGameAssetLibrary"
    })


def browse():
    """List all assets with optional filtering"""
    assets = []
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    
    # Get filters
    asset_type = request.args.get('type')
    game = request.args.get('game')
    available = request.args.get('available')
    tags = request.args.getlist('tag')
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if not filename.endswith('.json'):
                continue
                
            with open(os.path.join(assets_dir, filename), 'r') as f:
                asset = json.load(f)
                
                # Apply filters
                if asset_type and asset.get('type') != asset_type:
                    continue
                if game and asset.get('game_origin') != game:
                    continue
                if available is not None:
                    is_available = asset.get('available', True)
                    if (available.lower() == 'true') != is_available:
                        continue
                if tags and not any(tag in asset.get('tags', []) for tag in tags):
                    continue
                
                # Build response
                asset_info = {
                    "id": asset["id"],
                    "name": asset["name"],
                    "type": asset.get("type", "unknown"),
                    "author": asset.get("author", "unknown"),
                    "game_origin": asset.get("game_origin"),
                    "available": asset.get("available", True),
                    "current_borrower": asset.get("current_borrower"),
                    "rarity": asset.get("rarity", "common"),
                    "tags": asset.get("tags", [])
                }
                
                if asset.get("media"):
                    asset_info["media"] = asset["media"]
                
                assets.append(asset_info)
    
    assets.sort(key=lambda x: (x["type"], x["name"]))
    
    return jsonify({
        "total": len(assets),
        "assets": assets,
        "filters": {
            "type": asset_type,
            "game": game,
            "available": available,
            "tags": tags
        }
    })


def checkout():
    """Check out an asset from the library"""
    data = request.json
    asset_id = data.get('asset_id')
    borrower = data.get('borrower')
    game_context = data.get('game_context')
    
    if not asset_id or not borrower:
        return jsonify({"error": "Missing asset_id or borrower"}), 400
    
    asset_path = os.path.join(LIBRARY_PATH, "assets", f"{asset_id}.json")
    if not os.path.exists(asset_path):
        return jsonify({"error": "Asset not found"}), 404
    
    with open(asset_path, 'r') as f:
        asset = json.load(f)
    
    if not asset.get("available", True):
        return jsonify({"error": "Asset already checked out", 
                       "current_borrower": asset.get("current_borrower")}), 400
    
    asset["available"] = False
    asset["current_borrower"] = borrower
    asset.setdefault("checkout_history", []).append({
        "borrower": borrower,
        "checked_out": datetime.utcnow().isoformat(),
        "returned": None,
        "game_context": game_context
    })
    
    with open(asset_path, 'w') as f:
        json.dump(asset, f, indent=2)
    
    run_git(f"add {asset_path}")
    msg = f'Checkout: {asset["name"]} to {borrower}'
    if game_context:
        msg += f' for {game_context}'
    run_git(f'commit -m "{msg}"')
    
    return jsonify({
        "message": "Asset checked out successfully",
        "asset": {
            "id": asset["id"],
            "name": asset["name"],
            "type": asset.get("type"),
            "attributes": asset.get("attributes", {}),
            "media": asset.get("media", {}),
            "checkout_id": len(asset["checkout_history"]) - 1
        }
    })


def return_asset():
    """Return a checked out asset"""
    data = request.json
    asset_id = data.get('asset_id')
    borrower = data.get('borrower')
    condition = data.get('condition', 'good')
    notes = data.get('notes', '')
    
    if not asset_id or not borrower:
        return jsonify({"error": "Missing asset_id or borrower"}), 400
    
    asset_path = os.path.join(LIBRARY_PATH, "assets", f"{asset_id}.json")
    if not os.path.exists(asset_path):
        return jsonify({"error": "Asset not found"}), 404
    
    with open(asset_path, 'r') as f:
        asset = json.load(f)
    
    if asset.get("available", True):
        return jsonify({"error": "Asset is not checked out"}), 400
    
    if asset.get("current_borrower") != borrower:
        return jsonify({
            "error": "Asset is checked out to someone else",
            "actual_borrower": asset.get("current_borrower")
        }), 403
    
    # Find active checkout
    active_checkout = None
    for i, checkout in enumerate(asset.get("checkout_history", [])):
        if checkout["borrower"] == borrower and checkout["returned"] is None:
            active_checkout = i
            break
    
    if active_checkout is None:
        return jsonify({"error": "No active checkout found"}), 404
    
    # Update checkout record
    return_time = datetime.utcnow().isoformat()
    asset["checkout_history"][active_checkout]["returned"] = return_time
    asset["checkout_history"][active_checkout]["return_condition"] = condition
    asset["checkout_history"][active_checkout]["return_notes"] = notes
    
    asset["available"] = True
    asset["current_borrower"] = None
    
    with open(asset_path, 'w') as f:
        json.dump(asset, f, indent=2)
    
    run_git(f"add {asset_path}")
    run_git(f'commit -m "Return: {asset["name"]} from {borrower} (condition: {condition})"')
    
    return jsonify({
        "message": "Asset returned successfully",
        "return_details": {
            "asset_id": asset_id,
            "asset_name": asset["name"],
            "borrower": borrower,
            "condition": condition,
            "notes": notes
        }
    })


def add_asset():
    """Add a new game asset to the library"""
    data = request.json
    
    required = ['name', 'type', 'author', 'game_origin']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400
    
    asset_id = str(uuid.uuid4())
    asset = {
        "id": asset_id,
        "name": data["name"],
        "type": data["type"],
        "author": data["author"],
        "game_origin": data["game_origin"],
        "description": data.get("description", ""),
        "available": True,
        "current_borrower": None,
        "attributes": data.get("attributes", {}),
        "media": data.get("media", {}),
        "cross_game_compatible": data.get("cross_game_compatible", True),
        "rarity": data.get("rarity", "common"),
        "tags": data.get("tags", []),
        "created_at": datetime.utcnow().isoformat(),
        "checkout_history": []
    }
    
    # Auto-populate S3 URLs if media filenames provided
    if "media_files" in data:
        for media_type, filename in data["media_files"].items():
            asset["media"][media_type] = f"{S3_BUCKET}/{filename}"
    
    # Type-specific defaults
    if asset["type"] == "creature":
        defaults = {"power": 50, "defense": 50, "health": 100, "speed": 50}
        asset["attributes"] = {**defaults, **asset["attributes"]}
    elif asset["type"] == "npc":
        defaults = {
            "personality": "neutral",
            "faction": "neutral",
            "stats": {"health": 100, "friendliness": 50}
        }
        asset["attributes"] = {**defaults, **asset["attributes"]}
    
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    asset_path = os.path.join(assets_dir, f"{asset_id}.json")
    with open(asset_path, 'w') as f:
        json.dump(asset, f, indent=2)
    
    run_git(f"add {asset_path}")
    run_git(f'commit -m "Added {asset["type"]}: {asset["name"]} by {asset["author"]}"')
    
    return jsonify({"message": "Asset added successfully", "asset": asset})


# ============= HISTORY HANDLERS =============

def asset_history(asset_id):
    """Get the complete history of an asset"""
    asset_path = os.path.join(LIBRARY_PATH, "assets", f"{asset_id}.json")
    if not os.path.exists(asset_path):
        return jsonify({"error": "Asset not found"}), 404
    
    with open(asset_path, 'r') as f:
        asset = json.load(f)
    
    relative_path = f"assets/{asset_id}.json"
    git_commits = get_file_history(relative_path)
    
    checkout_history = asset.get("checkout_history", [])
    total_checkouts = len(checkout_history)
    active_checkout = any(c.get("returned") is None for c in checkout_history)
    unique_borrowers = len(set(c["borrower"] for c in checkout_history))
    
    return jsonify({
        "asset": {
            "id": asset_id,
            "name": asset["name"],
            "type": asset.get("type"),
            "author": asset.get("author"),
            "current_status": "checked_out" if not asset.get("available", True) else "available"
        },
        "statistics": {
            "total_checkouts": total_checkouts,
            "unique_borrowers": unique_borrowers,
            "currently_checked_out": active_checkout
        },
        "checkout_history": checkout_history,
        "git_history": git_commits
    })


def library_history():
    """Get overall library statistics"""
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    
    stats = {
        "total_assets": 0,
        "checked_out": 0,
        "available": 0,
        "by_type": {},
        "by_game": {},
        "by_rarity": {}
    }
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                with open(os.path.join(assets_dir, filename), 'r') as f:
                    asset = json.load(f)
                    
                    stats["total_assets"] += 1
                    
                    if asset.get("available", True):
                        stats["available"] += 1
                    else:
                        stats["checked_out"] += 1
                    
                    asset_type = asset.get("type", "unknown")
                    stats["by_type"][asset_type] = stats["by_type"].get(asset_type, 0) + 1
                    
                    game = asset.get("game_origin", "unknown")
                    stats["by_game"][game] = stats["by_game"].get(game, 0) + 1
                    
                    rarity = asset.get("rarity", "common")
                    stats["by_rarity"][rarity] = stats["by_rarity"].get(rarity, 0) + 1
    
    try:
        log_output, _ = run_git('log --oneline -5')
        stats["recent_commits"] = [
            line for line in log_output.split('\n') if line
        ]
    except:
        stats["recent_commits"] = []
    
    return jsonify({
        "library_statistics": stats,
        "timestamp": datetime.utcnow().isoformat()
    })


# ============= SEARCH HANDLERS =============

def search():
    """Advanced search with multiple criteria"""
    query = request.args.get('q', '').lower()
    search_type = request.args.get('type')
    game = request.args.get('game')
    author = request.args.get('author')
    rarity = request.args.get('rarity')
    available_only = request.args.get('available_only', 'false').lower() == 'true'
    
    results = []
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                with open(os.path.join(assets_dir, filename), 'r') as f:
                    asset = json.load(f)
                    
                    # Apply filters
                    if search_type and asset.get('type') != search_type:
                        continue
                    if game and asset.get('game_origin') != game:
                        continue
                    if author and asset.get('author') != author:
                        continue
                    if rarity and asset.get('rarity') != rarity:
                        continue
                    if available_only and not asset.get('available', True):
                        continue
                    
                    # Text search
                    if query:
                        searchable = (
                            asset.get('name', '').lower() + ' ' +
                            asset.get('description', '').lower() + ' ' +
                            ' '.join(asset.get('tags', []))
                        )
                        if query not in searchable:
                            continue
                    
                    results.append({
                        "id": asset["id"],
                        "name": asset["name"],
                        "type": asset.get("type"),
                        "author": asset.get("author"),
                        "game_origin": asset.get("game_origin"),
                        "description": asset.get("description", ""),
                        "available": asset.get("available", True),
                        "rarity": asset.get("rarity", "common"),
                        "tags": asset.get("tags", []),
                        "media": asset.get("media", {})
                    })
    
    results.sort(key=lambda x: x["name"])
    
    return jsonify({
        "query": query or None,
        "total_results": len(results),
        "results": results
    })


def popular():
    """Get most popular assets by checkout count"""
    limit = request.args.get('limit', 10, type=int)
    days = request.args.get('days', 30, type=int)
    
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    asset_stats = []
    
    threshold_date = datetime.utcnow() - timedelta(days=days)
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                with open(os.path.join(assets_dir, filename), 'r') as f:
                    asset = json.load(f)
                    
                    recent_checkouts = 0
                    total_checkouts = len(asset.get('checkout_history', []))
                    
                    for checkout in asset.get('checkout_history', []):
                        checkout_date = datetime.fromisoformat(
                            checkout['checked_out'].replace('Z', '+00:00')
                        )
                        if checkout_date >= threshold_date:
                            recent_checkouts += 1
                    
                    if recent_checkouts > 0:
                        asset_stats.append({
                            "asset": {
                                "id": asset["id"],
                                "name": asset["name"],
                                "type": asset.get("type"),
                                "rarity": asset.get("rarity", "common")
                            },
                            "recent_checkouts": recent_checkouts,
                            "total_checkouts": total_checkouts
                        })
    
    asset_stats.sort(key=lambda x: x["recent_checkouts"], reverse=True)
    
    return jsonify({
        "period_days": days,
        "popular_assets": asset_stats[:limit]
    })


# ============= BATCH HANDLERS =============

def batch_import():
    """Import multiple assets at once"""
    data = request.json
    assets = data.get('assets', [])
    
    if not assets:
        return jsonify({"error": "No assets provided"}), 400
    
    imported = []
    errors = []
    
    for asset_data in assets:
        try:
            required = ['name', 'type', 'author', 'game_origin']
            missing = [f for f in required if f not in asset_data]
            if missing:
                raise ValueError(f"Missing required fields: {missing}")
            
            new_asset = {
                "id": str(uuid.uuid4()),
                "name": asset_data["name"],
                "type": asset_data["type"],
                "author": asset_data["author"],
                "game_origin": asset_data["game_origin"],
                "description": asset_data.get("description", ""),
                "available": True,
                "current_borrower": None,
                "attributes": asset_data.get("attributes", {}),
                "media": asset_data.get("media", {}),
                "cross_game_compatible": asset_data.get("cross_game_compatible", True),
                "rarity": asset_data.get("rarity", "common"),
                "tags": asset_data.get("tags", []),
                "created_at": datetime.utcnow().isoformat(),
                "checkout_history": []
            }
            
            assets_dir = os.path.join(LIBRARY_PATH, "assets")
            os.makedirs(assets_dir, exist_ok=True)
            
            asset_path = os.path.join(assets_dir, f"{new_asset['id']}.json")
            with open(asset_path, 'w') as f:
                json.dump(new_asset, f, indent=2)
            
            imported.append({
                "id": new_asset["id"],
                "name": new_asset["name"]
            })
            
        except Exception as e:
            errors.append({
                "asset_name": asset_data.get("name", "unknown"),
                "error": str(e)
            })
    
    if imported:
        run_git("add assets/")
        run_git(f'commit -m "Batch import: {len(imported)} assets added"')
    
    return jsonify({
        "success": len(imported),
        "failed": len(errors),
        "imported": imported,
        "errors": errors
    })


def batch_checkout():
    """Check out multiple assets at once"""
    data = request.json
    asset_ids = data.get('asset_ids', [])
    borrower = data.get('borrower')
    game_context = data.get('game_context')
    
    if not asset_ids or not borrower:
        return jsonify({"error": "Missing asset_ids or borrower"}), 400
    
    checked_out = []
    errors = []
    
    for asset_id in asset_ids:
        try:
            asset_path = os.path.join(LIBRARY_PATH, "assets", f"{asset_id}.json")
            if not os.path.exists(asset_path):
                raise ValueError("Asset not found")
            
            with open(asset_path, 'r') as f:
                asset = json.load(f)
            
            if not asset.get("available", True):
                raise ValueError(f"Already checked out to {asset.get('current_borrower')}")
            
            asset["available"] = False
            asset["current_borrower"] = borrower
            asset.setdefault("checkout_history", []).append({
                "borrower": borrower,
                "checked_out": datetime.utcnow().isoformat(),
                "returned": None,
                "game_context": game_context
            })
            
            with open(asset_path, 'w') as f:
                json.dump(asset, f, indent=2)
            
            checked_out.append({
                "id": asset_id,
                "name": asset["name"]
            })
            
        except Exception as e:
            errors.append({
                "asset_id": asset_id,
                "error": str(e)
            })
    
    if checked_out:
        run_git("add assets/")
        run_git(f'commit -m "Batch checkout: {len(checked_out)} assets to {borrower}"')
    
    return jsonify({
        "success": len(checked_out),
        "failed": len(errors),
        "checked_out": checked_out,
        "errors": errors
    })


def export_collection():
    """Export a collection of assets based on filters"""
    asset_type = request.args.get('type')
    game = request.args.get('game')
    rarity = request.args.get('rarity')
    author = request.args.get('author')
    
    assets = []
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                with open(os.path.join(assets_dir, filename), 'r') as f:
                    asset = json.load(f)
                    
                    if asset_type and asset.get('type') != asset_type:
                        continue
                    if game and asset.get('game_origin') != game:
                        continue
                    if rarity and asset.get('rarity') != rarity:
                        continue
                    if author and asset.get('author') != author:
                        continue
                    
                    export_asset = asset.copy()
                    export_asset.pop('checkout_history', None)
                    export_asset.pop('current_borrower', None)
                    export_asset['available'] = True
                    
                    assets.append(export_asset)
    
    return jsonify({
        "export_timestamp": datetime.utcnow().isoformat(),
        "asset_count": len(assets),
        "assets": assets
    })


# ============= UTILITY HANDLERS =============

def generate_test_data():
    """Generate sample assets for testing"""
    CREATURE_NAMES = ["Fire Drake", "Ice Wyrm", "Thunder Beast", "Shadow Stalker"]
    ITEM_NAMES = ["Health Potion", "Mana Crystal", "Power Elixir", "Shield Charm"]
    ELEMENTS = ["fire", "ice", "thunder", "earth"]
    RARITIES = ["common", "uncommon", "rare", "epic", "legendary"]
    
    count = 10
    generated = []
    
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    for i in range(count):
        if i % 2 == 0:
            # Create creature
            asset = {
                "id": str(uuid.uuid4()),
                "name": f"{random.choice(CREATURE_NAMES)} #{i+1}",
                "type": "creature",
                "author": f"test_author_{random.randint(1, 3)}",
                "game_origin": random.choice(["battlemonsters3000", "survival_game"]),
                "description": "Auto-generated test creature",
                "available": True,
                "current_borrower": None,
                "attributes": {
                    "power": random.randint(30, 100),
                    "defense": random.randint(30, 100),
                    "health": random.randint(50, 250),
                    "element": random.choice(ELEMENTS)
                },
                "cross_game_compatible": random.choice([True, False]),
                "rarity": random.choice(RARITIES),
                "tags": ["test", "creature"],
                "created_at": datetime.utcnow().isoformat(),
                "checkout_history": []
            }
        else:
            # Create item
            asset = {
                "id": str(uuid.uuid4()),
                "name": f"{random.choice(ITEM_NAMES)} #{i+1}",
                "type": "item",
                "author": f"test_author_{random.randint(1, 3)}",
                "game_origin": random.choice(["battlemonsters3000", "survival_game"]),
                "description": "Auto-generated test item",
                "available": True,
                "current_borrower": None,
                "attributes": {
                    "effects": [{"type": "heal", "value": random.randint(10, 50)}],
                    "consumable": random.choice([True, False])
                },
                "cross_game_compatible": True,
                "rarity": random.choice(RARITIES),
                "tags": ["test", "item"],
                "created_at": datetime.utcnow().isoformat(),
                "checkout_history": []
            }
        
        asset_path = os.path.join(assets_dir, f"{asset['id']}.json")
        with open(asset_path, 'w') as f:
            json.dump(asset, f, indent=2)
        
        generated.append({
            "id": asset["id"],
            "name": asset["name"],
            "type": asset["type"]
        })
    
    run_git("add assets/")
    run_git(f'commit -m "Generated {count} test assets"')
    
    return jsonify({
        "message": f"Generated {count} test assets",
        "assets": generated
    })


def cleanup():
    """Clean up test data"""
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    removed = []
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(assets_dir, filename)
                with open(filepath, 'r') as f:
                    asset = json.load(f)
                
                if 'test' in asset.get('author', '').lower() or 'test' in asset.get('tags', []):
                    os.remove(filepath)
                    removed.append({
                        "id": asset["id"],
                        "name": asset["name"]
                    })
    
    if removed:
        run_git("add -A")
        run_git(f'commit -m "Cleaned up {len(removed)} test assets"')
    
    return jsonify({
        "message": f"Removed {len(removed)} test assets",
        "removed": removed
    })


def git_status():
    """Get current git status"""
    try:
        status, _ = run_git("status --porcelain")
        branch, _ = run_git("rev-parse --abbrev-ref HEAD")
        commit, _ = run_git("rev-parse HEAD")
        log, _ = run_git("log --oneline -5")
        
        return jsonify({
            "branch": branch,
            "current_commit": commit[:8],
            "uncommitted_changes": len(status.strip().split('\n')) if status.strip() else 0,
            "recent_commits": [line for line in log.split('\n') if line]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============= REGISTRATION =============

def register(app):
    """Register all endpoints with the Flask app"""
    # Core endpoints
    app.route('/ping', methods=['GET'])(ping)
    app.route('/browse', methods=['GET'])(browse)
    app.route('/checkout', methods=['POST'])(checkout)
    app.route('/return', methods=['POST'])(return_asset)
    app.route('/add_asset', methods=['POST'])(add_asset)
    
    # History endpoints
    app.route('/history/<asset_id>', methods=['GET'])(asset_history)
    app.route('/history', methods=['GET'])(library_history)
    
    # Search endpoints
    app.route('/search', methods=['GET'])(search)
    app.route('/popular', methods=['GET'])(popular)
    
    # Batch endpoints
    app.route('/batch/import', methods=['POST'])(batch_import)
    app.route('/batch/checkout', methods=['POST'])(batch_checkout)
    app.route('/export', methods=['GET'])(export_collection)
    
    # Utility endpoints
    app.route('/utils/generate', methods=['POST'])(generate_test_data)
    app.route('/utils/cleanup', methods=['POST'])(cleanup)
    app.route('/utils/git-status', methods=['GET'])(git_status)