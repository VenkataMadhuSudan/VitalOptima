# VitalOptima — Authentication, Session Lifecycle & RBAC Reference

**Document Version:** 2.0.0  
**Classification:** Technical Architecture Reference  
**Maintainer:** VitalOptima Core Security & Infrastructure Team  

---

## 1. Architectural Overview

VitalOptima implements a multi-layered security and identity access management (IAM) subsystem designed for mission-critical healthcare operations. The system enforces strict least-privilege boundaries, prevents credential enumeration, guards against persistent brute-force attacks, and maintains an immutable, cryptographically chained audit log for clinical governance.

```
                      +---------------------------------------+
                      |       Clinical User / Browser        |
                      +-------------------+-------------------+
                                          |
                                          | TLS 1.3 / HTTPS
                                          v
                      +---------------------------------------+
                      |         Streamlit Web Gateway         |
                      |   - Native Enter-to-Submit Form       |
                      |   - Show/Hide Password Masking        |
                      |   - Environment-Aware Demo Guard      |
                      +-------------------+-------------------+
                                          |
                                          | Form Submission
                                          v
+-----------------------------------------------------------------------------------+
|                            Authentication Engine                                  |
|                                                                                   |
|  1. IP Rate Limiting Check (login_attempts table)                                 |
|  2. Account Lockout Check (5 failed attempts in 15m)                              |
|  3. Non-Existent User Defense (Constant-time dummy PBKDF2 hash computation)       |
|  4. Credential Verification (PBKDF2-HMAC-SHA256, 600,000 iterations)              |
|  5. Session Token Minting (32-byte cryptographically secure token)                |
|  6. Append-Only Cryptographic Audit Log (SHA-256 Hash Chain)                     |
+-----------------------------------------+-----------------------------------------+
                                          |
                      +-------------------+-------------------+
                      |                                       |
                      v                                       v
         +--------------------------+           +--------------------------+
         |     SQLite Database      |           |   PostgreSQL Database    |
         |  - users table           |           |  - users table           |
         |  - login_attempts table  |           |  - login_attempts table  |
         |  - active_sessions table |           |  - active_sessions table |
         |  - audit_logs (chained)  |           |  - audit_logs (chained)  |
         +--------------------------+           +--------------------------+
```

---

## 2. Password Storage & Cryptographic Standards

### 2.1 Hashing Specification
Passwords are never stored in plaintext. VitalOptima adheres strictly to NIST SP 800-63B and OWASP Password Storage Guidelines:

* **Algorithm:** PBKDF2 (Password-Based Key Derivation Function 2)
* **Pseudorandom Function (PRF):** HMAC-SHA256
* **Iteration Count:** 600,000 rounds (OWASP 2024 recommendation)
* **Salt Length:** 16 bytes (32 hexadecimal characters) generated via `secrets.token_hex(16)`
* **Hash Output:** 32 bytes (64 hexadecimal characters)
* **Comparison Function:** Constant-time `secrets.compare_digest` to prevent timing side-channel attacks.

### 2.2 Backward Compatibility & Rehash-on-Login
Historical demonstration accounts generated during early prototypes used 100,000 iterations. To maintain seamless backward compatibility without compromising security:
1. `verify_password()` evaluates the modern 600,000-iteration digest first.
2. If unsuccessful, it evaluates the legacy 100,000-iteration fallback.
3. Upon successful legacy authentication, `authenticate_user()` immediately rehashes the password using 600,000 iterations, generates a fresh random salt, and updates the database record automatically.

