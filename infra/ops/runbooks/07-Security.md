# Security Runbook

**Purpose**: Procedures for security incidents, token revocation, Cloudflare actions, and audit logs.

## Prerequisites

- Access to staging server via SSH
- Database access for token revocation
- Cloudflare account access (for WAF/rate limit actions)
- Understanding of authentication system

## Token Revocation

### Revoke Specific Token

```bash
# SSH to staging server
ssh <STAGING_USER>@<STAGING_HOST>

# Navigate to deployment directory
cd ~/exam-platform-staging

# Connect to database
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB>

# Revoke refresh token (if stored in database)
UPDATE refresh_tokens SET revoked = true, revoked_at = NOW() WHERE token_hash = '<token_hash>';

# Revoke all tokens for a user
UPDATE refresh_tokens SET revoked = true, revoked_at = NOW() WHERE user_id = '<user_id>';

# Exit database
\q
```

### Revoke All Tokens for User

```bash
# Via database (as above)
# Or via API (if endpoint exists)
curl -X POST https://<STAGING_DOMAIN>/api/v1/auth/revoke-all \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "<user_id>"}'
```

### Check Token Status

```bash
# Check if token is revoked
docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT id, user_id, created_at, revoked, revoked_at FROM refresh_tokens WHERE token_hash = '<token_hash>';"
```

## Authentication Incident Steps

### Suspected Account Compromise

1. **Immediately revoke all tokens**:
   ```bash
   # Revoke all tokens for user
   docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "UPDATE refresh_tokens SET revoked = true, revoked_at = NOW() WHERE user_id = '<user_id>';"
   ```

2. **Check audit logs**:
   ```bash
   docker compose logs --since=24h backend_staging | jq 'select(.audit == true and .actor_id == "<user_id>")'
   ```

3. **Check login history**:
   ```bash
   docker compose logs --since=24h backend_staging | jq 'select(.event == "auth.login" and .user_id == "<user_id>")'
   ```

4. **Force password reset** (if endpoint exists):
   ```bash
   curl -X POST https://<STAGING_DOMAIN>/api/v1/auth/force-password-reset \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "<user_id>"}'
   ```

### Brute Force Attack

1. **Check rate limiting**:
   ```bash
   # Check Cloudflare rate limit logs (if available)
   # Check backend logs for failed login attempts
   docker compose logs --since=1h backend_staging | jq 'select(.event == "auth_login_failed")' | jq -s 'group_by(.ip_address) | map({ip: .[0].ip_address, count: length}) | sort_by(.count) | reverse'
   ```

2. **Block IP in Cloudflare** (see Cloudflare section below)

3. **Check if rate limiting is working**:
   ```bash
   # Test rate limit
   for i in {1..10}; do curl -X POST https://<STAGING_DOMAIN>/api/v1/auth/login -d '{"email":"test@example.com","password":"wrong"}'; done
   # Should see 429 after threshold
   ```

### Token Leakage

1. **Revoke compromised tokens** (see Token Revocation above)

2. **Check where tokens were used**:
   ```bash
   # Search audit logs for token usage
   docker compose logs --since=24h backend_staging | jq 'select(.request_id != null) | select(.trace_id == "<trace_id_from_compromised_request>")'
   ```

3. **Rotate secrets** (if JWT secret compromised):
   ```bash
   # Update JWT_SECRET in .env file
   # Restart backend
   docker compose -f docker-compose.staging.yml restart backend_staging
   ```

## Cloudflare WAF/Rate Limit Emergency Actions

### Block IP Address

**Via Cloudflare Dashboard:**

1. Navigate to: **Security → WAF → Tools**
2. Select: **IP Access Rules**
3. Add rule:
   - **IP Address**: `<ip_address>`
   - **Action**: Block
   - **Note**: Reason for blocking

**Via Cloudflare API** (if configured):

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/<zone_id>/firewall/access_rules/rules" \
  -H "Authorization: Bearer <api_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "block",
    "configuration": {
      "target": "ip",
      "value": "<ip_address>"
    },
    "notes": "Blocked due to security incident"
  }'
