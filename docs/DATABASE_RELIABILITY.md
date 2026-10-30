# VitalOptima — Database Reliability, Distributed Concurrency & Failover Architecture

**Document:** `docs/DATABASE_RELIABILITY.md`  
**Author:** Database Reliability Engineer & Senior Backend Architect  
**Persistence Layer:** Authoritative Local SQLite (`db/vitaloptima.db`) + Optional Cloud Neon PostgreSQL  
**Verification Suite:** `tests/test_database_reliability.py` & `tests/test_admission_concurrency.py`  

---

## 1. Concurrency Model & Database Invariants

In high-throughput acute hospitals, multiple triage coordinators, admission officers, and emergency charge nurses register patients and assign beds simultaneously across multiple workstations or browser sessions.

```
       Browser Session 1 (Triage)            Browser Session 2 (ED Boarding)
                   |                                       |
                   v                                       v
         [Worker Process 1]                      [Worker Process 2]
                   |                                       |
                   +-------------------+-------------------+
                                       |
               BEGIN IMMEDIATE / Atomic SQL Transaction
                                       |
                   v---------------------------------------v
                   | Partial Unique Index Enforcement      |
                   | idx_active_bed_occupancy              |
                   | (UNIQUE bed_number WHERE status=Admit)|
                   +---------------------------------------+
                                       |
                     +-----------------+-----------------+
                     |                                   |
              [First Committer]                  [Second Committer]
                     |                                   |
                     v                                   v
             SUCCESS (Bed Claimed)               CLEAN CONFLICT REJECTION
                                                 ("Bed just claimed by concurrent admission")
```

### 1.1 The In-Memory Mutex Fallacy
A threading lock (`threading.RLock`) in Python only coordinates threads running within the **same Python interpreter process**. In modern web deployments running multi-worker processes (e.g., Gunicorn or multi-process Streamlit) or multi-container clusters behind a load balancer, in-memory mutexes provide **zero cross-process safety**.

### 1.2 Database-Enforced Invariants
VitalOptima enforces concurrency invariants strictly at the database engine level across both SQLite and PostgreSQL schemas:

1. **Partial Unique Index:**
   ```sql
   CREATE UNIQUE INDEX IF NOT EXISTS idx_active_bed_occupancy 
   ON patient_admissions (bed_number) 
   WHERE status = 'Admitted' AND bed_number IS NOT NULL;
   ```
   - Discharged patients (`status = 'Discharged'`) release their unique hold on the bed number, allowing immediate subsequent re-admission without deleting historical records.
   - Any concurrent race condition attempting to admit two patients to the same bed triggers a database-level uniqueness violation.

2. **Immediate Transaction Serialization:**
   - On SQLite, transactions begin with `BEGIN IMMEDIATE` to acquire write locks upfront, preventing deadlocks and serialized write contention.
   - On PostgreSQL, isolation levels default to Read Committed with explicit atomic transactions.

3. **Multi-Connection Stress Verification:**
   - In `tests/test_database_reliability.py:test_multi_connection_concurrent_bed_contention`, 8 independent worker threads using 8 separate database connection handles simultaneously race to claim `TEST-CONC-BED-77`.
   - Verified Outcome: **Exactly 1 thread succeeds**; **7 threads receive actionable conflict errors**; exactly 1 active patient record exists in the database.

---

## 2. Safe Lifecycle Management & Idempotency

### 2.1 Idempotency Keys
Network retries or double-clicking forms in clinical workstations must not spawn duplicate patient admissions. VitalOptima enforces idempotency through client- or system-generated idempotency keys:
```sql
SELECT admission_id FROM patient_admissions WHERE admission_id = :idempotency_key;
```
If an admission key is already present, the transaction rolls back immediately and returns an informative rejection without touching bed inventory.

### 2.2 Safe Patient Discharge
Discharging an inpatient:
1. Marks `status = 'Discharged'` and sets `discharged_at = NOW()`.
2. Decrements `occupied_capacity` and increments `available_capacity` in `department_resources`.
3. Discharges are **idempotent**: attempting to discharge an already discharged patient raises `ValueError("Admission '...' is already discharged on ...")` and prevents double-incrementing bed capacity.

---

## 3. Dual-Engine Architecture & Outbox Synchronization

### 3.1 Authoritative Engine Topology
VitalOptima does not claim a fragile active-active multi-master replication topology. Instead, it enforces a clear, robust architecture:
- **Cloud Deployment:** Neon PostgreSQL is the authoritative system of record when `DATABASE_URL` is configured.
- **Local / Edge / Demo Deployment:** Local SQLite (`db/vitaloptima.db`) operates out-of-the-box with zero configuration and full offline resilience.

### 3.2 Reliable Outbox Journal (`sync_outbox`)
To prevent silent desynchronization when cloud connectivity fluctuates, local transactions append to a transactional outbox journal:

```sql
CREATE TABLE IF NOT EXISTS sync_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    entity_type TEXT NOT NULL,       -- 'admissions', 'decisions', 'resources'
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,         -- 'INSERT', 'UPDATE', 'DELETE'
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'SYNCED', 'CONFLICT', 'FAILED'
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    synced_at TEXT,
    error_message TEXT
);
```

#### Synchronization Protocol
1. Local SQLite transaction commits admission or discharge and registers an outbox event.
2. The application attempts immediate replication to Neon PostgreSQL.
3. If PostgreSQL is reachable, the row is inserted with `ON CONFLICT DO NOTHING`, and the outbox status transitions to `SYNCED`.
4. If PostgreSQL is unreachable (network timeout or offline mode), the transaction completes locally, outbox remains `PENDING`, and the system logs a structured notification.
5. When connectivity resumes, `sync_pending_outbox()` drains the queue idempotently.

---

## 4. Disaster Recovery & Zero-Downtime Atomic Backups

### 4.1 SQLite Online Backup API
Standard file copying (`shutil.copy` or `cp`) of an active SQLite database risks copying torn pages if a write transaction is in-flight. VitalOptima implements the native **SQLite Online Backup API** (`sqlite3.Connection.backup`):
```python
def backup_database(backup_path: Optional[Path] = None) -> Path:
    src_conn = get_sqlite_connection()
    dst_conn = sqlite3.connect(str(target))
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    return target
```
- Guarantees an atomic, consistent point-in-time snapshot with zero application downtime and zero locking of reader connections.
- Verified in `tests/test_database_reliability.py:test_atomic_online_backup_and_restore`.

