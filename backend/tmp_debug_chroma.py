import traceback
from app.rag.document_loader import load_transcripts, chunk_documents
from app.rag.vector_store import vector_store
import chromadb

print('chromadb version:', chromadb.__version__)
docs = load_transcripts('data/transcripts')
print('docs', len(docs))
chunks = chunk_documents(docs)
print('chunks', len(chunks))
ids = [c.metadata.get('chunk_id', f'chunk_{i}') for i, c in enumerate(chunks)]
documents = [c.page_content for c in chunks]
metadatas = [c.metadata for c in chunks]
print('lens', len(ids), len(documents), len(metadatas))
print('sample ids', ids[:3])
print('sample meta', metadatas[0])
vector_store._initialize()
print('initialized collection')
print('embedding function type:', type(vector_store._collection._embedding_function))
try:
    emb = vector_store._collection._embedding_function(['hello', 'world'])
    print('embedding output type:', type(emb))
    print('embedding count:', len(emb))
    print('embedding first item type:', type(emb[0]))
    print('embedding first item length:', len(emb[0]))
except Exception:
    print('embedding function failed:')
    traceback.print_exc()

try:
    print('attempting explicit embeddings upsert')
    explicit_embeddings = [list(map(float, emb[0])), list(map(float, emb[1]))] if 'emb' in locals() else [[0.0]*3072, [0.0]*3072]
    vector_store._collection.upsert(ids=ids[:2], embeddings=explicit_embeddings, metadatas=metadatas[:2], documents=documents[:2])
    print('explicit upsert success', vector_store._collection.count())
except Exception:
    print('explicit upsert failed:')
    traceback.print_exc()
