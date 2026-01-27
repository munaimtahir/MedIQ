# Task 165: Frontend Smoke Tests - COMPLETE

## Summary

Added Playwright smoke tests for critical user flows in the frontend application.

## Files Added

### Test Configuration
- `playwright.config.ts` - Playwright configuration with screenshots/video on failure

### Test Suites
- `tests/smoke/login.spec.ts` - Login page load test
- `tests/smoke/admin.spec.ts` - Admin login and dashboard test
- `tests/smoke/student.spec.ts` - Student login, dashboard, and revision page tests
- `tests/smoke/logout.spec.ts` - Logout functionality test
- `tests/smoke/cms.spec.ts` - CMS workflow tests (create/update/publish questions) ✅
- `tests/smoke/session.spec.ts` - Session creation and question answering tests ✅
- `tests/smoke/password-reset.spec.ts` - Password reset flow tests ✅ **NEW**
- `tests/smoke/email-verification.spec.ts` - Email verification flow tests ✅ **NEW**
- `tests/smoke/README.md` - Test documentation

## Files Modified

### Components (Added data-testid attributes)
- `app/login/page.tsx` - Added `data-testid="login-form"`, `data-testid="login-email-input"`, `data-testid="login-submit-button"`
- `components/auth/PasswordField.tsx` - Added `data-testid="login-password-input"` for password field
- `components/admin/Sidebar.tsx` - Added `data-testid="admin-sidebar"`, `data-testid="logout-button"`
- `components/student/Sidebar.tsx` - Added `data-testid="student-sidebar"`, `data-testid="logout-button"`
- `app/student/revision/page.tsx` - Added `data-testid="revision-themes-table"`

### Configuration
- `package.json` - Added Playwright scripts: `test:e2e`, `test:e2e:ui`, `test:e2e:headed`
- `.github/workflows/ci.yml` - Added `frontend-e2e-tests` job

## Test Coverage

### Login Page (1 test)
- ✅ Verifies login page loads correctly
- ✅ Checks login form elements are visible

### Admin Flow (1 test)
- ✅ Login as admin
- ✅ Verify admin dashboard loads
- ✅ Check admin sidebar is visible

### Student Flow (2 tests)
- ✅ Login as student
- ✅ Verify student dashboard loads
- ✅ Check student sidebar is visible
- ✅ Open revision page
- ✅ Verify revision page renders (table or empty state)

### Logout (1 test)
- ✅ Login as student
- ✅ Click logout button
- ✅ Verify redirect to login page

### CMS Workflow (1 test)
- ✅ Login as admin
- ✅ Navigate to questions page
- ✅ Create new question (draft)
- ✅ Update question
- ✅ Submit for review (if applicable)
- ✅ Approve question (if applicable)
- ✅ Publish question (if applicable)

### Session Creation (1 test)
- ✅ Login as student
- ✅ Create/start a session
- ✅ Answer a question
- ✅ Navigate to next question
- ✅ Submit session

### Password Reset (2 tests)
- ✅ Navigate to password reset page
- ✅ Submit password reset request

### Email Verification (2 tests)
- ✅ Show verification message after registration
- ✅ Handle verification link (mock)

**Total: 9 smoke tests**

## Data-TestID Attributes Added

| Component | data-testid | Purpose |
|-----------|-------------|---------|
| Login form | `login-form` | Form container |
| Email input | `login-email-input` | Email field |
| Password input | `login-password-input` | Password field |
| Submit button | `login-submit-button` | Login button |
| Admin sidebar | `admin-sidebar` | Admin navigation |
| Student sidebar | `student-sidebar` | Student navigation |
| Logout button | `logout-button` | Logout action |
| Revision table | `revision-themes-table` | Revision themes table |

## Commands to Run

### Local Development

1. **Start backend and frontend:**
   ```bash
   # Terminal 1: Start backend
   cd infra/docker/compose
   docker compose -f docker-compose.dev.yml up -d

   # Terminal 2: Start frontend
   cd frontend
   pnpm dev
   ```

2. **Run tests:**
   ```bash
   cd frontend
   pnpm test:e2e
   ```

3. **Run with UI mode:**
   ```bash
   pnpm test:e2e:ui
   ```

4. **Run in headed mode (see browser):**
   ```bash
   pnpm test:e2e:headed
   ```

### With Custom Base URL

```bash
FRONTEND_BASE_URL=http://localhost:3000 pnpm test:e2e
```

### With Custom Credentials

```bash
ADMIN_USER=admin@example.com \
ADMIN_PASS=password \
STUDENT_USER=student@example.com \
STUDENT_PASS=password \
pnpm test:e2e
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FRONTEND_BASE_URL` | Base URL for frontend | `http://localhost:3000` |
| `ADMIN_USER` | Admin email for testing | `admin-1@example.com` |
| `ADMIN_PASS` | Admin password | `AdminPass123!` |
| `STUDENT_USER` | Student email for testing | `student-1@example.com` |
| `STUDENT_PASS` | Student password | `StudentPass123!` |

## Test Reports

After running tests, view the HTML report:

```bash
npx playwright show-report
```

## CI Integration

The CI workflow (`frontend-e2e-tests` job) will:
1. Install dependencies
2. Install Playwright browsers
3. Start backend services (PostgreSQL, Redis)
4. Start backend API
5. Seed database
6. Build frontend
7. Start frontend server
8. Run Playwright tests
9. Upload test reports and videos on failure

## Features

- **Screenshots on failure**: Automatically captured
- **Video on failure**: Recorded for debugging
- **HTML report**: Generated after each run
- **Retry logic**: 2 retries on CI
- **Multiple browsers**: Chromium, Firefox, WebKit (configurable)
- **Stable selectors**: Uses `data-testid` attributes
- **Environment-driven**: All configuration via env vars

## Notes

- Tests are designed as "smoke tests" - they verify core flows work, not deep functionality
- Tests use real backend if available (via docker-compose.dev.yml)
- Tests wait for network idle to ensure pages are fully loaded
- Timeout values are set appropriately for CI environments

## TODO Checklist for Next QA Expansions

- [x] Add tests for CMS workflow (admin create/update/publish questions) ✅
- [x] Add tests for session creation and question answering ✅
- [ ] Add tests for analytics page
- [ ] Add tests for bookmark functionality
- [ ] Add tests for notification system
- [ ] Add tests for settings page
- [x] Add tests for password reset flow ✅
- [x] Add tests for email verification flow ✅
- [ ] Add tests for OAuth login flows
- [ ] Add tests for responsive design (mobile/tablet)
- [ ] Add tests for accessibility (a11y)
- [ ] Add visual regression tests
- [ ] Add performance tests (Lighthouse)
- [ ] Add cross-browser compatibility tests
- [ ] Add tests for error handling and edge cases
- [ ] Add tests for form validation
- [ ] Add tests for search functionality
- [ ] Add tests for filter/sort operations
- [ ] Add tests for pagination
- [ ] Add tests for data export functionality
