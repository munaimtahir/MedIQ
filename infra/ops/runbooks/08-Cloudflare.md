# Cloudflare Runbook

**Purpose**: Procedures for Cloudflare WAF incidents, rate limiting, cache invalidation, SSL/TLS issues, bot protection, and Zero Trust.

## Prerequisites

- Cloudflare account access
- Zone ID for your domain
- Cloudflare API token (for automated operations)
- Understanding of Cloudflare dashboard

## WAF Incident Response

### False Positives

**Identify False Positive:**

1. **Check WAF Events**:
   - Navigate to: **Security → Events**
   - Filter by: **Action: Block**
   - Review blocked requests
   - Check rule ID and reason

2. **Verify Legitimate Traffic**:
   - Check request details (IP, user agent, path)
   - Confirm it's from legitimate user/application
   - Review request pattern

**Create Exception:**

**Via Dashboard:**
1. Navigate to: **Security → WAF → Custom rules**
2. Click **Create rule**
3. Configure:
   - **Rule name**: `Exception: <description>`
   - **Expression**: `(http.request.uri.path contains "/api/v1/specific-endpoint" and ip.src eq <legitimate_ip>)`
   - **Action**: Skip
   - **Skip phases**: Select the WAF rule causing the block
4. Save rule

**Via API:**
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/<zone_id>/rulesets/phases/http_request_firewall_custom/entrypoint" \
  -H "Authorization: Bearer <api_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Exception: Legitimate endpoint",
    "action": "skip",
    "action_parameters": {
      "ruleset": "<ruleset_id>"
    },
    "expression": "(http.request.uri.path contains \"/api/v1/specific-endpoint\" and ip.src eq \"<legitimate_ip>\")"
  }'
```

**Adjust Rule Sensitivity:**

1. Navigate to: **Security → WAF → Managed rules**
2. Find the rule causing false positives
3. Click **Configure**
4. Change **Sensitivity**: High → Medium → Low
5. Save

### Attack Mitigation

**Immediate Actions:**

1. **Block Attacking IP**:
   - Navigate to: **Security → WAF → Tools → IP Access Rules**
   - Add rule:
     - **IP Address**: `<attacking_ip>`
     - **Action**: Block
     - **Note**: `Attack detected - <timestamp>`

2. **Enable Challenge Mode** (for suspicious traffic):
   - Navigate to: **Security → WAF → Managed rules**
   - Find relevant rule
   - Change **Action**: Block → Challenge

3. **Check Attack Pattern**:
   - Navigate to: **Security → Events**
   - Filter by time range
   - Review attack pattern (endpoints, IPs, user agents)

**Create Custom WAF Rule:**

1. Navigate to: **Security → WAF → Custom rules**
2. Click **Create rule**
3. Configure:
   - **Rule name**: `Block: <attack_pattern>`
   - **Expression**: `(http.request.uri.path contains "/api/v1/target" and http.request.method eq "POST" and rate(10m) > 100)`
   - **Action**: Block
4. Save rule

## Rate Limiting Incidents

### Legitimate User Blocks

**Identify Blocked User:**

1. **Check Rate Limit Events**:
   - Navigate to: **Security → WAF → Rate limiting rules**
   - Click on rule
   - View **Analytics** tab
   - Check blocked requests

2. **Verify Legitimacy**:
   - Check user IP address
   - Review request pattern
   - Confirm user identity (if possible)

**Temporary Bypass:**

**Via Dashboard:**
1. Navigate to: **Security → WAF → Tools → IP Access Rules**
2. Add rule:
   - **IP Address**: `<legitimate_user_ip>`
   - **Action**: Allow
   - **Note**: `Temporary bypass for legitimate user`

**Via API:**
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/<zone_id>/firewall/access_rules/rules" \
  -H "Authorization: Bearer <api_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "whitelist",
    "configuration": {
      "target": "ip",
      "value": "<legitimate_user_ip>"
    },
    "notes": "Temporary bypass for legitimate user"
  }'
```

**Adjust Rate Limit Threshold:**

1. Navigate to: **Security → WAF → Rate limiting rules**
2. Find rule causing blocks
3. Click **Edit**
4. Increase **Requests per minute** threshold
5. Save

**⚠️ Revert bypass/allowlist after issue resolved!**

### DDoS Response

**Immediate Actions:**

1. **Enable Under Attack Mode**:
   - Navigate to: **Security → Settings**
   - Toggle **Under Attack Mode**: On
   - This challenges all visitors with a JavaScript challenge

2. **Check DDoS Analytics**:
   - Navigate to: **Security → Events**
   - Filter by: **Action: Challenge** or **Action: Block**
   - Review attack volume and pattern

3. **Enable Rate Limiting** (if not already enabled):
   - Navigate to: **Security → WAF → Rate limiting rules**
   - Ensure rules are active
   - Consider lowering thresholds temporarily

**Automated DDoS Protection:**

Cloudflare automatically mitigates DDoS attacks. Monitor:
- **Security → Events**: Attack patterns
- **Analytics → Security**: Attack volume
- **Network → DDoS**: DDoS activity

