import os
import logging
import chromadb
from chromadb.config import Settings
import config

logger = logging.getLogger("core.vector_db")

def get_chroma_client():
    # Try HTTP Client if host is configured
    host = getattr(config, "CHROMADB_HOST", "localhost")
    port = getattr(config, "CHROMADB_PORT", 8000)
    
    # Check if remote Chroma server is reachable
    try:
        http_client = chromadb.HttpClient(host=host, port=port, settings=Settings(anonymized_telemetry=False))
        http_client.heartbeat()
        logger.info(f"Connected to remote ChromaDB at {host}:{port}")
        return http_client
    except Exception as e:
        logger.info(f"ChromaDB remote server ({host}:{port}) unavailable ({e}). Using local PersistentClient.")

    # Fallback to local PersistentClient
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_data")
    os.makedirs(db_path, exist_ok=True)
    return chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))

client = get_chroma_client()

def get_or_create_collection(name: str = "ftse_job_listings"):
    return client.get_or_create_collection(name=name)