```

### Unblock IP Address

**Via Cloudflare Dashboard:**

1. Navigate to: **Security → WAF → Tools → IP Access Rules**
2. Find IP address
3. Click **Delete** or change action to **Allow**

### Check Rate Limit Status

**Via Cloudflare Dashboard:**

1. Navigate to: **Security → WAF → Rate limiting rules**
2. Check active rules
3. View rate limit analytics

**Via Logs** (if Cloudflare Logpush enabled):

```bash
# Check rate limit hits
# (requires Cloudflare Logpush to be configured)
```

### Temporarily Disable Rate Limiting

**⚠️ Use with extreme caution - only for emergency access**

**Via Cloudflare Dashboard:**

1. Navigate to: **Security → WAF → Rate limiting rules**
2. Find rule
3. Click **Edit**
4. Change **Action** to **Log** (instead of Block)
5. Save

**⚠️ Re-enable rate limiting as soon as possible!**

### Check WAF Blocked Requests

**Via Cloudflare Dashboard:**

1. Navigate to: **Security → Events**
2. Filter by: **Action: Block**
3. Review blocked requests
4. Check if false positives

### Handle False Positives

1. **Identify rule causing false positive**:
   - Check WAF event details
   - Note rule ID

2. **Create exception** (if needed):
   - Navigate to: **Security → WAF → Custom rules**
   - Create exception rule for specific IP/pattern

3. **Adjust rule sensitivity** (if appropriate):
   - Navigate to: **Security → WAF → Managed rules**
   - Adjust sensitivity for specific rule

## Audit Log Usage

### Search Audit Logs

```bash
# All audit logs (last 24 hours)
docker compose logs --since=24h backend_staging | jq 'select(.audit == true)'

# Audit logs for specific user
docker compose logs --since=24h backend_staging | jq 'select(.audit == true and .actor_id == "<user_id>")'

# Audit logs for specific action
docker compose logs --since=24h backend_staging | jq 'select(.audit == true and .action == "delete_user")'

# Audit logs by time range
docker compose logs --since=1h --until=2h backend_staging | jq 'select(.audit == true)'
```

### Common Audit Events

```bash
# User deletions
docker compose logs --since=24h backend_staging | jq 'select(.audit == true and (.action | contains("delete")))'

# Permission changes
docker compose logs --since=24h backend_staging | jq 'select(.audit == true and (.action | contains("permission")))'

# Admin actions
docker compose logs --since=24h backend_staging | jq 'select(.audit == true and .actor_role == "ADMIN")'

# Failed authentication attempts
docker compose logs --since=24h backend_staging | jq 'select(.audit == true and .event == "auth_login_failed")'
```

### Export Audit Logs

```bash
# Export audit logs to file
docker compose logs --since=24h backend_staging | jq 'select(.audit == true)' > audit_logs_$(date +%Y%m%d).json

# Export specific user's audit logs
docker compose logs --since=30d backend_staging | jq 'select(.audit == true and .actor_id == "<user_id>")' > user_audit_logs_$(date +%Y%m%d).json
```

## Security Incident Response

### SEV-1: Active Attack

1. **Immediate actions** (within 5 minutes):
   - [ ] Block attacking IP in Cloudflare
   - [ ] Revoke compromised tokens
   - [ ] Check audit logs for scope of attack
   - [ ] Notify security team

2. **Investigation** (within 30 minutes):
   - [ ] Review audit logs
   - [ ] Check for data exfiltration
   - [ ] Identify attack vector
   - [ ] Assess impact

3. **Remediation** (within 1 hour):
   - [ ] Apply fixes
   - [ ] Rotate secrets if compromised
   - [ ] Update WAF rules if needed
   - [ ] Document incident

### SEV-2: Potential Compromise

1. **Immediate actions** (within 15 minutes):
   - [ ] Review audit logs
   - [ ] Check for suspicious activity
   - [ ] Revoke tokens if needed

2. **Investigation** (within 2 hours):
   - [ ] Identify suspicious patterns
   - [ ] Check user accounts
   - [ ] Review access logs

3. **Remediation** (within 4 hours):
   - [ ] Apply security measures
   - [ ] Update monitoring
   - [ ] Document findings

## Verification Checklist

After any security intervention:

1. **Tokens revoked** (if applicable):
   ```bash
   docker compose -f docker-compose.staging.yml exec postgres_staging psql -U <POSTGRES_USER> <POSTGRES_DB> -c "SELECT count(*) FROM refresh_tokens WHERE user_id = '<user_id>' AND revoked = false;"
   # Expected: 0
   ```

2. **IP blocked** (if applicable):
   ```bash
   # Test from blocked IP (should fail)
   curl -I https://<STAGING_DOMAIN>/
   # Expected: 403 Forbidden or connection refused
   ```

3. **Rate limiting active** (if applicable):
   ```bash
   # Test rate limit
   for i in {1..10}; do curl -X POST https://<STAGING_DOMAIN>/api/v1/auth/login -d '{"email":"test@example.com","password":"wrong"}'; done
   # Expected: 429 after threshold
   ```

4. **Audit logs captured**:
   ```bash
   docker compose logs --since=5m backend_staging | jq 'select(.audit == true)' | wc -l
   # Expected: > 0 if actions were taken
   ```

5. **No unauthorized access**:
   ```bash
   docker compose logs --since=1h backend_staging | jq 'select(.audit == true and .outcome == "deny")' | jq -s 'length'
   # Review for patterns
   ```

## Related Runbooks

- [01-Incident-Checklist.md](./01-Incident-Checklist.md) - Incident triage
- [00-QuickStart.md](./00-QuickStart.md) - Quick health checks
- [06-Observability.md](./06-Observability.md) - Log analysis
