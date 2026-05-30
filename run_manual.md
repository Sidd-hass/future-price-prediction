# Manual Run Guide for Futures‑Alert (Docker)

This document explains how to **create the required `token.txt` file**, build the Docker image, and run the container on a Windows machine.

---

## 1. Prerequisites
- **Docker Desktop** installed and running (Windows version).
- **PowerShell** (or Command Prompt) with access to the project folder.
- The project source located at `C:\Users\jal\Downloads\futures-alert\futures-alert`.

---

## 2. Create `token.txt`

You can obtain the `token.txt` access token either **automatically (recommended)** or **manually**.

### Method A: Automatically (Silent TOTP Login)
If you have configured your credentials in `.env`:
1. Open PowerShell and navigate to the project directory:
   ```powershell
   cd "C:\Users\jal\Downloads\futures-alert\futures-alert"
   ```
2. Activate your virtual environment and run the auth server:
   ```powershell
   .\venv\Scripts\activate
   python auth_server.py
   ```
   The script will log in silently, save `token.txt` in the root folder, and exit immediately.

### Method B: Manually (Browser Flow)
If you don't have automatic login credentials:
1. Run `python auth_server.py`.
2. Follow the login URL printed in the terminal, authenticate in the browser, and the browser redirect will save `token.txt` automatically.
*Alternatively*, you can manually paste your token:
```powershell
notepad token.txt
```
Paste the token, save and close.

---

## 3. Build the Docker Image
Make sure Docker Desktop is running, then build the image:
```powershell
docker build -t futures-alert .
```
- `-t futures-alert` tags the image with a friendly name.
- The trailing `.` tells Docker to use the `Dockerfile` in the current folder.

---

## 4. Run the Container
The container needs access to the `token.txt` file. Mount it as a volume so the code inside can read it.
```powershell
docker run --rm -v "${PWD}\token.txt:/app/token.txt" futures-alert
```
- `--rm` automatically removes the container after it exits.
- `-v "${PWD}\token.txt:/app/token.txt"` binds the host's `token.txt` into the container.

---

## 5. Common Issues & Fixes
- **Permission error when mounting** – Ensure Docker Desktop has file‑sharing permissions for the `C:\Users\jal\Downloads\futures-alert\futures-alert` folder (Docker Settings -> Resources -> File Sharing).
- **Container crashes** – Check logs with:
  ```powershell
  docker logs <container‑id>
  ```
  Verify the mount path matches what the code reads (`/app/token.txt`).

---

## 6. Summary Checklist
- [ ] Configure `.env` file with credentials.
- [ ] Run `python auth_server.py` to generate `token.txt`.
- [ ] Run `docker build -t futures-alert .`
- [ ] Run `docker run --rm -v "${PWD}\token.txt:/app/token.txt" futures-alert`
