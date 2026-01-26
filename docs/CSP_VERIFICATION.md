# CSP Implementation Verification Checklist

## ✅ Implementation Complete

### Frontend
- [x] `frontend/middleware.ts` - CSP headers middleware created
- [x] `Content-Security-Policy-Report-Only` header configured
- [x] `Report-To` header configured
- [x] API URL handling (supports both `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_API_URL`)

### Backend
- [x] `POST /v1/security/csp-report` endpoint created
- [x] Rate limiting configured (100/min per IP)
- [x] Database model `CSPReport` created
- [x] Alembic migration `046_add_csp_reports_table.py` created
- [x] Tests passing (5/5)

### Documentation
- [x] `docs/security.md` updated with CSP section
- [x] Rollout plan documented (3 phases)

## 🔍 Verification Steps

### 1. Check CSP Headers in Browser
1. Start the application (frontend + backend)
2. Open browser DevTools → Network tab
3. Load any page
4. Check response headers for:
   - `Content-Security-Policy-Report-Only` (should be present)
   - `Report-To` (should be present)

### 2. Test CSP Report Collection
1. Trigger a CSP violation (e.g., try to load an external script)
2. Check backend logs for CSP report entries
3. Query database: `SELECT * FROM csp_reports ORDER BY created_at DESC LIMIT 10;`

### 3. Verify No UI Breakage
- [ ] All pages load correctly
- [ ] No console errors related to CSP
- [ ] All features work as expected

## 📊 Next Phase: Data Collection

Once CSP is deployed in report-only mode:

1. **Monitor Reports** (1-2 weeks):
   - Query `csp_reports` table regularly
   - Identify common violations
   - Categorize by `violated_directive` and `blocked_uri`

2. **Analyze Patterns**:
   ```sql
   -- Most common violations
   SELECT violated_directive, COUNT(*) as count
   FROM csp_reports
   GROUP BY violated_directive
   ORDER BY count DESC;
   
   -- Most blocked URIs
   SELECT blocked_uri, COUNT(*) as count
   FROM csp_reports
   WHERE blocked_uri IS NOT NULL
   GROUP BY blocked_uri
   ORDER BY count DESC
   LIMIT 20;
   ```

3. **Plan Policy Tightening**:
   - Remove `unsafe-inline` from `script-src` (use nonces/hashes)
   - Remove `unsafe-inline` from `style-src` (use nonces/hashes)
   - Add specific domains for external resources
   - Test in report-only mode again

4. **Switch to Enforcing Mode**:
   - Change `Content-Security-Policy-Report-Only` to `Content-Security-Policy`
   - Monitor for false positives
   - Adjust as needed

## 🚨 Troubleshooting

### CSP Headers Not Appearing
- Check that `middleware.ts` is in `frontend/` root
- Verify Next.js is using the middleware (check build logs)
- Ensure route matcher is correct

### Reports Not Being Collected
- Check backend logs for errors
- Verify database migration ran: `alembic current`
- Check rate limiting (should allow 100/min per IP)
- Verify API URL in CSP header matches backend URL

### Too Many Reports
- Adjust sampling in `backend/app/api/v1/endpoints/security.py`
- Consider time-based sampling (e.g., 1% of reports)
- Add filtering for known false positives
