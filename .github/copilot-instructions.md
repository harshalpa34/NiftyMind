<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# NiftyMind GenAI Project Instructions

## Project Overview
NiftyMind is a full-stack GenAI application with:
- **Backend**: FastAPI with Python 3.11+ async runtime
- **Frontend**: Next.js 14 with React 18 and TypeScript

## Development Setup

### Backend (Python)
- Location: `./backend/`
- Runtime: Python 3.11+
- Package Manager: pip
- Virtual Environment: `./backend/venv/`

To start:
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python main.py
```

### Frontend (Next.js)
- Location: `./frontend/`
- Runtime: Node.js
- Package Manager: npm
- Port: 3000

To start:
```bash
cd frontend
npm install
npm run dev
```

## Technology Stack

### Backend
- FastAPI (modern async web framework)
- Uvicorn (ASGI server)
- Pydantic with pydantic-settings (type-safe configuration)
- httpx (async HTTP client)
- python-dotenv (environment management)

### Frontend
- Next.js 14 (App Router)
- React 18
- TypeScript
- CSS Modules

## Key Files & Directories

### Backend
- `backend/main.py` - FastAPI application entry point
- `backend/app/config.py` - Settings management with Pydantic
- `backend/app/routes.py` - API route handlers
- `backend/.env.example` - Environment template
- `backend/requirements.txt` - Python dependencies

### Frontend
- `frontend/src/app/page.tsx` - Home page component
- `frontend/src/lib/api-client.ts` - HTTP client for backend communication
- `frontend/next.config.ts` - Next.js configuration
- `frontend/package.json` - Dependencies and scripts

## API Communication

Frontend calls backend via `ApiClient` in `src/lib/api-client.ts`:
- Default API URL: `http://localhost:8000`
- Configure via `NEXT_PUBLIC_API_URL` in `.env.local`

## CORS Configuration

Backend is pre-configured for frontend at:
- `http://localhost:3000` (default Next.js)
- `http://localhost:3001` (alternative)

Update `CORS_ORIGINS` in backend `.env` to add more.

## Development Guidelines

1. **Python Code**: Follow PEP 8, use type hints
2. **React Components**: Use functional components with TypeScript
3. **API Routes**: Add endpoints in `backend/app/routes.py` with type hints
4. **Environment Variables**: Use `.env` files, never commit secrets

## Common Commands

### Backend
- `python main.py` - Start dev server with auto-reload
- `uvicorn main:app --reload` - Alternative start command

### Frontend  
- `npm run dev` - Start dev server
- `npm run build` - Build for production
- `npm run type-check` - Validate TypeScript

## Debugging

- Backend API docs: `http://localhost:8000/docs`
- Frontend debugging: Chrome DevTools (F12)
- Network tab: Check API requests/responses

## Project is ready for GenAI development with:
- Async/await for high-performance I/O
- Type safety across full stack
- Environment management for API keys
- HTTP client configured for external services
