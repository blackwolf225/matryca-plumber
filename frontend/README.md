# Sovereign UI (React + Vite)

Local control room for **Matryca Plumber** — served by the FastAPI backend on `http://127.0.0.1:8500` when you run `matryca plumber status` or `matryca plumber ui`.

## Prerequisites

- Node.js 22 (matches CI)
- Python deps installed at repo root (`make install`)

## Development

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies API calls to the Python UI server when it is running.

## Build (required before Python wheel)

CI and release workflows run:

```bash
npm ci
npm run build
```

Output lands in `frontend/dist/` and is bundled into the PyPI wheel via `setuptools` package data.

## Quality checks

```bash
npm run lint   # ESLint
npm run test   # Vitest
npm run build  # tsc -b && vite build
```

Root `make ci` runs Python gates plus frontend test/build. ESLint (`npm run lint`) has pre-existing react-hooks debt — run locally when touching UI code.

## Architecture notes

- React 19 + Tailwind CSS 4 + Vite 8
- Talks to `/api/*` on the local FastAPI server (`src/cli/ui_server.py`)
- See [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for the three-surface runtime diagram
