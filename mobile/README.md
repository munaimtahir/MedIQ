# Exam Prep Mobile - Proof Shell

Minimal React Native app validating mobile readiness contracts (Tasks 172-174).

## Overview

This is a **proof shell** app that demonstrates:
- ✅ Login with token refresh
- ✅ Test package download with ETag caching
- ✅ Offline attempt queuing
- ✅ Batch sync with idempotency
- ✅ Queue status diagnostics

**Note**: This is a correctness-first shell, not a production-ready app.

## Prerequisites

- Node.js 18+
- npm or yarn
- Expo CLI: `npm install -g expo-cli` (or use `npx expo`)
- iOS Simulator (Mac) or Android Emulator

**Note**: Assets (icon.png, splash.png) should be added to `assets/` directory. Placeholder files exist for now.

## Setup

### 1. Install Dependencies

```bash
cd mobile
npm install
```

### 2. Configure Backend URL

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and set your backend URL:

```
EXPO_PUBLIC_API_BASE_URL=https://api.example.com
```

### 3. Run the App

```bash
# Start Expo dev server
npm start

# Or run on specific platform
npm run ios      # iOS Simulator
npm run android  # Android Emulator
npm run web      # Web browser
```

## Testing Offline Flow

### 1. Login

1. Open the app
2. Enter email/password
3. Tap "Login"
4. You should see the Home screen

### 2. Download Packages

1. Tap "Download Packages"
2. Tap "Download" on a package
3. Package is saved locally with ETag
4. Tap "Download" again → Should show "Package already up to date (304)"

### 3. Create Offline Attempt

1. Enable airplane mode (or disconnect network)
2. Tap "Offline Attempt Demo"
3. Select a downloaded package
4. Answer some questions
5. Tap "Save Offline Attempt"
6. Attempts are queued locally (no API call)

### 4. Sync When Online

1. Disable airplane mode (reconnect network)
2. Tap "Sync Now"
3. Queued attempts are synced in batches
4. Check "Queue Status" to see results

### 5. Queue Status

1. Tap "Queue Status"
2. View counts: pending/sent/acked/duplicate/rejected
3. View recent attempts with error codes
4. Optionally reset rejected attempts to pending

## Project Structure

```
mobile/
├── src/
│   ├── api/
│   │   └── client.ts          # API client with retry/refresh
│   ├── auth/
│   │   └── tokenStore.ts      # Token storage & refresh
│   ├── storage/
│   │   └── db.ts              # SQLite database
│   ├── offline/
│   │   ├── packageManager.ts  # Package download with ETag
│   │   └── attemptQueue.ts    # Attempt queue management
│   ├── sync/
│   │   └── syncService.ts     # Batch sync service
│   ├── screens/
│   │   ├── LoginScreen.tsx
│   │   ├── HomeScreen.tsx
│   │   ├── PackagesScreen.tsx
│   │   ├── OfflineAttemptScreen.tsx
│   │   ├── QueueStatusScreen.tsx
│   │   └── SyncScreen.tsx
│   └── types/
│       ├── api.ts             # API response types
│       └── storage.ts         # Database types
├── App.tsx                     # Main app with navigation
├── package.json
├── tsconfig.json
└── .env.example
```

## Backend Contracts

The app assumes these backend endpoints (from Tasks 172-174):

- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh tokens
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/tests/packages` - List packages
- `GET /api/v1/tests/packages/{id}` - Download package (ETag support)
- `POST /api/v1/sync/attempts:batch` - Batch sync

All errors return: `{ error_code, message, details, request_id }`

## Key Features

### Token Refresh

- Automatic refresh on 401
- Refresh lock prevents concurrent refreshes
- Error codes: `REFRESH_EXPIRED`, `REFRESH_REVOKED`, `REFRESH_TOKEN_REUSE`

### ETag Caching

- Saves ETag on package download
- Sends `If-None-Match` on subsequent requests
- Handles 304 Not Modified

### Offline Queue

- SQLite storage for attempts
- Idempotency keys per attempt
- Payload hash verification
- Status tracking: pending/sent/acked/duplicate/rejected

### Batch Sync

- Processes up to 50 attempts per batch
- Handles partial failures
- Preserves queue state
- Never loses acked/duplicate items

## Troubleshooting

### "Network Error"

- Check `EXPO_PUBLIC_API_BASE_URL` in `.env`
- Ensure backend is running and accessible
- Check CORS settings on backend

### "Invalid refresh token"

- Token may have expired
- Try logging out and logging in again
- Check backend token expiry settings

### "Package download failed"

- Ensure package exists on backend
- Check authentication token
- Verify ETag header handling

### SQLite errors

- Database is created automatically on first run
- If issues persist, delete app and reinstall

## Development

### TypeScript

All code is TypeScript. Run type checking:

```bash
npx tsc --noEmit
```

### Debugging

- Use React Native Debugger
- Check console logs in Expo dev tools
- Use Queue Status screen for diagnostics

## Next Steps (Task 175+)

- [ ] Push notifications for sync status
- [ ] Background sync scheduling
- [ ] Better UX/UI design
- [ ] Full exam mode implementation
- [ ] Analytics integration
- [ ] Error reporting
- [ ] Offline package version management
- [ ] Sync conflict resolution UI

## Notes

- **Minimal UI**: This is a proof shell, not production-ready
- **No Secrets**: All config via environment variables
- **TypeScript**: Full type safety
- **Offline-First**: Works without network (except sync)

---

**Status**: Proof Shell Complete  
**Validates**: Tasks 172-174 mobile contracts
