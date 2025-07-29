# Simple Asset Library

A streamlined digital asset management system with checkout functionality, built with Flask and designed for simplicity and ease of use.

## Overview

This system provides a basic but robust digital asset library where users can:
- Add digital assets (artwork, 3D models, audio, etc.) with unique S3 storage URLs
- Browse and search the asset collection with filtering
- Check out assets permanently (no returns)
- View library statistics and asset details

**Design Philosophy:** Keep it simple. No complex versioning, no batch operations, no returns - just core library functionality that works.

## Features

- 🎯 **Simple Asset Management** - Add, browse, search, and checkout digital assets
- 🔍 **Flexible Search** - Text search with type, author, and rarity filters
- 📊 **Statistics Dashboard** - Library overview with breakdowns by type, rarity, and author
- 🔗 **Unique S3 URLs** - Each asset gets its own S3 storage path for downloads
- 📱 **REST API** - Clean JSON API for easy integration
- ✅ **No Dependencies** - No database required, uses simple JSON file storage

## Quick Start

### Prerequisites
- Python 3.7+
- pip

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd simple-asset-library
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python api_server.py
   ```

3. **Test the API:**
   ```bash
   python simple_test.py
   ```

The server will start on `http://127.0.0.1:5000` and automatically create sample data.

## API Documentation

### Core Endpoints

#### Health Check
```
GET /ping
```
Returns server status and version information.

#### Browse Assets
```
GET /browse[?type=X&author=Y&available=true]
```
List all assets with optional filtering:
- `type` - Filter by asset type (artwork, 3d_models, audio, etc.)
- `author` - Filter by creator
- `available` - Filter by availability (true/false)

#### Search Assets
```
GET /search?q=query[&type=X&author=Y&rarity=Z]
```
Search assets by text query in name, description, and tags. Supports additional filters:
- `q` - Text search query
- `type` - Asset type filter
- `author` - Creator filter  
- `rarity` - Rarity filter (common, uncommon, rare, epic, legendary)

#### Add Asset
```
POST /add
Content-Type: application/json

{
  "name": "Asset Name",
  "type": "artwork",
  "author": "Creator Name",
  "description": "Asset description",
  "attributes": {
    "file_size": "150MB",
    "format": "ZIP"
  },
  "tags": ["tag1", "tag2"],
  "rarity": "rare",
  "file_extension": "zip"
}
```

#### Checkout Asset
```
POST /checkout
Content-Type: application/json

{
  "asset_id": "uuid",
  "borrower": "username"
}
```
Permanently checks out an asset to a user.

#### Get Asset Details
```
GET /asset/{asset_id}
```
Returns complete asset information including S3 URL.

#### Library Statistics
```
GET /stats
```
Returns library overview with asset counts by type, rarity, author, and availability.

## Asset Data Structure

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sci-Fi Texture Pack",
  "type": "artwork",
  "author": "ArtistName",
  "description": "High-resolution sci-fi textures",
  "available": true,
  "borrower": null,
  "checkout_date": null,
  "attributes": {
    "file_count": 50,
    "total_size": "150MB",
    "resolution": "4K",
    "format": "ZIP"
  },
  "s3_url": "https://asset-library.s3.amazonaws.com/assets/550e8400-e29b-41d4-a716-446655440000/sci_fi_texture_pack.zip",
  "rarity": "rare",
  "tags": ["sci-fi", "textures", "4k"],
  "created_at": "2024-01-01T12:00:00.000Z"
}
```

## Supported Asset Types

- `artwork` - Digital art, textures, UI elements
- `3d_models` - 3D models, scenes, animations
- `audio` - Music, sound effects, voice
- `video` - Video files, animations, tutorials
- `documents` - Manuals, guides, scripts
- `other` - Miscellaneous digital assets

## Rarity Levels

- `common` - Standard assets
- `uncommon` - Quality assets
- `rare` - High-quality or specialized assets
- `epic` - Premium or complex assets
- `legendary` - Exceptional or exclusive assets

## Examples

### Adding a 3D Model Pack
```bash
curl -X POST http://localhost:5000/add \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Medieval Weapons Pack",
    "type": "3d_models",
    "author": "ModelMaster",
    "description": "Detailed medieval weapons with PBR textures",
    "attributes": {
      "model_count": 25,
      "poly_count": "5K-15K",
      "format": "FBX + Textures"
    },
    "tags": ["medieval", "weapons", "pbr"],
    "rarity": "epic",
    "file_extension": "zip"
  }'
```

### Searching for Art Assets
```bash
curl "http://localhost:5000/search?q=medieval&type=artwork&rarity=rare"
```

### Checking Out an Asset
```bash
curl -X POST http://localhost:5000/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "550e8400-e29b-41d4-a716-446655440000",
    "borrower": "gamedev_studio"
  }'
```

## Development

### Running Tests
```bash
# Quick test of basic endpoints
python simple_test.py

# Comprehensive integration tests
python int_tests.py
```

### Project Structure
```
simple-asset-library/
├── api_server.py          # Main Flask application
├── handlers.py            # API route handlers
├── requirements.txt       # Dependencies
├── simple_test.py         # Basic API tests
├── int_tests.py          # Integration tests
├── README.md             # This file
└── library-data/         # Auto-generated data directory
    └── assets/           # JSON files for each asset
```

### Adding New Features
The system is designed to be easily extensible:
- Add new endpoints in `handlers.py`
- Register routes in the `register()` function
- Asset schema can be extended by adding fields to the JSON structure

## TODOs

### Immediate Improvements
- [ ] Add file upload handling for actual asset storage to S3
- [ ] Implement user authentication and authorization
- [ ] Add asset thumbnails and preview images
- [ ] Create web UI for browsing and managing assets
- [ ] Add asset categories and subcategories
- [ ] Implement asset ratings and reviews

### Advanced Features
- [ ] **Add ball-tree search and nearest neighbor indexing with learned JSON-JSON and JSON-JSON-JSON metrics and simplices** for advanced asset discovery and recommendation
- [ ] Add collaborative filtering for asset recommendations
- [ ] Implement asset usage analytics and popularity tracking
- [ ] Add asset versioning and update capabilities
- [ ] Create asset collections and playlists
- [ ] Add real-time notifications for new assets
- [ ] Implement asset preview generation (thumbnails, audio waveforms, etc.)
- [ ] Add bulk operations with progress tracking
- [ ] Create asset dependency tracking and relationship mapping
- [ ] Add advanced search with semantic similarity
- [ ] Implement asset licensing and usage rights management

### Infrastructure
- [ ] Add database support (PostgreSQL/MongoDB) for larger deployments
- [ ] Implement caching layer (Redis) for better performance
- [ ] Add containerization (Docker) for easy deployment
- [ ] Create CI/CD pipeline for automated testing and deployment
- [ ] Add monitoring and logging infrastructure
- [ ] Implement backup and disaster recovery procedures

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions:
- Check the integration tests for API usage examples
- Review the handler code for implementation details
- Open an issue with detailed reproduction steps