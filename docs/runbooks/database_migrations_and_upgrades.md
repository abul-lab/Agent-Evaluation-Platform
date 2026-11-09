# Production Runbook: Database Migrations & Upgrade Procedures

**Classification**: Site Reliability Engineering (SRE) & DBA Playbook  
**System**: Agent Evaluation Platform (AEP) v1.0.0  

---

## 1. Migration Philosophy & Schema Evolution

AEP relies on **SQLModel** with automated SQLite schema initialization via `init_db()` in `app/db/session.py`.
- **Zero-Downtime Design**: Table additions and non-breaking column additions run during container boot inside the `lifespan` hook.
- **WAL Pragma Assurance**: Every database connection enforces:
  - `PRAGMA journal_mode=WAL;` (High concurrency, non-blocking reads during writes)
  - `PRAGMA foreign_keys=ON;` (Relational integrity enforcement across traces, evaluations, and workspaces)

---

## 2. Standard Platform Upgrade Procedure

To upgrade AEP from v1.0.0 to a future release (e.g. v1.1.0):

### Phase 1: Pre-Upgrade Verification
1. Verify system health on running cluster:
   ```bash
   curl -f http://localhost:8000/system/info
   ```
2. Take an automated hot snapshot backup (see [Backup Runbook](backup_and_disaster_recovery.md)).
3. Verify backup integrity before initiating deployment.

### Phase 2: Blue/Green or Rolling Container Upgrade
1. Pull the updated Git tag or Docker container image:
   ```bash
   git fetch --tags
   git checkout v1.1.0
   ```
2. Build updated images:
   ```bash
   docker compose build
   ```
3. Restart containers with zero volume loss:
   ```bash
   docker compose up -d --no-deps backend
   # Wait for backend healthcheck to reach 'healthy' state
   docker compose up -d --no-deps frontend
   ```

### Phase 3: Post-Upgrade Verification
1. Verify running version:
   ```bash
   curl -s http://localhost:8000/version | jq .
   ```
2. Verify all integrated modules:
   ```bash
   curl -s http://localhost:8000/system/info | jq .database_status
   ```
3. Run the automated verification test script:
   ```bash
   python examples/quickstart_api_walkthrough.py
   ```

---

## 3. Rollback Procedure

If the upgraded version encounters unexpected exceptions or fails health probes:

1. Roll back the Git checkout or Docker image tag to the previous stable release:
   ```bash
   git checkout v1.0.0
   docker compose up -d --build
   ```
2. If schema changes require rolling back data, execute the [Restore Procedure](backup_and_disaster_recovery.md#3-disaster-recovery--restore-testing) to restore the pre-upgrade snapshot.
3. Validate operational status at `http://localhost:8000/health`.

