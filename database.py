import json
import math
import uuid
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Tuple, Optional, Any, Set, Callable
import logging
import heapq
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def json_distance(obj1: Any, obj2: Any) -> float:
    """
    Calculate distance between two arbitrary JSON objects.
    Returns a value between 0.0 (identical) and 1.0 (completely different).
    """
    # 1. Type mismatch
    if type(obj1) != type(obj2):
        return 1.0
    
    # 2. None handling
    if obj1 is None:
        return 0.0 if obj2 is None else 1.0
    
    # 3. Dictionaries
    if isinstance(obj1, dict):
        keys1 = set(obj1.keys())
        keys2 = set(obj2.keys())
        all_keys = keys1 | keys2
        
        if not all_keys:
            return 0.0
            
        # Jaccard-like penalty for key mismatch
        intersection = keys1 & keys2
        union = keys1 | keys2
        key_dist = 1.0 - (len(intersection) / len(union))
        
        # Recursive value distance for shared keys
        val_dists = []
        for k in all_keys:
            # Skip metadata fields starting with _
            if k.startswith('_'):
                continue
                
            v1 = obj1.get(k)
            v2 = obj2.get(k)
            if v1 is not None and v2 is not None:
                val_dists.append(json_distance(v1, v2))
            else:
                # One is missing -> max distance for this field
                val_dists.append(1.0)
        
        if not val_dists:
            return key_dist
            
        avg_val_dist = sum(val_dists) / len(val_dists)
        
        # Combine structural difference and value difference
        return 0.4 * key_dist + 0.6 * avg_val_dist

    # 4. Lists
    if isinstance(obj1, list):
        if not obj1 and not obj2:
            return 0.0
        if not obj1 or not obj2:
            return 1.0
            
        # Length difference penalty
        len_diff = abs(len(obj1) - len(obj2)) / max(len(obj1), len(obj2))
        
        # Compare first N elements (order matters for this simple version)
        limit = min(len(obj1), len(obj2))
        item_dists = []
        for i in range(limit):
            item_dists.append(json_distance(obj1[i], obj2[i]))
            
        avg_item_dist = sum(item_dists) / len(item_dists) if item_dists else 0.0
        
        return 0.3 * len_diff + 0.7 * avg_item_dist

    # 5. Strings
    if isinstance(obj1, str):
        if obj1 == obj2:
            return 0.0
        # Simple case-insensitive containment or Levenshtein approximation
        s1, s2 = obj1.lower(), obj2.lower()
        if s1 == s2:
            return 0.0
        if s1 in s2 or s2 in s1:
            return 0.3
        return 1.0

    # 6. Numbers
    if isinstance(obj1, (int, float)):
        if obj1 == obj2:
            return 0.0
        diff = abs(obj1 - obj2)
        # Normalize by sum (avoid div by zero)
        denom = abs(obj1) + abs(obj2)
        if denom == 0:
            return 0.0
        return diff / denom

    # 7. Booleans
    if isinstance(obj1, bool):
        return 0.0 if obj1 == obj2 else 1.0

    return 1.0


