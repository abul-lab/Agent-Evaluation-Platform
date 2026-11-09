# Deployment Guide — Agent Evaluation Platform (AEP)

**Version**: 1.0.0  
**Scope**: Running AEP locally, with Docker Compose, and behind a reverse proxy.

Read section 7 (security checklist) before exposing the service to any network other than your own machine.

---

## 1. System Requirements

| Resource | Minimum (single user / evaluation) | Recommended (shared team) |
| :--- | :--- | :--- |
| **CPU** | 2 vCPU | 4 vCPU |
| **Memory** | 2 GB RAM | 4 GB RAM |
| **Disk** | 10 GB SSD | 20 GB SSD (database grows with traces) |
| **Container Engine** | Docker Engine 24+ & Compose v2 | Docker Engine 26+ & Compose v2 |

AEP runs a single backend process with a SQLite database. It is designed for one backend instance. It is not horizontally scalable as shipped.

---

## 2. Configuration Reference

### 2.1. Backend (`backend/app/core/config.py`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | One of `development`, `test`, `staging`, `production`. Anonymous access is only possible in `development`. |
| `ALLOW_ANONYMOUS_VIEWER` | `false` | When `true` **and** `ENVIRONMENT=development`, anonymous callers get read-only VIEWER access. Ignored in every other environment. |
| `CORS_ALLOWED_ORIGINS` | unset | Comma-separated browser origins, for example `https://aep.example.com`. Required outside `development` and `test`. Wildcards are rejected. In development and test it defaults to `http://localhost:3000,http://127.0.0.1:3000`. |
| `DATABASE_URL` | `sqlite:///./agent_eval.db` | SQLAlchemy URL. In containers: `sqlite:////app/data/agent_eval.db`. |
| `PROJECT_NAME` | `Agent Evaluation Platform` | Display name. |
| `VERSION` | `1.0.0` | Reported by `/version`. |
| `BUILD_DATE` | `2026-11-08T12:00:00Z` | Reported by `/version`. Set it from your build pipeline. |
| `COMMIT_SHA` | `unknown` | Reported by `/version`. Set it from your build pipeline (for example `git rev-parse HEAD`). |

The application refuses to start if `CORS_ALLOWED_ORIGINS` is missing outside development or test, or if it contains `*`.

### 2.2. Frontend (build time)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Backend API base **including** `/api/v1`. It is inlined when the frontend is built, so changing it requires a rebuild. In Docker Compose pass it as a build argument (already configured). |

Do not put API keys in `NEXT_PUBLIC_*` variables. They are visible to every visitor. See section 6.

---

## 3. Docker Compose Deployment

The repository's `docker-compose.yml` runs the backend and frontend in production mode:

```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - ALLOW_ANONYMOUS_VIEWER=false
      - CORS_ALLOWED_ORIGINS=http://localhost:3000
      - DATABASE_URL=sqlite:////app/data/agent_eval.db
    volumes:
      - aep_data:/app/data
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy

volumes:
  aep_data:
    driver: local
```

The backend image runs as the non-root user `app`. The frontend image runs as `node`. Each image excludes `.env` files, SQLite databases, `node_modules`, and `.next` through its `.dockerignore`.

### 3.1. Start the stack

```bash
docker compose up -d --build
```

### 3.2. Create the first ADMIN key

Production requires an API key for every operation, so the first key is created inside the backend container:

```bash
docker compose exec backend python scripts/create_admin_key.py --name "bootstrap-admin"
```

The raw key is printed once. Store it in your secret manager. Then use the key to create ENGINEER keys for CI jobs and VIEWER keys for dashboards, and revoke the bootstrap key if it is no longer needed:

```bash
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer $AEP_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "ci-runner", "role": "ENGINEER", "expires_in_days": 90}'
```

### 3.3. Use the dashboard with a key

The dashboard calls the API from the browser and does not have a login screen. Until one is added, store a key in the browser:

```js
localStorage.setItem("aep_api_key", "aep_...")
```

Use a VIEWER key for read-only dashboards. An ADMIN key is required for the demo data button and for workspace or policy changes. See SECURITY.md, risk R2, before using this in a shared environment.

---

## 4. Reverse Proxy and TLS (Nginx)

AEP does not terminate TLS itself. Put a reverse proxy in front of both services. The proxy must forward every API path, including the OTLP path `/v1/traces`.

