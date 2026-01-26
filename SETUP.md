# Setup Instructions

## Initial Setup

1. **Clone the repository** (if applicable)

2. **Start with Docker Compose** (Recommended)

```bash
docker-compose up --build
```

This will:
- Start PostgreSQL database
- Start FastAPI backend (auto-seeds database)
- Start Next.js frontend

3. **Access the applications**

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs (Swagger UI)

## Manual Setup (Development)

**Use Docker only.** No virtual environments. All backend work (run, test, migrations) happens in containers.

### Backend (Docker)

```bash
# From project root. Ensure .env exists (copy from .env.example).
docker compose -f infra/docker/compose/docker-compose.dev.yml up -d --build

# Run tests
docker compose -f infra/docker/compose/docker-compose.dev.yml run --rm backend python -m pytest tests/ -v

# Backend shell
docker compose -f infra/docker/compose/docker-compose.dev.yml exec backend bash

# Seed database (if needed)
curl -X POST http://localhost:8000/seed
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Set environment variables (create .env.local file)
# Copy from .env.example and update values
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/v1

# Start development server
pnpm run dev
```

## Demo Users

The database is seeded with:

- **Student**: `student-1`
- **Admin**: `admin-1`

To login:
1. Go to http://localhost:3000
2. Click "Continue as Student" or "Continue as Admin"
3. The app will automatically set the `X-User-Id` header

## Testing the Flow

### Admin Flow

1. Login as admin
2. Go to `/admin/questions`
3. Click "Create New Question"
4. Fill in question details (must have 5 options)
5. Add tags (required for publishing)
6. Click "Create Question"
7. Click "Publish" to make it available to students

### Student Flow

1. Login as student
2. Go to `/student/dashboard`
3. Click on a block or go to `/student/practice/build`
4. Select block/theme and configure session
5. Click "Start Session"
6. Answer questions in the test player
7. Submit session
8. Review results

## Troubleshooting

### Database Connection Issues

- Ensure PostgreSQL is running
- Check `DATABASE_URL` environment variable
- Verify database credentials match docker-compose.yml

### CORS Errors

- Ensure `CORS_ORIGINS` includes your frontend URL
- Check backend is running on port 8000
- Verify frontend is calling correct API URL

### Frontend Not Loading

- Check Node.js version (18+)
- Clear `.next` folder and rebuild
- Check browser console for errors

### Backend Not Starting

- Check Python version (3.11+)
- Verify all dependencies installed
- Check port 8000 is not in use

## Next Steps

- See `docs/architecture.md` for system design
- See `docs/api-contracts.md` for API documentation
- See `docs/future-services.md` for roadmap

