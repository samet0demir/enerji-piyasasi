
import os
import sys
from dotenv import load_dotenv

# Get the absolute path to the backend directory
# This assumes this script is in backend/src/ml/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
ENV_PATH = os.path.join(BACKEND_DIR, '.env')

# Load .env file
load_dotenv(ENV_PATH)

def get_db_path():
    """
    Get the absolute path to the database based on .env configuration.
    Falls back to 'data/energy.db' if DB_PATH is not set.
    """
    # Get relative path from env or default
    db_path_rel = os.getenv('DB_PATH', 'data/energy.db')
    
    # Construct absolute path
    # If it's already absolute, join ignores the start path
    db_path = os.path.join(BACKEND_DIR, db_path_rel)
    
    return os.path.normpath(db_path)

DB_PATH = get_db_path()

if __name__ == "__main__":
    print(f"Database Path: {DB_PATH}")