### 2.3 Password Complexity Policy
All user-supplied passwords (during account provisioning, password reset, or first-time forced rotation) must satisfy:
* Minimum 8 characters in length ($\ge 10$ recommended for clinical administrators).
* At least one uppercase Latin letter ($A-Z$).
* At least one lowercase Latin letter ($a-z$).
* At least one numerical digit ($0-9$).
* At least one special character (`!@#$%^&*(),.?":{}|<>-_=+[]\/`~`).

---

## 3. Persistent Brute-Force & Rate-Limiting Protection

### 3.1 Persistence Across Restarts
Unlike systems that store login failures in process memory, VitalOptima records all authentication attempts in the `login_attempts` table. This prevents attackers from resetting throttling thresholds by crashing or restarting the application.

```sql
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier TEXT NOT NULL,       -- username or IP address
    attempt_type TEXT NOT NULL,     -- 'username' or 'ip'
    attempt_time REAL NOT NULL,     -- epoch timestamp
    success INTEGER NOT NULL DEFAULT 0,
    ip_address TEXT
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_lookup 
ON login_attempts (identifier, attempt_type, attempt_time);
```

### 3.2 Throttling Rules
* **Account-Level Lockout:** If 5 consecutive failed attempts occur within 900 seconds (15 minutes), the account is locked for the remainder of the 15-minute window.
* **IP-Level Throttling:** If 15 failed attempts originate from a single IP address within 900 seconds (across any combination of usernames), all requests from that IP are blocked.
* **Lockout Reset:** A single successful authentication immediately purges failed attempt records for that username and IP.

### 3.3 Timing Attack Defense
When an authentication request targets an invalid or non-existent username:
1. The engine computes a dummy PBKDF2 calculation against a static salt with 600,000 iterations:
   $$\text{digest} = \text{PBKDF2-HMAC-SHA256}(\text{password}, \text{salt}_{\text{static}}, 600000)$$
2. The processing latency matches a legitimate verification ($\approx 150\text{ ms}$).
3. A generic failure is returned: `"Invalid username or password"`.

---

## 4. Server-Side Session Lifecycle Management

VitalOptima does not trust client-controlled session cookies or mutable front-end state dictionaries alone. All sessions are validated against the server-side `active_sessions` table.

```
                      +-------------------+
                      |   User Login      |
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      | Session Minted    |
                      | token = 32-bytes  |
                      | is_revoked = 0    |
                      +---------+---------+
                                |
                   +------------+------------+
                   |                         |
                   v                         v
         [ Inactive > 30m ]       [ Total Age > 8h ]
                   |                         |
                   +------------+------------+
                                |
                                v
                      +-------------------+
                      | Session Revoked   |
                      | is_revoked = 1    |
                      | User Logged Off   |
                      +-------------------+
```

### 4.1 Session Parameters
* **Idle Timeout (`SESSION_IDLE_TIMEOUT_SECONDS`):** 1,800 seconds (30 minutes). If no activity is recorded within 30 minutes, the session is invalidated.
* **Absolute Lifetime (`SESSION_ABSOLUTE_LIFETIME_SECONDS`):** 28,800 seconds (8 hours). Requires fresh reauthentication at the end of a clinical shift.
* **Session Token:** 32-byte URL-safe cryptographically secure token generated via `secrets.token_urlsafe(32)`.

### 4.2 Tampering & Spoofing Defense
When `get_current_user()` is called:
1. It extracts `session_token` from Streamlit session state.
2. It executes `validate_server_session(session_token)`.
3. If the user was deactivated or the session expired, the session is purged and `None` is returned.
4. If a client attempts to edit `st.session_state["authenticated_user"]["role"] = "ADMIN"`, the validator retrieves the true role from the database and overwrites the spoofed value.

---

## 5. Role-Based Access Control (RBAC) Matrix

VitalOptima defines two primary clinical roles operating under least-privilege boundaries:

1. **`ADMIN` (Hospital Command Center & Medical Director):**
   Full access to executive analytics, AI insights, linear programming optimization, disaster simulation, user administration, and cryptographic audit logs.
2. **`ADMISSION_OFFICER` (Triage & Ward Coordinator):**
   Strictly scoped to patient admissions, bed allocation workflows, bed occupancy views, and safe patient discharges.

| System Permission | Permission Scope | `ADMIN` | `ADMISSION_OFFICER` |
| :--- | :--- | :---: | :---: |
| `admissions.view` | View patient census and active admissions | ✅ | ✅ |
| `admissions.create` | Admit patient and allocate physical bed | ✅ | ✅ |
| `admissions.update` | Update clinical triage notes and assignment | ✅ | ✅ |
| `admissions.discharge` | Safely discharge patient and release bed | ✅ | ✅ |
| `beds.view` | Inspect live ward occupancy and availability | ✅ | ✅ |
| `analytics.view` | Executive census charts and operational KPIs | ✅ | ❌ |
| `forecasting.view` | View emergency arrivals and ICU demand forecasts | ✅ | ❌ |
| `forecasting.manage`| Trigger ML retraining and conformal prediction | ✅ | ❌ |
| `optimization.view` | View mathematical staff and bed allocation plans | ✅ | ❌ |
| `optimization.manage`| Execute OR-Tools MILP optimization models | ✅ | ❌ |
| `simulator.view` | Run disaster surge and epidemic what-if scenarios | ✅ | ❌ |
| `inventory.view` | Medical supply consumption and burn tracking | ✅ | ❌ |
| `decisions.manage` | Commit clinical overrides and governance decisions | ✅ | ❌ |
| `audit.view` | View and verify cryptographic audit log chain | ✅ | ❌ |
| `users.manage` | Provision, update, or deactivate accessor accounts | ✅ | ❌ |
| `settings.view` | Access system configuration and audit reports | ✅ | ❌ |

---

## 6. Administrator Provisioning Guide

### 6.1 Initial Administrator Setup in Production
In production environments, default demo credentials are never pre-seeded. To provision the initial administrator:

```python
from services.auth_service import provision_initial_admin

# Programmatic provisioning
res = provision_initial_admin(
    username="admin",
    password=None,  # Generates a strong random 18-character secret
    full_name="Dr. Rajesh Sharma (Medical Director)",
    department="Hospital Administration"
)

if res["created"]:
    print(f"Temporary password: {res['temporary_password']}")
```

Alternatively, configure the initial password via environment variable before container startup:
```bash
export ADMIN_INITIAL_PASSWORD="YourStrongCustomPassword@2026!"
export APP_ENV=production
export SEED_DEMO_USERS=false
```

### 6.2 Forced Password Rotation Workflow
When `must_change_password` is True:
1. The user logs in with their temporary credentials.
2. `login_view.py` intercepts the session before dashboard routing.
3. The user is presented with the **Password Change Required** interface.
4. The user enters their current temporary password, new password, and confirmation.
5. `change_user_password()` verifies credentials, enforces complexity, resets `must_change_password=0`, and revokes all other active sessions.
6. The user is routed to the authorized workspace.

---

## 7. Cryptographic Audit Log Integrity

All security and clinical events are written to an append-only, SHA-256 hash-chained audit log:

$$\text{record\_hash}_i = \text{SHA256}\left(\text{JSON}_{\text{canonical}}\left(\text{prev\_hash}_{i-1}, \text{timestamp}_i, \text{actor}_i, \text{action}_i, \text{target}_i, \text{status}_i, \text{details}_i\right)\right)$$

* **Chain Verification:** `verify_audit_log_chain()` traverses the database from genesis to head, recalculating hashes to identify any modified records, dropped rows, or reordered entries.
* **Checkpoint Signatures:** `export_audit_chain_checkpoint()` signs the chain head and record count to detect trailing truncation attacks where an adversary attempts to delete recent logs.

