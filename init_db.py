"""
Database initialization script - creates collections and indexes
"""
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/connecther'))
db = client['connecther']

# Create collections if they don't exist
collections = ['users', 'communities', 'memberships', 'posts', 'comments']

for collection_name in collections:
    if collection_name not in db.list_collection_names():
        db.create_collection(collection_name)
        print(f"✓ Created collection: {collection_name}")
    else:
        print(f"✓ Collection already exists: {collection_name}")

# Create indexes for better performance
db.users.create_index('email', unique=True)
db.users.create_index('cnic', unique=True)
db.communities.create_index('name')
db.memberships.create_index([('user_id', 1), ('community_id', 1)], unique=True)
db.posts.create_index('community_id')
db.posts.create_index('date_posted')

print("\n✓ All collections and indexes created successfully!")
print("✓ Your MongoDB database is ready to use!")
