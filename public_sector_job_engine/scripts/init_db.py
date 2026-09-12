import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import init_db

if __name__ == "__main__":
    print("Initializing Database...")
    init_db()
    print("Database Initialized.")
