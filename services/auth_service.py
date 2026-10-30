"""
VitalOptima Authentication, Session Security & Centralized RBAC Engine
Provides NIST-compliant PBKDF2-HMAC-SHA256 password hashing, trusted role verification,
defense-in-depth permission enforcement, session handling, and tamper-resistant audit logging.
"""
import hashlib
import secrets
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Centralized Role Definitions
ROLE_ADMIN = "ADMIN"
ROLE_ADMISSION_OFFICER = "ADMISSION_OFFICER"

VALID_ROLES = {ROLE_ADMIN, ROLE_ADMISSION_OFFICER}

# Centralized Permissions Matrix
# Least-privilege role boundaries
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    ROLE_ADMIN: {
        "admissions.view",
        "admissions.create",
        "admissions.update",
        "admissions.discharge",
        "beds.view",
        "analytics.view",
        "forecasting.view",
        "forecasting.manage",
        "optimization.view",
        "optimization.manage",
        "simulator.view",
        "inventory.view",
        "decisions.manage",
        "audit.view",
        "users.manage",
        "settings.view"
    },
    ROLE_ADMISSION_OFFICER: {
        "admissions.view",
        "admissions.create",
        "admissions.update",
        "admissions.discharge",
        "beds.view",
    }
}


import json
import threading

# Re-entrant thread lock for serialized append-only audit logging
_AUDIT_LOG_LOCK = threading.RLock()

# Login attempt throttling tracker: {username: [timestamp1, timestamp2, ...]}
_FAILED_LOGINS = {}
_FAILED_LOGIN_LOCK = threading.Lock()
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes

# Modern cryptographic parameters (OWASP Password Storage Cheat Sheet recommendation for PBKDF2-HMAC-SHA256)
DEFAULT_PBKDF2_ITERATIONS = 600000
LEGACY_PBKDF2_ITERATIONS = 100000


def hash_password(password: str, salt: Optional[str] = None, iterations: int = DEFAULT_PBKDF2_ITERATIONS) -> tuple[str, str]:
    """
    Hashes password using PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP recommendation)
    and a cryptographically secure 16-byte random salt.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    )
    return key.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Verifies a plain password against the stored hash and salt using constant-time comparison.
    Backward-compatible: tests modern 600,000 iterations first, then checks legacy 100,000.
    """
    if not password or not password_hash or not salt:
        return False

    # 1. Test modern 600,000 iterations
    key_modern = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        DEFAULT_PBKDF2_ITERATIONS
    )
    if secrets.compare_digest(key_modern.hex(), password_hash):
        return True

    # 2. Backward-compatible fallback: test legacy 100,000 iterations
    key_legacy = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        LEGACY_PBKDF2_ITERATIONS
    )
    return secrets.compare_digest(key_legacy.hex(), password_hash)


