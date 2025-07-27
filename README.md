# OpenGameAssetLibrary

A REST API for managing game assets with Git-based version control and S3 media storage. Perfect for indie game developers who need a simple, versioned asset management system.

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd OpenGameAssetLibrary
pip install -r requirements.txt

# 2. Start the API server
python api_server.py

# 3. Run tests to verify everything works
python int_tests.py

# 4. (Optional) Add example multimedia assets
python setup_multimedia_assets.py
```

The API will be available at `http://localhost:5000`

## 📁 Project Structure

```
OpenGameAssetLibrary/
├── api_server.py              # Main Flask application
├── handlers.py                # All API endpoint handlers
├── utils/
│   ├── __init__.py
│   └── git_wrapper.py         # Git operations wrapper
├── library-repo/              # Git repository (auto-created)
│   └── assets/               # JSON files for each asset
├── int_tests.py              # Integration tests
├── setup_multimedia_assets.py # Example assets setup
├── example_usage.py          # Usage examples
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🎮 Asset Types

The library supports various game asset types:

- **creature** - Game monsters/characters with combat stats
- **item** - Usable items with effects
- **npc** - Non-player characters with dialogue and personality
- **text** - Story content, descriptions, lore
- **image** - Concept art, textures, UI elements
- **video** - Cutscenes, trailers, tutorials
- **audio** - Music, sound effects, voice lines
- **code** - Shaders, AI behaviors, scripts
- **data** - Game balance data, configuration files

## 🔌 API Endpoints

### Core Operations

#### `GET /ping`
Health check
```bash
curl http://localhost:5000/ping
```

#### `GET /browse`
List assets with optional filters
```bash
# All assets
curl http://localhost:5000/browse

# Filter by type and availability
curl "http://localhost:5000/browse?type=creature&available=true"

# Filter by tags
curl "http://localhost:5000/browse?tag=fire&tag=legendary"
```

#### `POST /add_asset`
Add a new asset
```bash
curl -X POST http://localhost:5000/add_asset \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Fire Dragon",
    "type": "creature",
    "author": "game_designer",
    "game_origin": "my_rpg",
    "description": "A powerful fire-breathing dragon",
    "rarity": "legendary",
    "tags": ["dragon", "fire", "boss"],
    "attributes": {
      "power": 95,
      "defense": 80,
      "health": 500
    },
    "media": {
      "model": "https://mithrilmedia.s3.amazonaws.com/models/fire_dragon.glb",
      "texture": "https://mithrilmedia.s3.amazonaws.com/textures/fire_dragon.png"
    }
  }'
```

#### `POST /checkout`
Check out an asset for use
```bash
curl -X POST http://localhost:5000/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "asset-uuid-here",
    "borrower": "player123",
    "game_context": "dungeon_level_5"
  }'
```

#### `POST /return`
Return a checked-out asset
```bash
curl -X POST http://localhost:5000/return \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "asset-uuid-here",
    "borrower": "player123",
    "condition": "good",
    "notes": "Used in boss battle"
  }'
```

### Search & Analytics

#### `GET /search`
Advanced search with multiple criteria
```bash
# Text search
curl "http://localhost:5000/search?q=dragon"

# Combined filters
curl "http://localhost:5000/search?type=creature&rarity=legendary&available_only=true"
```

#### `GET /popular`
Get most checked-out assets
```bash
curl "http://localhost:5000/popular?limit=10&days=30"
```

### History & Statistics

#### `GET /history`
Library statistics
```bash
curl http://localhost:5000/history
```

#### `GET /history/{asset_id}`
Individual asset history
```bash
curl http://localhost:5000/history/asset-uuid-here
```

### Batch Operations

#### `POST /batch/import`
Import multiple assets at once
```bash
curl -X POST http://localhost:5000/batch/import \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {
        "name": "Health Potion",
        "type": "item",
        "author": "game_designer",
        "game_origin": "my_rpg",
        "attributes": {"effects": [{"type": "heal", "value": 50}]}
      },
      {
        "name": "Mana Potion",
        "type": "item",
        "author": "game_designer",
        "game_origin": "my_rpg",
        "attributes": {"effects": [{"type": "mana", "value": 30}]}
      }
    ]
  }'
```

#### `GET /export`
Export filtered assets
```bash
curl "http://localhost:5000/export?type=creature&game=my_rpg"
```

### Utilities

#### `POST /utils/generate`
Generate test data
```bash
curl -X POST http://localhost:5000/utils/generate
```

#### `GET /utils/git-status`
Check Git repository status
```bash
curl http://localhost:5000/utils/git-status
```

## 📊 Asset Structure

Assets are JSON documents with media files hosted on S3:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Epic Battle Theme",
  "type": "audio",
  "author": "composer_jane",
  "game_origin": "space_adventure",
  "description": "Main battle theme with dynamic intensity",
  "available": true,
  "current_borrower": null,
  "attributes": {
    "format": "ogg",
    "duration": 240,
    "bpm": 140,
    "loop_points": {"start": 30, "end": 210}
  },
  "media": {
    "audio_file": "https://mithrilmedia.s3.amazonaws.com/audio/epic_battle.ogg",
    "sheet_music": "https://mithrilmedia.s3.amazonaws.com/scores/epic_battle.pdf"
  },
  "tags": ["music", "battle", "epic"],
  "rarity": "epic",
  "cross_game_compatible": true,
  "created_at": "2024-01-15T10:30:00Z",
  "checkout_history": []
}
```

## 🧪 Testing

Run the comprehensive integration test suite:

```bash
python int_tests.py
```

This will test all endpoints including:
- Core CRUD operations
- Asset checkout/return flow
- Search and filtering
- Batch operations
- Error handling
- Multimedia asset support

## 🎯 Features

- **Git Version Control**: Every transaction creates a commit
- **S3 Media Storage**: Large files hosted on `https://mithrilmedia.s3.amazonaws.com`
- **Asset Checkout System**: Track who's using what assets
- **Rich Metadata**: Attributes, tags, rarity levels
- **Cross-Game Support**: Share assets between multiple games
- **Batch Operations**: Import/export multiple assets efficiently
- **Advanced Search**: Query by type, tags, attributes, usage

## 🛠️ Configuration

The system uses these defaults:
- **API Port**: 5000
- **Library Path**: `./library-repo/`
- **S3 Bucket**: `https://mithrilmedia.s3.amazonaws.com`

## 📝 Examples

See `example_usage.py` for detailed examples of:
- Working with multimedia assets
- Batch operations
- Advanced searches
- Asset checkout workflows

## 🤝 Contributing

1. Keep handlers in the consolidated `handlers.py` file
2. Add tests for new endpoints in `int_tests.py`
3. Follow the existing asset structure
4. Document new asset types in this README

## 📄 License

[Your License Here]

---

Built for game developers who value simplicity and version control 🎮