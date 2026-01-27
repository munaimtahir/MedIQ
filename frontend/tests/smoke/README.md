# Frontend Smoke Tests

Basic smoke tests for critical user flows using Playwright.

## Test Coverage

- **Login Page**: Verifies login page loads correctly
- **Admin Flow**: Login as admin and verify admin dashboard loads
- **Student Flow**: Login as student, verify dashboard, and check revision page
- **Logout**: Verify logout functionality works

## Running Tests

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

## Test Selectors

Tests use `data-testid` attributes for stable selectors:

- `login-form`: Login form container
- `login-email-input`: Email input field
- `login-password-input`: Password input field
- `login-submit-button`: Submit button
- `admin-sidebar`: Admin sidebar navigation
- `student-sidebar`: Student sidebar navigation
- `logout-button`: Logout button
- `revision-themes-table`: Revision themes table

## Notes

- Tests are designed to be "smoke tests" - they verify core flows work, not deep functionality
- Tests use real backend if available (via docker-compose.dev.yml)
- Screenshots and videos are captured on failure
- Tests retry up to 2 times on CI
