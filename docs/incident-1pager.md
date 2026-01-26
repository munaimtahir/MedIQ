# Exam-Day Incident Response Playbook (1-Pager)

**Last Updated:** 2026-01-25  
**For:** On-call engineers during exam periods

---

## 🚨 Severity Definitions

| Severity | Impact | Response Time | Example |
|----------|--------|---------------|---------|
| **SEV1** | Exam blocked, students cannot start/submit | **Immediate** | DB down, API 5xx >10%, Redis required but down |
| **SEV2** | Degraded experience, some features broken | **15 minutes** | Slow p95 (>2s), elevated 5xx (<10%), Redis degraded |
| **SEV3** | Minor issues, non-critical | **1 hour** | Single endpoint failing, non-exam features affected |

---

## 📋 Order of Operations (Exam-Time)

**⚠️ CRITICAL: Execute in this exact order. Do not skip steps.**

### Step 1: Enable EXAM_MODE (if not already)
```bash
# Via API (requires admin auth)
curl -X POST https://api.<DOMAIN>/v1/admin/system/exam-mode \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "reason": "Exam day - enabling exam mode",
    "confirmation_phrase": "ENABLE EXAM MODE"
  }'
```
**What it does:** Freezes question content, disables admin mutations, enables exam-specific behavior.

### Step 2: If Instability Detected → Enable FREEZE_UPDATES
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/algorithms/runtime/freeze_updates \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Exam instability - freezing learning updates",
    "confirmation_phrase": "FREEZE UPDATES"
  }'
```
**What it does:** Blocks all learning state mutations (BKT, FSRS, difficulty updates). System becomes read-only for learning algorithms. **Students can still take exams.**

### Step 3: If Critical → Switch to FALLBACK Profile
```bash
curl -X POST https://api.<DOMAIN>/v1/admin/algorithms/runtime/switch \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "V0_FALLBACK",
    "reason": "Exam day - critical algorithm issue, switching to fallback",
    "confirmation_phrase": "SWITCH TO FALLBACK PROFILE"
  }'
```
**What it does:** Switches all algorithms to v0 (baseline). **Note:** Requires two-person approval if police mode enabled. **Active sessions use snapshot config (not affected).**

---

## 🔥 Common Incidents & Responses

### DB Saturation (SEV1)
**Symptoms:** Slow queries, connection pool exhaustion, timeouts

**Immediate Actions:**
1. Check DB connections: `docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "SELECT count(*) FROM pg_stat_activity;"`
2. Check slow queries: `docker exec exam_platform_postgres psql -U exam_user -d exam_platform -c "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 10;"`
3. **Enable FREEZE_UPDATES** (reduces write load)
4. Kill long-running queries if safe: `SELECT pg_terminate_backend(pid);`
5. Scale DB connections if possible (requires config change)

**Escalation:** If persists >5min, consider read-only mode (FREEZE_UPDATES already enabled).

### Redis Down (SEV1 if REDIS_REQUIRED=true, SEV2 if optional)
**Symptoms:** Rate limiting fails, session blacklist fails, cache misses

**Check:**
```bash
docker exec exam_platform_redis redis-cli PING
# Should return: PONG
```

**If REDIS_REQUIRED=true:**
- **Immediate:** System may be down. Check `/ready` endpoint.
- Restart Redis: `docker restart exam_platform_redis`
- Verify: `curl https://api.<DOMAIN>/v1/ready`

**If REDIS_REQUIRED=false:**
- System degrades gracefully (rate limiting fails open)
- Restart Redis when convenient
- Monitor for rate limit abuse

### Elevated 5xx Errors (>10% = SEV1, <10% = SEV2)
**Symptoms:** `/ready` shows degraded/down, error logs spike

**Immediate Actions:**
1. Check error logs: `docker logs exam_platform_backend --tail=100 | grep -i "error\|exception\|500"`
2. Check Traefik access logs: `docker logs exam_platform_traefik --tail=100 | grep " 5[0-9][0-9] "`
3. Check metrics: `curl -H "Authorization: Bearer <ADMIN_TOKEN>" https://api.<DOMAIN>/v1/admin/observability/metrics`
4. **Enable FREEZE_UPDATES** if learning algorithms causing issues
5. **Switch to FALLBACK** if v1 algorithms misbehaving

**Common Causes:**
- DB connection pool exhausted → Enable FREEZE_UPDATES
- Algorithm computation timeout → Switch to FALLBACK
- Memory pressure → Check container limits, restart if needed

### Slow p95 (>2s = SEV2)
**Symptoms:** Students report slow page loads, metrics show high latency

**Immediate Actions:**
1. Check metrics: `curl -H "Authorization: Bearer <ADMIN_TOKEN>" https://api.<DOMAIN>/v1/admin/observability/metrics | jq '.latency_p95'`
2. Identify slow routes (p95 >2000ms)
3. **Enable FREEZE_UPDATES** if learning updates causing slowness
4. Check DB query performance (see DB Saturation)
5. Check Redis latency: `docker exec exam_platform_redis redis-cli --latency`

**If persists:** Consider switching to FALLBACK profile.

---

## 📞 Communication Template

**Subject:** [SEV1/2/3] Exam Platform - [Brief Description]

**Body:**
```
Incident: [Description]
Severity: SEV[X]
Time: [UTC timestamp]
Impact: [X students affected / [specific feature broken]]

Actions Taken:
- [ ] EXAM_MODE enabled
- [ ] FREEZE_UPDATES enabled (if applicable)
- [ ] FALLBACK profile activated (if applicable)
- [ ] [Other actions]

Status: [Investigating / Mitigated / Resolved]
ETA: [If known]

Next Update: [Time]
```

---

## ✅ Post-Incident Checklist

**Within 1 hour:**
- [ ] Export audit logs: `SELECT * FROM audit_log WHERE created_at >= '<incident_start>' ORDER BY created_at;`
- [ ] Document root cause (create `docs/incidents/YYYY-MM-DD-<description>.md`)
- [ ] Review system flags state: `SELECT * FROM system_flags;`
- [ ] Check algorithm runtime config: `SELECT * FROM algo_runtime_config;`

**Within 24 hours:**
- [ ] Complete root cause analysis document
- [ ] Review monitoring gaps (what should have alerted earlier?)
- [ ] Update this playbook if new patterns discovered
- [ ] Schedule post-mortem if SEV1

---

## 🔗 Quick Links

- **Health Check:** `https://api.<DOMAIN>/v1/health`
- **Readiness:** `https://api.<DOMAIN>/v1/ready`
- **Metrics:** `https://api.<DOMAIN>/v1/admin/observability/metrics` (admin only)
- **System Info:** `https://api.<DOMAIN>/v1/admin/system/info` (admin only)
- **Command Reference:** See `docs/exam-day-commands.md`

---

## ⚠️ Safety Reminders

1. **Never disable EXAM_MODE during active exam** (unless explicitly instructed)
2. **FREEZE_UPDATES is reversible** - safe to enable if unsure
3. **FALLBACK switch requires two-person approval** if police mode enabled
4. **Active sessions use snapshot config** - profile switches don't affect in-progress exams
5. **Always provide reason** when toggling flags (audit trail)

---

**Emergency Contact:** [Add on-call contact info]
