from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
print('stats_before', client.get('/api/v1/rag/stats').json())
resp = client.post('/api/v1/rag/ingest', json={'directory':'data/transcripts'})
print('ingest status', resp.status_code)
print('ingest body', resp.json())
if resp.status_code == 201:
    q = client.post('/api/v1/rag/query', json={'question':'What is the key result of the quarter?','top_k':1})
    print('query status', q.status_code)
    print('query body', q.json())
