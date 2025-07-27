"""
OpenGameAssetLibrary API Handlers
Contains all the route handlers for the asset library API
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

def ping():
    """Health check endpoint"""
    return jsonify({"status": "alive", "timestamp": datetime.utcnow().isoformat()})

def browse():
    """List all assets in the library with optional filtering"""
    assets = []
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    
    # Filters
    asset_type = request.args.get('type')
    game = request.args.get('game')
    available = request.args.get('available')
    tags = request.args.getlist('tag')
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if not filename.endswith('.json'):
                continue
                
            try:
                with open(os.path.join(assets_dir, filename), 'r') as f:
                    asset = json.load(f)
                    
                    # Apply filters
                    if asset_type and asset.get('type') != asset_type:
                        continue
                    if game and asset.get('game_origin') != game:
                        continue
                    if available is not None:
                        if (available.lower() == 'true') != asset.get('available', True):
                            continue
                    if tags and not any(tag in asset.get('tags', []) for tag in tags):
                        continue
                    
                    assets.append({
                        "id": asset["id"],
                        "name": asset["name"],
                        "type": asset.get("type"),
                        "author": asset.get("author"),
                        "game_origin": asset.get("game_origin"),
                        "available": asset.get("available", True),
                        "current_borrower": asset.get("current_borrower"),
                        "rarity": asset.get("rarity", "common"),
                        "tags": asset.get("tags", []),
                        "media": asset.get("media", {})
                    })
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error reading asset file {filename}: {e}")
                continue
    
    return jsonify({"total": len(assets), "assets": assets})

def checkout():
    """Check out an asset from the library"""
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    asset_id = data.get('asset_id')
    borrower = data.get('borrower')
    
    if not asset_id or not borrower:
        return jsonify({"error": "Missing asset_id or borrower"}), 400
    
    asset_path = os.path.join(LIBRARY_PATH, "assets", f"{asset_id}.json")
    if not os.path.exists(asset_path):
        return jsonify({"error": "Asset not found"}), 404
    
    try:
        with open(asset_path, 'r') as f:
            asset = json.load(f)
        
        if not asset.get("available", True):
            return jsonify({"error": "Already checked out"}), 400
        
        # Update asset
        asset["available"] = False
        asset["current_borrower"] = borrower
        asset.setdefault("checkout_history", []).append({
            "borrower": borrower,
            "checked_out": datetime.utcnow().isoformat(),
            "returned": None,
            "game_context": data.get('game_context')
        })
        
        with open(asset_path, 'w') as f:
            json.dump(asset, f, indent=2)
        
        run_git(f"add {asset_path}")
        run_git(f'commit -m "Checkout: {asset["name"]} to {borrower}"')
        
        return jsonify({
            "message": "Checked out successfully", 
            "asset": {
                "id": asset["id"],
                "name": asset["name"],
                "type": asset.get("type"),
                "media": asset.get("media", {})
            }
        })
    except Exception as e:
        return jsonify({"error": f"Failed to checkout asset: {str(e)}"}), 500

def return_asset():
    """Return a checked out asset"""
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    asset_id = data.get('asset_id')
    borrower = data.get('borrower')
    
    if not asset_id or not borrower:
        return jsonify({"error": "Missing asset_id or borrower"}), 400
    
    asset_path = os.path.join(LIBRARY_PATH, "assets", f"{asset_id}.json")
    if not os.path.exists(asset_path):
        return jsonify({"error": "Asset not found"}), 404
    
    try:
        with open(asset_path, 'r') as f:
            asset = json.load(f)
        
        if asset.get("current_borrower") != borrower:
            return jsonify({"error": "Asset not checked out to this borrower"}), 403
        
        # Update checkout history
        for checkout in reversed(asset.get("checkout_history", [])):
            if checkout["borrower"] == borrower and checkout["returned"] is None:
                checkout["returned"] = datetime.utcnow().isoformat()
                checkout["return_condition"] = data.get('condition', 'good')
                break
        
        asset["available"] = True
        asset["current_borrower"] = None
        
        with open(asset_path, 'w') as f:
            json.dump(asset, f, indent=2)
        
        run_git(f"add {asset_path}")
        run_git(f'commit -m "Return: {asset["name"]} from {borrower}"')
        
        return jsonify({"message": "Asset returned successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to return asset: {str(e)}"}), 500

def add_asset():
    """Add a new asset to the library"""
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    # Validate required fields
    required_fields = ['name', 'type', 'author', 'game_origin']
    if not all(k in data for k in required_fields):
        return jsonify({"error": f"Missing required fields: {required_fields}"}), 400
    
    try:
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
        
        assets_dir = os.path.join(LIBRARY_PATH, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        asset_path = os.path.join(assets_dir, f"{asset_id}.json")
        with open(asset_path, 'w') as f:
            json.dump(asset, f, indent=2)
        
        run_git(f"add {asset_path}")
        run_git(f'commit -m "Added {asset["type"]}: {asset["name"]}"')
        
        return jsonify({"message": "Asset added successfully", "asset": asset})
    except Exception as e:
        return jsonify({"error": f"Failed to add asset: {str(e)}"}), 500

def asset_history(asset_id):
    """Get the history for a specific asset"""
    asset_path = os.path.join(LIBRARY_PATH, "assets", f"{asset_id}.json")
    if not os.path.exists(asset_path):
        return jsonify({"error": "Asset not found"}), 404
    
    try:
        with open(asset_path, 'r') as f:
            asset = json.load(f)
        
        return jsonify({
            "asset": {
                "id": asset_id,
                "name": asset["name"],
                "type": asset.get("type"),
                "status": "available" if asset.get("available", True) else "checked_out"
            },
            "checkout_history": asset.get("checkout_history", []),
            "git_history": get_file_history(f"assets/{asset_id}.json")
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get asset history: {str(e)}"}), 500

def library_history():
    """Get overall library statistics"""
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    stats = {"total_assets": 0, "checked_out": 0, "by_type": {}, "by_rarity": {}}
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(assets_dir, filename), 'r') as f:
                        asset = json.load(f)
                        stats["total_assets"] += 1
                        if not asset.get("available", True):
                            stats["checked_out"] += 1
                        
                        asset_type = asset.get("type", "unknown")
                        stats["by_type"][asset_type] = stats["by_type"].get(asset_type, 0) + 1
                        
                        rarity = asset.get("rarity", "common")
                        stats["by_rarity"][rarity] = stats["by_rarity"].get(rarity, 0) + 1
                except (json.JSONDecodeError, KeyError):
                    continue
    
    return jsonify({"library_statistics": stats})

def search():
    """Search for assets with text query and filters"""
    query = request.args.get('q', '').lower()
    filters = {k: request.args.get(k) for k in ['type', 'game', 'author', 'rarity'] if request.args.get(k)}
    
    results = []
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(assets_dir, filename), 'r') as f:
                        asset = json.load(f)
                        
                        # Apply filters
                        skip = False
                        for key, value in filters.items():
                            if asset.get(key) != value:
                                skip = True
                                break
                        if skip:
                            continue
                        
                        # Text search
                        if query:
                            searchable = f"{asset.get('name', '')} {asset.get('description', '')} {' '.join(asset.get('tags', []))}".lower()
                            if query not in searchable:
                                continue
                        
                        results.append(asset)
                except (json.JSONDecodeError, KeyError):
                    continue
    
    return jsonify({"total_results": len(results), "results": results})

def batch_import():
    """Import multiple assets at once"""
    data = request.json
    if not data or 'assets' not in data:
        return jsonify({"error": "No assets data provided"}), 400
    
    imported = []
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    for asset_data in data.get('assets', []):
        try:
            if not all(k in asset_data for k in ['name', 'type', 'author', 'game_origin']):
                continue
                
            asset = {
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
                "tags": asset_data.get("tags", []),
                "rarity": asset_data.get("rarity", "common"),
                "created_at": datetime.utcnow().isoformat(),
                "checkout_history": []
            }
            
            asset_path = os.path.join(assets_dir, f"{asset['id']}.json")
            with open(asset_path, 'w') as f:
                json.dump(asset, f, indent=2)
            
            imported.append({"id": asset["id"], "name": asset["name"]})
        except Exception as e:
            print(f"Error importing asset: {e}")
            continue
    
    if imported:
        run_git("add assets/")
        run_git(f'commit -m "Batch import: {len(imported)} assets"')
    
    return jsonify({"imported": imported, "count": len(imported)})

def export_collection():
    """Export assets matching filters"""
    filters = {k: request.args.get(k) for k in ['type', 'game', 'rarity', 'author'] if request.args.get(k)}
    assets = []
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(assets_dir, filename), 'r') as f:
                        asset = json.load(f)
                        
                        # Apply filters
                        skip = False
                        for key, value in filters.items():
                            if asset.get(key) != value:
                                skip = True
                                break
                        
                        if not skip:
                            # Remove sensitive checkout info for export
                            export_asset = asset.copy()
                            export_asset.pop('checkout_history', None)
                            export_asset.pop('current_borrower', None)
                            assets.append(export_asset)
                except (json.JSONDecodeError, KeyError):
                    continue
    
    return jsonify({"assets": assets, "total": len(assets)})

def generate_test_data():
    """Generate test assets for development"""
    count = int(request.args.get('count', 10))
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    asset_types = ["creature", "item", "npc", "spell", "environment"]
    rarities = ["common", "uncommon", "rare", "epic", "legendary"]
    
    generated = []
    for i in range(count):
        asset = {
            "id": str(uuid.uuid4()),
            "name": f"Test Asset {i+1}",
            "type": random.choice(asset_types),
            "author": "test_generator",
            "game_origin": "test_game",
            "description": f"Auto-generated test asset #{i+1}",
            "available": True,
            "current_borrower": None,
            "attributes": {"power": random.randint(10, 100)},
            "tags": ["test", "generated"],
            "rarity": random.choice(rarities),
            "created_at": datetime.utcnow().isoformat(),
            "checkout_history": []
        }
        
        asset_path = os.path.join(assets_dir, f"{asset['id']}.json")
        with open(asset_path, 'w') as f:
            json.dump(asset, f, indent=2)
        
        generated.append({"id": asset["id"], "name": asset["name"]})
    
    if generated:
        run_git("add assets/")
        run_git(f'commit -m "Generated {count} test assets"')
    
    return jsonify({"message": f"Generated {count} assets", "assets": generated})

def cleanup():
    """Remove test assets"""
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    removed = 0
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(assets_dir, filename)
                    with open(filepath, 'r') as f:
                        asset = json.load(f)
                    
                    if 'test' in asset.get('tags', []) or 'test' in asset.get('author', ''):
                        os.remove(filepath)
                        removed += 1
                except (json.JSONDecodeError, KeyError):
                    continue
    
    if removed:
        run_git("add -A")
        run_git(f'commit -m "Removed {removed} test assets"')
    
    return jsonify({"removed": removed, "message": f"Cleaned up {removed} test assets"})

def popular():
    """Get popular assets (simplified implementation)"""
    limit = request.args.get('limit', 10, type=int)
    # For now, just return empty - could implement based on checkout frequency
    return jsonify({"popular_assets": [], "limit": limit})

def batch_checkout():
    """Check out multiple assets at once"""
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    asset_ids = data.get('asset_ids', [])
    borrower = data.get('borrower')
    
    if not borrower:
        return jsonify({"error": "Missing borrower"}), 400
    
    checked_out = []
    errors = []
    
    for asset_id in asset_ids:
        try:
            asset_path = os.path.join(LIBRARY_PATH, "assets", f"{asset_id}.json")
            if os.path.exists(asset_path):
                with open(asset_path, 'r') as f:
                    asset = json.load(f)
                
                if asset.get("available", True):
                    asset["available"] = False
                    asset["current_borrower"] = borrower
                    asset.setdefault("checkout_history", []).append({
                        "borrower": borrower,
                        "checked_out": datetime.utcnow().isoformat(),
                        "returned": None
                    })
                    
                    with open(asset_path, 'w') as f:
                        json.dump(asset, f, indent=2)
                    
                    checked_out.append({"id": asset_id, "name": asset["name"]})
                else:
                    errors.append({"id": asset_id, "error": "Already checked out"})
            else:
                errors.append({"id": asset_id, "error": "Asset not found"})
        except Exception as e:
            errors.append({"id": asset_id, "error": str(e)})
    
    if checked_out:
        run_git("add assets/")
        run_git(f'commit -m "Batch checkout: {len(checked_out)} assets to {borrower}"')
    
    return jsonify({"checked_out": checked_out, "errors": errors, "success_count": len(checked_out)})

def git_status():
    """Get git repository status"""
    try:
        from utils.git_wrapper import get_repo_status
        status = get_repo_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": f"Git error: {str(e)}"}), 500

def register(app):
    """Register all routes with the Flask app"""
    app.route('/ping', methods=['GET'])(ping)
    app.route('/browse', methods=['GET'])(browse)
    app.route('/checkout', methods=['POST'])(checkout)
    app.route('/return', methods=['POST'])(return_asset)
    app.route('/add_asset', methods=['POST'])(add_asset)
    app.route('/history/<asset_id>', methods=['GET'])(asset_history)
    app.route('/history', methods=['GET'])(library_history)
    app.route('/search', methods=['GET'])(search)
    app.route('/popular', methods=['GET'])(popular)
    app.route('/batch/import', methods=['POST'])(batch_import)
    app.route('/batch/checkout', methods=['POST'])(batch_checkout)
    app.route('/export', methods=['GET'])(export_collection)
    app.route('/utils/generate', methods=['POST'])(generate_test_data)
    app.route('/utils/cleanup', methods=['POST'])(cleanup)
    app.route('/utils/git-status', methods=['GET'])(git_status)