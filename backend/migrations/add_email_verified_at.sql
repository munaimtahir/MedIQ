-- Add email_verified_at and email_verification_sent_at columns to users table
-- This migration fixes the error: column users.email_verified_at does not exist

-- Check if columns exist before adding them
DO $$
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
END $$;