def get_sqlite_conn():
    from config import DB_PATH
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieves an active user record by username."""
    if not username:
        return None
    username_clean = username.strip().lower()

    # Try PostgreSQL first if available
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.connect() as conn:
                res = conn.execute(
                    text("SELECT * FROM users WHERE LOWER(username) = :u AND is_active = true LIMIT 1;"),
                    {"u": username_clean}
                ).mappings().first()
                if res:
                    return dict(res)
    except Exception:
        pass

    # Fallback to local SQLite
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = ? AND is_active = 1 LIMIT 1", (username_clean,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as e:
        print(f"[Auth] Error fetching user '{username}': {e}")

    return None


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticates a user against server-side stored credentials.
    Returns sanitized user profile dict on success, None on failure.
    Logs authentication success or failure to the audit trail.
    """
    if not username or not password:
        log_audit_event(
            actor_username=username or "anonymous",
            actor_role="UNKNOWN",
            action="auth.login",
            status="FAILED",
            details="Empty username or password provided"
        )
        return None

    user = get_user_by_username(username)
    if not user:
        log_audit_event(
            actor_username=username,
            actor_role="UNKNOWN",
            action="auth.login",
            status="FAILED",
            details="User not found or inactive"
        )
        return None

    # Rate limiting & brute-force throttling check
    import time
    u_key = username.strip().lower()
    now_epoch = time.time()
    with _FAILED_LOGIN_LOCK:
        recent_fails = [ts for ts in _FAILED_LOGINS.get(u_key, []) if now_epoch - ts < LOCKOUT_WINDOW_SECONDS]
        _FAILED_LOGINS[u_key] = recent_fails
        if len(recent_fails) >= MAX_FAILED_ATTEMPTS:
            log_audit_event(
                actor_username=user["username"],
                actor_role=user["role"],
                action="auth.login",
                status="DENIED",
                details=f"Account temporarily locked: {len(recent_fails)} consecutive failed attempts. 15-minute cooldown active."
            )
            return None

    if not verify_password(password, user["password_hash"], user["salt"]):
        with _FAILED_LOGIN_LOCK:
            _FAILED_LOGINS.setdefault(u_key, []).append(now_epoch)
        log_audit_event(
            actor_username=user["username"],
            actor_role=user["role"],
            action="auth.login",
            status="FAILED",
            details=f"Invalid password attempt (Attempt {len(_FAILED_LOGINS.get(u_key, []))}/{MAX_FAILED_ATTEMPTS})"
        )
        return None

    # Clear failed attempts upon successful authentication
    with _FAILED_LOGIN_LOCK:
        _FAILED_LOGINS.pop(u_key, None)

    # Rehash-on-login migration: if user authenticated using legacy iterations, upgrade to 600,000
    try:
        legacy_check = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            user["salt"].encode('utf-8'),
            LEGACY_PBKDF2_ITERATIONS
        ).hex()
        if secrets.compare_digest(legacy_check, user["password_hash"]):
            new_hash, new_salt = hash_password(password, iterations=DEFAULT_PBKDF2_ITERATIONS)
            conn_rehash = get_sqlite_conn()
            c_rehash = conn_rehash.cursor()
            c_rehash.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (new_hash, new_salt, user["id"]))
            conn_rehash.commit()
            conn_rehash.close()
            user["password_hash"] = new_hash
            user["salt"] = new_salt
    except Exception as e:
        print(f"[Auth] Notice during rehash-on-login upgrade: {e}")

    # Update last login
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_str, user["id"]))
        conn.commit()
        conn.close()
    except Exception:
        pass

    # Audit login success
    log_audit_event(
        actor_username=user["username"],
        actor_role=user["role"],
        action="auth.login",
        status="SUCCESS",
        details="User successfully authenticated"
    )

    # Return safe user dictionary without hash or salt
    safe_user = {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "full_name": user["full_name"],
        "department": user.get("department", "Hospital"),
        "last_login": now_str,
        "login_timestamp": time.time()
    }
    return safe_user


def has_permission(user_or_role: Any, permission: str) -> bool:
    """
    Evaluates whether the given user or role holds the specified permission.
    Strict least-privilege verification.
    """
    if not user_or_role or not permission:
        return False
    
    role = user_or_role
    if isinstance(user_or_role, dict):
        role = user_or_role.get("role")
    
    if role not in ROLE_PERMISSIONS:
        return False

    return permission in ROLE_PERMISSIONS[role]


def require_permission(permission: str, user: Optional[Dict[str, Any]] = None):
    """
    Defense-in-depth authorization check for service layer and backend handlers.
    Raises PermissionError if unauthorized.
    """
    if user is None:
        user = get_current_user()
    
    if not user or not user.get("role"):
        log_audit_event(
            actor_username="anonymous",
            actor_role="NONE",
            action=permission,
            status="DENIED",
            details="Unauthenticated caller attempted protected action"
        )
        raise PermissionError(f"Authentication required to perform '{permission}'")

    if not has_permission(user, permission):
        log_audit_event(
            actor_username=user.get("username", "unknown"),
            actor_role=user.get("role", "unknown"),
            action=permission,
            status="DENIED",
            details=f"Role '{user.get('role')}' does not hold required permission '{permission}'"
        )
        raise PermissionError(
            f"Access Denied: Role '{user.get('role')}' is not authorized to perform '{permission}'"
        )


