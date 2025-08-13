import json
from tqdm import tqdm  # For progress bar, optional but helpful for large files
import uuid
import sys
from database import JSONDatabase

db = JSONDatabase(
    bucket="mithrilmedia",  # Use your actual bucket
    prefix="mtg-cards",     # Custom prefix for MtG data
    distance_method="custom",  # Or "euclidean" if you add feature vectors
    feature_dim=16,         # Increase if using euclidean for more card attributes
    index_size=1000,        # Larger index for better search coverage on many cards
    similarity_threshold=0.2  # Adjust based on testing
)

with open(sys.argv[1]) as fin:
    _all = json.load(fin)
print(len(_all))

for card in _all[0:100]:
    obj_id = card.get('oracle_id') or card.get('name', str(uuid.uuid4())).replace(' ', '_').lower()
    db.insert(card, obj_id=obj_id)

print('all done')
