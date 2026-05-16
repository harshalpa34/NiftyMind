# NiftyMind GenAI Frontend

Modern React frontend built with Next.js 14 for GenAI applications.

## Quick Start

### 1. Install Dependencies

```bash
npm install
# or
yarn install
# or
pnpm install
```

### 2. Configure Environment

Create a `.env.local` file:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx      # Root layout
│   │   ├── page.tsx        # Home page
│   │   ├── globals.css     # Global styles
│   │   └── page.module.css # Page styles
│   ├── components/         # Reusable React components
│   ├── lib/
│   │   └── api-client.ts   # API client utilities
│   └── public/             # Static assets
├── next.config.ts          # Next.js configuration
├── tsconfig.json           # TypeScript configuration
├── package.json
└── .gitignore
```

## Tech Stack

- **Next.js 14** - React framework with App Router
- **React 18** - UI library
- **TypeScript** - Type-safe development
- **CSS Modules** - Component-scoped styling

## Environment Variables

Create a `.env.local` file in the `frontend/` directory:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Type check with TypeScript

## API Integration

The `ApiClient` in `src/lib/api-client.ts` provides methods for API communication:

```typescript
import { ApiClient } from '@/lib/api-client';

// GET request
const data = await ApiClient.get<HealthStatus>('/api/v1/health');

// POST request
const result = await ApiClient.post<Response>('/api/v1/data', { /* payload */ });
```

## Components

The `src/components/` directory is for reusable React components. Example:

```typescript
// src/components/Header.tsx
export default function Header() {
  return <header>...</header>;
}
```

## Styling

- Global styles: `src/app/globals.css`
- Component styles: Use CSS Modules (`.module.css`)
- Inline styles: Use CSS-in-JS if needed

## Connecting to Backend

Make sure your FastAPI backend is running on `http://localhost:8000`. Update `NEXT_PUBLIC_API_URL` in `.env.local` if using a different port.

Example API call:

```typescript
useEffect(() => {
  const fetchData = async () => {
    try {
      const response = await ApiClient.get('/api/v1/health');
      console.log(response);
    } catch (error) {
      console.error('API error:', error);
    }
  };
  
  fetchData();
}, []);
```

## Production

Before deploying:

1. Build the project: `npm run build`
2. Test production build: `npm start`
3. Ensure `NEXT_PUBLIC_API_URL` is correctly set for your production backend
4. Deploy to your preferred hosting (Vercel, AWS, etc.)

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
