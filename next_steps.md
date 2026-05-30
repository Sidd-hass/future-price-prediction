# Next Steps & Pending Tasks

This document outlines the pending setup steps and recommended future improvements for the **Futures Alert** system so you can take over from here.

## 1. Immediate Action Items (Setup)

- [ ] **Configure Credentials in `.env`**:
  Add your Upstox credentials and TOTP secret key to the [local .env file](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/.env):
  ```env
  UPSTOX_USERNAME=your-mobile-number
  UPSTOX_PASSWORD=your-password
  UPSTOX_PIN_CODE=your-upstox-pin
  UPSTOX_TOTP_SECRET=your-totp-secret-key
  ```
- [ ] **Verify Silent Authentication**:
  Run the authentication server manually to ensure it successfully generates `token.txt` without prompting for a browser:
  ```bash
  python auth_server.py
  ```
- [ ] **Confirm Main App Starts**:
  Run the continuous scanner with the `--force` flag (to run outside market hours) to verify the new token works:
  ```bash
  python main.py --force
  ```

---

## 2. Recommended Next Technical Enhancements

### 🛡️ Automatic Token Refresh on App Startup
* **Current Behavior**: If `token.txt` is missing or expired, `main.py` prints an error and exits, requiring the user to run `python auth_server.py` manually.
* **Proposed Enhancement**: Modify `main.py` to import and call `attempt_silent_login()` automatically if `token.txt` is missing or if a `401 Unauthorized` response is received from the Upstox API, ensuring fully hands-off operations.

### 🔌 WebSocket Robustness & Reconnect Logic
* **Current Behavior**: `data_feed.py` opens a WebSocket connection to Upstox. If there is a network glitch or session drop, it may remain disconnected.
* **Proposed Enhancement**: Implement exponential backoff reconnection logic within `PriceFeed` in [data_feed.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/data_feed.py) to automatically reconnect if the socket drops.

### 🐳 Docker Verification
* **Current Behavior**: Docker setup is outlined in the Dockerfile and docker-compose.yml.
* **Proposed Enhancement**: Test building and running the container with the newly configured environment credentials:
  ```bash
  docker-compose up --build -d
  ```
  Ensure `token.txt` and `instruments_cache.csv` are persisted on the host machine using volumes.