def require_role(allowed_roles: List[str], user: Optional[Dict[str, Any]] = None):
    """Verifies that the caller possesses one of the allowed roles."""
    if user is None:
        user = get_current_user()
    
    if not user or user.get("role") not in allowed_roles:
        actor_role = user.get("role") if user else "NONE"
        actor_name = user.get("username") if user else "anonymous"
        log_audit_event(
            actor_username=actor_name,
            actor_role=actor_role,
            action="role.check",
            status="DENIED",
            details=f"Required role in {allowed_roles}, got '{actor_role}'"
        )
        raise PermissionError(f"Access Denied: Requires one of roles {allowed_roles}")


def get_current_user() -> Optional[Dict[str, Any]]:
    """Retrieves the currently authenticated user from Streamlit session state if available."""
    try:
        import streamlit as st
        if hasattr(st, "session_state") and "authenticated_user" in st.session_state:
            return st.session_state["authenticated_user"]
    except Exception:
        pass
    return None


def logout_user():
    """Logs out current user, records audit event, and purges session state."""
    current = get_current_user()
    if current:
        log_audit_event(
            actor_username=current.get("username", "user"),
            actor_role=current.get("role", "UNKNOWN"),
            action="auth.logout",
            status="SUCCESS",
            details="User logged out"
        )
    try:
        import streamlit as st
        if "authenticated_user" in st.session_state:
            del st.session_state["authenticated_user"]
        st.session_state["current_page"] = "Dashboard"
    except Exception:
        pass


