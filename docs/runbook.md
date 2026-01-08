# Runbook

## Local Development Email (Mailpit)

### Mailpit Inbox
- **Web UI**: `http://localhost:8025`
- **SMTP Port**: `1025` (inside docker network: `mailpit:1025`)

### Configuration
- Email backend is configured via `EMAIL_BACKEND` environment variable:
  - `mailpit` or `smtp`: Uses SMTP provider (connects to Mailpit in dev)
  - `console`: Falls back to console logging (if Mailpit is unavailable)

### Testing Password Reset
1. Start Mailpit: `docker compose up -d mailpit`
2. Open Mailpit UI: `http://localhost:8025`
3. Trigger password reset from frontend or admin panel
4. Check Mailpit inbox for reset email with reset link

### Fallback Behavior
If Mailpit is not running or SMTP connection fails, the system automatically falls back to console provider, which logs emails to backend logs/console. - Operations Guide

## Overview

This runbook provides operational procedures, troubleshooting guides, and runbooks for common tasks and incidents.

## Table of Contents

1. [Deployment Procedures](#deployment-procedures)
2. [Common Operations](#common-operations)
3. [Troubleshooting](#troubleshooting)
4. [Incident Response](#incident-response)
5. [Maintenance Tasks](#maintenance-tasks)

---

## Deployment Procedures

### Initial Setup

#### Prerequisites

- Docker and Docker Compose installed
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- PostgreSQL 15+ (if not using Docker)

#### First-Time Deployment

```bash
# 1. Clone repository
git clone <repository-url>
cd "New Exam Prep Site"

# 2. Start services with Docker Compose
docker-compose up --build -d

# 3. Verify services are running
docker-compose ps

# 4. Check logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres

# 5. Seed database (if needed)
curl -X POST http://localhost:8000/seed
```

#### Service URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432

---

### Update Deployment

#### Backend Update

```bash
# 1. Pull latest code
git pull

# 2. Rebuild and restart backend
docker-compose up -d --build backend

# 3. Verify health
curl http://localhost:8000/health

# 4. Check logs for errors
docker-compose logs -f backend
```

#### Frontend Update

```bash
# 1. Pull latest code
git pull

# 2. Rebuild and restart frontend
docker-compose up -d --build frontend

# 3. Verify frontend loads
curl http://localhost:3000

# 4. Check logs
docker-compose logs -f frontend
```

#### Database Migration (Future)

```bash
# When Alembic is set up
cd backend
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

---

## Common Operations

### Database Operations

#### Backup Database

```bash
# Using Docker
docker-compose exec postgres pg_dump -U examplatform examplatform > backup_$(date +%Y%m%d).sql

# Or directly
pg_dump -U examplatform -h localhost examplatform > backup.sql
```

#### Restore Database

```bash
# Using Docker
docker-compose exec -T postgres psql -U examplatform examplatform < backup.sql

# Or directly
psql -U examplatform -h localhost examplatform < backup.sql
```

#### Reset Database

```bash
# WARNING: This deletes all data
docker-compose down -v
docker-compose up -d postgres
# Wait for postgres to be ready
curl -X POST http://localhost:8000/seed
```

#### Access Database Console

```bash
# Using Docker
docker-compose exec postgres psql -U examplatform examplatform

# Common queries
SELECT COUNT(*) FROM questions WHERE is_published = true;
SELECT COUNT(*) FROM attempt_sessions;
SELECT * FROM users;
```

---

### Service Management

#### Start All Services

```bash
docker-compose up -d
```

#### Stop All Services

```bash
docker-compose down
```

#### Restart Service

```bash
# Restart specific service
docker-compose restart backend
docker-compose restart frontend

# Restart all
docker-compose restart
```

#### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 backend
```

#### Check Service Status

```bash
# Service status
docker-compose ps

# Health checks
curl http://localhost:8000/health
curl http://localhost:3000
```

---

### User Management

#### Create Test User (Backend)

```python
# Access Python shell
docker-compose exec backend python

# In Python shell
from database import SessionLocal
from models import User

db = SessionLocal()
user = User(id="test-student", role="student")
db.add(user)
db.commit()
db.close()
```

#### List Users

```sql
-- In database console
SELECT id, role, created_at FROM users;
```

---

## Troubleshooting

### Service Won't Start

#### Backend Won't Start

**Symptoms:**
- Container exits immediately
- Health check fails
- Port 8000 not accessible

**Diagnosis:**
```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Database not ready
# 2. Port 8000 already in use
# 3. Missing environment variables
# 4. Python dependencies not installed
```

**Solutions:**

1. **Database Connection Error:**
   ```bash
   # Wait for postgres to be ready
   docker-compose up -d postgres
   sleep 5
   docker-compose up -d backend
   ```

2. **Port Already in Use:**
   ```bash
   # Find process using port 8000
   netstat -ano | findstr :8000  # Windows
   lsof -i :8000  # Mac/Linux
   
   # Kill process or change port in docker-compose.yml
   ```

3. **Missing Dependencies:**
   ```bash
   # Rebuild with no cache
   docker-compose build --no-cache backend
   docker-compose up -d backend
   ```

---

#### Frontend Won't Start

**Symptoms:**
- Container exits immediately
- Port 3000 not accessible
- Build errors

**Diagnosis:**
```bash
# Check logs
docker-compose logs frontend

# Common issues:
# 1. Node modules not installed
# 2. Port 3000 already in use
# 3. Build errors
# 4. API URL not configured
```

**Solutions:**

1. **Node Modules Missing:**
   ```bash
   # Rebuild with no cache
   docker-compose build --no-cache frontend
   docker-compose up -d frontend
   ```

2. **Build Errors:**
   ```bash
   # Check for TypeScript errors
   cd frontend
   npm run build
   
   # Fix errors, then restart
   docker-compose up -d --build frontend
   ```

3. **API Connection Error:**
   ```bash
   # Verify backend is running
   curl http://localhost:8000/health
   
   # Check NEXT_PUBLIC_API_URL in frontend/.env.local
   ```

---

#### Database Connection Issues

**Symptoms:**
- Backend can't connect to database
- "Connection refused" errors
- Timeout errors

**Diagnosis:**
```bash
# Check postgres is running
docker-compose ps postgres

# Check postgres logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U examplatform
```

**Solutions:**

1. **Postgres Not Running:**
   ```bash
   docker-compose up -d postgres
   # Wait 10 seconds for initialization
   ```

2. **Wrong Credentials:**
   ```bash
   # Check docker-compose.yml for DATABASE_URL
   # Verify username/password match
   ```

3. **Database Doesn't Exist:**
   ```bash
   # Create database
   docker-compose exec postgres psql -U examplatform -c "CREATE DATABASE examplatform;"
   ```

---

### Performance Issues

#### Slow API Responses

**Symptoms:**
- API takes >2 seconds to respond
- Timeout errors
- High CPU usage

**Diagnosis:**
```bash
# Check backend logs for slow queries
docker-compose logs backend | grep "slow"

# Check database performance
docker-compose exec postgres psql -U examplatform -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query
  FROM pg_stat_activity
  WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '1 second';
"
```

**Solutions:**

1. **Database Query Optimization:**
   - Add indexes (see data-model.md)
   - Review slow query log
   - Optimize N+1 queries

2. **Resource Limits:**
   ```yaml
   # In docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 2G
   ```

3. **Connection Pool:**
   - Increase database connection pool size
   - Check for connection leaks

---

#### High Memory Usage

**Symptoms:**
- Container memory usage >80%
- Out of memory errors
- Service restarts

**Diagnosis:**
```bash
# Check memory usage
docker stats

# Check for memory leaks
docker-compose logs backend | grep -i "memory"
```

**Solutions:**

1. **Increase Memory Limit:**
   ```yaml
   # docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 4G
   ```

2. **Optimize Code:**
   - Review for memory leaks
   - Limit result set sizes
   - Use pagination

---

### Data Issues

#### Missing Questions

**Symptoms:**
- Students can't see questions
- Question count is zero

**Diagnosis:**
```sql
-- Check question count
SELECT COUNT(*) FROM questions;
SELECT COUNT(*) FROM questions WHERE is_published = true;

-- Check themes
SELECT COUNT(*) FROM themes;
```

**Solutions:**

1. **Reseed Database:**
   ```bash
   curl -X POST http://localhost:8000/seed
   ```

2. **Check Publishing Status:**
   ```sql
   -- List unpublished questions
   SELECT id, question_text, is_published FROM questions WHERE is_published = false;
   ```

---

#### User Can't Login

**Symptoms:**
- Login fails
- "Invalid credentials" error
- User not found

**Diagnosis:**
```bash
# Check if user exists
curl -H "X-User-Id: student-1" http://localhost:8000/sessions

# Check backend logs
docker-compose logs backend | grep -i "user"
```

**Solutions:**

1. **Verify User Exists:**
   ```sql
   SELECT * FROM users WHERE id = 'student-1';
   ```

2. **Reseed Users:**
   ```bash
   curl -X POST http://localhost:8000/seed
   ```

3. **Check Demo Credentials:**
   - Email: `student@demo.com`
   - Password: `demo123`

---

## Incident Response

### Service Down

#### Backend API Down

**Severity:** Critical

**Steps:**
1. Check service status: `docker-compose ps backend`
2. Check logs: `docker-compose logs --tail=50 backend`
3. Check health endpoint: `curl http://localhost:8000/health`
4. Restart service: `docker-compose restart backend`
5. If still down, rebuild: `docker-compose up -d --build backend`
6. Check database connectivity
7. Escalate if issue persists

**Rollback:**
```bash
# Revert to previous version
git checkout <previous-commit>
docker-compose up -d --build backend
```

---

#### Frontend Down

**Severity:** High

**Steps:**
1. Check service status: `docker-compose ps frontend`
2. Check logs: `docker-compose logs --tail=50 frontend`
3. Check if accessible: `curl http://localhost:3000`
4. Restart service: `docker-compose restart frontend`
5. If build errors, check TypeScript: `cd frontend && npm run build`
6. Rebuild if needed: `docker-compose up -d --build frontend`

---

#### Database Down

**Severity:** Critical

**Steps:**
1. Check service status: `docker-compose ps postgres`
2. Check logs: `docker-compose logs --tail=50 postgres`
3. Check disk space: `df -h` (if host)
4. Check postgres health: `docker-compose exec postgres pg_isready`
5. Restart: `docker-compose restart postgres`
6. If data corruption suspected, restore from backup
7. Check for disk full errors

**Data Recovery:**
```bash
# Restore from backup
docker-compose exec -T postgres psql -U examplatform examplatform < backup.sql
```

---

### Data Loss

**Severity:** Critical

**Steps:**
1. Stop writes if possible
2. Assess scope of data loss
3. Check if backup exists
4. Restore from most recent backup
5. Verify data integrity
6. Investigate root cause
7. Document incident

**Prevention:**
- Regular automated backups
- Test restore procedures
- Monitor disk space
- Use transaction logs

---

## Maintenance Tasks

### Daily Tasks

- [ ] Check service health
- [ ] Review error logs
- [ ] Monitor resource usage
- [ ] Check backup completion

### Weekly Tasks

- [ ] Review performance metrics
- [ ] Check disk space
- [ ] Update dependencies (security patches)
- [ ] Review and rotate logs

### Monthly Tasks

- [ ] Database optimization (VACUUM, ANALYZE)
- [ ] Security audit
- [ ] Dependency updates
- [ ] Capacity planning review
- [ ] Backup restoration test

---

### Database Maintenance

#### Vacuum and Analyze

```sql
-- Vacuum to reclaim space
VACUUM;

-- Analyze for query optimization
ANALYZE;

-- Full vacuum (requires exclusive lock)
VACUUM FULL;
```

#### Index Maintenance

```sql
-- Reindex
REINDEX DATABASE examplatform;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

---

### Log Rotation

#### Application Logs

```bash
# Rotate logs (if using file-based logging)
logrotate /etc/logrotate.d/examprep

# Or manually
mv app.log app.log.$(date +%Y%m%d)
touch app.log
```

#### Docker Logs

```bash
# Limit log size in docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Emergency Contacts

### On-Call Rotation

**Primary:** [To be defined]  
**Secondary:** [To be defined]  
**Escalation:** [To be defined]

### External Services

**Database Hosting:** [If applicable]  
**Cloud Provider:** [If applicable]  
**Monitoring Service:** [If applicable]

---

## Quick Reference

### Common Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart service
docker-compose restart <service>

# Rebuild service
docker-compose up -d --build <service>

# Access database
docker-compose exec postgres psql -U examplatform examplatform

# Backup database
docker-compose exec postgres pg_dump -U examplatform examplatform > backup.sql

# Restore database
docker-compose exec -T postgres psql -U examplatform examplatform < backup.sql

# Seed database
curl -X POST http://localhost:8000/seed

# Check health
curl http://localhost:8000/health
```

### Service Ports

- Frontend: 3000
- Backend: 8000
- PostgreSQL: 5432

### Environment Variables

**Backend:**
- `DATABASE_URL`: PostgreSQL connection string
- `CORS_ORIGINS`: Allowed CORS origins

**Frontend:**
- `NEXT_PUBLIC_API_URL`: Backend API URL

---

## Appendix

### Useful SQL Queries

```sql
-- Count published questions
SELECT COUNT(*) FROM questions WHERE is_published = true;

-- List active sessions
SELECT id, user_id, started_at FROM attempt_sessions WHERE is_submitted = false;

-- User performance summary
SELECT 
  user_id,
  COUNT(*) as total_sessions,
  AVG(score) as avg_score
FROM attempt_sessions
WHERE is_submitted = true
GROUP BY user_id;

-- Most answered questions
SELECT 
  question_id,
  COUNT(*) as attempt_count,
  SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_count
FROM attempt_answers
GROUP BY question_id
ORDER BY attempt_count DESC
LIMIT 10;
```

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "Checking services..."

# Backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
  echo "✓ Backend is healthy"
else
  echo "✗ Backend is down"
fi

# Frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
  echo "✓ Frontend is accessible"
else
  echo "✗ Frontend is down"
fi

# Database
if docker-compose exec -T postgres pg_isready -U examplatform > /dev/null 2>&1; then
  echo "✓ Database is ready"
else
  echo "✗ Database is down"
fi
```

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2024-12-30 | Initial runbook created | System |

