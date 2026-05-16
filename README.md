# NiftyMind - GenAI Application

A modern full-stack GenAI application built with:
- **Backend**: FastAPI (Python 3.11+) with async/await
- **Frontend**: Next.js 14 with React 18 and TypeScript

## Project Structure

```
NiftyMind/
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py       # Settings management
│   │   └── routes.py       # API routes
│   ├── main.py             # FastAPI application
│   ├── requirements.txt
│   ├── .env.example
│   ├── .gitignore
│   └── README.md
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # Next.js App Router
│   │   ├── components/    # React components
│   │   ├── lib/          # Utilities (API client, etc.)
│   │   └── public/       # Static assets
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   ├── .gitignore
│   └── README.md
├── .github/               # GitHub configuration
└── README.md             # This file
```

## Getting Started

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` from `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Run the development server:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create `.env.local`:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```

The application will be available at `http://localhost:3000`

## Tech Stack

### Backend
- **Python 3.11+** - Runtime with improved asyncio performance
- **FastAPI** - Modern async web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation with `pydantic-settings`
- **httpx** - Async HTTP client
- **python-dotenv** - Environment variable management

### Frontend
- **Next.js 14** - React framework with App Router
- **React 18** - UI library
- **TypeScript** - Type-safe development
- **CSS Modules** - Component-scoped styling

## Development Workflow

### Start Backend
```bash
cd backend
python main.py
```

### Start Frontend
```bash
cd frontend
npm run dev
```

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Available Endpoints

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### API Info
```bash
curl http://localhost:8000/
```

## Environment Variables

### Backend (.env)
See [backend/.env.example](backend/.env.example)

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Building for Production

### Backend
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend
```bash
cd frontend
npm run build
npm start
```

## Project Features

✨ **Modern Stack**
- Fully async Python backend with FastAPI
- Next.js 14 with App Router
- Type-safe across full stack (Python type hints + TypeScript)

🚀 **Developer Experience**
- Hot reload for both backend and frontend
- Interactive API documentation
- Environment variable management
- CORS already configured

🔌 **Ready for GenAI**
- Pre-configured for API integration
- Async HTTP client for external API calls
- Extensible architecture

## Next Steps

1. **Extend Routes**: Add your API endpoints in `backend/app/routes.py`
2. **Add Components**: Create React components in `frontend/src/components/`
3. **Connect to AI Services**: Use `httpx` for async calls to OpenAI, Anthropic, etc.
4. **Add Database**: Integrate SQLAlchemy or another ORM in the backend
5. **Deploy**: Choose your hosting (Vercel for frontend, Render/AWS for backend)

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)

## License

MIT

## Support

For issues or questions, refer to the individual README files in the `backend/` and `frontend/` directories.
