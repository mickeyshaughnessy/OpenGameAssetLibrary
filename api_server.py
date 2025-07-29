#!/usr/bin/env python3
"""
Simple Asset Library API Server - S3 Version
Manages a basic library of digital assets with S3 storage and checkout functionality
"""
from flask import Flask
from flask_cors import CORS
import json
import uuid
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging

# Import handlers
import handlers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# S3 Configuration
S3_BUCKET = "mithrilmedia"
S3_PREFIX = "OpenGameAssetLibrary"
S3_ASSETS_PREFIX = f"{S3_PREFIX}/assets"
S3_BASE_URL = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/{S3_PREFIX}"

def init_library():
    """Initialize the library in S3 and create sample data if it doesn't exist"""
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Check if bucket is accessible
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET)
            logger.info(f"Connected to S3 bucket: {S3_BUCKET}")
        except ClientError as e:
            logger.error(f"Cannot access S3 bucket {S3_BUCKET}: {e}")
            return False
        
        # Check if library already has assets
        try:
            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=f"{S3_ASSETS_PREFIX}/",
                MaxKeys=1
            )
            
            if 'Contents' in response and len(response['Contents']) > 0:
                logger.info("Library already initialized with existing assets")
                return True
        except ClientError as e:
            logger.error(f"Error checking existing assets: {e}")
        
        # Create sample asset if library is empty
        logger.info("Initializing library with sample asset...")
        
        sample_asset_id = str(uuid.uuid4())
        sample_asset = {
            "id": sample_asset_id,
            "name": "Digital Art Collection",
            "type": "artwork",
            "author": "System",
            "description": "A sample digital art collection for testing the S3-powered asset library",
            "available": True,
            "borrower": None,
            "checkout_date": None,
            "attributes": {
                "file_size": "15MB",
                "format": "PSD",
                "resolution": "4K"
            },
            "s3_url": f"{S3_BASE_URL}/assets/{sample_asset_id}/digital_art_collection.zip",
            "rarity": "common",
            "tags": ["art", "digital", "sample", "s3"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save sample asset to S3
        key = f"{S3_ASSETS_PREFIX}/{sample_asset_id}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(sample_asset, indent=2),
            ContentType='application/json'
        )
        
        logger.info("Library initialized with sample asset!")
        return True
        
    except NoCredentialsError:
        logger.error("AWS credentials not found. Please configure your AWS credentials.")
        logger.error("You can set them using:")
        logger.error("  - AWS CLI: aws configure")
        logger.error("  - Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        logger.error("  - IAM roles (if running on EC2)")
        return False
    except Exception as e:
        logger.error(f"Error initializing library: {e}")
        return False

# Register all the handlers
handlers.register(app)

@app.errorhandler(404)
def not_found(error):
    return {"error": "Endpoint not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    return {"error": "Internal server error"}, 500

if __name__ == '__main__':
    print("Starting Simple Asset Library API Server (S3 Version)...")
    print(f"Using S3 bucket: {S3_BUCKET}")
    print(f"Library prefix: {S3_PREFIX}")
    
    if init_library():
        print("✓ Library initialization successful!")
    else:
        print("✗ Library initialization failed - check AWS credentials and S3 access")
        print("The server will start but some functions may not work properly.")
    
    print("\nAPI Server ready!")
    print("Available endpoints:")
    print("  GET  /ping")
    print("  GET  /browse")
    print("  GET  /search")
    print("  GET  /stats")
    print("  GET  /asset/<asset_id>")
    print("  POST /add")
    print("  POST /checkout")
    print(f"\nS3 Storage: {S3_BASE_URL}")
    print("Starting Flask server on http://127.0.0.1:5000")
    
    app.run(debug=True, host='127.0.0.1', port=5000)