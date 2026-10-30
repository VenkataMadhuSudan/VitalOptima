# VitalOptima Enterprise Production Deployment & Operations Guide

**Document Version:** 2.0.0  
**Target Environment:** Linux / Windows Server / Containerized Kubernetes & Docker  
**Status:** Validated in CI/CD  

---

## 1. System Overview & Architecture

VitalOptima is an AI-assisted hospital operations intelligence and mathematical resource optimization decision-support platform.

```
                           +----------------------------------------+
                           |     Clinical Operations Endpoints      |
                           |     (Browser: Desktop & Mobile UI)     |
                           +-------------------+--------------------+
                                               | HTTP / WebSocket (:8501)
                                               v
+---------------------------------------------------------------------------------------------+
| VitalOptima Application Host (Docker Container / Bare-Metal Linux VM)                       |
|                                                                                             |
|   +-------------------------------------------------------------------------------------+   |
|   | Streamlit Application Engine (Light Mode Enterprise UI, Headless)                   |   |
|   +------------------------------------------+------------------------------------------+   |
|                                              |                                              |
|         +------------------------------------+------------------------------------+         |
|         |                                    |                                    |         |
|         v                                    v                                    v         |
|   +-----------------------+            +-----------------------+            +-------------+ |
|   | Time-Series ML Engine |            | Mixed-Integer Linear  |            | Security &  | |
|   | (Ridge, RF, Conformal |            | Programming (OR-Tools |            | Audit Chain | |
|   | Prediction Intervals) |            | SCIP / CBC MILP)      |            | (SHA-256)   | |
|   +-----------+-----------+            +-----------+-----------+            +------+------+ |
|               |                                    |                               |        |
|               +------------------+  +--------------+                               |        |
|                                  |  |                                              |        |
|                                  v  v                                              v        |
|   +-------------------------------------------------------------------------------------+   |
|   | Authoritative Persistence Layer                                                     |   |
|   | - SQLite with Partial Unique Indexes & WAL mode (Standalone/Air-gapped)             |   |
|   | - PostgreSQL with Sync Outbox Journal (Multi-worker Enterprise Cluster)             |   |
|   +------------------------------------------+------------------------------------------+   |
|                                              |                                              |
+----------------------------------------------|----------------------------------------------+
                                               |
                                               v
                          +------------------------------------------+
                          | Persistent Volumes & Backup Snapshots    |
                          | - /app/data/vitaloptima.db               |
                          | - /app/backups/vitaloptima_backup_*.db   |
                          | - /app/evaluation/                       |
                          +------------------------------------------+
```

---

## 2. Prerequisites & Environment Requirements

### Hardware Sizing
- **Minimum:** 2 vCPUs, 4 GB RAM, 20 GB SSD storage
- **Recommended Production:** 4 vCPUs, 8 GB RAM, 50 GB NVMe storage
- **Network:** Port `8501` open for internal hospital intranet access (TLS termination via reverse proxy)

### Software Dependencies
- **Python:** Version `3.11.x` (strictly enforced in `pyproject.toml` and CI matrix)
- **Container Engine:** Docker Engine 24.0+ and Docker Compose 2.20+ (if deploying via containers)

---

## 3. Deployment Option A: Containerized Deployment (Recommended)

### 3.1 Build and Launch Containers
```bash
# Clone or navigate to the repository
cd C:\Projects\VitalOptima

# Build and start in detached background mode
docker compose up -d --build
```

### 3.2 Verify Container Health Status
The container includes a built-in HTTP health check polling `http://localhost:8501/_stcore/health`:
```bash
docker inspect --format='{{json .State.Health}}' vitaloptima-decision-engine
```
Expected output:
```json
{"Status":"healthy","FailingStreak":0,"Log":[{"ExitCode":0,"Output":""}]}
```

### 3.3 Container Logs Inspection
```bash
docker compose logs -f vitaloptima-app
```

---

## 4. Deployment Option B: Bare-Metal / Local VM Deployment

