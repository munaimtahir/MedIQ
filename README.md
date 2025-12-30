# Medical Exam Practice Platform

A production-grade skeleton for a medical exam practice platform with Student and Admin web applications.

## Architecture

- **Frontend**: Next.js (App Router) with TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI (Python) with PostgreSQL
- **Deployment**: Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Running with Docker Compose

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your local values if needed
   ```

2. **Start all services:**
   ```bash
   docker compose -f infra/docker/compose/docker-compose.dev.yml up -d --build
   ```

This will start:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Neo4j: http://localhost:7474
- Elasticsearch: http://localhost:9200

The database will be automatically seeded with demo data on first startup. If you need to reseed, call `POST http://localhost:8000/seed`.

**Useful commands:**
```bash
# View logs
docker compose -f infra/docker/compose/docker-compose.dev.yml logs -f

# Stop services
docker compose -f infra/docker/compose/docker-compose.dev.yml down

# Access backend shell
docker compose -f infra/docker/compose/docker-compose.dev.yml exec backend bash
```

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Demo Credentials

- **Student**: Use header `X-User-Id: student-1`
- **Admin**: Use header `X-User-Id: admin-1`

## Project Structure

```
/
├── frontend/          # Next.js app
├── backend/           # FastAPI app
├── infra/             # Infrastructure configurations
│   └── docker/
│       └── compose/
│           └── docker-compose.dev.yml
└── docs/              # Architecture documentation
```

## Code Formatting

This project uses automated formatting tools to maintain consistent code style.

### Format All Code

```bash
# Linux/Mac
./infra/scripts/format-all.sh

# Windows PowerShell
.\infra\scripts\format-all.ps1
```

### Check Formatting (CI)

```bash
# Linux/Mac
./infra/scripts/format-check.sh

# Windows PowerShell
.\infra\scripts\format-check.ps1
```

### Individual Services

**Frontend:**
```bash
cd frontend
npm run format          # Format code
npm run format:check    # Check formatting
npm run lint            # Run ESLint
npm run typecheck       # TypeScript check
```

**Backend:**
```bash
cd backend
black .                 # Format code
ruff check .            # Lint code
ruff check . --fix      # Auto-fix linting issues
pytest -v               # Run tests
```

### Tools Used

- **Frontend**: Prettier (with Tailwind plugin) + ESLint
- **Backend**: Black (formatting) + Ruff (linting)

## Next Steps

See `docs/architecture.md` for detailed architecture and `docs/api-contracts.md` for API specifications.

## Development Roadmap

- Phase 1: ✅ Skeleton (current)
- Phase 2: Authentication & Authorization
- Phase 3: Adaptive Testing Logic
- Phase 4: ML/AI Integration
- Phase 5: Mobile App
- Phase 6: Advanced Analytics

