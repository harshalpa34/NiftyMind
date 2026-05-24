import chromadb
from chromadb.utils.embedding_functions.chroma_langchain_embedding_function import create_langchain_embedding
from app.rag.embeddings import get_embeddings

client = chromadb.PersistentClient(path='data/chroma_db_direct_test')
langchain_embed = get_embeddings()
embedding_function = create_langchain_embedding(langchain_embed)
collection = client.get_or_create_collection(name='test_collection', embedding_function=embedding_function)
print('collection created', collection.name)
ids = ['a', 'b']
docs = ['hello world', 'goodbye world']
metadatas = [{'source':'test','chunk_id':'a'},{'source':'test','chunk_id':'b'}]
print('computing embeddings...')
embs = embedding_function(docs)
print('embs type', type(embs), 'len', len(embs), 'first type', type(embs[0]), 'first len', len(embs[0]))
try:
    collection.upsert(ids=ids, embeddings=embs, metadatas=metadatas, documents=docs)
    print('explicit upsert done', collection.count())
except Exception:
    print('explicit upsert failed')
    import traceback
    traceback.print_exc()
