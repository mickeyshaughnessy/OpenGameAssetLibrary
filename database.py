import json
import math
import uuid
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Tuple, Optional, Any, Set, Callable
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JSONDatabase:
    """A generic S3-backed JSON database with configurable distance functions."""
    
    def __init__(self, 
                 bucket: str = "mithrilmedia",
                 prefix: str = "database",
                 distance_method: str = "euclidean",
                 feature_dim: int = 8,
                 index_size: int = 20,
                 similarity_threshold: float = 0.1):
        """
        Initialize S3-backed JSON database with nearest neighbor search.
        
        Args:
            bucket: S3 bucket name
            prefix: S3 prefix for all database objects
            distance_method: Distance calculation method ("euclidean", "custom", or "auto")
            feature_dim: Dimension for auto-generated feature vectors
            index_size: Maximum number of indexed entries for fast search
            similarity_threshold: Threshold for considering items similar (lower = more similar)
        """
        self.bucket = bucket
        self.prefix = prefix
        self.data_prefix = f"{prefix}/data"
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3')
        
        # Configuration
        self.distance_method = distance_method
        self.feature_dim = feature_dim
        self.index_size = index_size
        self.similarity_threshold = similarity_threshold
        
        # Load or initialize search index
        self.search_index = self._load_index()
        
        # Statistics
        self.last_search_stats = {}
    
    def _get_data_key(self, obj_id: str) -> str:
        """Generate S3 key for data object."""
        return f"{self.data_prefix}/{obj_id}.json"
    
    def _get_index_key(self) -> str:
        """Get S3 key for search index."""
        return f"{self.prefix}/index.json"
    
    def _load_index(self) -> List[str]:
        """Load search index from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=self._get_index_key()
            )
            index_data = json.loads(response['Body'].read().decode('utf-8'))
            return index_data.get('index', [])
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info("No index found, creating new one")
                return []
            logger.error(f"Error loading index: {e}")
            return []
    
    def _save_index(self):
        """Save search index to S3."""
        try:
            index_data = {
                'index': self.search_index,
                'config': {
                    'distance_method': self.distance_method,
                    'feature_dim': self.feature_dim,
                    'index_size': self.index_size
                }
            }
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=self._get_index_key(),
                Body=json.dumps(index_data),
                ContentType='application/json'
            )
        except ClientError as e:
            logger.error(f"Error saving index: {e}")
    
    def _update_index(self, obj_id: str):
        """Add object to search index if space available."""
        if obj_id not in self.search_index:
            if len(self.search_index) >= self.index_size:
                # Remove oldest entry (FIFO)
                self.search_index.pop(0)
            self.search_index.append(obj_id)
            self._save_index()
    
    # ============== Core Database Operations ==============
    
    def insert(self, data: Dict[str, Any], obj_id: Optional[str] = None) -> str:
        """
        Insert arbitrary JSON data into database.
        
        Args:
            data: Any JSON-serializable dictionary
            obj_id: Optional ID (auto-generated if not provided)
            
        Returns:
            The object ID
        """
        if obj_id is None:
            obj_id = str(uuid.uuid4())
        
        # Auto-generate features if using euclidean distance
        if self.distance_method == "euclidean" and "features" not in data:
            data["features"] = self._extract_features(data)
        
        # Store the object ID within the data
        data["_id"] = obj_id
        
        try:
            # Store in S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=self._get_data_key(obj_id),
                Body=json.dumps(data),
                ContentType='application/json'
            )
            
            # Update search index
            self._update_index(obj_id)
            
            logger.info(f"Inserted object: {obj_id}")
            return obj_id
            
        except ClientError as e:
            logger.error(f"Error inserting object: {e}")
            raise
    
    def get(self, obj_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve JSON data by ID.
        
        Args:
            obj_id: Object ID
            
        Returns:
            JSON data or None if not found
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=self._get_data_key(obj_id)
            )
            return json.loads(response['Body'].read().decode('utf-8'))
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(f"Object not found: {obj_id}")
                return None
            logger.error(f"Error retrieving object: {e}")
            return None
    
    def delete(self, obj_id: str) -> bool:
        """
        Delete object from database.
        
        Args:
            obj_id: Object ID
            
        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=self._get_data_key(obj_id)
            )
            
            # Remove from index
            if obj_id in self.search_index:
                self.search_index.remove(obj_id)
                self._save_index()
            
            logger.info(f"Deleted object: {obj_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting object: {e}")
            return False
    
    def update(self, obj_id: str, data: Dict[str, Any]) -> bool:
        """
        Update existing object.
        
        Args:
            obj_id: Object ID
            data: New data (completely replaces old data)
            
        Returns:
            True if successful
        """
        # Preserve the ID
        data["_id"] = obj_id
        
        # Auto-generate features if needed
        if self.distance_method == "euclidean" and "features" not in data:
            data["features"] = self._extract_features(data)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=self._get_data_key(obj_id),
                Body=json.dumps(data),
                ContentType='application/json'
            )
            logger.info(f"Updated object: {obj_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error updating object: {e}")
            return False
    
    # ============== Distance Functions ==============
    
    def calculate_distance(self, obj1: Dict[str, Any], obj2: Dict[str, Any]) -> float:
        """
        Calculate distance between two JSON objects using configured method.
        
        Args:
            obj1: First JSON object
            obj2: Second JSON object
            
        Returns:
            Distance score (lower = more similar)
        """
        if self.distance_method == "euclidean":
            return self._euclidean_distance(obj1, obj2)
        elif self.distance_method == "custom":
            return self._custom_json_distance(obj1, obj2)
        elif self.distance_method == "auto":
            # Try custom first, fall back to euclidean
            try:
                return self._custom_json_distance(obj1, obj2)
            except:
                return self._euclidean_distance(obj1, obj2)
        else:
            raise ValueError(f"Unknown distance method: {self.distance_method}")
    
    def _euclidean_distance(self, obj1: Dict[str, Any], obj2: Dict[str, Any]) -> float:
        """
        Calculate Euclidean distance using feature vectors.
        
        Args:
            obj1: First object (with 'features' or auto-extracted)
            obj2: Second object (with 'features' or auto-extracted)
            
        Returns:
            Euclidean distance
        """
        # Get or generate features
        features1 = obj1.get("features") or self._extract_features(obj1)
        features2 = obj2.get("features") or self._extract_features(obj2)
        
        # Calculate Euclidean distance
        min_len = min(len(features1), len(features2))
        distance = math.sqrt(sum(
            (features1[i] - features2[i])**2 
            for i in range(min_len)
        ))
        
        # Penalize different lengths
        if len(features1) != len(features2):
            distance += abs(len(features1) - len(features2)) * 0.1
        
        return distance
    
    def _custom_json_distance(self, obj1: Dict[str, Any], obj2: Dict[str, Any]) -> float:
        """
        Custom JSON-to-JSON distance function (TO BE IMPLEMENTED).
        
        This is a placeholder for a sophisticated JSON comparison that could:
        - Compare nested structures
        - Handle different data types intelligently
        - Weight certain fields more than others
        - Use semantic similarity for text fields
        - Handle missing fields gracefully
        
        Args:
            obj1: First JSON object
            obj2: Second JSON object
            
        Returns:
            Distance score (0 = identical, higher = more different)
        """
        # ===== STUB IMPLEMENTATION =====
        # This is where we'll implement the custom JSON distance logic
        
        # For now, a simple implementation that counts differences
        distance = 0.0
        
        # Get all keys from both objects
        all_keys = set(obj1.keys()) | set(obj2.keys())
        
        for key in all_keys:
            if key.startswith('_'):  # Skip internal fields
                continue
                
            val1 = obj1.get(key)
            val2 = obj2.get(key)
            
            # Missing field penalty
            if val1 is None or val2 is None:
                distance += 1.0
                continue
            
            # Type mismatch penalty
            if type(val1) != type(val2):
                distance += 0.5
                continue
            
            # Value comparison
            if isinstance(val1, (int, float)):
                # Numeric difference (normalized)
                if val1 != 0 or val2 != 0:
                    distance += abs(val1 - val2) / (abs(val1) + abs(val2) + 1)
            elif isinstance(val1, str):
                # String difference (simple)
                if val1 != val2:
                    distance += 1.0
            elif isinstance(val1, bool):
                if val1 != val2:
                    distance += 0.5
            elif isinstance(val1, dict):
                # Recursive comparison (simplified)
                distance += self._custom_json_distance(val1, val2) * 0.5
            elif isinstance(val1, list):
                # List comparison (simplified)
                if len(val1) != len(val2):
                    distance += abs(len(val1) - len(val2)) * 0.1
                # Compare first few elements
                for i in range(min(len(val1), len(val2), 3)):
                    if val1[i] != val2[i]:
                        distance += 0.2
        
        return distance
        # ===== END STUB =====
    
    def _extract_features(self, obj: Dict[str, Any]) -> List[float]:
        """
        Auto-extract feature vector from arbitrary JSON.
        
        Args:
            obj: JSON object
            
        Returns:
            Feature vector of fixed dimension
        """
        features = []
        
        def extract_value(value):
            """Extract numeric feature from any value type."""
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # Use hash for consistent conversion
                return (hash(value) % 10000) / 10000
            elif isinstance(value, bool):
                return 1.0 if value else 0.0
            elif isinstance(value, (dict, list)):
                return len(value) / 100.0
            else:
                return 0.0
        
        # Extract features from all fields
        for key in sorted(obj.keys()):
            if key.startswith('_') or key == 'features':
                continue
            features.append(extract_value(obj[key]))
        
        # Pad or truncate to fixed dimension
        while len(features) < self.feature_dim:
            features.append(0.0)
        
        return features[:self.feature_dim]
    
    # ============== Search Operations ==============
    
    def find_similar(self, 
                     query: Dict[str, Any], 
                     max_results: int = 5,
                     max_distance: Optional[float] = None) -> List[Tuple[str, Dict[str, Any], float]]:
        """
        Find similar objects using nearest neighbor search.
        
        Args:
            query: Query object (can be partial)
            max_results: Maximum number of results
            max_distance: Maximum distance threshold (None = no limit)
            
        Returns:
            List of (id, object, distance) tuples, sorted by distance
        """
        if max_distance is None:
            max_distance = float('inf')
        
        # Reset statistics
        self.last_search_stats = {
            'objects_checked': 0,
            'index_size': len(self.search_index)
        }
        
        results = []
        
        # Check all indexed objects
        for obj_id in self.search_index:
            obj = self.get(obj_id)
            if obj:
                self.last_search_stats['objects_checked'] += 1
                
                # Calculate distance
                distance = self.calculate_distance(query, obj)
                
                # Add if within threshold
                if distance <= max_distance:
                    results.append((obj_id, obj, distance))
        
        # Sort by distance and limit results
        results.sort(key=lambda x: x[2])
        return results[:max_results]
    
    def find_nearest(self, query: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any], float]]:
        """
        Find the single nearest neighbor.
        
        Args:
            query: Query object
            
        Returns:
            (id, object, distance) tuple or None if database is empty
        """
        results = self.find_similar(query, max_results=1)
        return results[0] if results else None
    
    # ============== Utility Operations ==============
    
    def list_all(self, limit: int = 1000) -> List[str]:
        """List all object IDs in database."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=self.data_prefix,
                MaxKeys=limit
            )
            
            ids = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.startswith(self.data_prefix + '/') and key.endswith('.json'):
                        obj_id = key[len(self.data_prefix) + 1:-5]
                        ids.append(obj_id)
            
            return ids
            
        except ClientError as e:
            logger.error(f"Error listing objects: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        all_ids = self.list_all(limit=10000)
        
        return {
            'total_objects': len(all_ids),
            'indexed_objects': len(self.search_index),
            'index_coverage': len(self.search_index) / max(len(all_ids), 1),
            'distance_method': self.distance_method,
            'feature_dim': self.feature_dim,
            'last_search_stats': self.last_search_stats
        }
    
    def rebuild_index(self, sample_size: Optional[int] = None):
        """
        Rebuild search index from all objects.
        
        Args:
            sample_size: If provided, randomly sample this many objects
        """
        all_ids = self.list_all(limit=10000)
        
        if sample_size and len(all_ids) > sample_size:
            import random
            all_ids = random.sample(all_ids, sample_size)
        
        self.search_index = all_ids[-self.index_size:]
        self._save_index()
        
        logger.info(f"Rebuilt index with {len(self.search_index)} objects")


# ============== Test Suite ==============

def run_tests():
    """Run comprehensive tests of the JSON database."""
    print("=" * 60)
    print("JSON DATABASE TEST SUITE")
    print("=" * 60)
    
    # Test 1: Basic Operations
    print("\n1. Testing Basic Operations")
    print("-" * 40)
    
    db = JSONDatabase(
        bucket="mithrilmedia",
        prefix="json-db-test",
        distance_method="euclidean",
        feature_dim=5,
        index_size=10
    )
    
    # Insert various JSON objects
    test_data = [
        {"name": "Alice", "age": 30, "city": "New York", "score": 95},
        {"name": "Bob", "age": 25, "city": "Los Angeles", "score": 87},
        {"name": "Charlie", "age": 35, "city": "Chicago", "score": 92},
        {"name": "Diana", "age": 28, "city": "New York", "score": 88},
        {"product": "Laptop", "price": 999, "brand": "TechCo", "rating": 4.5},
        {"product": "Phone", "price": 599, "brand": "Gadgets", "rating": 4.2},
        {"type": "event", "timestamp": 1234567890, "action": "click", "user_id": 42},
    ]
    
    inserted_ids = []
    for data in test_data:
        obj_id = db.insert(data)
        inserted_ids.append(obj_id)
        print(f"✓ Inserted: {obj_id[:8]}... -> {list(data.keys())}")
    
    # Test 2: Retrieval
    print("\n2. Testing Retrieval")
    print("-" * 40)
    
    for obj_id in inserted_ids[:3]:
        obj = db.get(obj_id)
        if obj:
            print(f"✓ Retrieved: {obj_id[:8]}... -> {obj.get('name') or obj.get('product') or 'object'}")
    
    # Test 3: Euclidean Distance Search
    print("\n3. Testing Euclidean Distance Search")
    print("-" * 40)
    
    query = {"name": "Eve", "age": 29, "city": "New York", "score": 90}
    results = db.find_similar(query, max_results=3)
    
    print(f"Query: {query}")
    print(f"Results:")
    for obj_id, obj, distance in results:
        print(f"  {distance:.3f} -> {obj.get('name', obj.get('product', 'unknown'))}")
    
    # Test 4: Custom JSON Distance
    print("\n4. Testing Custom JSON Distance")
    print("-" * 40)
    
    db.distance_method = "custom"
    
    query2 = {"product": "Tablet", "price": 799, "brand": "TechCo", "rating": 4.3}
    results2 = db.find_similar(query2, max_results=3)
    
    print(f"Query: {query2}")
    print(f"Results:")
    for obj_id, obj, distance in results2:
        print(f"  {distance:.3f} -> {obj.get('name', obj.get('product', 'unknown'))}")
    
    # Test 5: Update
    print("\n5. Testing Update")
    print("-" * 40)
    
    if inserted_ids:
        update_id = inserted_ids[0]
        new_data = {"name": "Alice Updated", "age": 31, "city": "Boston", "score": 98}
        success = db.update(update_id, new_data)
        print(f"✓ Updated {update_id[:8]}... -> {new_data['name']}")
    
    # Test 6: Statistics
    print("\n6. Database Statistics")
    print("-" * 40)
    
    stats = db.get_stats()
    for key, value in stats.items():
        if key != 'last_search_stats':
            print(f"  {key}: {value}")
    
    # Test 7: Cleanup
    print("\n7. Cleanup")
    print("-" * 40)
    
    for obj_id in inserted_ids:
        db.delete(obj_id)
    print(f"✓ Deleted {len(inserted_ids)} test objects")
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()