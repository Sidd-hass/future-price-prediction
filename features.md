# Feature Completed: Automatic Authentication with TOTP

This document details the completed and operational feature that automates the daily Upstox authentication process using credentials and a Time-Based One-Time Password (TOTP) secret, eliminating manual browser interaction.

## How it works

The automatic silent authentication flow is fully integrated. If the required environment variables are set in `.env`, the system bypasses the local Flask callback server and generates a new access token programmatically.

## Configuration (.env)

```env
# Upstox Automatic Login Credentials
UPSTOX_USERNAME=your-mobile-number
UPSTOX_PASSWORD=your-password
UPSTOX_PIN_CODE=your-upstox-pin
UPSTOX_TOTP_SECRET=your-totp-secret-key
```

## Implementation Details

1. **Dependency Added**: Integrated the `upstox-totp` library for generating programmatic 2FA codes.
2. **Silent Verification**: `auth_server.py` checks for the presence of these environment variables on start.
3. **Execution**:
   - If present, `attempt_silent_login()` is executed. It simulates the login steps, fetches the auth token, and writes it directly to `token.txt`.
   - If absent, it seamlessly falls back to launching the local Flask callback server on port 5000 and prints the manual login dialog URL.
