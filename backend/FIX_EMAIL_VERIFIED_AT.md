# Fix: Missing email_verified_at Column

## Problem
When signing up with Google OAuth, you're getting this error:
```
column users.email_verified_at does not exist
```

## Solution

The database is missing the `email_verified_at` column that the User model expects. You need to add this column to your database.

### Option 1: Quick Fix via Docker (Recommended if using Docker)

**Windows:**
```bash
cd backend
run_migration.bat
```

**Linux/Mac:**
```bash
cd backend
chmod +x run_migration.sh
./run_migration.sh
```

**Or run directly:**
```bash
# Windows (CMD)
docker compose -f infra/docker/compose/docker-compose.dev.yml exec -T postgres psql -U exam_user -d exam_platform -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE NULL;"
docker compose -f infra/docker/compose/docker-compose.dev.yml exec -T postgres psql -U exam_user -d exam_platform -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_sent_at TIMESTAMP WITH TIME ZONE NULL;"

# Linux/Mac
docker compose -f infra/docker/compose/docker-compose.dev.yml exec -T postgres psql -U exam_user -d exam_platform <<EOF
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_sent_at TIMESTAMP WITH TIME ZONE NULL;
EOF
```

### Option 2: Run SQL Directly via psql

Connect to your database and run:

```sql
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE NULL;

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS email_verification_sent_at TIMESTAMP WITH TIME ZONE NULL;
```

**Using Docker:**
```bash
docker compose -f infra/docker/compose/docker-compose.dev.yml exec postgres psql -U exam_user -d exam_platform
```
Then paste the SQL commands above.

### Option 3: Use Python Script (if you have dependencies installed)

```bash
cd backend
python fix_email_verified_at.py
```

### Option 4: Run Alembic Migration (if Alembic is set up)

```bash
cd backend
alembic upgrade head
```

## Verify the Fix

After running the migration, verify the columns exist:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('email_verified_at', 'email_verification_sent_at');
```

You should see both columns listed.

## Next Steps

After fixing this, try signing up with Google OAuth again. The error should be resolved.
