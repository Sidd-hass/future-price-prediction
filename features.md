# Future Feature: Automatic Authentication with TOTP

This document outlines the proposed feature to automate the daily Upstox authentication process using your login credentials and a Time-Based One-Time Password (TOTP) secret, removing the need for manual browser interactions.

## How it will work

To enable automatic authentication, you will need to:
1. Enable TOTP 2FA on your Upstox profile (if you haven't already).
2. Copy the **TOTP Secret Key** (text key) shown during the TOTP setup.
3. Add your login mobile number, password, PIN, and TOTP secret key to your `.env` file.

## Environment Variables to Add

```env
# Upstox Automatic Login Credentials
UPSTOX_USERNAME=your-mobile-number
UPSTOX_PASSWORD=your-password
UPSTOX_PIN_CODE=your-upstox-pin
UPSTOX_TOTP_SECRET=your-totp-secret-key
```

## Proposed Implementation Plan

### 1. Update Dependencies
Add `upstox-totp>=0.1.0` to `requirements.txt`.

### 2. Update `auth_server.py`
Modify the authentication flow to attempt silent login using the `upstox-totp` library:
- If `UPSTOX_USERNAME`, `UPSTOX_PASSWORD`, `UPSTOX_PIN_CODE`, and `UPSTOX_TOTP_SECRET` are all set in the environment:
  - Generate the token using the `UpstoxTOTP` library.
  - Write it to `token.txt`.
  - Exit successfully without opening a browser.
- If they are not set, fall back to the manual Flask server redirect flow.
