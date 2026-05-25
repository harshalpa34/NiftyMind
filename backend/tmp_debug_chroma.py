import chromadb
from chromadb.utils import embedding_functions
import os
os.environ["GOOGLE_API_KEY"] = ""  # will read from config

# Load config
import sys
sys.path.insert(0, ".")
from app.config import get_settings
settings = get_settings()

# Connect to existing ChromaDB
client = chromadb.PersistentClient(path="data/chroma_db")

# List all collections
print("Collections:", client.list_collections())

# Connect to collection
embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key=settings.gemini_api_key,
    model_name="models/text-embedding-004"
)

collection = client.get_collection(
    name="earnings_transcripts",
    embedding_function=embedding_fn
)

print(f"Total vectors: {collection.count()}")

# Peek at stored data
peek = collection.peek(limit=3)
print("\nSample documents:")
for i, doc in enumerate(peek["documents"]):
    print(f"\n[{i}] {doc[:100]}...")
    print(f"    Metadata: {peek['metadatas'][i]}")

# Try raw query
print("\n--- Raw Query Test ---")
results = collection.query(
    query_texts=["What are the operating margins?"],
    n_results=3,
    include=["documents", "metadatas"]
)
print(f"Results found: {len(results['documents'][0])}")
for i, doc in enumerate(results["documents"][0]):
    print(f"\n[{i}] {doc[:150]}...")