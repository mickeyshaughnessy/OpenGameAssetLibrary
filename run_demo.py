import sys
import json
from database import JSONDatabase
from demo_data import generate_assets

def print_separator(title):
    print(f"\n{'='*20} {title} {'='*20}")

def run_demo():
    print_separator("Initializing OpenGameAssetLibrary Demo")
    
    # Initialize Database
    # Note: Using a demo-specific prefix to avoid messing with main library if needed, 
    # but for this task I'll use the main one or a specific demo path.
    db = JSONDatabase(bucket="mithrilmedia", prefix="OpenGameAssetLibraryDemo")
    
    # 1. Setup Data
    print("\n[1] Checking/Generating Assets...")
    assets = generate_assets()
    
    # Insert assets (this triggers index rebuild)
    # In a real scenario, we'd check if they exist, but for demo we'll just overwrite/add
    print(f"    Injecting {len(assets)} assets into S3 and building Ball Tree...")
    
    # Batch insert simulation (rebuilding once at the end is more efficient usually, 
    # but our DB rebuilds on insert currently. We will just rebuild explicitly once.)
    # To avoid 12 rebuilds, we can manually inject to S3 then call rebuild.
    
    for asset in assets:
        # Direct S3 put to avoid trigger overhead for every single item
        key = f"{db.assets_prefix}/{asset['id']}.json"
        db.s3_client.put_object(
            Bucket=db.bucket,
            Key=key,
            Body=json.dumps(asset),
            ContentType='application/json'
        )
        print(f"    -> Uploaded {asset['name']}")
        
    print("    Rebuilding Ball Tree Index...")
    db.rebuild_index()
    print("    Done.")

    # 2. Execute Queries
    print_separator("Demonstrating Intelligent Search")

    queries = [
        {
            "name": "Find a Warrior (Combat Focus)",
            "query": {
                "game_type": "dungeon_crawler",
                "category": "character",
                "role": "warrior", # Exact match on role
                "stats": {"strength": 20} # Ideal strength
            },
            "explanation": "Targeting a high-strength character in the dungeon crawler set."
        },
        {
            "name": "Find a Farm Animal",
            "query": {
                "game_type": "farming_sim",
                "category": "animal",
                "produce": "milk" # Specific product
            },
            "explanation": "Looking for a milk-producing animal in the farming sim."
        },
        {
            "name": "Find Weather",
            "query": {
                "category": "weather", 
                "condition": "rain"
            },
            "explanation": "Searching for weather conditions, specifically rain."
        },
        {
            "name": "Find High Intellect NPC (Vague)",
            "query": {
                "stats": {"intelligence": 18}
            },
            "explanation": "Cross-genre search for high intelligence. Should find the Mage."
        }
    ]

    for q in queries:
        print(f"\n>>> Query: {q['name']}")
        print(f"    Context: {q['explanation']}")
        print(f"    Search Object: {json.dumps(q['query'], indent=2)}")
        
        results = db.search(q['query'], k=3)
        
        print("\n    Results (Ranked by Similarity Distance):")
        for dist, asset in results:
            # Normalize distance for display if needed, or just show raw
            similarity = (1.0 - dist) * 100
            print(f"    [{dist:.4f}] {asset['name']} ({asset.get('category', 'unknown')}/{asset.get('role', asset.get('species', ''))})")
            # Optional: Print why it matched? (Hard with just a distance number)

    print_separator("Demo Complete")

if __name__ == "__main__":
    run_demo()
