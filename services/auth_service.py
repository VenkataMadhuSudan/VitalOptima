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


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hashes password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a cryptographically
    secure 16-byte random salt.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies a plain password against the stored hash and salt using constant-time comparison."""
    if not password or not password_hash or not salt:
        return False
    computed_key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return secrets.compare_digest(computed_key.hex(), password_hash)


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

    if not verify_password(password, user["password_hash"], user["salt"]):
        log_audit_event(
            actor_username=user["username"],
            actor_role=user["role"],
            action="auth.login",
            status="FAILED",
            details="Invalid password attempt"
        )
        return None

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
        "last_login": now_str
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
    Records an immutable audit event in both PostgreSQL (primary) and SQLite (durability fallback).
    Never logs plaintext passwords, tokens, or sensitive patient identifiable keys.
    """
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # 1. PostgreSQL
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO audit_logs (timestamp, actor_username, actor_role, action, target_id, target_type, status, details)
                    VALUES (:ts, :act_user, :act_role, :action, :tgt_id, :tgt_type, :status, :details);
                """), {
                    "ts": datetime.utcnow(),
                    "act_user": actor_username,
                    "act_role": actor_role,
                    "action": action,
                    "tgt_id": target_id,
                    "tgt_type": target_type,
                    "status": status,
                    "details": details or ""
                })
    except Exception:
        pass

    # 2. Local SQLite fallback
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, actor_username, actor_role, action, target_id, target_type, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (now_str, actor_username, actor_role, action, target_id, target_type, status, details or ""))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AuditLog] Fallback write error: {e}")


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
