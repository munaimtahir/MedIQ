# Architecture Documentation

## Overview

The Medical Exam Platform is a monorepo application consisting of:

- **Frontend**: Next.js 14 (App Router) with TypeScript
- **Backend**: FastAPI (Python) with PostgreSQL
- **Deployment**: Docker Compose

## System Architecture

```
┌─────────────────┐
│   Next.js App   │
│  (Frontend)     │
│  Port: 3000     │
└────────┬────────┘
         │ REST API
         │
┌────────▼────────┐
│   FastAPI       │
│  (Backend)      │
│  Port: 8000     │
└────────┬────────┘
         │ SQL
         │
┌────────▼────────┐
│   PostgreSQL    │
│  Port: 5432     │
└─────────────────┘
```

## Frontend Architecture

### Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── (public)/          # Public routes (landing, login)
│   ├── student/           # Student app routes
│   └── admin/             # Admin app routes
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── student/          # Student-specific components
│   └── admin/            # Admin-specific components
├── lib/                  # Utilities and API client
└── store/                # Zustand state management
```

### Key Technologies

- **Next.js 14**: App Router for routing
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **shadcn/ui**: UI component library
- **Zustand**: State management
- **GSAP**: Animation library (placeholder hooks)
- **D3.js**: Analytics charts (placeholder)

## Backend Architecture

### Structure

```
backend/
├── main.py              # FastAPI app and routes
├── database.py          # SQLAlchemy setup
├── models.py            # Database models
├── schemas.py           # Pydantic schemas
└── seed.py              # Database seeding
```

### Database Schema

#### Core Entities

1. **User**
   - `id` (String, PK)
   - `role` (String: "student" | "admin")
   - `created_at` (DateTime)

2. **Block**
   - `id` (String, PK: "A", "B", "C", etc.)
   - `name` (String)
   - `year` (Integer: 1 or 2)
   - `description` (Text)

3. **Theme**
   - `id` (Integer, PK)
   - `block_id` (String, FK → Block)
   - `name` (String)
   - `description` (Text)

4. **Question**
   - `id` (Integer, PK)
   - `theme_id` (Integer, FK → Theme)
   - `question_text` (Text)
   - `options` (JSON: List[String], exactly 5)
   - `correct_option_index` (Integer: 0-4)
   - `explanation` (Text, optional)
   - `tags` (JSON: List[String], optional)
   - `difficulty` (String: "easy" | "medium" | "hard", optional)
   - `is_published` (Boolean)
   - `created_at`, `updated_at` (DateTime)

5. **AttemptSession**
   - `id` (Integer, PK)
   - `user_id` (String, FK → User)
   - `question_count` (Integer)
   - `time_limit_minutes` (Integer)
   - `question_ids` (JSON: List[Integer])
   - `is_submitted` (Boolean)
   - `started_at`, `submitted_at` (DateTime)

6. **AttemptAnswer**
   - `id` (Integer, PK)
   - `session_id` (Integer, FK → AttemptSession)
   - `question_id` (Integer, FK → Question)
   - `selected_option_index` (Integer)
   - `is_correct` (Boolean)
   - `is_marked_for_review` (Boolean)
   - `answered_at` (DateTime)

### API Design

#### Authentication

- Handled by JWT (JSON Web Tokens).

#### REST Endpoints

See `api-contracts.md` for detailed API documentation.

## Future Architecture Considerations

### Planned Services (Not Implemented)

1. **Neo4j**: Concept graph for question relationships
2. **Redis**: Session caching and rate limiting
3. **Elasticsearch**: Full-text search for questions
4. **Snowflake**: Analytics data warehouse
5. **ML Services**: PyTorch/TensorFlow for adaptive testing
6. **Mobile API**: React Native compatible endpoints

### Scalability Design

- **API Boundaries**: REST endpoints designed to support GraphQL/gRPC later
- **Database**: PostgreSQL with read replicas support
- **Caching**: Redis layer ready for integration
- **Microservices**: Backend structured to split into services later
- **Kubernetes**: Docker images compatible with K8s deployment

## Security (Design Phase)

- **OAuth2**: Planned for authentication
- **JWT**: Token-based auth
- **Zero Trust**: Network security model
- **Input Validation**: Pydantic schemas enforce validation

## Monitoring (Placeholders)

- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **OpenTelemetry**: Distributed tracing

## Deployment

### Development

```bash
docker-compose up
```

### Production (Planned)

- Kubernetes manifests
- CI/CD with GitHub Actions
- Cloud deployment (AWS/Azure/Cloudflare)
- Load balancing
- Auto-scaling

## Data Flow

### Student Practice Flow

1. Student selects block/theme
2. Frontend calls `POST /sessions`
3. Backend creates session, selects questions
4. Student answers questions
5. Frontend calls `POST /sessions/{id}/answer` for each answer
6. Student submits: `POST /sessions/{id}/submit`
7. Student reviews: `GET /sessions/{id}/review`

### Admin Content Flow

1. Admin creates question: `POST /admin/questions`
2. Question saved as draft (`is_published: false`)
3. Admin adds tags (required for publishing)
4. Admin publishes: `POST /admin/questions/{id}/publish`
5. Question becomes available to students via `GET /questions`

## Extensibility Points

1. **Question Types**: Schema supports multiple types (currently MCQ only)
2. **Adaptive Testing**: Session creation can be enhanced with ML
3. **Analytics**: Review data structure supports detailed analytics
4. **Content Pipeline**: Admin endpoints support review workflows
5. **Mobile**: API design compatible with mobile clients

