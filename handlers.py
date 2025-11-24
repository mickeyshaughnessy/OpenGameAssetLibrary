"""
Simple Asset Library API Handlers - S3 Version
Streamlined handlers for basic library operations using S3 storage
Supports multiple simultaneous checkouts per asset
"""

from flask import jsonify, request
import json
import uuid
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging
from database import JSONDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Database
# We use the standard bucket and prefix
db = JSONDatabase(bucket="mithrilmedia", prefix="OpenGameAssetLibrary")

# S3 Configuration for direct access where needed (like checkouts)
S3_BUCKET = db.bucket
S3_CHECKOUTS_PREFIX = f"{db.prefix}/checkouts"

def ping():
    """Health check endpoint"""
    s3_status = "connected" if db.s3_client else "no_credentials"
    return jsonify({
        "status": "alive", 
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.2-balltree",
        "s3_status": s3_status,
        "bucket": S3_BUCKET
    })

def browse():
    """List all assets in the library with optional filtering"""
    # Note: For a large DB, we should implement pagination in JSONDatabase
    # For now, we can iterate the tree or S3. 
    # Since JSONDatabase focuses on KNN, we'll rely on its internal S3 client for listing.
    
    try:
        assets = []
        # Use the DB's list capability (needs to be added or we use s3 directly)
        # Let's use the s3_client from db
        paginator = db.s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=db.bucket, Prefix=db.assets_prefix)
        
        asset_type = request.args.get('type')
        author = request.args.get('author')
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith('.json'):
                        try:
                            resp = db.s3_client.get_object(Bucket=db.bucket, Key=key)
                            asset = json.loads(resp['Body'].read().decode('utf-8'))
                            
                            if asset_type and asset.get('type') != asset_type:
                                continue
                            if author and asset.get('author') != author:
                                continue
                                
                            assets.append(asset)
                        except:
                            continue
                            
        return jsonify({
            "total": len(assets), 
            "assets": assets
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def search():
    """
    Search for assets.
    Supports:
    1. ?q=text -> Standard text search (legacy/simple)
    2. JSON body -> Intelligent Similarity Search (Ball Tree)
    """
    
    # Check if JSON query is provided for Ball Tree search
    if request.is_json:
        query_obj = request.json
        k = int(request.args.get('k', 5))
        
        results = db.search(query_obj, k=k)
        
        formatted_results = []
        for dist, asset in results:
            formatted_results.append({
                "similarity_score": 1.0 - dist, # Rough conversion
                "distance": dist,
                "asset": asset
            })
            
        return jsonify({
            "method": "ball_tree_similarity",
            "results": formatted_results
        })
    
    # Fallback to basic text search
    query = request.args.get('q', '').lower()
    # ... (reimplement text search or reuse existing logic)
    # For brevity, let's reuse the browse logic with text filter
    
    results = []
    paginator = db.s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=db.bucket, Prefix=db.assets_prefix)
    
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                if not key.endswith('.json'): continue
                
                try:
                    resp = db.s3_client.get_object(Bucket=db.bucket, Key=key)
                    asset = json.loads(resp['Body'].read().decode('utf-8'))
                    
                    if query:
                        searchable = f"{asset.get('name', '')} {asset.get('description', '')} {' '.join(asset.get('tags', []))}".lower()
                        if query not in searchable:
                            continue
                    results.append(asset)
                except:
                    continue
                    
    return jsonify({
        "method": "text_search",
        "query": query,
        "total_results": len(results), 
        "results": results
    })

def add_asset():
    """Add a new asset to the library"""
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    try:
        asset_id = db.insert(data)
        return jsonify({
            "message": "Asset added successfully", 
            "id": asset_id
        })
    except Exception as e:
        return jsonify({"error": f"Failed to add asset: {str(e)}"}), 500

def add_assets_batch():
    """Add multiple assets to the library"""
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"error": "No JSON list provided"}), 400
    
    try:
        asset_ids = db.insert_many(data)
        return jsonify({
            "message": f"Successfully added {len(asset_ids)} assets", 
            "ids": asset_ids
        })
    except Exception as e:
        return jsonify({"error": f"Failed to add assets: {str(e)}"}), 500

# ... keep checkout and stats as they are mostly independent ...
def checkout():
    """Check out an asset from the library (non-exclusive - multiple users can checkout)"""
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    asset_id = data.get('asset_id')
    user = data.get('borrower') or data.get('user')
    
    if not asset_id or not user:
        return jsonify({"error": "Missing asset_id or user/borrower"}), 400
    
    try:
        # Use direct S3 for retrieving asset to check existence
        # Or assume db.insert saves it where we expect
        key = f"{db.assets_prefix}/{asset_id}.json"
        resp = db.s3_client.get_object(Bucket=db.bucket, Key=key)
        asset = json.loads(resp['Body'].read().decode('utf-8'))
        
        # Create checkout record
        checkout_id = str(uuid.uuid4())
        checkout_record = {
            "id": checkout_id,
            "asset_id": asset_id,
            "user": user,
            "checkout_date": datetime.utcnow().isoformat(),
            "asset_name": asset.get("name"),
            "asset_type": asset.get("type"),
            # "s3_url": asset.get("s3_url") # Optional if we don't store it in DB explicitly
        }
        
        checkout_key = f"{S3_CHECKOUTS_PREFIX}/{checkout_id}.json"
        db.s3_client.put_object(
            Bucket=db.bucket,
            Key=checkout_key,
            Body=json.dumps(checkout_record, indent=2),
            ContentType='application/json'
        )

        return jsonify({
            "message": "Asset checked out successfully", 
            "checkout": checkout_record
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to checkout asset: {str(e)}"}), 500

def get_asset(asset_id):
    """Get detailed information about a specific asset"""
    try:
        key = f"{db.assets_prefix}/{asset_id}.json"
        resp = db.s3_client.get_object(Bucket=db.bucket, Key=key)
        asset = json.loads(resp['Body'].read().decode('utf-8'))
        return jsonify({"asset": asset})
    except ClientError:
         return jsonify({"error": "Asset not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to get asset: {str(e)}"}), 500

def library_stats():
    """Get overall library statistics"""
    # Simplified stats
    return jsonify({"status": "Not fully implemented in new DB version yet"})

def register(app):
    """Register all routes with the Flask app"""
    app.route('/ping', methods=['GET'])(ping)
    app.route('/browse', methods=['GET'])(browse)
    app.route('/search', methods=['GET', 'POST'])(search) # Added POST for JSON search
    app.route('/add', methods=['POST'])(add_asset)
    app.route('/add_batch', methods=['POST'])(add_assets_batch)
    app.route('/checkout', methods=['POST'])(checkout)
    app.route('/asset/<asset_id>', methods=['GET'])(get_asset)
    app.route('/stats', methods=['GET'])(library_stats)