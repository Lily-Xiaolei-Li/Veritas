# Agent B Research - Frontend

React/Next.js frontend for Agent B's Cognitive Workbench, providing a three-panel resizable interface for interacting with autonomous AI agents.

## Overview

This is the frontend implementation for **Agent B Milestone B1.0 - Workbench Shell**. It provides a modern, responsive web interface with:

- **Three-panel resizable layout**: Reasoning (left), Artifacts (top-right), Console (bottom-right)
- **Backend health monitoring**: Real-time connection status to FastAPI backend
- **Type-safe API client**: Full TypeScript integration with backend models
- **State management**: Zustand stores with localStorage persistence
- **Future-ready**: Prepared for SSE streaming (B1.1), chat interface (B1.1), and file outputs (B1.3)

## Technology Stack

- **Next.js 14.2.13** - React framework with App Router
- **React 18.2.0** - UI library
- **TypeScript** - Type safety and developer experience
- **Tailwind CSS 3.4.0** - Utility-first styling
- **react-resizable-panels 2.x** - Performant panel resizing
- **Zustand 4.5.0** - Lightweight state management
- **TanStack Query 5.x** - Data fetching and caching
- **Lucide React** - Icon library

## Quick Start

### Prerequisites

- Node.js 18+ installed
- Backend running on `http://localhost:8000` (see root README.md)

### Installation

```bash
# From the frontend directory
npm install

# Or from the root directory
make frontend-install
```

### Environment Configuration

Create `.env.local` from the example:

```bash
cp .env.local.example .env.local
```

Default configuration:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_PATH=/api/v1
NEXT_PUBLIC_DEFAULT_SESSION_ID=hardcoded-session-001
NEXT_PUBLIC_ENABLE_AUTH=false
```

### Development

```bash
# Start development server (from frontend directory)
npm run dev

# Or from root directory
make frontend-dev

# Access the UI
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Production Build

```bash
# Build for production
npm run build

# Or from root directory
make frontend-build

# Start production server
npm start
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Build optimized production bundle |
| `npm start` | Start production server |
| `npm run lint` | Run ESLint code linter |
| `npm test` | Run tests with Vitest |
| `npm run test:watch` | Run tests in watch mode |
| `npm run test:coverage` | Generate test coverage report |

Or use Makefile commands from root directory:

| Command | Description |
|---------|-------------|
| `make frontend-install` | Install dependencies |
| `make frontend-dev` | Start development server |
| `make frontend-build` | Build for production |
| `make frontend-test` | Run tests |
| `make frontend-lint` | Lint code |
| `make frontend-clean` | Clean build artifacts |

## Project Structure

```
frontend/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx                # Root layout with providers
│   │   ├── page.tsx                  # Main workbench page
│   │   ├── globals.css               # Global styles
│   │   └── providers.tsx             # React Query provider setup
│   │
│   ├── components/
│   │   ├── workbench/                # Main workbench components
│   │   │   ├── WorkbenchLayout.tsx   # Three-panel resizable layout
│   │   │   ├── ReasoningPanel.tsx    # Left panel (chat - B1.1)
│   │   │   ├── ArtifactsPanel.tsx    # Top-right (files - B1.3)
│   │   │   └── ConsolePanel.tsx      # Bottom-right (logs - B1.1)
│   │   │
│   │   ├── health/                   # Health monitoring
│   │   │   ├── HealthStatus.tsx      # Detailed health display
│   │   │   └── HealthIndicator.tsx   # Status indicator badge
│   │   │
│   │   └── ui/                       # Reusable UI components
│   │       ├── Button.tsx
│   │       ├── Card.tsx
│   │       ├── Badge.tsx
│   │       └── ErrorBoundary.tsx
│   │
│   ├── lib/
│   │   ├── api/                      # API client layer
│   │   │   ├── client.ts             # Base fetch wrapper
│   │   │   ├── types.ts              # TypeScript API types
│   │   │   ├── health.ts             # Health endpoint
│   │   │   ├── sessions.ts           # Session CRUD
│   │   │   └── messages.ts           # Message operations
│   │   │
│   │   ├── hooks/                    # React hooks
│   │   │   ├── useHealth.ts          # Health monitoring hook
│   │   │   ├── useSession.ts         # Session management
│   │   │   └── useSSE.ts             # SSE streaming (B1.1)
│   │   │
│   │   ├── store/                    # Zustand state stores
│   │   │   ├── sessionStore.ts       # Session state
│   │   │   └── uiStore.ts            # UI preferences
│   │   │
│   │   └── utils/                    # Utilities
│   │       ├── cn.ts                 # Tailwind class merger
│   │       └── constants.ts          # App constants
│   │
│   └── types/                        # TypeScript definitions
│       ├── api.ts
│       ├── session.ts
│       └── index.ts
│
├── tests/                            # Test files (Vitest)
│   ├── components/
│   ├── lib/
│   └── setup.ts
│
├── .env.local.example                # Environment template
├── .env.local                        # Local environment (gitignored)
├── next.config.mjs                   # Next.js configuration
├── tailwind.config.ts                # Tailwind configuration
├── tsconfig.json                     # TypeScript configuration
├── vitest.config.ts                  # Vitest test configuration
└── package.json                      # Dependencies and scripts
```

## Architecture

### Component Hierarchy

```
page.tsx (Main Entry)
├── Header
│   ├── App Name & Version
│   └── HealthIndicator
│
└── WorkbenchLayout
    ├── ReasoningPanel (Left - 40% width)
    │   └── [Chat interface - B1.1]
    │
    └── RightSide (60% width)
        ├── ArtifactsPanel (Top - 60% height)
        │   └── [File outputs - B1.3]
        │
        └── ConsolePanel (Bottom - 40% height)
            └── [Logs and events - B1.1]
