"""
Simple Asset Library API Handlers
Streamlined handlers for basic library operations without git or complex features
"""

from flask import jsonify, request
import os
import json
import uuid
from datetime import datetime

LIBRARY_PATH = "./library-data"
S3_BASE_URL = "https://asset-library.s3.amazonaws.com/assets"

def ping():
    """Health check endpoint"""
    return jsonify({
        "status": "alive", 
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0-simple"
    })

def browse():
    """List all assets in the library with optional filtering"""
    assets = []
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    
    # Simple filters
    asset_type = request.args.get('type')
    available = request.args.get('available')
    author = request.args.get('author')
    
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
                    if author and asset.get('author') != author:
                        continue
                    if available is not None:
                        if (available.lower() == 'true') != asset.get('available', True):
                            continue
                    
                    # Return simplified asset info
                    assets.append({
                        "id": asset["id"],
                        "name": asset["name"],
                        "type": asset.get("type"),
                        "author": asset.get("author"),
                        "available": asset.get("available", True),
                        "borrower": asset.get("borrower"),
                        "rarity": asset.get("rarity", "common"),
                        "tags": asset.get("tags", []),
                        "checkout_date": asset.get("checkout_date")
                    })
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error reading asset file {filename}: {e}")
                continue
    
    return jsonify({
        "total": len(assets), 
        "assets": assets
    })

def search():
    """Search for assets with text query and filters"""
    query = request.args.get('q', '').lower()
    asset_type = request.args.get('type')
    author = request.args.get('author')
    rarity = request.args.get('rarity')
    
    results = []
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(assets_dir, filename), 'r') as f:
                        asset = json.load(f)
                        
                        # Apply filters
                        if asset_type and asset.get('type') != asset_type:
                            continue
                        if author and asset.get('author') != author:
                            continue
                        if rarity and asset.get('rarity') != rarity:
                            continue
                        
                        # Text search in name, description, and tags
                        if query:
                            searchable = f"{asset.get('name', '')} {asset.get('description', '')} {' '.join(asset.get('tags', []))}".lower()
                            if query not in searchable:
                                continue
                        
                        results.append(asset)
                except (json.JSONDecodeError, KeyError):
                    continue
    
    return jsonify({
        "query": request.args.get('q', ''),
        "total_results": len(results), 
        "results": results
    })

def add_asset():
    """Add a new asset to the library"""
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    # Validate required fields
    required_fields = ['name', 'type', 'author']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400
    
    try:
        asset_id = str(uuid.uuid4())
        
        # Generate unique S3 URL for this asset
        file_extension = data.get('file_extension', 'zip')
        s3_url = f"{S3_BASE_URL}/{asset_id}/{data['name'].lower().replace(' ', '_')}.{file_extension}"
        
        asset = {
            "id": asset_id,
            "name": data["name"],
            "type": data["type"],
            "author": data["author"],
            "description": data.get("description", ""),
            "available": True,
            "borrower": None,
            "checkout_date": None,
            "attributes": data.get("attributes", {}),
            "s3_url": s3_url,
            "rarity": data.get("rarity", "common"),
            "tags": data.get("tags", []),
            "created_at": datetime.utcnow().isoformat()
        }
        
        assets_dir = os.path.join(LIBRARY_PATH, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        asset_path = os.path.join(assets_dir, f"{asset_id}.json")
        with open(asset_path, 'w') as f:
            json.dump(asset, f, indent=2)
        
        return jsonify({
            "message": "Asset added successfully", 
            "asset": asset
        })
    except Exception as e:
        return jsonify({"error": f"Failed to add asset: {str(e)}"}), 500

def checkout():
    """Check out an asset from the library (permanent checkout)"""
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
            return jsonify({
                "error": f"Asset already checked out to {asset.get('borrower')}"
            }), 400
        
        # Update asset - permanent checkout
        asset["available"] = False
        asset["borrower"] = borrower
        asset["checkout_date"] = datetime.utcnow().isoformat()
        
        with open(asset_path, 'w') as f:
            json.dump(asset, f, indent=2)
        
        return jsonify({
            "message": "Asset checked out successfully", 
            "asset": {
                "id": asset["id"],
                "name": asset["name"],
                "type": asset.get("type"),
                "s3_url": asset.get("s3_url"),
                "borrower": borrower,
                "checkout_date": asset["checkout_date"]
            }
        })
    except Exception as e:
        return jsonify({"error": f"Failed to checkout asset: {str(e)}"}), 500

def get_asset(asset_id):
    """Get detailed information about a specific asset"""
    asset_path = os.path.join(LIBRARY_PATH, "assets", f"{asset_id}.json")
    if not os.path.exists(asset_path):
        return jsonify({"error": "Asset not found"}), 404
    
    try:
        with open(asset_path, 'r') as f:
            asset = json.load(f)
        
        return jsonify({"asset": asset})
    except Exception as e:
        return jsonify({"error": f"Failed to get asset: {str(e)}"}), 500

def library_stats():
    """Get overall library statistics"""
    assets_dir = os.path.join(LIBRARY_PATH, "assets")
    stats = {
        "total_assets": 0, 
        "available": 0,
        "checked_out": 0, 
        "by_type": {}, 
        "by_rarity": {},
        "by_author": {}
    }
    
    if os.path.exists(assets_dir):
        for filename in os.listdir(assets_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(assets_dir, filename), 'r') as f:
                        asset = json.load(f)
                        stats["total_assets"] += 1
                        
                        if asset.get("available", True):
                            stats["available"] += 1
                        else:
                            stats["checked_out"] += 1
                        
                        # Count by type
                        asset_type = asset.get("type", "unknown")
                        stats["by_type"][asset_type] = stats["by_type"].get(asset_type, 0) + 1
                        
                        # Count by rarity
                        rarity = asset.get("rarity", "common")
                        stats["by_rarity"][rarity] = stats["by_rarity"].get(rarity, 0) + 1
                        
                        # Count by author
                        author = asset.get("author", "unknown")
                        stats["by_author"][author] = stats["by_author"].get(author, 0) + 1
                        
                except (json.JSONDecodeError, KeyError):
                    continue
    
    return jsonify({"library_stats": stats})

def register(app):
    """Register all routes with the Flask app"""
    app.route('/ping', methods=['GET'])(ping)
    app.route('/browse', methods=['GET'])(browse)
    app.route('/search', methods=['GET'])(search)
    app.route('/add', methods=['POST'])(add_asset)
    app.route('/checkout', methods=['POST'])(checkout)
    app.route('/asset/<asset_id>', methods=['GET'])(get_asset)
    app.route('/stats', methods=['GET'])(library_stats)