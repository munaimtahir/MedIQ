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

## Constants and Configuration Management

### Philosophy

This project enforces strict provenance for all algorithmic constants to ensure scientific rigor and maintainability.

**Core Principles:**
1. **No Magic Numbers:** All constants centralized in `backend/app/learning_engine/config.py`
2. **Source Attribution:** Every constant documents its origin (research paper, library default, or heuristic)
3. **Import-time Validation:** Invalid constants fail at startup, not in production
4. **Calibration Tracking:** Heuristic constants have explicit improvement plans

### Adding New Constants

```python
# In backend/app/learning_engine/config.py

from dataclasses import dataclass

MY_NEW_THRESHOLD = SourcedValue(
    value=42,
    sources=[
        "Smith et al. (2024) - Optimal threshold for X was empirically determined as 42",
        "Validated on 10,000+ student attempts with 95% confidence interval [40, 44]"
    ]
)
```

**Requirements:**
- Must use `SourcedValue` wrapper
- Must include at least one source explaining the value
- Sources must be specific (not just "set to 42")
- For heuristics, mention "placeholder" or "needs calibration"

### Documentation

- **Constants Audit:** `docs/constants-audit.md` - inventory of all 23 constants
- **Calibration Plan:** `docs/calibration-plan.md` - roadmap for tuning heuristic constants
- **Algorithm Docs:** `docs/algorithms.md` - detailed descriptions of all learning algorithms

### Testing

```bash
cd backend
pytest tests/test_constants_provenance.py -v
```

This test suite enforces:
- All constants have non-empty source attribution
- Sources explain reasoning (not just "value is X")
- Heuristic constants mention calibration plans
- FSRS weights have exactly 19 parameters
- BKT constraints satisfy non-degeneracy (S + G < 1)

## Next Steps

See `docs/architecture.md` for detailed architecture and `docs/api-contracts.md` for API specifications.

## Development Roadmap

- Phase 1: ✅ Skeleton (current)
- Phase 2: Authentication & Authorization
- Phase 3: Adaptive Testing Logic
- Phase 4: ML/AI Integration
- Phase 5: Mobile App
- Phase 6: Advanced Analytics

