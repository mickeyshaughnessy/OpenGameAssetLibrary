# OpenGameAssetLibrary

REST API for game asset management with Git version control and S3 storage.

## Quick Start

```bash
pip install flask requests
python api_server.py

# Run tests
python int_tests.py

# Upload assets (requires boto3)
pip install boto3
python setup_multimedia_assets.py my_assets/ --game "my_game"
```

## API Endpoints

- `GET /ping` - Health check
- `GET /browse` - List assets (?type=, ?game=, ?available=, ?tag=)
- `POST /add_asset` - Add asset
- `POST /checkout` - Check out asset
- `POST /return` - Return asset
- `GET /search` - Search assets (?q=, ?type=, ?rarity=)
- `GET /history` - Library stats
- `GET /history/<id>` - Asset history
- `POST /batch/import` - Import multiple assets
- `GET /export` - Export collection
- `POST /utils/generate` - Generate test data
- `POST /utils/cleanup` - Remove test assets

## Asset Structure

```json
{
  "id": "uuid",
  "name": "Fire Sword",
  "type": "item",
  "author": "designer",
  "game_origin": "my_game",
  "description": "A flaming sword",
  "attributes": {"damage": 100},
  "media": {"model": "https://s3.url/sword.glb"},
  "tags": ["weapon", "fire"],
  "rarity": "epic",
  "available": true
}
```

## Asset Types

creature, item, npc, text, image, video, audio, code, data, model

## Upload Assets

```bash
# Upload directory
python setup_multimedia_assets.py assets_folder/

# Mock mode (no upload)
python setup_multimedia_assets.py assets_folder/ --mock

# AWS credentials
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
```

## File Structure

```
OpenGameAssetLibrary/
├── api_server.py
├── handlers.py
├── utils/
│   ├── __init__.py
│   └── git_wrapper.py
├── int_tests.py
├── setup_multimedia_assets.py
└── requirements.txt
```