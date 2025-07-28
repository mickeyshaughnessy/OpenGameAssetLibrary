#!/usr/bin/env python3
"""
Simple Asset Library API Server
Manages a basic library of digital assets with checkout functionality
"""

from flask import Flask
from flask_cors import CORS
import os
import json
import uuid
from datetime import datetime

# Import handlers
import handlers

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

LIBRARY_PATH = "./library-data"

def init_library():
    """Initialize the library directory and create sample data if it doesn't exist"""
    if not os.path.exists(LIBRARY_PATH):
        print("Initializing library...")
        os.makedirs(LIBRARY_PATH)
        
        # Create assets directory
        assets_dir = os.path.join(LIBRARY_PATH, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        # Add a sample asset
        sample_asset = {
            "id": str(uuid.uuid4()),
            "name": "Digital Art Collection",
            "type": "artwork",
            "author": "System",
            "description": "A sample digital art collection for testing",
            "available": True,
            "borrower": None,
            "checkout_date": None,
            "attributes": {
                "file_size": "15MB",
                "format": "PSD",
                "resolution": "4K"
            },
            "s3_url": f"https://asset-library.s3.amazonaws.com/assets/{str(uuid.uuid4())}/digital_art_collection.zip",
            "rarity": "common",
            "tags": ["art", "digital", "sample"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        asset_path = os.path.join(assets_dir, f"{sample_asset['id']}.json")
        with open(asset_path, 'w') as f:
            json.dump(sample_asset, f, indent=2)
        
        print("Library initialized with sample asset!")

# Register all the handlers
handlers.register(app)

@app.errorhandler(404)
def not_found(error):
    return {"error": "Endpoint not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    return {"error": "Internal server error"}, 500

if __name__ == '__main__':
    print("Starting Simple Asset Library API Server...")
    init_library()
    print("API Server ready!")
    print("Available endpoints:")
    print("  GET  /ping")
    print("  GET  /browse")
    print("  GET  /search")
    print("  GET  /stats")
    print("  GET  /asset/<asset_id>")
    print("  POST /add")
    print("  POST /checkout")
    print("\nStarting Flask server on http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)