```nginx
server {
    listen 80;
    server_name aep.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name aep.example.com;

    ssl_certificate /etc/ssl/certs/aep.crt;
    ssl_certificate_key /etc/ssl/private/aep.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 16m;   # OTLP payloads are capped at 15 MB by the backend

    # Frontend dashboard
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API, OTLP ingestion, and health probes
    location ~ ^/(api|health|version|system|v1/traces) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

After you put the dashboard behind `https://aep.example.com`:

- Set `CORS_ALLOWED_ORIGINS=https://aep.example.com` on the backend.
- Rebuild the frontend with `NEXT_PUBLIC_API_URL=https://aep.example.com/api/v1`.

Apply request rate limits at this layer (for example `limit_req`). The backend's own collector limiter is per process only.

---

## 5. Storage Persistence and SQLite Backups

AEP initializes SQLite in WAL mode with foreign keys enabled (`PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`).

### Online backup

```bash
docker compose exec backend python -c '
import sqlite3
src = sqlite3.connect("/app/data/agent_eval.db")
dst = sqlite3.connect("/app/data/agent_eval_backup.db")
src.backup(dst)
dst.close()
src.close()
print("Backup complete.")
'
```

Copy the backup out of the volume and store it encrypted. The database contains webhook URLs in plaintext (SECURITY.md, R3), so treat backups as secrets.

---

## 6. Health and Monitoring Endpoints

| Endpoint | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /health` | none | Liveness probe used by Compose. |
| `GET /api/v1/health` | none | API health with version and environment. |
| `GET /version` | none | Version, build date, and commit SHA. |
| `GET /api/v1/system/info` | none | Module list and database status. Restrict at the proxy if you do not want to publish it (SECURITY.md, R9). |

All other endpoints require an API key.

---

## 7. Production Security Checklist

Complete this list before exposing the service:

- [ ] `ENVIRONMENT=production` and `ALLOW_ANONYMOUS_VIEWER=false` (the defaults; do not override them).
- [ ] `CORS_ALLOWED_ORIGINS` lists only your dashboard origin(s), using `https://`.
- [ ] TLS terminates at the reverse proxy, and HTTP redirects to HTTPS.
- [ ] A bootstrap ADMIN key was created on the server, stored in a secret manager, and used only for administration. CI jobs use ENGINEER keys with an expiry date.
- [ ] Keys are revoked when a person or pipeline leaves. Review `GET /api/v1/auth/api-keys` regularly.
- [ ] Rate limits are configured at the reverse proxy.
- [ ] The database volume and backups are encrypted and access-controlled.
- [ ] Egress from the backend is restricted, so it cannot reach internal networks through webhook hostnames (SECURITY.md, R4).
- [ ] The commit SHA and build date are set from your pipeline.
- [ ] `docker compose config` shows no secrets in the rendered file.

---

## 8. Dependency Management

- **Backend runtime**: `backend/requirements.txt` (pinned). Used by the backend container.
- **Backend development**: `backend/requirements-dev.txt` (pinned). Used by CI for tests, linting, and type checking.
- Edit the abstract requirements in `backend/requirements.in` and `backend/requirements-dev.in`, then regenerate the locks for Python 3.11:

  ```bash
  cd backend
  uv pip compile requirements.in --python-version 3.11 -o requirements.txt
  uv pip compile requirements-dev.in --python-version 3.11 -o requirements-dev.txt
  ```

- **Frontend**: `frontend/package-lock.json`. Install with `npm ci`.

---

## 9. Upgrading from Earlier Development Builds

These changes are breaking for existing clients and scripts:

| Change | Action |
| :--- | :--- |
| Anonymous requests no longer have admin rights. Anonymous writes and most anonymous reads are rejected. | Create an API key and send it as `Authorization: Bearer <key>`. |
| OTLP ingestion (`/api/v1/otel/collector`, `/v1/traces`) requires an ADMIN or ENGINEER key. | Add the key to the OpenTelemetry exporter headers. |
| Default `ENVIRONMENT` is `production`. | Set `ENVIRONMENT=development` for local work. |
| `CORS_ALLOWED_ORIGINS` is required outside development. | Set it to your dashboard origin. |
| The notification channel response returns `webhook_url_masked` instead of `webhook_url`. | Update any client that read `webhook_url`. |
| Webhook URLs must use HTTPS and may not target localhost or private IPs. | Update channels that use HTTP or internal hosts. |
| `POST /api/v1/workspaces/demo/seed` requires an ADMIN key. | Use an ADMIN key. |
| Demo and example scripts send `AEP_API_KEY` when it is set. | Export `AEP_API_KEY`. |
| The default `COMMIT_SHA` is `unknown`. | Set it from your build pipeline. |
