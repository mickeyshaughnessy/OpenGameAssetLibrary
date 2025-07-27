#!/usr/bin/env python3
"""
OpenGameAssetLibrary API Server
Main Flask application that serves the game asset library API
"""

from flask import Flask
from flask_cors import CORS
import os
import json
import uuid
from datetime import datetime

# Import handlers
import handlers
from utils.git_wrapper import run_git

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

LIBRARY_PATH = "./library-repo"

def init_library():
    """Initialize the git repository and create sample data if it doesn't exist"""
    if not os.path.exists(LIBRARY_PATH):
        print("Initializing library repository...")
        os.makedirs(LIBRARY_PATH)
        run_git("init")
        
        # Create assets directory
        assets_dir = os.path.join(LIBRARY_PATH, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        # Add a sample asset
        sample_asset = {
            "id": str(uuid.uuid4()),
            "name": "Mithril Sword",
            "type": "item",
            "author": "System",
            "game_origin": "sample_game",
            "description": "A legendary sword forged from mithril",
            "available": True,
            "current_borrower": None,
            "attributes": {
                "damage": 45,
                "durability": 100,
                "weight": 2.5,
                "enchantment": "flame"
            },
            "media": {
                "image": "https://example.com/mithril_sword.png",
                "model": "https://example.com/mithril_sword.obj"
            },
            "cross_game_compatible": True,
            "rarity": "legendary",
            "tags": ["sword", "weapon", "mithril", "enchanted"],
            "created_at": datetime.utcnow().isoformat(),
            "checkout_history": []
        }
        
        asset_path = os.path.join(assets_dir, f"{sample_asset['id']}.json")
        with open(asset_path, 'w') as f:
            json.dump(sample_asset, f, indent=2)
        
        run_git("add .")
        run_git('commit -m "Initial library setup with sample asset"')
        print("Library initialized successfully!")

# Register all the handlers
handlers.register(app)

@app.errorhandler(404)
def not_found(error):
    return {"error": "Endpoint not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    return {"error": "Internal server error"}, 500

if __name__ == '__main__':
    print("Starting OpenGameAssetLibrary API Server...")
    print("Initializing library...")
    init_library()
    print("API Server ready!")
    print("Available endpoints:")
    print("  GET  /ping")
    print("  GET  /browse")
    print("  GET  /search")
    print("  GET  /history")
    print("  GET  /history/<asset_id>")
    print("  GET  /popular")
    print("  GET  /export")
    print("  GET  /utils/git-status")
    print("  POST /add_asset")
    print("  POST /checkout")
    print("  POST /return")
    print("  POST /batch/import")
    print("  POST /batch/checkout")
    print("  POST /utils/generate")
    print("  POST /utils/cleanup")
    print("\nStarting Flask server on http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)