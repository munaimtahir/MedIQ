#!/bin/bash
# Run the email_verified_at migration via Docker

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run the SQL migration
docker compose -f infra/docker/compose/docker-compose.dev.yml exec -T postgres psql -U exam_user -d exam_platform <<EOF
-- Add email_verified_at and email_verification_sent_at columns to users table
DO \$\$
BEGIN
    -- Add email_verified_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'email_verified_at'
    ) THEN
        ALTER TABLE users 
        ADD COLUMN email_verified_at TIMESTAMP WITH TIME ZONE NULL;
        RAISE NOTICE 'Added email_verified_at column';
    ELSE
        RAISE NOTICE 'Column email_verified_at already exists';
    END IF;

    -- Add email_verification_sent_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'email_verification_sent_at'
    ) THEN
        ALTER TABLE users 
        ADD COLUMN email_verification_sent_at TIMESTAMP WITH TIME ZONE NULL;
        RAISE NOTICE 'Added email_verification_sent_at column';
    ELSE
        RAISE NOTICE 'Column email_verification_sent_at already exists';
    END IF;
END \$\$;
EOF

echo "Migration completed!"
