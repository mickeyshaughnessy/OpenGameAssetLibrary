import uuid
import random

def generate_assets():
    assets = []
    
    # --- Helpers ---
    def create_asset(game_type, category, **kwargs):
        asset = {
            "id": str(uuid.uuid4()),
            "game_type": game_type,
            "category": category
        }
        asset.update(kwargs)
        return asset

    # --- Dungeon Crawler Assets ---
    
    classes = ["warrior", "mage", "rogue", "cleric", "paladin", "ranger", "bard", "monk"]
    races = ["human", "elf", "dwarf", "orc", "halfling", "gnome", "tiefling"]
    adjectives = ["Brave", "Cunning", "Wise", "Strong", "Swift", "Dark", "Light", "Ancient"]
    names_base = ["Thorin", "Elara", "Grom", "Lilith", "Fay", "Dorian", "Kael", "Mira"]
    
    # 1. Characters (Generate 40)
    for i in range(40):
        cls = random.choice(classes)
        race = random.choice(races)
        name = f"{random.choice(names_base)} the {random.choice(adjectives)}"
        
        stats = {
            "strength": random.randint(8, 20),
            "dexterity": random.randint(8, 20),
            "intelligence": random.randint(8, 20),
            "wisdom": random.randint(8, 20),
            "constitution": random.randint(8, 20),
            "charisma": random.randint(8, 20)
        }
        
        # Bias stats based on class
        if cls == "warrior": stats["strength"] += 5
        elif cls == "mage": stats["intelligence"] += 5
        elif cls == "rogue": stats["dexterity"] += 5
        
        inventory = []
        if cls == "warrior": inventory = ["Sword", "Shield", "Plate Armor"]
        elif cls == "mage": inventory = ["Staff", "Robes", "Spellbook"]
        elif cls == "rogue": inventory = ["Dagger", "Leather Armor", "Poison"]
        else: inventory = ["Adventurer's Kit"]
        
        assets.append(create_asset(
            "dungeon_crawler", "character",
            name=name,
            role=cls,
            race=race,
            stats=stats,
            inventory=inventory,
            description=f"A {random.choice(adjectives).lower()} {race} {cls}."
        ))

    # 2. NPCs (Generate 20)
    professions = ["blacksmith", "innkeeper", "merchant", "guard", "farmer", "alchemist"]
    for i in range(20):
        prof = random.choice(professions)
        assets.append(create_asset(
            "dungeon_crawler", "npc",
            name=f"{random.choice(names_base)} {random.choice(['Smith', 'Baker', 'Miller', 'Cooper'])}",
            role=prof,
            location=f"Town {random.choice(['Square', 'Gate', 'Hall', 'Market'])}",
            services=[f"service_{prof}", "gossip"],
            dialogue=[f"Welcome to my {prof} shop!", "Stay out of trouble."]
        ))

    # 3. Items (Generate 20)
    item_types = ["weapon", "armor", "potion", "scroll"]
    for i in range(20):
        itype = random.choice(item_types)
        assets.append(create_asset(
            "dungeon_crawler", "item",
            name=f"{random.choice(adjectives)} {itype.capitalize()}",
            item_type=itype,
            rarity=random.choice(["common", "uncommon", "rare", "legendary"]),
            value=random.randint(10, 1000),
            weight=random.uniform(0.1, 10.0)
        ))

    # --- Farming Sim Assets ---
    
    # 1. Animals (Generate 20)
    animals = [
        ("cow", "milk"), ("chicken", "eggs"), ("sheep", "wool"), 
        ("pig", "truffles"), ("goat", "milk"), ("duck", "feathers")
    ]
    for i in range(20):
        species, produce = random.choice(animals)
        assets.append(create_asset(
            "farming_sim", "animal",
            name=f"{species.capitalize()} #{i+1}",
            species=species,
            produce=produce,
            value=random.randint(50, 1000),
            needs=["food", "water", "love"]
        ))

    # 2. Plants (Generate 20)
    crops = ["wheat", "corn", "potato", "carrot", "tomato", "pumpkin", "strawberry"]
    seasons = ["spring", "summer", "fall", "winter"]
    for i in range(20):
        crop = random.choice(crops)
        assets.append(create_asset(
            "farming_sim", "plant",
            name=f"{random.choice(['Giant', 'Sweet', 'Red', 'Golden'])} {crop.capitalize()}",
            species=crop,
            growth_days=random.randint(3, 30),
            preferred_season=random.choice(seasons),
            sell_price=random.randint(5, 100)
        ))
        
    # 3. Weather (Generate 10)
    weather_types = ["sunny", "rain", "storm", "snow", "cloudy", "fog"]
    for i in range(10):
        cond = random.choice(weather_types)
        assets.append(create_asset(
            "farming_sim", "weather",
            name=f"{cond.capitalize()} Day",
            condition=cond,
            effects={"water_crops": cond in ["rain", "storm"], "mood": random.uniform(0.5, 1.5)},
            description=f"A typical {cond} day."
        ))

    return assets