def compute_audit_record_hash(
    prev_hash: str,
    timestamp: str,
    actor_username: str,
    actor_role: str,
    action: str,
    target_id: Optional[str],
    target_type: Optional[str],
    status: str,
    details: Optional[str]
) -> str:
    """
    Computes SHA-256 digest over unambiguous canonical JSON representation of an audit event.
    Keys are strictly sorted with compact separators to prevent boundary blurring.
    """
    canonical_payload = {
        "action": str(action),
        "actor_role": str(actor_role),
        "actor_username": str(actor_username),
        "details": str(details or ""),
        "prev_hash": str(prev_hash),
        "status": str(status),
        "target_id": str(target_id or ""),
        "target_type": str(target_type or ""),
        "timestamp": str(timestamp)
    }
    canonical_str = json.dumps(canonical_payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()


def compute_legacy_audit_record_hash(
    prev_hash: str,
    timestamp: str,
    actor_username: str,
    actor_role: str,
    action: str,
    target_id: Optional[str],
    target_type: Optional[str],
    status: str,
    details: Optional[str]
) -> str:
    """Legacy pipe-delimited digest for backward-compatibility with historical pre-audit records."""
    canonical_payload = (
        f"{prev_hash}|{timestamp}|{actor_username}|{actor_role}|{action}|"
        f"{target_id or ''}|{target_type or ''}|{status}|{details or ''}"
    )
    return hashlib.sha256(canonical_payload.encode('utf-8')).hexdigest()


def log_audit_event(
    actor_username: str,
    actor_role: str,
    action: str,
    target_id: Optional[str] = None,
    target_type: Optional[str] = None,
    status: str = "SUCCESS",
    details: Optional[str] = None
):
    """
    Records an append-only, cryptographic hash-chained audit event in both PostgreSQL and SQLite.
    Each record links to the previous event's SHA-256 hash to detect unauthorized tampering.
    Thread-safe and concurrency-locked: uses _AUDIT_LOG_LOCK and serialized DB transactions
    to prevent competing chain entries from referencing stale prev_hash values.
    Never logs plaintext passwords, tokens, or sensitive patient identifiable keys.
    """
    with _AUDIT_LOG_LOCK:
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Local SQLite serialized append
        prev_hash = "GENESIS"
        conn = None
        try:
            conn = get_sqlite_conn()
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.cursor()
            cur.execute("SELECT record_hash FROM audit_logs WHERE record_hash IS NOT NULL ORDER BY id DESC LIMIT 1")
            last_row = cur.fetchone()
            if last_row and last_row["record_hash"]:
                prev_hash = last_row["record_hash"]

            record_hash = compute_audit_record_hash(
                prev_hash=prev_hash,
                timestamp=now_str,
                actor_username=actor_username,
                actor_role=actor_role,
                action=action,
                target_id=target_id,
                target_type=target_type,
                status=status,
                details=details
            )

            cur.execute("""
                INSERT INTO audit_logs (timestamp, actor_username, actor_role, action, target_id, target_type, status, details, prev_hash, record_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (now_str, actor_username, actor_role, action, target_id, target_type, status, details or "", prev_hash, record_hash))
            conn.commit()
            conn.close()
            conn = None
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
            print(f"[AuditLog] Fallback write error: {e}")
            record_hash = "ERROR_HASH"

        # PostgreSQL sync if available
        try:
            from db.postgres import get_engine
            from sqlalchemy import text
            engine = get_engine()
            if engine is not None:
                with engine.begin() as pg_conn:
                    pg_conn.execute(text("""
                        INSERT INTO audit_logs (timestamp, actor_username, actor_role, action, target_id, target_type, status, details, prev_hash, record_hash)
                        VALUES (:ts, :act_user, :act_role, :action, :tgt_id, :tgt_type, :status, :details, :phash, :rhash);
                    """), {
                        "ts": datetime.utcnow(),
                        "act_user": actor_username,
                        "act_role": actor_role,
                        "action": action,
                        "tgt_id": target_id,
                        "tgt_type": target_type,
                        "status": status,
                        "details": details or "",
                        "phash": prev_hash,
                        "rhash": record_hash
                    })
        except Exception:
            pass


def verify_audit_log_chain() -> Dict[str, Any]:
    """
    Cryptographically verifies the append-only SHA-256 hash chain of the audit log.
    Detects tampering, modified record payloads, modified prev_hash links, dropped middle records,
    reordered records, and sequential corruptions.
    Supports both canonical JSON hashing and legacy format backward compatibility.
    """
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, actor_username, actor_role, action, target_id, target_type, status, details, prev_hash, record_hash FROM audit_logs ORDER BY id ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if not rows:
            return {"valid": True, "total_records": 0, "chained_records": 0, "tampered_at_id": None, "details": "Audit log is empty."}

        expected_prev_hash = "GENESIS"
        chained_count = 0

        for row in rows:
            rec_id = row["id"]
            actual_prev = row.get("prev_hash")
            actual_hash = row.get("record_hash")

            # Records before cryptographic chaining was introduced have NULL hash
            if actual_hash is None:
                continue

            chained_count += 1

            # Verify chain link
            if actual_prev != expected_prev_hash and expected_prev_hash != "GENESIS":
                return {
                    "valid": False,
                    "total_records": len(rows),
                    "chained_records": chained_count,
                    "tampered_at_id": rec_id,
                    "details": f"Broken chain link at log ID {rec_id}: expected prev_hash '{expected_prev_hash}', got '{actual_prev}'."
                }

            # Verify payload digest: check canonical JSON first, fallback to legacy pipe
            canonical_hash = compute_audit_record_hash(
                prev_hash=actual_prev or "GENESIS",
                timestamp=row["timestamp"],
                actor_username=row["actor_username"],
                actor_role=row["actor_role"],
                action=row["action"],
                target_id=row["target_id"],
                target_type=row["target_type"],
                status=row["status"],
                details=row["details"]
            )
            legacy_hash = compute_legacy_audit_record_hash(
                prev_hash=actual_prev or "GENESIS",
                timestamp=row["timestamp"],
                actor_username=row["actor_username"],
                actor_role=row["actor_role"],
                action=row["action"],
                target_id=row["target_id"],
                target_type=row["target_type"],
                status=row["status"],
                details=row["details"]
            )

            if actual_hash not in (canonical_hash, legacy_hash):
                return {
                    "valid": False,
                    "total_records": len(rows),
                    "chained_records": chained_count,
                    "tampered_at_id": rec_id,
                    "details": f"Digest mismatch at log ID {rec_id}: record payload has been altered."
                }

            expected_prev_hash = actual_hash

        return {
            "valid": True,
            "total_records": len(rows),
            "chained_records": chained_count,
            "tampered_at_id": None,
            "details": f"Cryptographic integrity verified across {chained_count} chained audit records."
        }
    except Exception as e:
        return {"valid": False, "total_records": 0, "chained_records": 0, "tampered_at_id": None, "details": f"Verification error: {str(e)}"}


def get_recent_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent audit logs for administrative inspection."""
    # Try PostgreSQL first
    try:
        from db.postgres import fetch_table_df
        df = fetch_table_df("audit_logs", limit=limit)
        if not df.empty:
            df = df.sort_values(by="id", ascending=False)
            return df.to_dict(orient="records")
    except Exception:
        pass

    # Fallback to SQLite
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def get_all_users() -> List[Dict[str, Any]]:
    """Retrieves all registered hospital accessors and user accounts for administrative inspection."""
    # Try PostgreSQL first
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.connect() as conn:
                res = conn.execute(
                    text("SELECT id, username, role, full_name, department, is_active, created_at, last_login FROM users ORDER BY id ASC;")
                ).mappings().all()
                if res:
                    return [dict(r) for r in res]
    except Exception:
        pass

    # Fallback to local SQLite
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, role, full_name, department, is_active, created_at, last_login FROM users ORDER BY id ASC"
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[Auth] Error fetching all users: {e}")
        return []


def create_new_user(
    username: str,
    password: str,
    role: str,
    full_name: str,
    department: Optional[str] = None,
    actor_user: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Provisions a new authorized user account (ADMIN or ADMISSION_OFFICER).
    Enforces 'users.manage' permission on the administrative caller.
    """
    require_permission("users.manage", actor_user)
    actor_username = actor_user.get("username", "admin") if actor_user else "admin"
    actor_role = actor_user.get("role", ROLE_ADMIN) if actor_user else ROLE_ADMIN

    # Validation
    if not username or not username.strip():
        raise ValueError("Username is required.")
    if not password or len(password.strip()) < 6:
        raise ValueError("Password must be at least 6 characters long.")
    if not full_name or not full_name.strip():
        raise ValueError("Full Name is required.")
    
    clean_role = role.strip().upper()
    if clean_role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Permitted roles are: {VALID_ROLES}")

    clean_user = username.strip().lower()
    clean_name = full_name.strip()
    clean_dept = (department or "Hospital").strip()

    # Check for existing user
    existing = get_user_by_username(clean_user)
    if existing:
        raise ValueError(f"User account '{clean_user}' already exists.")

    pw_hash, salt = hash_password(password.strip())
    now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # 1. SQLite insert
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (username, password_hash, salt, role, full_name, department, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    """, (clean_user, pw_hash, salt, clean_role, clean_name, clean_dept, now_ts))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # 2. PostgreSQL insert if available
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.begin() as pg_conn:
                pg_conn.execute(text("""
                    INSERT INTO users (username, password_hash, salt, role, full_name, department, is_active, created_at)
                    VALUES (:u, :h, :s, :r, :fn, :d, true, :ts)
                    ON CONFLICT (username) DO NOTHING;
                """), {
                    "u": clean_user, "h": pw_hash, "s": salt, "r": clean_role,
                    "fn": clean_name, "d": clean_dept, "ts": datetime.utcnow()
                })
    except Exception as e:
        print(f"[Auth] Warning writing new user to Postgres: {e}")

    # Audit creation
    log_audit_event(
        actor_username=actor_username,
        actor_role=actor_role,
        action="users.create",
        target_id=clean_user,
        target_type="user",
        status="SUCCESS",
        details=f"Provisioned new {clean_role} account for {clean_name} ({clean_dept})"
    )

    return {
        "id": user_id,
        "username": clean_user,
        "role": clean_role,
        "full_name": clean_name,
        "department": clean_dept,
        "created_at": now_ts
    }


def _resolve_username(identifier: Any) -> Optional[str]:
    """Safely determines the unique username regardless of DB-specific autoincrement sequence."""
    if identifier is None:
        return None
    s = str(identifier).strip()
    if not s:
        return None

    # Check if directly matches a username
    u = get_user_by_username(s)
    if u:
        return u["username"]

    # Try matching ID in Postgres
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.connect() as conn:
                res = conn.execute(
                    text("SELECT username FROM users WHERE id::text = :id OR LOWER(username) = LOWER(:u) LIMIT 1;"),
                    {"id": s, "u": s}
                ).mappings().first()
                if res:
                    return res["username"]
    except Exception:
        pass

    # Try matching ID in SQLite
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE CAST(id AS TEXT) = ? OR LOWER(username) = LOWER(?) LIMIT 1", (s, s))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row["username"]
    except Exception:
        pass

    return s


def toggle_user_status(
    user_identifier: Any,
    is_active: bool,
    actor_user: Optional[Dict[str, Any]] = None
) -> bool:
    """Activates or deactivates an accessor account."""
    require_permission("users.manage", actor_user)
    actor_username = (actor_user.get("username", "admin") if actor_user else "admin").strip().lower()
    actor_role = actor_user.get("role", ROLE_ADMIN) if actor_user else ROLE_ADMIN

    target_name = _resolve_username(user_identifier)
    if not target_name:
        raise ValueError(f"Accessor account '{user_identifier}' not found.")

    clean_target = target_name.strip().lower()

    # Prevent self-deactivation (only when attempting to deactivate)
    if not is_active and actor_username and clean_target == actor_username:
        raise ValueError("Cannot deactivate your own active session account.")

    # Update SQLite
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_active = ? WHERE LOWER(username) = ?", 
                   (1 if is_active else 0, clean_target))
    conn.commit()
    conn.close()

    # Update PostgreSQL if available
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.begin() as pg_conn:
                pg_conn.execute(
                    text("UPDATE users SET is_active = :act WHERE LOWER(username) = :u;"),
                    {"act": bool(is_active), "u": clean_target}
                )
    except Exception:
        pass

    status_str = "activated" if is_active else "deactivated"
    log_audit_event(
        actor_username=actor_username,
        actor_role=actor_role,
        action="users.update_status",
        target_id=clean_target,
        target_type="user",
        status="SUCCESS",
        details=f"Account '{clean_target}' was {status_str}"
    )
    return True


def delete_user(
    user_identifier: Any,
    actor_user: Optional[Dict[str, Any]] = None
) -> bool:
    """Deletes a user account with safeguards against self-deletion."""
    require_permission("users.manage", actor_user)
    actor_username = (actor_user.get("username", "admin") if actor_user else "admin").strip().lower()
    actor_role = actor_user.get("role", ROLE_ADMIN) if actor_user else ROLE_ADMIN

    target_name = _resolve_username(user_identifier)
    if not target_name:
        raise ValueError(f"Accessor account '{user_identifier}' not found.")

    clean_target = target_name.strip().lower()

    if actor_username and clean_target == actor_username:
        raise ValueError("Cannot delete your own active administrator account.")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE LOWER(username) = ?", (clean_target,))
    conn.commit()
    conn.close()

    # Delete in PostgreSQL
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.begin() as pg_conn:
                pg_conn.execute(
                    text("DELETE FROM users WHERE LOWER(username) = :u;"),
                    {"u": clean_target}
                )
    except Exception:
        pass

    log_audit_event(
        actor_username=actor_username,
        actor_role=actor_role,
        action="users.delete",
        target_id=clean_target,
        target_type="user",
        status="SUCCESS",
        details=f"Deleted accessor account '{clean_target}'"
    )
    return True


def update_user_password(
    user_identifier: Any,
    new_password: str,
    actor_user: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Updates the password for an accessor account.
    Enforces 'users.manage' permission, validates password complexity (>=6 chars),
    hashes with PBKDF2-HMAC-SHA256, and synchronizes across SQLite and PostgreSQL.
    """
    require_permission("users.manage", actor_user)
    actor_username = (actor_user.get("username", "admin") if actor_user else "admin").strip().lower()
    actor_role = actor_user.get("role", ROLE_ADMIN) if actor_user else ROLE_ADMIN

    if not new_password or len(new_password.strip()) < 6:
        raise ValueError("New password must be at least 6 characters long.")

    target_name = _resolve_username(user_identifier)
    if not target_name:
        raise ValueError(f"Accessor account '{user_identifier}' not found.")

    clean_target = target_name.strip().lower()
    pw_hash, salt = hash_password(new_password.strip())

    # Update SQLite
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE LOWER(username) = ?",
        (pw_hash, salt, clean_target)
    )
    conn.commit()
    conn.close()

    # Update PostgreSQL if available
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.begin() as pg_conn:
                pg_conn.execute(
                    text("UPDATE users SET password_hash = :h, salt = :s WHERE LOWER(username) = :u;"),
                    {"h": pw_hash, "s": salt, "u": clean_target}
                )
    except Exception as e:
        print(f"[Auth] Warning updating password in Postgres: {e}")

    log_audit_event(
        actor_username=actor_username,
        actor_role=actor_role,
        action="users.update_password",
        target_id=clean_target,
        target_type="user",
        status="SUCCESS",
        details=f"Password updated for accessor '{clean_target}'"
    )
    return True


def update_user_profile(
    user_identifier: Any,
    full_name: Optional[str] = None,
    department: Optional[str] = None,
    role: Optional[str] = None,
    actor_user: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Updates an accessor's account metadata (Full Name, Department, and/or Role).
    Enforces 'users.manage' permission on the administrative caller.
    Synchronizes updates across SQLite and PostgreSQL and logs the audit event.
    """
    require_permission("users.manage", actor_user)
    actor_username = (actor_user.get("username", "admin") if actor_user else "admin").strip().lower()
    actor_role = actor_user.get("role", ROLE_ADMIN) if actor_user else ROLE_ADMIN

    target_name = _resolve_username(user_identifier)
    if not target_name:
        raise ValueError(f"Accessor account '{user_identifier}' not found.")

    clean_target = target_name.strip().lower()

    # Validate role if provided
    clean_role = None
    if role is not None:
        clean_role = role.strip().upper()
        if clean_role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Permitted roles are: {VALID_ROLES}")
        # Safeguard: Prevent admin from demoting their own active session if they are currently an admin
        if clean_target == actor_username and clean_role != ROLE_ADMIN:
            raise ValueError("You cannot demote your own active administrator account.")

    clean_name = full_name.strip() if full_name is not None and full_name.strip() else None
    clean_dept = department.strip() if department is not None and department.strip() else None

    # Update SQLite
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET full_name = COALESCE(?, full_name),
            department = COALESCE(?, department),
            role = COALESCE(?, role)
        WHERE LOWER(username) = ?
    """, (clean_name, clean_dept, clean_role, clean_target))
    conn.commit()

    cursor.execute("SELECT id, username, role, full_name, department, is_active FROM users WHERE LOWER(username) = ?", (clean_target,))
    updated_row = cursor.fetchone()
    conn.close()

    # Update PostgreSQL if available
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.begin() as pg_conn:
                pg_conn.execute(text("""
                    UPDATE users
                    SET full_name = COALESCE(:fn, full_name),
                        department = COALESCE(:dept, department),
                        role = COALESCE(:r, role)
                    WHERE LOWER(username) = :u;
                """), {"fn": clean_name, "dept": clean_dept, "r": clean_role, "u": clean_target})
    except Exception as e:
        print(f"[Auth] Warning updating user profile in Postgres: {e}")

    changes = []
    if clean_name:
        changes.append(f"name='{clean_name}'")
    if clean_dept:
        changes.append(f"dept='{clean_dept}'")
    if clean_role:
        changes.append(f"role='{clean_role}'")

    log_audit_event(
        actor_username=actor_username,
        actor_role=actor_role,
        action="users.update_profile",
        target_id=clean_target,
        target_type="user",
        status="SUCCESS",
        details=f"Updated accessor profile for '{clean_target}': {', '.join(changes) if changes else 'no change'}"
    )

    return dict(updated_row) if updated_row else {"username": clean_target}




def is_session_valid(user: Optional[Dict[str, Any]], max_age_seconds: int = 28800) -> bool:
    """
    Verifies that a user session has not expired and that the user account
    remains active in the database.
    """
    if not user or not isinstance(user, dict):
        return False
    # Check database if user was disabled since session creation
    db_user = get_user_by_username(user.get("username", ""))
    if not db_user or not db_user.get("is_active"):
        return False
    # Check session age if login_timestamp provided
    login_ts = user.get("login_timestamp")
    if login_ts:
        try:
            import time
            age = time.time() - float(login_ts)
            if age > max_age_seconds:
                return False
        except Exception:
            pass
    return True


def export_audit_chain_checkpoint(target_file: Optional[Path] = None) -> Path:
    """
    Exports a signed cryptographic checkpoint of the current audit chain head.
    Enables detection of trailing record deletion (threat model limitation mitigation).
    """
    from config import DB_DIR
    checkpoint_path = target_file or (DB_DIR / "audit_checkpoint_latest.json")
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, action, prev_hash, record_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
    latest = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM audit_logs")
    total_count = cursor.fetchone()[0]
    conn.close()

    curr_hash = latest["record_hash"] if latest else "GENESIS"
    checkpoint_data = {
        "checkpoint_timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_records": total_count,
        "latest_record_id": latest["id"] if latest else 0,
        "latest_record_hash": curr_hash,
        "latest_action": latest["action"] if latest else "NONE",
        "signature_digest": hashlib.sha256(f"{total_count}|{curr_hash}".encode("utf-8")).hexdigest()
    }

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f, indent=2)

    return checkpoint_path


def verify_audit_checkpoint(checkpoint_file: Path) -> Dict[str, Any]:
    """
    Verifies the current audit log table against an exported chain checkpoint.
    Detects trailing truncation where records were silently deleted from the tail.
    """
    p = Path(checkpoint_file)
    if not p.exists():
        return {"valid": False, "error": f"Checkpoint file not found: {checkpoint_file}"}

    with open(p, "r", encoding="utf-8") as f:
        cp = json.load(f)

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM audit_logs")
    curr_count = cursor.fetchone()[0]
    cursor.execute("SELECT id, record_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
    latest = cursor.fetchone()
    conn.close()

    if curr_count < cp["total_records"]:
        return {
            "valid": False,
            "error": f"Trailing truncation detected! Checkpoint expected {cp['total_records']} records, but table only contains {curr_count}."
        }

    curr_hash = latest["record_hash"] if latest else "GENESIS"
    if cp["latest_record_id"] == (latest["id"] if latest else 0) and curr_hash != cp["latest_record_hash"]:
        return {
            "valid": False,
            "error": f"Chain head mismatch! Expected hash {cp['latest_record_hash']}, found {curr_hash}."
        }

    return {
        "valid": True,
        "checkpoint_records": cp["total_records"],
        "current_records": curr_count,
        "details": "Audit chain matches or extends exported cryptographic checkpoint."
    }
