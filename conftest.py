import os

# Set required env vars before any neonbot imports
os.environ.setdefault('TOKEN', 'test-token-for-testing')
os.environ.setdefault('MONGO_DB_HOST', 'localhost')
os.environ.setdefault('MONGO_DB_NAME', 'test_db')
