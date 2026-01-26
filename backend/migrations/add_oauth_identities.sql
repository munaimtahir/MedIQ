-- Create oauth_identities table for OAuth provider linking
-- Safe to run idempotently (IF NOT EXISTS)

CREATE TABLE IF NOT EXISTS oauth_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR NOT NULL,
    provider_subject VARCHAR NOT NULL,
    email_at_link_time VARCHAR NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_oauth_provider_subject UNIQUE (provider, provider_subject)
);

CREATE INDEX IF NOT EXISTS ix_oauth_identities_user_id ON oauth_identities(user_id);
