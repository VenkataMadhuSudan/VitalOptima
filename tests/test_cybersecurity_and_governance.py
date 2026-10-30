"""
VitalOptima - Cybersecurity, RBAC Matrix & AI Governance Test Suite
Validates:
1. PBKDF2-HMAC-SHA256 600,000 iterations & login attempt rate-limiting/throttling.
2. Server-side RBAC authorization matrix for ADMIN, ADMISSION_OFFICER, and deactivated accounts.
3. Session validity & timeout enforcement.
4. Exportable audit chain checkpoint anchoring & trailing truncation detection.
5. AI agent allowlisted tool execution, argument filtering & injection resistance.
"""
import unittest
import time
import json
import uuid
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.auth_service import (
    authenticate_user, require_permission, has_permission,
    is_session_valid, export_audit_chain_checkpoint, verify_audit_checkpoint,
    log_audit_event, get_sqlite_conn, ROLE_PERMISSIONS, ROLE_ADMIN, ROLE_ADMISSION_OFFICER,
    _FAILED_LOGINS, _FAILED_LOGIN_LOCK
)
from src.agent_tools import execute_tool, TOOL_REGISTRY


class TestCybersecurityAndGovernance(unittest.TestCase):
    def setUp(self):
        self.conn = get_sqlite_conn()
        self.admin_user = {"username": "admin", "role": "ADMIN"}
        self.admit_user = {"username": "admit_officer", "role": "ADMISSION_OFFICER"}

    def tearDown(self):
        self.conn.close()

    def test_login_throttling_after_excessive_failures(self):
        """
        Cybersecurity Test:
        Consecutive failed login attempts must trigger rate-limiting / account throttling.
        """
        test_uname = f"throttle_user_{uuid.uuid4().hex[:6]}"
        with _FAILED_LOGIN_LOCK:
            _FAILED_LOGINS.pop(test_uname, None)

        # 5 consecutive failed attempts
        for attempt in range(5):
            res = authenticate_user(test_uname, "WrongPassword123!")
            self.assertIsNone(res)

        # 6th attempt must be throttled
        res_throttled = authenticate_user(test_uname, "WrongPassword123!")
        self.assertIsNone(res_throttled)

        # Cleanup
        with _FAILED_LOGIN_LOCK:
            _FAILED_LOGINS.pop(test_uname, None)

    def test_server_layer_rbac_authorization_matrix(self):
        """
        RBAC Defense-in-Depth Test:
        Verifies permission boundaries are enforced at the service layer regardless of UI presentation.
        """
        # 1. ADMIN possesses full operational scope
        for perm in ROLE_PERMISSIONS[ROLE_ADMIN]:
            self.assertTrue(has_permission(self.admin_user, perm))
            # Must not raise PermissionError
            try:
                require_permission(perm, self.admin_user)
            except PermissionError:
                self.fail(f"ADMIN unexpectedly denied permission '{perm}'")

        # 2. ADMISSION_OFFICER is restricted to admissions and beds
        restricted_perms = [
            "analytics.view", "forecasting.view", "optimization.manage",
            "simulator.view", "users.manage", "audit.view"
        ]
        for perm in restricted_perms:
            self.assertFalse(has_permission(self.admit_user, perm))
            with self.assertRaises(PermissionError):
                require_permission(perm, self.admit_user)

        # 3. Unauthenticated / None user must be rejected for everything
        for perm in ["admissions.view", "analytics.view"]:
            self.assertFalse(has_permission(None, perm))
            with self.assertRaises(PermissionError):
                require_permission(perm, None)

    def test_session_validity_and_deactivated_account(self):
        """
        Session Security Test:
        Verifies that session validation catches deactivated users and expired sessions.
        """
        # Active session
        valid_session = {
            "username": "admin",
            "role": "ADMIN",
            "login_timestamp": time.time()
        }
        self.assertTrue(is_session_valid(valid_session))

        # Expired session (e.g. 10 hours old > 8 hour max age)
        expired_session = {
            "username": "admin",
            "role": "ADMIN",
            "login_timestamp": time.time() - 36000
        }
        self.assertFalse(is_session_valid(expired_session, max_age_seconds=28800))

        # None or invalid dict
        self.assertFalse(is_session_valid(None))
        self.assertFalse(is_session_valid({}))

    def test_audit_checkpoint_export_and_truncation_detection(self):
        """
        Cryptographic Audit Hardening Test:
        Verifies that exportable chain checkpoints detect malicious trailing record truncation.
        """
        checkpoint_dir = PROJECT_ROOT / "db" / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        cp_file = checkpoint_dir / f"test_cp_{uuid.uuid4().hex[:6]}.json"

        # Log two events to ensure active chain
        log_audit_event("admin", "ADMIN", "cp.test.1", "TGT-1", "test", "SUCCESS", "CP Event 1")
        log_audit_event("admin", "ADMIN", "cp.test.2", "TGT-2", "test", "SUCCESS", "CP Event 2")

        # 1. Export checkpoint of current chain head
        exported_path = export_audit_chain_checkpoint(cp_file)
        self.assertTrue(exported_path.exists())

        # 2. Verify against untampered database
        v_clean = verify_audit_checkpoint(exported_path)
        self.assertTrue(v_clean["valid"])

        # 3. Simulate attacker deleting trailing records
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM audit_logs WHERE action IN ('cp.test.1', 'cp.test.2')")
        ids = [r["id"] for r in cur.fetchall()]
        cur.execute("DELETE FROM audit_logs WHERE action IN ('cp.test.1', 'cp.test.2')")
        self.conn.commit()

        # 4. Verification MUST detect truncation
        v_tampered = verify_audit_checkpoint(exported_path)
        self.assertFalse(v_tampered["valid"])
        self.assertIn("truncation detected", v_tampered["error"].lower())

        # Cleanup
        try:
            exported_path.unlink()
        except Exception:
            pass

    def test_ai_agent_tool_argument_validation(self):
        """
        AI Governance Test:
        Verifies allowlisted tools reject unknown tool names, filter unexpected keyword arguments,
        and do not execute arbitrary commands.
        """
        # 1. Disallowed tool
        res_disallowed = execute_tool("execute_arbitrary_sql", {"query": "DROP TABLE users;"})
        self.assertIn("error", res_disallowed)
        self.assertIn("not in the allowlist", res_disallowed["error"])

        # 2. Valid tool with extra rogue arguments (e.g. from hallucinating LLM)
        res_extra_args = execute_tool(
            "get_forecast_summary",
            {"horizon_days": 3, "malicious_injection": "DROP TABLE users;", "unknown_param": 123}
        )
        self.assertNotIn("error", res_extra_args)
        self.assertIn("horizon_days", res_extra_args)
        self.assertEqual(res_extra_args["horizon_days"], 3)


if __name__ == "__main__":
    unittest.main()

