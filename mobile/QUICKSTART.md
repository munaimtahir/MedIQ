# Quick Start Guide

## Setup (5 minutes)

```bash
# 1. Install dependencies
cd mobile
npm install

# 2. Configure backend URL
cp .env.example .env
# Edit .env and set: EXPO_PUBLIC_API_BASE_URL=https://your-backend.com

# 3. Start Expo
npm start
```

## Testing Flows

### 1. Login Flow
- Enter email/password
- Tap "Login"
- Should navigate to Home screen

### 2. Package Download (ETag Test)
- Tap "Download Packages"
- Tap "Download" on a package → Downloads (200 OK)
- Tap "Download" again → Shows "already up to date" (304 Not Modified)

### 3. Offline Attempt
- Enable airplane mode
- Tap "Offline Attempt Demo"
- Select package → Answer questions → Tap "Save Offline Attempt"
- Attempts queued locally (no network required)

### 4. Batch Sync
- Disable airplane mode
- Tap "Sync Now"
- Check "Queue Status" → See acked/duplicate/rejected counts

## Troubleshooting

**"Network Error"**
- Check `.env` file has correct `EXPO_PUBLIC_API_BASE_URL`
- Ensure backend is running
- Check CORS settings

**"Invalid refresh token"**
- Token expired → Logout and login again
- Check backend token expiry settings

**SQLite errors**
- Database auto-creates on first run
- If issues: delete app and reinstall

## Notes

- Assets (icon.png, splash.png) need to be added to `assets/` directory
- For production: ensure expo-crypto is working for SHA-256 hashing
- NetInfo may need additional setup on some platforms