class BallTreeNode:
    def __init__(self, centroid: Dict, radius: float, left=None, right=None, items: List[Dict] = None):
        self.centroid = centroid
        self.radius = radius
        self.left = left
        self.right = right
        self.items = items or []  # Leaf nodes contain data items

    def is_leaf(self):
        return self.left is None and self.right is None

    def to_dict(self):
        """Serialize node to dictionary for JSON storage."""
        return {
            "centroid": self.centroid,
            "radius": self.radius,
            "is_leaf": self.is_leaf(),
            "items": self.items if self.is_leaf() else [],
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize node from dictionary."""
        if not data:
            return None
        
        node = cls(
            centroid=data["centroid"],
            radius=data["radius"],
            items=data.get("items", [])
        )
        
        if not data.get("is_leaf"):
            node.left = cls.from_dict(data["left"])
            node.right = cls.from_dict(data["right"])
            
        return node


class BallTree:
    def __init__(self, leaf_size=5):
        self.root = None
        self.leaf_size = leaf_size

    def build(self, data_objects: List[Dict]):
        """Build the tree from a list of JSON objects."""
        if not data_objects:
            self.root = None
            return
        self.root = self._build_recursive(data_objects)

    def _build_recursive(self, objects: List[Dict]) -> BallTreeNode:
        # Base case: Create leaf node
        if len(objects) <= self.leaf_size:
            # Pick the first object as representative centroid for the leaf
            centroid = objects[0]
            # Radius is max distance from centroid to any object in leaf
            radius = max([json_distance(centroid, obj) for obj in objects]) if len(objects) > 1 else 0
            return BallTreeNode(centroid=centroid, radius=radius, items=objects)

        # Recursive step: Split data
        # 1. Pick a random pivot A
        pivot_a = random.choice(objects)
        
        # 2. Find pivot B (farthest from A)
        pivot_b = max(objects, key=lambda o: json_distance(pivot_a, o))
        
        # 3. Find real pivot A (farthest from B) to maximize spread
        pivot_a = max(objects, key=lambda o: json_distance(pivot_b, o))

        # 4. Split objects based on closeness to A or B
        set_a = []
        set_b = []
        
        for obj in objects:
            dist_a = json_distance(obj, pivot_a)
            dist_b = json_distance(obj, pivot_b)
            if dist_a < dist_b:
                set_a.append(obj)
            else:
                set_b.append(obj)
        
        # Edge case: If all points are identical or split failed, force split
        if not set_a or not set_b:
            mid = len(objects) // 2
            set_a = objects[:mid]
            set_b = objects[mid:]

        # 5. Create node
        # Centroid is pivot_a (arbitrary choice, can be improved)
        centroid = pivot_a
        # Radius covers ALL points in this subtree
        radius = max([json_distance(centroid, obj) for obj in objects])
        
        node = BallTreeNode(centroid=centroid, radius=radius)
        node.left = self._build_recursive(set_a)
        node.right = self._build_recursive(set_b)
        
        return node

    def search(self, query: Dict, k: int = 5) -> List[Tuple[float, Dict]]:
        """
        Search for k nearest neighbors.
        Returns list of (distance, object).
        """
        if not self.root:
            return []

        # Priority queue to store (negative_distance, unique_id, object)
        # We use unique_id as tiebreaker for non-comparable dicts
        heap = [] 
        
        self._search_recursive(self.root, query, k, heap)
        
        # Convert back to positive distances and sort
        # Heap items are (-d, id, item)
        results = [(-t[0], t[2]) for t in heap]
        results.sort(key=lambda x: x[0])
        return results

    def _search_recursive(self, node: BallTreeNode, query: Dict, k: int, heap: List):
        # Distance from query to node centroid
        dist_to_centroid = json_distance(query, node.centroid)
        
        # Pruning:
        # If the heap is full (has k items), let 'worst_dist' be the largest distance in the heap.
        # Lower bound distance to any point in this ball is (dist_to_centroid - node.radius).
        # If (dist_to_centroid - node.radius) >= worst_dist, we can prune this node.
        
        worst_dist = -heap[0][0] if len(heap) == k else float('inf')
        
        if dist_to_centroid - node.radius >= worst_dist:
            return

        # If leaf, check all items
        if node.is_leaf():
            for item in node.items:
                d = json_distance(query, item)
                # Use id(item) as tiebreaker since dicts aren't comparable
                entry = (-d, id(item), item)
                
                if len(heap) < k:
                    heapq.heappush(heap, entry)
                elif d < worst_dist:
                    heapq.heappushpop(heap, entry)
                    worst_dist = -heap[0][0]
        else:
            # Visit children. Order matters for performance: visit closer child first.
            # Distance to left child's region vs right child's region isn't known perfectly without checking centroids
            # But we can guess based on centroid distance? Actually, we just check both, but order helps pruning.
            
            # Simple heuristic: check distance to child centroids
            dist_left = json_distance(query, node.left.centroid)
            dist_right = json_distance(query, node.right.centroid)
            
            first, second = (node.left, node.right) if dist_left < dist_right else (node.right, node.left)
            
            self._search_recursive(first, query, k, heap)
            
            # Re-check pruning condition before visiting second child, as heap might have improved
            worst_dist = -heap[0][0] if len(heap) == k else float('inf')
            
            # Triangle inequality check again for the second child
            # (We do this inside the recursive call, but checking here saves a stack frame)
            dist_to_second_centroid = dist_left if first == node.right else dist_right
            radius_second = second.radius
            
            if dist_to_second_centroid - radius_second < worst_dist:
                 self._search_recursive(second, query, k, heap)


class JSONDatabase:
    """S3-backed JSON database using Ball Tree indexing."""
    
    def __init__(self, bucket: str = "mithrilmedia", prefix: str = "OpenGameAssetLibrary"):
        self.bucket = bucket
        self.prefix = prefix
        self.assets_prefix = f"{prefix}/assets"
        self.index_key = f"{prefix}/index.json"
        self.s3_client = boto3.client('s3')
        self.tree = BallTree()
        
        # Try to load existing index
        self.load_index()

    def load_index(self):
        """Load the Ball Tree index from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=self.index_key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            self.tree.root = BallTreeNode.from_dict(data)
            logger.info("Index loaded successfully.")
        except ClientError as e:
            logger.info(f"No existing index found or error loading: {e}")
            self.tree.root = None

    def save_index(self):
        """Save the Ball Tree index to S3."""
        if not self.tree.root:
            return
        try:
            data = self.tree.root.to_dict()
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=self.index_key,
                Body=json.dumps(data),
                ContentType='application/json'
            )
            logger.info("Index saved successfully.")
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def rebuild_index(self):
        """Fetch all assets from S3 and rebuild the Ball Tree."""
        logger.info("Rebuilding index from S3 assets...")
        assets = []
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket, Prefix=self.assets_prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if key.endswith('.json'):
                            # Fetch object body
                            try:
                                resp = self.s3_client.get_object(Bucket=self.bucket, Key=key)
                                asset = json.loads(resp['Body'].read().decode('utf-8'))
                                assets.append(asset)
                            except Exception as err:
                                logger.warning(f"Failed to read {key}: {err}")
            
            logger.info(f"Fetched {len(assets)} assets. Building tree...")
            self.tree.build(assets)
            self.save_index()
            logger.info("Index rebuild complete.")
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")

    def insert(self, asset: Dict):
        """Insert a new asset (updates S3 and local tree, saves index)."""
        asset_id = asset.get("id") or str(uuid.uuid4())
        asset["id"] = asset_id
        
        key = f"{self.assets_prefix}/{asset_id}.json"
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(asset, indent=2),
                ContentType='application/json'
            )
            # For a Ball Tree, insertion is complex (balancing). 
            # For this demo, we'll just trigger a rebuild if it's small, 
            # or lazily handle it. 
            # Let's just rebuild for now as it ensures correctness.
            # Optimization: In real world, we'd append to a buffer and batch rebuild.
            self.rebuild_index()
            return asset_id
        except Exception as e:
            logger.error(f"Error inserting asset: {e}")
            raise

    def search(self, query: Dict, k: int = 5):
        """Search for similar assets."""
        return self.tree.search(query, k)
