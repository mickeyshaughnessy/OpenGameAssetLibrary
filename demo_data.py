import uuid

def generate_assets():
    assets = []
    
    # --- Dungeon Crawler Assets ---
    
    # Characters
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Garroth Ironhewer",
        "game_type": "dungeon_crawler",
        "category": "character",
        "role": "warrior",
        "stats": {"strength": 18, "dexterity": 12, "intelligence": 8},
        "inventory": ["Greatsword", "Plate Armor", "Health Potion"],
        "description": "A battle-hardened veteran of the Goblin Wars."
    })
    
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Elara Moonwhisper",
        "game_type": "dungeon_crawler",
        "category": "character",
        "role": "mage",
        "stats": {"strength": 6, "dexterity": 14, "intelligence": 19},
        "inventory": ["Elder Staff", "Silk Robes", "Mana Crystal"],
        "description": "A scholar of the arcane arts seeking ancient scrolls."
    })
    
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Varin Shadowstep",
        "game_type": "dungeon_crawler",
        "category": "character",
        "role": "rogue",
        "stats": {"strength": 10, "dexterity": 20, "intelligence": 14},
        "inventory": ["Daggers", "Leather Armor", "Lockpicks"],
        "description": "A silent blade in the dark."
    })
    
    # NPCs
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Barnaby Smith",
        "game_type": "dungeon_crawler",
        "category": "npc",
        "role": "blacksmith",
        "location": "Town Square",
        "services": ["repair", "sell_weapons"],
        "dialogue": ["Fine steel for sale!", "Keep your blade sharp."]
    })

    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Martha Pourwell",
        "game_type": "dungeon_crawler",
        "category": "npc",
        "role": "innkeeper",
        "location": "The Rusty Tankard",
        "services": ["rent_room", "sell_food"],
        "dialogue": ["Warm bed and cold ale!", "Hear any rumors lately?"]
    })

    # --- Farming Sim Assets ---
    
    # Animals
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Bessie",
        "game_type": "farming_sim",
        "category": "animal",
        "species": "cow",
        "produce": "milk",
        "value": 500,
        "needs": ["hay", "water"]
    })
    
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Cluck",
        "game_type": "farming_sim",
        "category": "animal",
        "species": "chicken",
        "produce": "eggs",
        "value": 50,
        "needs": ["seeds"]
    })

    # Plants
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Golden Wheat",
        "game_type": "farming_sim",
        "category": "plant",
        "species": "wheat",
        "growth_days": 5,
        "seasons": ["spring", "summer"],
        "sell_price": 10
    })
    
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Sweet Corn",
        "game_type": "farming_sim",
        "category": "plant",
        "species": "corn",
        "growth_days": 12,
        "seasons": ["summer", "fall"],
        "sell_price": 25
    })

    # Environment
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Sunny Day",
        "game_type": "farming_sim",
        "category": "weather",
        "condition": "sunny",
        "effects": {"crop_growth": 1.2, "animal_happiness": 1.1},
        "description": "Clear blue skies."
    })

    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Heavy Rain",
        "game_type": "farming_sim",
        "category": "weather",
        "condition": "rain",
        "effects": {"crop_growth": 1.5, "animal_happiness": 0.8, "water_crops": True},
        "description": "A thorough soaking for the fields."
    })
    
    assets.append({
        "id": str(uuid.uuid4()),
        "name": "Market Boom",
        "game_type": "farming_sim",
        "category": "economy",
        "state": "inflation",
        "modifiers": {"sell_price": 1.5, "buy_price": 1.5},
        "description": "Prices are high everywhere!"
    })

    return assets
