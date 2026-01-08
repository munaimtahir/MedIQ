@echo off
REM Script to create admin user via Docker (Windows)
REM Run from project root: backend\scripts\create_admin.bat

cd /d "%~dp0\..\.."
docker compose -f infra\docker\compose\docker-compose.dev.yml exec -T backend python scripts/create_admin.py %*
