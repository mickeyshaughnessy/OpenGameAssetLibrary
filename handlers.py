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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# S3 Configuration
S3_BUCKET = "mithrilmedia"
S3_PREFIX = "OpenGameAssetLibrary"
S3_ASSETS_PREFIX = f"{S3_PREFIX}/assets"
S3_CHECKOUTS_PREFIX = f"{S3_PREFIX}/checkouts"
S3_BASE_URL = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/{S3_PREFIX}"

# Initialize S3 client
try:
    s3_client = boto3.client('s3', region_name='us-east-1')
except NoCredentialsError:
    logger.error("AWS credentials not found. Please configure your AWS credentials.")
    s3_client = None

def ping():
    """Health check endpoint"""
    s3_status = "connected" if s3_client else "no_credentials"
    return jsonify({
        "status": "alive", 
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.1-s3-multi-checkout",
        "s3_status": s3_status,
        "bucket": S3_BUCKET
    })

def _list_asset_keys():
    """Helper function to list all asset JSON files in S3"""
    if not s3_client:
        return []
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_ASSETS_PREFIX}/",
            Delimiter='/'
        )
        
        keys = []
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.json'):
                    keys.append(key)
        
        return keys
    except ClientError as e:
        logger.error(f"Error listing S3 objects: {e}")
        return []

def _get_asset_from_s3(asset_id):
    """Helper function to get asset data from S3"""
    if not s3_client:
        return None
    
    try:
        key = f"{S3_ASSETS_PREFIX}/{asset_id}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        asset_data = json.loads(response['Body'].read().decode('utf-8'))
        return asset_data
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        logger.error(f"Error getting asset from S3: {e}")
        return None

def _save_asset_to_s3(asset_id, asset_data):
    """Helper function to save asset data to S3"""
    if not s3_client:
        return False
    
    try:
        key = f"{S3_ASSETS_PREFIX}/{asset_id}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(asset_data, indent=2),
            ContentType='application/json'
        )
        return True
    except ClientError as e:
        logger.error(f"Error saving asset to S3: {e}")
        return False

def _save_checkout_record(checkout_id, checkout_data):
    """Helper function to save checkout record to S3"""
    if not s3_client:
        return False
    
    try:
        key = f"{S3_CHECKOUTS_PREFIX}/{checkout_id}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(checkout_data, indent=2),
            ContentType='application/json'
        )
        return True
    except ClientError as e:
        logger.error(f"Error saving checkout record to S3: {e}")
        return False

def _count_asset_checkouts(asset_id):
    """Count how many times an asset has been checked out"""
    if not s3_client:
        return 0
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_CHECKOUTS_PREFIX}/",
            Delimiter='/'
        )
        
        count = 0
        if 'Contents' in response:
            for obj in response['Contents']:
                try:
                    checkout_response = s3_client.get_object(Bucket=S3_BUCKET, Key=obj['Key'])
                    checkout_data = json.loads(checkout_response['Body'].read().decode('utf-8'))
                    if checkout_data.get('asset_id') == asset_id:
                        count += 1
                except:
                    continue
        
        return count
    except ClientError:
        return 0

def browse():
    """List all assets in the library with optional filtering"""
    if not s3_client:
        return jsonify({"error": "S3 not available"}), 500
    
    assets = []
    
    # Simple filters
    asset_type = request.args.get('type')
    author = request.args.get('author')
    
    asset_keys = _list_asset_keys()
    
    for key in asset_keys:
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            asset = json.loads(response['Body'].read().decode('utf-8'))
            
            # Apply filters
            if asset_type and asset.get('type') != asset_type:
                continue
            if author and asset.get('author') != author:
                continue
            
            # Count checkouts for this asset
            checkout_count = _count_asset_checkouts(asset["id"])
            
            # Return simplified asset info
            assets.append({
                "id": asset["id"],
                "name": asset["name"],
                "type": asset.get("type"),
                "author": asset.get("author"),
                "rarity": asset.get("rarity", "common"),
                "tags": asset.get("tags", []),
                "checkout_count": checkout_count,
                "created_at": asset.get("created_at")
            })
        except (json.JSONDecodeError, KeyError, ClientError) as e:
            logger.error(f"Error reading asset from S3 key {key}: {e}")
            continue
    
    return jsonify({
        "total": len(assets), 
        "assets": assets
    })

def search():
    """Search for assets with text query and filters"""
    if not s3_client:
        return jsonify({"error": "S3 not available"}), 500
    
    query = request.args.get('q', '').lower()
    asset_type = request.args.get('type')
    author = request.args.get('author')
    rarity = request.args.get('rarity')
    
    results = []
    asset_keys = _list_asset_keys()
    
    for key in asset_keys:
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            asset = json.loads(response['Body'].read().decode('utf-8'))
            
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
        except (json.JSONDecodeError, KeyError, ClientError):
            continue
    
    return jsonify({
        "query": request.args.get('q', ''),
        "total_results": len(results), 
        "results": results
    })

