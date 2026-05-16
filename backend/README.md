# NiftyMind GenAI Backend

Modern async Python backend for GenAI applications.

## Quick Start

### 1. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

### 3. Run the Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### 4. Access API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py       # Settings and configuration
│   └── routes.py       # API routes
├── main.py            # FastAPI application entry point
├── requirements.txt   # Python dependencies
├── .env.example      # Example environment variables
└── .gitignore
```

## Tech Stack

- **Python 3.11+** - Runtime with significant asyncio improvements
- **FastAPI** - Modern async web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation
- **httpx** - Async HTTP client
- **python-dotenv** - Environment variable management

## Development

### Install in editable mode with dev dependencies

```bash
pip install -e ".[dev]"
```

### Run with auto-reload

```bash
uvicorn main:app --reload
```

### Environment Variables

See `.env.example` for all available configuration options.

## API Endpoints

- `GET /` - Root endpoint with API info
- `GET /api/v1/health` - Health check
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

## CORS Configuration

The backend is configured to accept requests from:
- `http://localhost:3000` (Default Next.js port)
- `http://localhost:3001` (Alternative frontend port)

Update `CORS_ORIGINS` in `.env` to add more origins.

## Adding New Routes

1. Create a new router file in the `app/` directory
2. Import and include it in `main.py`:

```python
from app.new_router import router as new_router
app.include_router(new_router)
```

## Production Deployment

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

For production, set `DEBUG=false` in your `.env` file.
