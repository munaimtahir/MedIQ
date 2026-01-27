# Operational Runbooks

This directory contains operational runbooks for the Exam Prep Platform, providing step-by-step procedures for common operational tasks and incident response.

## Quick Reference

- **[00-QuickStart.md](./00-QuickStart.md)** - Fast reference for checking status, restarting services, and verifying health
- **[01-Incident-Checklist.md](./01-Incident-Checklist.md)** - Structured triage and response for production incidents
- **[02-Rollback.md](./02-Rollback.md)** - Safely rollback to a previous working version
- **[03-Database.md](./03-Database.md)** - Database migrations, backups, restores, and troubleshooting
- **[04-Redis.md](./04-Redis.md)** - Redis troubleshooting, inspection, and when to flush
- **[05-Traefik.md](./05-Traefik.md)** - Traefik routing, certificates, and middleware troubleshooting
- **[06-Observability.md](./06-Observability.md)** - How to use Grafana, Prometheus, Tempo, and logs for diagnosis
- **[07-Security.md](./07-Security.md)** - Security incidents, token revocation, Cloudflare actions, and audit logs
- **[08-Cloudflare.md](./08-Cloudflare.md)** - Cloudflare WAF, rate limiting, cache, SSL/TLS, bot protection, and Zero Trust

## Usage

These runbooks are designed for:
- **On-call engineers** responding to incidents
- **DevOps engineers** performing routine operations
- **SREs** troubleshooting production issues

Each runbook includes:
- Concrete commands (no placeholders, except for environment-specific values like `<STAGING_DOMAIN>`)
- Verification checklists (5 bullets) after any intervention
- Clear decision trees and workflows
- Related runbook references

## Environment Variables

Replace these placeholders with actual values:
- `<STAGING_DOMAIN>` - Your staging domain (e.g., `staging.example.com`)
- `<STAGING_USER>` - SSH user for staging server
- `<STAGING_HOST>` - SSH hostname/IP for staging server
- `<POSTGRES_USER>` - PostgreSQL username
- `<POSTGRES_DB>` - PostgreSQL database name
- `<OWNER>` - GitHub repository owner
- `<REPO>` - GitHub repository name

## Contributing

When updating runbooks:
1. Test commands in staging first
2. Update verification checklists
3. Add related runbook references
4. Keep language crisp and operational
5. No placeholders (except environment variables)
