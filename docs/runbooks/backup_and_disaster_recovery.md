# Production Runbook: Backup & Disaster Recovery

**Classification**: Site Reliability Engineering (SRE) Playbook  
**System**: Agent Evaluation Platform (AEP) v1.0.0  
**RPO (Recovery Point Objective)**: ≤ 1 hour  
**RTO (Recovery Time Objective)**: ≤ 15 minutes  

---

## 1. Architecture of Persistence
AEP utilizes SQLite in Write-Ahead Logging (`WAL`) mode with persistent data stored at:
- Docker Container Path: `/app/data/agent_eval.db`
- Host Named Volume: `aep_data`
- Associated WAL Files: `agent_eval.db-wal` and `agent_eval.db-shm`

---

## 2. Automated Hot Backup Procedure

Because WAL mode decouples concurrent readers and writers, hot backups can be taken without locking or stopping the application service.

### Daily Backup Cron Job
Run the following script on the host node daily at 02:00 UTC:

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/aep"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_FILE="${BACKUP_DIR}/aep_backup_${TIMESTAMP}.db"

mkdir -p "${BACKUP_DIR}"

echo "[AEP SRE] Initiating online hot backup at ${TIMESTAMP}..."

# Execute SQLite online backup API inside the running backend container
docker exec -i $(docker compose ps -q backend) python -c '
import sqlite3
src = sqlite3.connect("/app/data/agent_eval.db")
dst = sqlite3.connect("/app/data/snapshot.db")
src.backup(dst)
dst.close()
src.close()
'

# Copy the consistent snapshot out of the container volume
docker cp $(docker compose ps -q backend):/app/data/snapshot.db "${BACKUP_FILE}"
docker exec -i $(docker compose ps -q backend) rm -f /app/data/snapshot.db

# Compress backup archive
gzip -9 "${BACKUP_FILE}"
echo "[AEP SRE] Hot backup successfully saved to ${BACKUP_FILE}.gz"

# Retention policy: Delete backups older than 30 days
find "${BACKUP_DIR}" -name "aep_backup_*.db.gz" -mtime +30 -delete
```

---

## 3. Disaster Recovery & Restore Testing

### Restore Procedure (Target RTO: < 15 mins)
In the event of database corruption, accidental deletion, or host failure:

1. **Stop Application Services**:
   ```bash
   docker compose down
   ```

2. **Locate Most Recent Valid Backup**:
   ```bash
   LATEST_BACKUP=$(ls -t /var/backups/aep/aep_backup_*.db.gz | head -n 1)
   echo "Restoring from: ${LATEST_BACKUP}"
   ```

3. **Restore Database File into Volume**:
   ```bash
   # Uncompress to temporary location
   gunzip -c "${LATEST_BACKUP}" > /tmp/agent_eval_restored.db
   
   # Mount the volume temporarily to replace the file
   docker run --rm -v aep_data:/app/data -v /tmp:/backup alpine sh -c '
     cp /backup/agent_eval_restored.db /app/data/agent_eval.db
     rm -f /app/data/agent_eval.db-wal /app/data/agent_eval.db-shm
     chmod 664 /app/data/agent_eval.db
   '
   rm -f /tmp/agent_eval_restored.db
   ```

4. **Restart Services and Execute Health Checks**:
   ```bash
   docker compose up -d
   docker compose ps
   curl -f http://localhost:8000/system/info
   ```

---

## 4. Quarterly Restore Drill Verification Schedule
- **Frequency**: Every 90 days.
- **Verification Criteria**:
  1. Restore backup onto a sandbox staging host.
  2. Query `GET /api/v1/traces` to verify count matches pre-backup state.
  3. Run evaluation contract tests against restored database.
  4. Log restore duration and verify RTO compliance.