## Cache Invalidation

### Emergency Cache Clear

**Purge Everything:**

**Via Dashboard:**
1. Navigate to: **Caching → Configuration → Purge Cache**
2. Select: **Purge Everything**
3. Click **Purge Everything**
4. Confirm

**Via API:**
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/<zone_id>/purge_cache" \
  -H "Authorization: Bearer <api_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "purge_everything": true
  }'
```

**Purge Specific Files:**

**Via Dashboard:**
1. Navigate to: **Caching → Configuration → Purge Cache**
2. Select: **Custom purge**
3. Enter URLs (one per line):
   ```
   https://example.com/api/v1/endpoint
   https://example.com/static/js/bundle.js
   ```
4. Click **Purge**

**Via API:**
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/<zone_id>/purge_cache" \
  -H "Authorization: Bearer <api_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      "https://example.com/api/v1/endpoint",
      "https://example.com/static/js/bundle.js"
    ]
  }'
```

**Purge by Tag:**

**Via API:**
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/<zone_id>/purge_cache" \
  -H "Authorization: Bearer <api_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["tag1", "tag2"]
  }'
```

### Automated Cache Purge on Deployment

**Add to CI/CD Pipeline:**

```yaml
# .github/workflows/staging.yml
- name: Purge Cloudflare Cache
  if: success()
  run: |
    curl -X POST "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/purge_cache" \
      -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{
        "files": [
          "https://${STAGING_DOMAIN}/",
          "https://${STAGING_DOMAIN}/_next/static/*"
        ]
      }'
  env:
    CLOUDFLARE_ZONE_ID: ${{ secrets.CLOUDFLARE_ZONE_ID }}
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    STAGING_DOMAIN: ${{ secrets.STAGING_DOMAIN }}
```

**Purge Script:**

```bash
#!/bin/bash
# purge-cloudflare-cache.sh

ZONE_ID="${CLOUDFLARE_ZONE_ID}"
API_TOKEN="${CLOUDFLARE_API_TOKEN}"
DOMAIN="${STAGING_DOMAIN}"

# Purge frontend static assets
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"files\": [
      \"https://${DOMAIN}/\",
      \"https://${DOMAIN}/_next/static/*\"
    ]
  }"