### 4.1 Environment Setup
```bash
# 1. Create a dedicated Python 3.11 virtual environment
python -m venv venv

# 2. Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 3. Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4.2 Initialize Production Database
```bash
# Initializes schemas, partial unique index, and seeds baseline hospital resources
python -c "from db.database import init_db; init_db()"
```

### 4.3 Launch the Application
```bash
streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true
```

---

## 5. Configuration & Environment Variables Reference

VitalOptima adheres to 12-factor configuration principles via environment variables:

| Variable | Default Value | Allowed Values | Purpose & Clinical Impact |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `development` | `production`, `development`, `testing` | Controls security boundaries. In `production`, default demo credentials are NEVER seeded. |
| `SEED_DEMO_USERS` | `false` | `true`, `false` | When set to `false`, prevents injection of predictable credentials into the user table. |
| `DATABASE_URL` | `sqlite:///data/vitaloptima.db` | SQLite URI or PostgreSQL DSN | Sets the authoritative persistence backend. |
| `SQLITE_BUSY_TIMEOUT_MS` | `15000` | Integer (ms) | Database connection lock retry timeout to prevent `database is locked` under concurrency. |
| `SECRET_KEY` | *(Auto-generated)* | 32+ character hex string | Cryptographic key for session token signing and state integrity. |
| `STREAMLIT_SERVER_PORT` | `8501` | Valid TCP port | Listening port for Streamlit web server. |
| `XAI_API_KEY` | `""` | Valid API key or empty | Optional key for xAI/Grok conversational agent. If omitted, falls back to deterministic hospital NLQ. |

---

## 6. Database Operations & Maintenance

### 6.1 Zero-Downtime Atomic Online Backup
VitalOptima provides a non-blocking online backup utility utilizing SQLite's Online Backup API:
```bash
# Create timestamped snapshot in backups/ directory
python scripts/backup_db.py

# Or specify a custom target path
python scripts/backup_db.py --output /secure/mount/vitaloptima_snapshot.db
```
The CLI automatically:
1. Performs non-blocking snapshot during active user operations.
2. Runs SQLite `PRAGMA integrity_check`.
3. Calculates SHA-256 integrity checksum.

### 6.2 Safe Database Restore
```bash
# Restore with interactive confirmation
python scripts/restore_db.py --input backups/vitaloptima_backup_20261030_194346.db

# Force restore (non-interactive in automated recovery pipelines)
python scripts/restore_db.py --force --input backups/vitaloptima_backup_20261030_194346.db
```

---

## 7. The 11-Step Clinical Operator Workflow

To demonstrate or operate VitalOptima during hospital administrative rounds:

1. **Secure Administrator Authentication:**
   Log in at `http://localhost:8501` using valid credentials. Failed attempts trigger exponential backoff and 15-minute lockouts after 5 strikes.
2. **Review Real-Time Census Dashboard:**
   Inspect current hospital occupancy across Internal Medicine, Surgery, ICU, Pediatrics, and Emergency units.
3. **Inspect Time-Series Forecasts (`Forecasting Engine`):**
   Review 24-hour diurnal arrival estimates with 90% calibrated conformal prediction intervals.
4. **Identify Departmental Bottlenecks:**
   Identify saturated units (e.g., ICU operating at 100% capacity) and damaged/offline beds.
5. **Run Mathematical Bed Allocation (`Resource Optimizer`):**
   Execute Google OR-Tools SCIP MILP solver to allocate pending admissions against available bed capacities.
6. **Verify Physical & Clinical Invariants:**
   Confirm that zero incompatible assignments are made and effective capacity boundaries are strictly respected.
7. **Simulate Crisis Surge in What-If Workbench (`Simulator`):**
   Stress-test the system with +50% emergency arrival surge and 6 damaged ICU beds.
8. **Execute Conformal Stochastic Optimization (`Simulator` -> Tab 3):**
   Solve the two-stage stochastic MILP across Expected, High (+1q), and Severe Surge (+2q) scenarios.
9. **Authorize Float Pool Staffing:**
   Review Stage 1 regular nurse staffing commitments and approve supplemental nurse overtime.
10. **Execute Atomic Patient Admission (`Admissions`):**
    Admit a patient to a verified open bed. If two admission officers attempt to book the same bed, database-level partial unique indexing rejects the second atomically.
11. **Sign Cryptographic Audit Checkpoint (`Security`):**
    Export the SHA-256 tamper-evident audit chain anchor to detect trailing truncation attacks.

