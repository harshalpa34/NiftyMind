import sys
sys.path.insert(0, ".")

from app.rag.document_loader import load_transcripts, chunk_documents

# Step 1 — Load documents
docs = load_transcripts("data/transcripts")
print(f"Documents loaded: {len(docs)}")
for d in docs:
    print(f"  - {d.metadata.get('company')} | chars: {len(d.page_content)}")

# Step 2 — Chunk documents
chunks = chunk_documents(docs)
print(f"\nChunks generated: {len(chunks)}")

# Step 3 — Check for duplicate chunk_ids (this is the bug)
ids = [c.metadata.get("chunk_id", f"NO_ID_{i}") for i, c in enumerate(chunks)]
print(f"\nChunk IDs:")
for i, (chunk, cid) in enumerate(zip(chunks, ids)):
    print(f"  [{i}] id={cid} | chars={len(chunk.page_content)}")

# Check for duplicates
duplicates = len(ids) - len(set(ids))
if duplicates > 0:
    print(f"\n❌ FOUND {duplicates} DUPLICATE IDs — this is the bug!")
    print("   Pinecone upsert overwrites same IDs → only 1 vector stored")
else:
    print(f"\n✅ All {len(ids)} chunk IDs are unique")