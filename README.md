# SceneTap API (prototype)

Minimal FastAPI backend for Xiaomi Home scenes and devices that are online and expose a `toggle` action.

## Requirements

- Python 3.10+
- Network access from the machine running the API to Xiaomi's services

## Windows setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
add .env file with SCENETAP_API_KEY="put-your-superstrong-and-long-random-key"

## Run locally

```powershell
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000/docs`. Xiaomi endpoints require `Authorization: Bearer <token>`.

Example test:

```powershell
$token = "PASTE_TOKEN_HERE"
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Uri "http://127.0.0.1:8000/scenes" -Headers $headers
Invoke-RestMethod -Uri "http://127.0.0.1:8000/devices" -Headers $headers
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/devices/YOUR_DID/toggle" -Headers $headers
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/scenes/YOUR_SCENE_ID/run" -Headers $headers
```

The final two commands operate real devices/scenes. Use them only when ready.

## Endpoints

- `GET /scenes` — enabled manual scenes for the authenticated Xiaomi account. Only `scene_id`, `name`, and `home_id` are returned internally; the endpoint returns only the fields needed by the watch.
- `GET /devices` — online devices where the library exposes a `toggle` action. Returns only `did`, `name`, and `model`.
- `POST /scenes/{scene_id}/run` — executes an enabled manual scene belonging to the authenticated user.
- `POST /devices/{did}/toggle` — toggles an online device only if the library reports `toggle` as supported.

## Important notes

- This is a local prototype, not yet production-ready. Do not expose it publicly before configuring HTTPS, token revocation/rotation, rate limiting, backups, and a user-facing account-connection flow.
- `mijiaAPI` uses unofficial Xiaomi Home interfaces; compatibility and token lifetime are outside SceneTap's control.
- The library resolves `mijiaDevice` via device name in the verified code path. To avoid controlling the wrong device, this prototype omits duplicate online device names and rejects their toggle requests.
- On the tested version, `mijiaDevice.run_action("toggle")` returns `None` while successfully switching the device; the API therefore returns an acknowledgment only when no exception occurred.
- Each user gets a separate auth file. Never commit or share `data/`.

## Screenshots

![Image](./screenshots/Screenshot%202026-10-30%20083554.png)
![Image](./screenshots/Screenshot%202026-10-30%20085757.png)