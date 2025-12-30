# Infrastructure Scripts

This directory contains utility scripts for infrastructure management and operations.

## Formatting Scripts

### `format-all.sh` / `format-all.ps1`
Formats all code in the repository:
- Frontend: Runs Prettier
- Backend: Runs Black

**Usage:**
```bash
# Linux/Mac
./infra/scripts/format-all.sh

# Windows PowerShell
.\infra\scripts\format-all.ps1
```

### `format-check.sh` / `format-check.ps1`
Checks formatting across the repository without making changes:
- Frontend: Runs Prettier check
- Backend: Runs Black check + Ruff lint

**Usage:**
```bash
# Linux/Mac
./infra/scripts/format-check.sh

# Windows PowerShell
.\infra\scripts\format-check.ps1
```

## Planned Scripts

### Database
- `migrate.sh` - Database migration runner
- `backup.sh` - Database backup script
- `restore.sh` - Database restore script
- `seed.sh` - Database seeding utility

### Deployment
- `deploy.sh` - Deployment automation
- `rollback.sh` - Rollback procedures
- `health-check.sh` - Service health validation

### Monitoring
- `logs.sh` - Centralized log aggregation
- `metrics.sh` - Metrics collection utilities

## Guidelines

- All scripts should be idempotent where possible
- Include error handling and logging
- Document script parameters and usage
- Test scripts in development before production use