def add_asset():
    """Add a new asset to the library"""
    if not s3_client:
        return jsonify({"error": "S3 not available"}), 500
    
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
        s3_url = f"{S3_BASE_URL}/assets/{asset_id}/{data['name'].lower().replace(' ', '_')}.{file_extension}"
        
        asset = {
            "id": asset_id,
            "name": data["name"],
            "type": data["type"],
            "author": data["author"],
            "description": data.get("description", ""),
            "attributes": data.get("attributes", {}),
            "s3_url": s3_url,
            "rarity": data.get("rarity", "common"),
            "tags": data.get("tags", []),
            "created_at": datetime.utcnow().isoformat()
        }
        
        if _save_asset_to_s3(asset_id, asset):
            return jsonify({
                "message": "Asset added successfully", 
                "asset": asset
            })
        else:
            return jsonify({"error": "Failed to save asset to S3"}), 500
        
    except Exception as e:
        return jsonify({"error": f"Failed to add asset: {str(e)}"}), 500

def checkout():
    """Check out an asset from the library (non-exclusive - multiple users can checkout)"""
    if not s3_client:
        return jsonify({"error": "S3 not available"}), 500
    
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    asset_id = data.get('asset_id')
    user = data.get('borrower') or data.get('user')  # Support both field names
    
    if not asset_id or not user:
        return jsonify({"error": "Missing asset_id or user/borrower"}), 400
    
    try:
        asset = _get_asset_from_s3(asset_id)
        if not asset:
            return jsonify({"error": "Asset not found"}), 404
        
        # Create checkout record
        checkout_id = str(uuid.uuid4())
        checkout_record = {
            "id": checkout_id,
            "asset_id": asset_id,
            "user": user,
            "checkout_date": datetime.utcnow().isoformat(),
            "asset_name": asset["name"],
            "asset_type": asset.get("type"),
            "s3_url": asset.get("s3_url")
        }
        
        if _save_checkout_record(checkout_id, checkout_record):
            return jsonify({
                "message": "Asset checked out successfully", 
                "checkout": {
                    "checkout_id": checkout_id,
                    "asset_id": asset["id"],
                    "name": asset["name"],
                    "type": asset.get("type"),
                    "s3_url": asset.get("s3_url"),
                    "user": user,
                    "checkout_date": checkout_record["checkout_date"]
                }
            })
        else:
            return jsonify({"error": "Failed to save checkout record"}), 500
        
    except Exception as e:
        return jsonify({"error": f"Failed to checkout asset: {str(e)}"}), 500

def get_asset(asset_id):
    """Get detailed information about a specific asset"""
    if not s3_client:
        return jsonify({"error": "S3 not available"}), 500
    
    try:
        asset = _get_asset_from_s3(asset_id)
        if not asset:
            return jsonify({"error": "Asset not found"}), 404
        
        # Add checkout count to asset info
        asset["checkout_count"] = _count_asset_checkouts(asset_id)
        
        return jsonify({"asset": asset})
    except Exception as e:
        return jsonify({"error": f"Failed to get asset: {str(e)}"}), 500

def library_stats():
    """Get overall library statistics"""
    if not s3_client:
        return jsonify({"error": "S3 not available"}), 500
    
    stats = {
        "total_assets": 0,
        "total_checkouts": 0,
        "by_type": {}, 
        "by_rarity": {},
        "by_author": {}
    }
    
    # Count assets
    asset_keys = _list_asset_keys()
    
    for key in asset_keys:
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            asset = json.loads(response['Body'].read().decode('utf-8'))
            stats["total_assets"] += 1
            
            # Count by type
            asset_type = asset.get("type", "unknown")
            stats["by_type"][asset_type] = stats["by_type"].get(asset_type, 0) + 1
            
            # Count by rarity
            rarity = asset.get("rarity", "common")
            stats["by_rarity"][rarity] = stats["by_rarity"].get(rarity, 0) + 1
            
            # Count by author
            author = asset.get("author", "unknown")
            stats["by_author"][author] = stats["by_author"].get(author, 0) + 1
            
        except (json.JSONDecodeError, KeyError, ClientError):
            continue
    
    # Count total checkouts
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_CHECKOUTS_PREFIX}/",
            Delimiter='/'
        )
        if 'Contents' in response:
            stats["total_checkouts"] = len(response['Contents'])
    except ClientError:
        pass
    
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