"""Script to clear all documents in a ChromaDB collection without deleting the collection."""
import os
import chromadb
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

chroma_host = os.environ.get("CHROMA_HOST", "localhost")
chroma_port = int(os.environ.get("CHROMA_PORT", 8000))
collection_name = os.environ.get("CHROMA_COLLECTION_NAME", "collection")

print(f"Connecting to ChromaDB at {chroma_host}:{chroma_port}...")
client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

try:
    collection = client.get_collection(name=collection_name)
    print(f"Found collection: {collection_name}")
    
    # Get all items in the collection
    results = collection.get()
    ids = results.get("ids", [])
    
    if ids:
        print(f"Deleting {len(ids)} chunks from collection...")
        # delete by IDs
        collection.delete(ids=ids)
        print("Success! Collection cleared.")
    else:
        print("Collection is already empty.")
        
except Exception as e:
    print(f"Error: {e}")
