import json
import math
import uuid
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Tuple, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, 
                 bucket: str = "mithrilmedia",
                 prefix: str = "OpenGameAssetLibrary",
                 feature_dim: int = 8,
                 candle_len: int = 12,
                 initial_threshold: float = 0.6):
        """
        Initialize S3-backed ball-tree database.
        
        Args:
            bucket: S3 bucket name
            prefix: S3 prefix for all database objects
            feature_dim: Dimension of feature vectors
            candle_len: Maximum number of candle entries
            initial_threshold: Initial stopping criteria threshold
        """
        self.bucket = bucket
        self.prefix = prefix
        self.assets_prefix = f"{prefix}/assets"
        self.base_url = f"https://{bucket}.s3.us-east-1.amazonaws.com/{prefix}"
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3')
        
        # Algorithm parameters
        self.FEATURE_D = feature_dim
        self.CANDLE_LEN = candle_len
        self.initial_stopping_criteria = initial_threshold
        self.stopping_criteria = self.initial_stopping_criteria
        self.recursive_steps = 0
        self.stopping_criteria_hits = 0
        
        # Load or initialize candles
        self.candles = self._load_candles()
        
    def _get_s3_key(self, key: str) -> str:
        """Generate full S3 key with prefix."""
        return f"{self.assets_prefix}/{key}.json"
    
    def _get_candles_key(self) -> str:
        """Get S3 key for candles index."""
        return f"{self.prefix}/candles.json"
    
    def _load_candles(self) -> List[str]:
        """Load candles index from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=self._get_candles_key()
            )
            candles_data = json.loads(response['Body'].read().decode('utf-8'))
            return candles_data.get('candles', [])
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info("No candles index found, creating new one")
                return []
            else:
                logger.error(f"Error loading candles: {e}")
                return []
    
    def _save_candles(self):
        """Save candles index to S3."""
        try:
            candles_data = {'candles': self.candles}
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=self._get_candles_key(),
                Body=json.dumps(candles_data),
                ContentType='application/json'
            )
        except ClientError as e:
            logger.error(f"Error saving candles: {e}")
    
    def set(self, key: str, value: Dict[str, Any]) -> bool:
        """
        Store an object in S3.
        
        Args:
            key: Unique identifier for the object
            value: Dictionary containing the object data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add to candles if space available
            if len(self.candles) < self.CANDLE_LEN and key not in self.candles:
                self.candles.append(key)
                self._save_candles()
            
            # Store object in S3
            s3_key = self._get_s3_key(key)
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=json.dumps(value),
                ContentType='application/json',
                Metadata={
                    'entity-id': key,
                    'feature-dim': str(self.FEATURE_D)
                }
            )
            return True
            
        except ClientError as e:
            logger.error(f"Error storing object {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an object from S3.
        
        Args:
            key: Unique identifier for the object
            
        Returns:
            Dictionary containing the object data, or None if not found
        """
        try:
            s3_key = self._get_s3_key(key)
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return json.loads(response['Body'].read().decode('utf-8'))
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(f"Object {key} not found")
            else:
                logger.error(f"Error retrieving object {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete an object from S3.
        
        Args:
            key: Unique identifier for the object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            s3_key = self._get_s3_key(key)
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            
            # Remove from candles if present
            if key in self.candles:
                self.candles.remove(key)
                self._save_candles()
                
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting object {key}: {e}")
            return False
    
    def distance_function(self, event: Dict[str, Any], db_event: Dict[str, Any]) -> Optional[float]:
        """
        Calculate Euclidean distance between two feature vectors.
        
        Args:
            event: Query event with features
            db_event: Database event with features
            
        Returns:
            Euclidean distance or None if features missing
        """
        if not event or not db_event:
            return None
            
        features1 = event.get("features")
        features2 = db_event.get("features")
        
        if not features1 or not features2:
            return None
            
        try:
            return math.sqrt(sum((features1[i] - features2[i])**2 
                               for i in range(min(len(features1), len(features2)))))
        except (IndexError, TypeError) as e:
            logger.error(f"Error calculating distance: {e}")
            return None
    
    def update_stopping_criteria(self, db_size: int, depth: int):
        """
        Dynamically adjust stopping criteria based on recursion depth and database size.
        
        Args:
            db_size: Current database size
            depth: Current recursion depth
        """
        self.stopping_criteria = self.initial_stopping_criteria + \
                                (0.001 * depth * math.log(db_size + 1))
    
    def recursive_descent(self, 
                         event: Dict[str, Any], 
                         db_events_keys: List[str], 
                         last_distances: Optional[List[Tuple[float, Dict]]], 
                         depth: int = 0) -> Optional[Dict[str, Any]]:
        """
        Perform recursive descent to find nearest neighbor.
        
        Args:
            event: Query event
            db_events_keys: List of keys to search
            last_distances: Previous iteration's distances
            depth: Current recursion depth
            
        Returns:
            Best matching event or None
        """
        self.recursive_steps += 1
        
        if not db_events_keys:
            return None
            
        # Fetch events from S3 (this is the expensive operation)
        db_events = []
        for key in db_events_keys:
            db_event = self.get(str(key))
            if db_event:
                db_events.append(db_event)
        
        if not db_events:
            return None
        
        # Calculate distances
        distances = []
        for db_event in db_events:
            dist = self.distance_function(event, db_event)
            if dist is not None:
                distances.append((dist, db_event))
        
        if not distances:
            return None
        
        # Sort by distance
        distances.sort(key=lambda x: x[0])
        
        best_match = distances[0][1]
        new_best_distance = distances[0][0]
        
        # Update dynamic stopping criteria
        self.update_stopping_criteria(len(db_events_keys), depth)
        
        # Check stopping conditions
        if new_best_distance < self.stopping_criteria:
            self.stopping_criteria_hits += 1
            return best_match
        elif last_distances and new_best_distance > last_distances[0][0]:
            # Distance is getting worse, return previous best
            return event
        else:
            # Continue searching with nearest neighbors
            num_neighbors_to_check = min(5 + depth, len(distances))
            next_keys = []
            
            # Extract keys from the nearest neighbors
            for _, db_event in distances[:num_neighbors_to_check]:
                if 'id' in db_event:
                    next_keys.append(db_event['id'])
            
            return self.recursive_descent(event, next_keys, distances, depth + 1)
    
    def get_by_event(self, event: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], int]:
        """
        Find nearest neighbor for given event.
        
        Args:
            event: Query event with features
            
        Returns:
            Tuple of (best matching event, number of recursive steps)
        """
        self.recursive_steps = 0
        self.stopping_criteria_hits = 0
        result = self.recursive_descent(event, self.candles, last_distances=None)
        return result, self.recursive_steps
    
    def insert_event(self, event: Dict[str, Any]) -> bool:
        """
        Insert event into database with automatic ID generation if needed.
        
        Args:
            event: Event to insert (must have 'features' field)
            
        Returns:
            True if successful, False otherwise
        """
        if 'id' not in event:
            event['id'] = str(uuid.uuid4())
        
        if 'features' not in event:
            logger.error("Event must have 'features' field")
            return False
        
        success = self.set(event['id'], event)
        
        # Update candles to include this new event
        if success and event['id'] not in self.candles:
            if len(self.candles) >= self.CANDLE_LEN:
                # Remove oldest candle
                self.candles.pop(0)
            self.candles.append(event['id'])
            self._save_candles()
        
        return success
    
    def list_all_keys(self, max_keys: int = 1000) -> List[str]:
        """
        List all asset keys in the database.
        
        Args:
            max_keys: Maximum number of keys to return
            
        Returns:
            List of asset keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=self.assets_prefix,
                MaxKeys=max_keys
            )
            
            keys = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Extract key from S3 path
                    full_key = obj['Key']
                    if full_key.startswith(self.assets_prefix + '/') and full_key.endswith('.json'):
                        key = full_key[len(self.assets_prefix) + 1:-5]  # Remove prefix and .json
                        keys.append(key)
            
            return keys
            
        except ClientError as e:
            logger.error(f"Error listing keys: {e}")
            return []
    
    def get_asset_url(self, key: str) -> str:
        """
        Get the public URL for an asset.
        
        Args:
            key: Asset key
            
        Returns:
            Public S3 URL for the asset
        """
        return f"{self.base_url}/assets/{key}.json"
    
    def batch_get(self, keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve multiple objects from S3.
        
        Args:
            keys: List of keys to retrieve
            
        Returns:
            Dictionary mapping keys to their data
        """
        results = {}
        for key in keys:
            data = self.get(key)
            if data:
                results[key] = data
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the database.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Test S3 connectivity
            self.s3_client.head_bucket(Bucket=self.bucket)
            
            # Get candles status
            candles_count = len(self.candles)
            
            # Count total objects (limited check)
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=self.assets_prefix,
                MaxKeys=1
            )
            has_objects = 'Contents' in response and len(response['Contents']) > 0
            
            return {
                'status': 'healthy',
                'bucket': self.bucket,
                'prefix': self.prefix,
                'candles_count': candles_count,
                'has_objects': has_objects,
                'feature_dimension': self.FEATURE_D
            }
            
        except ClientError as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'bucket': self.bucket
            }


# Helper function to convert arbitrary data to features
def event_to_features(event: Dict[str, Any], feature_dim: int = 8) -> List[float]:
    """
    Convert event data to feature vector using hashing.
    
    Args:
        event: Event data
        feature_dim: Target feature dimension
        
    Returns:
        Feature vector
    """
    features = []
    
    for key, value in sorted(event.items()):
        if key == 'features':  # Skip if already has features
            continue
            
        if isinstance(value, (int, float)):
            features.append(float(value))
        elif isinstance(value, str):
            # Hash string to number between 0 and 1
            features.append((hash(value) % 1000) / 1000)
        elif isinstance(value, bool):
            features.append(1.0 if value else 0.0)
    
    # Pad or truncate to match feature dimension
    while len(features) < feature_dim:
        features.append(0.0)
    
    return features[:feature_dim]