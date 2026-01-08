@echo off
REM Run the email_verified_at migration via Docker (Windows)

docker compose -f infra/docker/compose/docker-compose.dev.yml exec -T postgres psql -U exam_user -d exam_platform -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE NULL;"

docker compose -f infra/docker/compose/docker-compose.dev.yml exec -T postgres psql -U exam_user -d exam_platform -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_sent_at TIMESTAMP WITH TIME ZONE NULL;"

echo Migration completed!
