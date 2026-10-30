# VitalOptima — Application Security Model & Cryptographic Audit Specifications

**Document:** `docs/SECURITY_MODEL.md`  
**Author:** Application Security Engineer & Infrastructure Architect  
**Scope:** Authentication, Session Protection, RBAC Matrix, Cryptographic Audit Hash Chain, Checkpoint Anchoring  
**Verification Suite:** `tests/test_cybersecurity_and_governance.py` & `tests/test_audit_hash_chain.py`  

---

## 1. Threat Model & Security Boundaries

VitalOptima operates as an administrative healthcare command center. The system's threat model assumes:
1. **Network Interception:** Hostile local network traffic; credentials and session tokens must never be logged or transmitted in cleartext.
2. **Brute-Force & Credential Stuffing:** Automated credential attacks against the web login interface.
3. **Privilege Escalation:** Legitimate admission officers attempting unauthorized access to strategic capacity forecasting, MILP solver overrides, or security audit logs.
4. **Historical Audit Tampering:** Malicious administrators attempting to retroactively alter past bed reallocations, delete controversial disaster authorizations, or reorder events.
5. **Prompt Injection & AI Poisoning:** Untrusted user input attempting to force language models into executing unauthorized SQL queries or changing bed statuses.

---

## 2. Authentication & Credential Architecture

### 2.1 Password Hashing Configuration
- **Algorithm:** PBKDF2-HMAC-SHA256
- **Work Factor:** 600,000 iterations (meeting current OWASP Password Storage Guidelines)
- **Salt:** 16 bytes of cryptographically secure random entropy (`secrets.token_hex(16)`)
- **Comparison:** Constant-time equality checks (`secrets.compare_digest`) to defeat timing attacks.

### 2.2 Transparent Rehash-on-Login Migration
Legacy accounts created with historical parameters (100,000 iterations) authenticate seamlessly via backward-compatible checks and are **transparently rehashed to 600,000 iterations in the database** upon their next successful login.

### 2.3 Brute-Force Rate Limiting & Throttling
- An in-memory thread-safe rate limiter tracks failed login attempts by username.
- **Lockout Policy:** 5 consecutive failed authentication attempts trigger an automatic 15-minute cooldown. Subsequent attempts return clean `None` rejections and log a high-severity `DENIED` audit event.
- Successful authentication immediately clears the failure counter.

### 2.4 Session Expiration & Account Deactivation
- Inpatient sessions track `login_timestamp`. Sessions older than 8 hours are invalidated (`is_session_valid() == False`).
- If an account is toggled to `is_active = 0` by an administrator in the database, all existing sessions for that user fail validation immediately on their next request.

---

## 3. Server-Layer Role-Based Access Control (RBAC)

VitalOptima implements **least-privilege, defense-in-depth authorization**. Authorization checks are enforced at the service and data layer via `require_permission(permission, user)`—hiding a frontend UI button is never treated as a security boundary.

### Complete Authorization Matrix

| Operational Permission | Scope Description | Hospital Administrator (`ADMIN`) | Admission Officer (`ADMISSION_OFFICER`) |
| :--- | :--- | :---: | :---: |
| `admissions.view` | View active inpatient roster & occupancy | **ALLOWED** | **ALLOWED** |
| `admissions.create` | Register patients & assign physical beds | **ALLOWED** | **ALLOWED** |
| `admissions.update` | Update clinical notes & ward transfers | **ALLOWED** | **ALLOWED** |
| `admissions.discharge` | Discharge patient & release bed | **ALLOWED** | **ALLOWED** |
| `beds.view` | Inspect unit-level bed availability | **ALLOWED** | **ALLOWED** |
| `analytics.view` | Command Center telemetry & KPI charts | **ALLOWED** | **DENIED (403)** |
| `forecasting.view` | Demand forecasts & prediction intervals | **ALLOWED** | **DENIED (403)** |
| `forecasting.manage`| Trigger model retraining & backtests | **ALLOWED** | **DENIED (403)** |
| `optimization.view` | Inspect MILP allocations & bottlenecks | **ALLOWED** | **DENIED (403)** |
| `optimization.manage`| Override constraints & solver parameters | **ALLOWED** | **DENIED (403)** |
| `simulator.view` | Run What-If disaster stress simulations | **ALLOWED** | **DENIED (403)** |
| `inventory.view` | Supply chain burn rates & stockouts | **ALLOWED** | **DENIED (403)** |
| `decisions.manage` | Commit signed operational determinations | **ALLOWED** | **DENIED (403)** |
| `audit.view` | View cryptographic audit logs | **ALLOWED** | **DENIED (403)** |
| `users.manage` | Provision users & toggle active status | **ALLOWED** | **DENIED (403)** |
| `settings.view` | System configurations & database tools | **ALLOWED** | **DENIED (403)** |

---

## 4. Tamper-Evident SHA-256 Audit Trail & Anchoring

### 4.1 Canonical Serialization
Audit records are serialized to canonical JSON before hashing:
- Strictly sorted dictionary keys (`sort_keys=True`).
- Compact delimiters without whitespace (`separators=(',', ':')`).
- Eliminates delimiter ambiguity present in naive string-concatenated formats (e.g., pipe-delimited strings).

### 4.2 Cryptographic Hash Chain
Each audit event $i$ contains:
$$\text{RecordHash}_i = \text{SHA-256}\Big(\text{CanonicalJSON}\big(\text{Payload}_i \parallel \text{PrevHash}_{i-1}\big)\Big)$$

```
[Record 1]                 [Record 2]                 [Record 3]
prev_hash: "GENESIS"       prev_hash: Hash(1)         prev_hash: Hash(2)
record_hash: Hash(1) ----> record_hash: Hash(2) ----> record_hash: Hash(3)
```

### 4.3 Tamper Detection Capabilities
1. **Payload Alteration:** Modifying details in row $k$ causes $\text{RecordHash}_k$ mismatch.
2. **Intermediate Deletion:** Deleting row $k$ causes row $k+1$'s `prev_hash` to point to a nonexistent hash.
3. **Reordering:** Swapping row $j$ and $k$ breaks bidirectional linkage.
4. **Link Corruption:** Modifying `prev_hash` directly breaks verification.

### 4.4 Trailing Truncation Threat Model & External Checkpoint Anchoring
> [!WARNING]
> **Threat Model Limitation Disclosure:**  
> A hash chain stored within a mutable relational database table cannot prevent a privileged administrator with direct SQL access from deleting records from the **tail** of the table without breaking the remaining chain links.

#### Mitigation: Signed Checkpoint Export
VitalOptima implements `export_audit_chain_checkpoint()`:
- Exports signed JSON snapshot:
  ```json
  {
    "checkpoint_timestamp": "2026-10-31 00:51:00 UTC",
    "total_records": 142,
    "latest_record_id": 142,
    "latest_record_hash": "a4f8...b129",
    "signature_digest": "7c82...901e"
  }
  ```
- `verify_audit_checkpoint()` compares current database row counts and latest hash against the exported anchor. If trailing records were deleted, verification fails immediately: `"Trailing truncation detected! Checkpoint expected 142 records, found 138."`