echo "Cache purged for ${DOMAIN}"
```

## SSL/TLS Incidents

### Certificate Issues

**Check Certificate Status:**

1. **Via Dashboard**:
   - Navigate to: **SSL/TLS → Overview**
   - Check certificate status
   - Review expiration date

2. **Via Command Line**:
   ```bash
   openssl s_client -connect <STAGING_DOMAIN>:443 -servername <STAGING_DOMAIN> < /dev/null 2>/dev/null | openssl x509 -noout -dates
   ```

**Certificate Expired:**

1. **Force Certificate Renewal**:
   - Navigate to: **SSL/TLS → Edge Certificates**
   - Click **Re-check now** (if available)
   - Or wait for automatic renewal (usually 7 days before expiration)

2. **Check Origin Certificate** (if using Full/Full Strict):
   - Ensure origin server has valid certificate
   - Check Traefik certificate status (see [05-Traefik.md](./05-Traefik.md))

**Certificate Mismatch:**

1. **Check SSL/TLS Mode**:
   - Navigate to: **SSL/TLS → Overview**
   - Ensure mode is **Full (strict)** for production
   - Check if origin certificate is valid

2. **Verify Origin Certificate**:
   ```bash
   # Check origin certificate
   openssl s_client -connect <origin_ip>:443 -servername <STAGING_DOMAIN> < /dev/null 2>/dev/null | openssl x509 -noout -subject -issuer
   ```

### Handshake Failures

**Check Handshake Errors:**

1. **Via Analytics**:
   - Navigate to: **Analytics → Security**
   - Check for SSL/TLS errors
   - Review error types

2. **Check Origin Configuration**:
   - Verify origin server supports TLS 1.2+
   - Check cipher suites
   - Verify certificate chain

**Troubleshooting:**

1. **Test SSL Connection**:
   ```bash
   openssl s_client -connect <STAGING_DOMAIN>:443 -servername <STAGING_DOMAIN>
   ```

2. **Check TLS Version**:
   ```bash
   openssl s_client -connect <STAGING_DOMAIN>:443 -servername <STAGING_DOMAIN> -tls1_2
   ```

3. **Review Cloudflare SSL Settings**:
   - Navigate to: **SSL/TLS → Edge Certificates**
   - Check **Minimum TLS Version** (should be 1.2 or higher)
   - Check **TLS 1.3** is enabled

## Bot Protection Tuning

### Adjusting Thresholds

**Check Bot Scores:**

1. Navigate to: **Security → Bots**
2. Review **Bot scores** and **Bot management** settings
3. Check **Bot analytics** for false positives/negatives

**Adjust Bot Fight Mode:**

1. Navigate to: **Security → Bots**
2. Select **Bot Fight Mode**:
   - **On**: Challenges all bots
   - **Off**: Allows all bots
   - **Auto**: Cloudflare determines

**Configure Bot Management (if available):**

1. Navigate to: **Security → Bots → Bot Management**
2. Adjust **Sensitivity**:
   - **Low**: More permissive
   - **Medium**: Balanced
   - **High**: More aggressive

3. Configure **Challenge behavior**:
   - **Interactive Challenge**: JavaScript challenge
   - **Non-Interactive Challenge**: CAPTCHA

### Handling Challenges

**Legitimate Bot Issues:**

1. **Add Bot Exception**:
   - Navigate to: **Security → WAF → Custom rules**
   - Create rule to allow specific user agents/IPs
   - Expression: `(http.user_agent contains "LegitimateBot" or ip.src eq "<bot_ip>")`
   - Action: Allow

2. **Verify Bot Identity**:
   - Check user agent
   - Verify IP address
   - Confirm with bot operator

**False Positives (Legitimate Users):**

1. **Lower Bot Sensitivity**:
   - Navigate to: **Security → Bots**
   - Reduce sensitivity temporarily
   - Monitor for false negatives

2. **Whitelist User IP**:
   - Navigate to: **Security → WAF → Tools → IP Access Rules**
   - Add rule: IP → Allow

## Zero Trust Access Troubleshooting

### Access Issues

**Check Zero Trust Policy:**

1. Navigate to: **Zero Trust → Access → Applications**
2. Find application policy
3. Review **Policy rules** and **Include/Exclude** conditions

**Verify IP Allowlist:**

1. Navigate to: **Zero Trust → Access → Applications → <app> → Policies**
2. Check **Include** rules for IP allowlists
3. Verify user IP is in allowlist

**Check User Identity:**

1. Navigate to: **Zero Trust → Access → Users**
2. Find user
3. Check **Groups** and **Access policies**

### Troubleshooting Steps

1. **Check Access Logs**:
   - Navigate to: **Zero Trust → Logs → Access**
   - Filter by user/IP
   - Review access attempts and results

2. **Test Access**:
   - Try accessing from allowed IP
   - Try accessing from blocked IP
   - Compare results

3. **Review Policy Order**:
   - Policies are evaluated in order
   - First matching policy applies
   - Check policy order in application settings

## Cloudflare Analytics Integration

### View Analytics

**Security Analytics:**

1. Navigate to: **Analytics → Security**
2. Review:
   - **Threats blocked**
   - **WAF events**
   - **Rate limit hits**
   - **Bot challenges**

**Performance Analytics:**

1. Navigate to: **Analytics → Performance**
2. Review:
   - **Cache hit ratio**
   - **Bandwidth saved**
   - **Request rate**

### Export Logs

**Enable Logpush (for detailed logs):**

1. Navigate to: **Analytics → Logs → Logpush**
2. Configure:
   - **Dataset**: HTTP Requests, Firewall Events, etc.
   - **Destination**: S3, GCS, Datadog, etc.
3. Enable Logpush

**Query Logs via API:**

```bash
curl -X GET "https://api.cloudflare.com/client/v4/zones/<zone_id>/logs/received?start=<timestamp>&end=<timestamp>" \
  -H "Authorization: Bearer <api_token>"
```

## DNS Failover

### Configure DNS Failover

1. Navigate to: **DNS → Records**
2. Add **A** or **AAAA** record:
   - **Name**: `<subdomain>`
   - **IPv4/IPv6**: `<primary_server_ip>`
   - **Proxy status**: Proxied
   - **TTL**: Auto

3. Add **Secondary record** (for failover):
   - **Name**: `<subdomain>`
   - **IPv4/IPv6**: `<backup_server_ip>`
   - **Proxy status**: Proxied
   - **TTL**: Auto

**Note**: Cloudflare does not provide automatic DNS failover. Use external DNS failover service or configure at application level.

## Verification Checklist

After any Cloudflare intervention:

1. **WAF rules are active**:
   - Navigate to: **Security → WAF → Managed rules**
   - Verify rules are enabled
   - Check no false positives

2. **Rate limiting is working**:
   - Test rate limit threshold
   - Verify legitimate users not blocked
   - Check analytics for rate limit hits

3. **Cache is purged** (if applicable):
   - Test URL after purge
   - Verify fresh content served
   - Check cache status headers

4. **SSL/TLS is valid**:
   ```bash
   openssl s_client -connect <STAGING_DOMAIN>:443 -servername <STAGING_DOMAIN> < /dev/null 2>/dev/null | openssl x509 -noout -dates
   # Expected: Valid dates, not expired
   ```

5. **No service disruption**:
   ```bash
   curl -I https://<STAGING_DOMAIN>/
   curl -I https://<STAGING_DOMAIN>/api/v1/health
   # Expected: 200 OK
   ```

## Related Runbooks

- [07-Security.md](./07-Security.md) - Security incidents and token revocation
- [05-Traefik.md](./05-Traefik.md) - Traefik troubleshooting
- [01-Incident-Checklist.md](./01-Incident-Checklist.md) - Incident triage
