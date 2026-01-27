# Traefik Runbook

**Purpose**: Troubleshooting Traefik routing, certificates, and middleware issues.

## Prerequisites

- Access to staging server via SSH
- Traefik container running
- Understanding of Traefik configuration

## Common Routing Failures

### Check Traefik Status

```bash
# SSH to staging server
ssh <STAGING_USER>@<STAGING_HOST>

# Navigate to deployment directory
cd ~/exam-platform-staging

# Check Traefik container status
docker compose -f docker-compose.staging.yml ps traefik

# Check Traefik logs
docker compose -f docker-compose.staging.yml logs --tail=100 traefik

# Check Traefik API (if enabled)
curl http://localhost:8080/api/http/routers  # Traefik dashboard API
```

### Check Router Configuration

```bash
# List all routers
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/routers | jq .

# List services
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/services | jq .

# Check specific router
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/routers/api-staging | jq .
```

### Common Routing Issues

#### Issue: 404 Not Found

```bash
# Check if router exists
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/routers | jq '.[] | select(.name | contains("api"))'

# Check if service is registered
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/services | jq '.[] | select(.name | contains("api"))'

# Check backend container is running
docker compose -f docker-compose.staging.yml ps backend_staging

# Check backend is accessible from Traefik
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://backend_staging:8000/v1/health
```

#### Issue: 502 Bad Gateway

```bash
# Check backend is running
docker compose -f docker-compose.staging.yml ps backend_staging

# Check backend health
docker compose -f docker-compose.staging.yml exec backend_staging curl -I http://localhost:8000/v1/health

# Check network connectivity
docker compose -f docker-compose.staging.yml exec traefik ping backend_staging

# Check service configuration
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/services/api-staging | jq .
```

#### Issue: 503 Service Unavailable

```bash
# Check if backend is healthy
docker compose -f docker-compose.staging.yml exec backend_staging curl http://localhost:8000/v1/ready

# Check Traefik health checks
docker compose -f docker-compose.staging.yml logs traefik | grep -i "health\|unhealthy"

# Check service load balancer status
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/services/api-staging | jq '.serverStatus'
```

## Certificate/Entrypoint Checks

### Check Certificate Status

```bash
# Check Let's Encrypt certificates
docker compose -f docker-compose.staging.yml exec traefik ls -la /letsencrypt/acme.json

# Check certificate in Traefik API
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/routers | jq '.[] | select(.tls != null)'

# Check certificate expiration (from host)
openssl s_client -connect <STAGING_DOMAIN>:443 -servername <STAGING_DOMAIN> < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

### Check Entrypoints

```bash
# List entrypoints
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/entrypoints | jq .

# Check entrypoint configuration
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/entrypoints/websecure | jq .
```

### Certificate Renewal Issues

```bash
# Check Let's Encrypt logs
docker compose -f docker-compose.staging.yml logs traefik | grep -i "acme\|certificate\|letsencrypt"

# Force certificate renewal (restart Traefik)
docker compose -f docker-compose.staging.yml restart traefik

# Check certificate after renewal
sleep 30
openssl s_client -connect <STAGING_DOMAIN>:443 -servername <STAGING_DOMAIN> < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

## Middleware/Rate Limit Checks

### Check Middleware Configuration

```bash
# List all middlewares
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/middlewares | jq .

# Check specific middleware
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/middlewares/staging-auth | jq .

# Check middleware chain for router
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/routers/api-staging | jq '.middlewares'
```

### Rate Limiting Issues

```bash
# Check rate limit middleware
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/middlewares | jq '.[] | select(.name | contains("rate"))'

# Check rate limit configuration
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/middlewares/conn-limit | jq .

# Test rate limiting
for i in {1..10}; do curl -I https://<STAGING_DOMAIN>/api/v1/health; done
# Should see 429 Too Many Requests after threshold
```

### Basic Auth Issues

```bash
# Check basic auth middleware
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/middlewares/staging-auth | jq .

# Test basic auth
curl -I https://<STAGING_DOMAIN>/
# Should return 401 if basic auth is enabled

curl -u username:password -I https://<STAGING_DOMAIN>/
# Should return 200 if credentials are correct
```

### IP Allowlist Issues

```bash
# Check IP allowlist middleware
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/middlewares/staging-ip | jq .

# Test from allowed IP
curl -I https://<STAGING_DOMAIN>/
# Should work if IP is in allowlist

# Test from blocked IP (if possible)
# Should return 403 Forbidden
```

## Restart Traefik

### Graceful Restart

```bash
# Restart Traefik
docker compose -f docker-compose.staging.yml restart traefik

# Wait for Traefik to be ready
sleep 10

# Verify Traefik is running
docker compose -f docker-compose.staging.yml ps traefik

# Check Traefik logs
docker compose -f docker-compose.staging.yml logs --tail=50 traefik
```

### Force Restart (if Traefik is hung)

```bash
# Force stop
docker compose -f docker-compose.staging.yml kill traefik

# Start
docker compose -f docker-compose.staging.yml start traefik

# Wait and verify
sleep 10
docker compose -f docker-compose.staging.yml ps traefik
```

## Debugging Tips

### Enable Debug Logging

```bash
# Check current log level
docker compose -f docker-compose.staging.yml logs traefik | head -5

# Enable debug mode (edit docker-compose.staging.yml)
# Add to traefik command: --log.level=DEBUG

# Restart Traefik
docker compose -f docker-compose.staging.yml restart traefik

# Check debug logs
docker compose -f docker-compose.staging.yml logs -f traefik
```

### Test Routing from Inside Container

```bash
# Test backend connectivity from Traefik
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://backend_staging:8000/v1/health

# Test frontend connectivity from Traefik
docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://frontend_staging:3000/
```

### Check Network Connectivity

```bash
# Check if Traefik can reach backend
docker compose -f docker-compose.staging.yml exec traefik ping backend_staging

# Check if Traefik can reach frontend
docker compose -f docker-compose.staging.yml exec traefik ping frontend_staging

# Check DNS resolution
docker compose -f docker-compose.staging.yml exec traefik nslookup backend_staging
```

## Verification Checklist

After any Traefik intervention:

1. **Traefik container is running**:
   ```bash
   docker compose -f docker-compose.staging.yml ps traefik
   # Expected: Up status
   ```

2. **Routers are registered**:
   ```bash
   docker compose -f docker-compose.staging.yml exec traefik wget -qO- http://localhost:8080/api/http/routers | jq 'length'
   # Expected: > 0
   ```

3. **Services are accessible**:
   ```bash
   curl -I https://<STAGING_DOMAIN>/
   curl -I https://<STAGING_DOMAIN>/api/v1/health
   # Expected: 200 OK
   ```

4. **Certificates are valid**:
   ```bash
   openssl s_client -connect <STAGING_DOMAIN>:443 -servername <STAGING_DOMAIN> < /dev/null 2>/dev/null | openssl x509 -noout -dates
   # Expected: Valid dates, not expired
   ```

5. **No errors in Traefik logs**:
   ```bash
   docker compose -f docker-compose.staging.yml logs --since=5m traefik | grep -i error
   # Expected: No output or only expected errors
   ```

## Related Runbooks

- [01-Incident-Checklist.md](./01-Incident-Checklist.md) - Incident triage
- [00-QuickStart.md](./00-QuickStart.md) - Quick health checks
- [07-Security.md](./07-Security.md) - Security and rate limiting