```

### State Management

**Session Store** (`sessionStore.ts`):
- Current session ID
- Message history
- Persisted to localStorage

**UI Store** (`uiStore.ts`):
- Panel sizes
- Theme preferences
- Persisted to localStorage

### API Integration

The frontend communicates with the FastAPI backend using a type-safe API client:

```typescript
// Example: Fetching health status
import { useHealth } from '@/lib/hooks/useHealth';

function MyComponent() {
  const { data, isLoading, error } = useHealth();

  if (isLoading) return <div>Checking health...</div>;
  if (error) return <div>Backend unavailable</div>;

  return <div>Status: {data.status}</div>;
}
```

**API Endpoints**:
- `GET /health` - Backend health check
- `GET /api/v1/sessions` - List sessions
- `POST /api/v1/sessions` - Create session
- `GET /api/v1/sessions/{id}` - Get session
- `POST /api/v1/sessions/{id}/messages` - Send message
- `GET /api/v1/sessions/{id}/stream` - SSE stream (B1.1)

### Panel Resizing

Panel sizes are managed by `react-resizable-panels` and persisted via the UI store:

```typescript
// Panels are resizable by dragging dividers
// Sizes automatically save to localStorage
// Default sizes: Reasoning 40%, Artifacts 60%, Console 40%
```

## Development Workflow

### Starting Both Servers

```bash
# Terminal 1: Start backend
cd Veritas
make dev

# Terminal 2: Start frontend
cd Veritas
make frontend-dev
```

Or use the combined command (displays instructions):
```bash
make dev-all
```

### Hot Reload

- Frontend changes auto-reload on save
- Backend changes auto-reload with `--reload` flag
- No manual restart needed during development

### Testing

```bash
# Run all tests
npm test

# Watch mode (auto-run on changes)
npm run test:watch

# Coverage report
npm run test:coverage
```

### Linting

```bash
# Check for issues
npm run lint

# Auto-fix issues
npm run lint -- --fix
```

## Component Documentation

### WorkbenchLayout

Three-panel resizable layout using `react-resizable-panels`.

**Props**: None

**Features**:
- Horizontal split: Reasoning (left) | Right panels
- Vertical split (right side): Artifacts (top) | Console (bottom)
- Draggable resize handles
- Minimum/maximum size constraints
- Auto-persists sizes to localStorage

### HealthIndicator

Visual health status indicator with optional label.

**Props**:
- `showLabel?: boolean` - Show status text (default: false)

**States**:
- Green circle: Backend healthy
- Yellow circle: Backend degraded
- Red circle: Backend unavailable
- Gray circle: Checking...

### Panel Components

**ReasoningPanel**: Placeholder for chat interface (B1.1)
**ArtifactsPanel**: Placeholder for file outputs (B1.3)
**ConsolePanel**: Placeholder for logs and events (B1.1)

All panels include:
- Header with title
- Scrollable content area
- Empty state with description

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |
| `NEXT_PUBLIC_API_BASE_PATH` | API path prefix | `/api/v1` |
| `NEXT_PUBLIC_DEFAULT_SESSION_ID` | Hardcoded session ID (B1.0) | `hardcoded-session-001` |
| `NEXT_PUBLIC_ENABLE_AUTH` | Enable authentication (B2.0+) | `false` |

**Note**: All environment variables must be prefixed with `NEXT_PUBLIC_` to be accessible in the browser.

## TypeScript Configuration

The project uses strict TypeScript with path aliases:

```typescript
// Import using @ alias
import { Button } from '@/components/ui/Button';
import { useHealth } from '@/lib/hooks/useHealth';

// Configured in tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

## Troubleshooting

### "Cannot connect to backend"

**Symptoms**: Red health indicator, "Backend unavailable" errors

**Solutions**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check backend logs for errors
3. Ensure CORS is enabled in backend `.env`: `CORS_ENABLED=true`
4. Verify `NEXT_PUBLIC_API_URL` in frontend `.env.local`

### Build errors with Tailwind

**Symptoms**: "Cannot apply unknown utility class"

**Solutions**:
1. Ensure Tailwind CSS 3.x is installed (not v4): `npm list tailwindcss`
2. Verify `postcss.config.mjs` uses `tailwindcss` plugin (not `@tailwindcss/postcss`)
3. Clear Next.js cache: `rm -rf .next`

### TypeScript errors

**Symptoms**: Type mismatches, import errors

**Solutions**:
1. Ensure types are up to date: `npm install --save-dev @types/react @types/node`
2. Restart TypeScript server in your editor
3. Check `tsconfig.json` includes all source files

### Panel sizes not persisting

**Symptoms**: Panel sizes reset on page refresh

**Solutions**:
1. Check browser localStorage is enabled
2. Verify UI store is properly initialized in providers
3. Clear localStorage and try again: `localStorage.clear()`

## Future Milestones

This B1.0 implementation prepares for:

- **B1.1**: Chat interface in ReasoningPanel, SSE streaming, Console logs
- **B1.2**: Session management (create/switch/delete sessions)
- **B1.3**: File artifacts display in ArtifactsPanel
- **B2.0**: Authentication and authorization
- **B2.1**: Multi-user support

## Contributing

When adding new features:

1. Follow existing component structure
2. Add TypeScript types for all API responses
3. Use Zustand stores for global state
4. Add tests for new components
5. Update this README with new features

## License

See root LICENSE file.

## Support

For issues and questions:
- Backend issues: See `backend/README.md`
- Frontend issues: Check this README's troubleshooting section
- General project: See root `README.md`
