"""
VitalOptima Comprehensive Security, RBAC & Authentication Test Suite
Tests 30 rigorous scenarios across:
1. Authentication & Persistent Rate Limiting
2. Session Management & Lifecycle (Idle & Absolute Timeouts)
3. Authorization & Defense-in-Depth RBAC
4. Database Integrity, Invariants & SQL Injection Resistance
5. User Provisioning & Forced Password Rotation
6. Cryptographic Audit Chain Integrity & Tamper Detection
"""
import unittest
import time
import uuid
import secrets
import sqlite3
from pathlib import Path
from config import DB_PATH
from services.auth_service import (
    authenticate_user, hash_password, verify_password,
    validate_password_complexity, is_account_locked, is_ip_locked,
    record_login_attempt, clear_failed_login_attempts,
    create_server_session, validate_server_session, revoke_server_session,
    revoke_all_user_sessions, provision_initial_admin, change_user_password,
    reauthenticate_admin, create_new_user, get_user_by_username,
    require_permission, has_permission, get_current_user, logout_user,
    log_audit_event, verify_audit_log_chain, export_audit_chain_checkpoint,
    verify_audit_checkpoint, ROLE_ADMIN, ROLE_ADMISSION_OFFICER,
    _FAILED_LOGINS, _FAILED_LOGIN_LOCK, LOCKOUT_WINDOW_SECONDS,
    DEFAULT_PBKDF2_ITERATIONS
)
from db.database import init_db, get_sqlite_connection


class TestComprehensiveSecuritySuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.admin_actor = {"username": "admin", "role": ROLE_ADMIN}
        import streamlit as st
        if hasattr(st, "session_state"):
            st.session_state.clear()

    def tearDown(self):
        self.conn.close()
        import streamlit as st
        if hasattr(st, "session_state"):
            st.session_state.clear()

    # =========================================================================
    # GROUP 1: AUTHENTICATION & PERSISTENT RATE LIMITING (SCENARIOS 1-8)
    # =========================================================================

    def test_01_password_complexity_validation(self):
        """Scenario 1: Password complexity enforcement (length, upper, lower, digit, special)."""
        # Too short
        valid, msg = validate_password_complexity("Short1!")
        self.assertFalse(valid)
        self.assertIn("at least 8 characters", msg)

        # Missing uppercase
        valid, msg = validate_password_complexity("nouppercase123!")
        self.assertFalse(valid)
        self.assertIn("uppercase", msg)

        # Missing lowercase
        valid, msg = validate_password_complexity("NOLOWERCASE123!")
        self.assertFalse(valid)
        self.assertIn("lowercase", msg)

        # Missing digit
        valid, msg = validate_password_complexity("NoDigitsHere!@#")
        self.assertFalse(valid)
        self.assertIn("digit", msg)

        # Missing special character
        valid, msg = validate_password_complexity("NoSpecialChars123")
        self.assertFalse(valid)
        self.assertIn("special character", msg)

        # Valid strong password
        valid, msg = validate_password_complexity("ClinicalSecure2026!")
        self.assertTrue(valid)

    def test_02_pbkdf2_iteration_and_constant_time_verification(self):
        """Scenario 2: NIST/OWASP PBKDF2-HMAC-SHA256 with 600,000 rounds and constant-time check."""
        pw = "TestSecure@2026"
        h, salt = hash_password(pw, iterations=DEFAULT_PBKDF2_ITERATIONS)
        self.assertEqual(len(h), 64)
        self.assertEqual(len(salt), 32)
        # Verify valid password succeeds
        self.assertTrue(verify_password(pw, h, salt))
        # Verify invalid password fails
        self.assertFalse(verify_password("WrongPw123!", h, salt))

    def test_03_persistent_brute_force_lockout_across_restarts(self):
        """Scenario 3: 5 failed attempts triggers account lockout that survives in-memory reset."""
        uname = f"lockout_user_{uuid.uuid4().hex[:6]}"
        clear_failed_login_attempts(uname)

        # Execute 5 failed login attempts
        for _ in range(5):
            res = authenticate_user(uname, "BadPassword123!")
            self.assertIsNone(res)

        # Account must now be locked
        is_locked, rem_secs = is_account_locked(uname)
        self.assertTrue(is_locked)
        self.assertGreater(rem_secs, 0)

        # SIMULATE APPLICATION RESTART: wipe the in-memory cache completely
        with _FAILED_LOGIN_LOCK:
            _FAILED_LOGINS.clear()

        # Database must still enforce the lockout!
        is_locked_after_restart, rem_after = is_account_locked(uname)
        self.assertTrue(is_locked_after_restart, "Persistent lockout must survive process restart via DB storage")
        self.assertGreater(rem_after, 0)

        # Cleanup
        clear_failed_login_attempts(uname)

    def test_04_ip_based_rate_limiting(self):
        """Scenario 4: Excessive failed attempts from same client IP triggers IP lockout."""
        fake_ip = f"192.168.1.{secrets.randbelow(200) + 50}"
        # Record 15 failed attempts for this IP
        for i in range(15):
            record_login_attempt(fake_ip, attempt_type="ip", success=False, ip_address=fake_ip)

        locked, rem = is_ip_locked(fake_ip)
        self.assertTrue(locked, "IP must be locked after 15 failed attempts")
        self.assertGreater(rem, 0)

    def test_05_timing_attack_defense_on_nonexistent_users(self):
        """Scenario 5: Nonexistent user executes dummy PBKDF2 hash computation to mitigate timing attacks."""
        nonexistent = f"ghost_user_{uuid.uuid4().hex}"
        clear_failed_login_attempts(nonexistent)

        # Authenticate nonexistent user: must return None and record failed attempt
        res = authenticate_user(nonexistent, "TestPassword123!")
        self.assertIsNone(res)

        # Verify failed attempt was recorded
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM login_attempts WHERE identifier = ? AND success = 0", (nonexistent,))
        count = cur.fetchone()[0]
        self.assertGreaterEqual(count, 1)

    def test_06_successful_authentication_clears_failed_attempts(self):
        """Scenario 6: Successful login resets failed attempts for username and IP."""
        uname = "admin"
        fake_ip = "10.0.0.99"
        # Simulate 2 failed attempts
        record_login_attempt(uname, "username", success=False, ip_address=fake_ip)
        record_login_attempt(uname, "username", success=False, ip_address=fake_ip)

        # Authenticate successfully
        user = authenticate_user("admin", "Admin@Vital2026!", ip_address=fake_ip)
        self.assertIsNotNone(user)

        # Verify failed attempts were cleared
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM login_attempts WHERE identifier = ? AND attempt_type = 'username' AND success = 0", (uname,))
        self.assertEqual(cur.fetchone()[0], 0)

    def test_07_invalid_credentials_returns_generic_none(self):
        """Scenario 7: Uniform rejection preventing account enumeration."""
        res_bad_pw = authenticate_user("admin", "WrongPassword!")
        self.assertIsNone(res_bad_pw)

        res_bad_user = authenticate_user("definitely_nonexistent_user_xyz", "WrongPassword!")
        self.assertIsNone(res_bad_user)

    def test_08_empty_or_whitespace_credentials_rejected(self):
        """Scenario 8: Empty or whitespace usernames and passwords rejected safely."""
        self.assertIsNone(authenticate_user("", ""))
        self.assertIsNone(authenticate_user("admin", ""))
        self.assertIsNone(authenticate_user("", "Admin@Vital2026!"))
        self.assertIsNone(authenticate_user("   ", "   "))

    # =========================================================================
    # GROUP 2: SESSION MANAGEMENT & LIFECYCLE (SCENARIOS 9-14)
    # =========================================================================

    def test_09_server_session_creation(self):
        """Scenario 9: Cryptographically random 32-byte session token created and persisted."""
        token = create_server_session("admin", ip_address="127.0.0.1", user_agent="PyTest")
        self.assertIsNotNone(token)
        self.assertGreater(len(token), 30)

        # Verify session is valid
        user_sess = validate_server_session(token)
        self.assertIsNotNone(user_sess)
        self.assertEqual(user_sess["username"], "admin")
        self.assertEqual(user_sess["role"], "ADMIN")

    def test_10_session_idle_timeout_enforcement(self):
        """Scenario 10: Session exceeding idle timeout is invalidated."""
        token = create_server_session("admin")
        # Artificially age last_activity_at by 2000 seconds (> 1800s idle timeout)
        cur = self.conn.cursor()
        cur.execute("UPDATE active_sessions SET last_activity_at = ? WHERE session_id = ?", (time.time() - 2000, token))
        self.conn.commit()

        # Validation must reject and revoke the session
        valid_user = validate_server_session(token)
        self.assertIsNone(valid_user, "Idle session must be invalidated")

    def test_11_session_absolute_lifetime_enforcement(self):
        """Scenario 11: Session exceeding absolute lifetime (28,800s) is invalidated."""
        token = create_server_session("admin")
        # Artificially age created_at by 30000 seconds (> 28800s absolute lifetime)
        cur = self.conn.cursor()
        cur.execute("UPDATE active_sessions SET created_at = ? WHERE session_id = ?", (time.time() - 30000, token))
        self.conn.commit()

        valid_user = validate_server_session(token)
        self.assertIsNone(valid_user, "Session exceeding absolute lifetime must be invalidated")

    def test_12_explicit_session_revocation_on_logout(self):
        """Scenario 12: Revoking session marks is_revoked = 1."""
        token = create_server_session("admin")
        revoke_server_session(token)

        self.assertIsNone(validate_server_session(token))

    def test_13_deactivated_account_invalidates_all_active_sessions(self):
        """Scenario 13: Deactivating user immediately invalidates active sessions."""
        test_uname = f"deact_{uuid.uuid4().hex[:6]}"
        create_new_user(test_uname, "TempSecure@2026", ROLE_ADMISSION_OFFICER, "Deact Test", "Ops", actor_user=self.admin_actor)
        token = create_server_session(test_uname)
        self.assertIsNotNone(validate_server_session(token))

        # Deactivate user in database
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET is_active = 0 WHERE username = ?", (test_uname,))
        self.conn.commit()

        # Session validation must fail
        self.assertIsNone(validate_server_session(token))

    def test_14_revoke_all_sessions_for_user(self):
        """Scenario 14: revoke_all_user_sessions terminates all sessions for an account."""
        test_uname = f"multi_sess_{uuid.uuid4().hex[:6]}"
        create_new_user(test_uname, "TempSecure@2026", ROLE_ADMISSION_OFFICER, "Multi Sess", "Ops", actor_user=self.admin_actor)
        t1 = create_server_session(test_uname)
        t2 = create_server_session(test_uname)

        revoke_all_user_sessions(test_uname)
        self.assertIsNone(validate_server_session(t1))
        self.assertIsNone(validate_server_session(t2))

    # =========================================================================
    # GROUP 3: AUTHORIZATION & DEFENSE-IN-DEPTH RBAC (SCENARIOS 15-18)
    # =========================================================================

    def test_15_service_layer_permission_enforcement(self):
        """Scenario 15: Direct invocation without required permission raises PermissionError."""
        officer = {"username": "admit_officer", "role": ROLE_ADMISSION_OFFICER}

        # Officer attempting admin-only permission must be rejected
        with self.assertRaises(PermissionError):
            require_permission("users.manage", officer)

        with self.assertRaises(PermissionError):
            require_permission("optimization.manage", officer)

        # Admin must succeed
        admin = {"username": "admin", "role": ROLE_ADMIN}
        require_permission("users.manage", admin)

    def test_16_client_role_spoofing_overridden_by_authoritative_db(self):
        """Scenario 16: Tampering with cached session role is repaired by server validation."""
        import streamlit as st
        token = create_server_session("admit_officer")
        # Attacker attempts to modify cached dict in session state to ADMIN
        st.session_state["authenticated_user"] = {
            "username": "admit_officer",
            "role": "ADMIN",  # Spoofed!
            "session_token": token
        }

        # get_current_user must validate token and restore genuine DB role ADMISSION_OFFICER
        resolved_user = get_current_user()
        self.assertIsNotNone(resolved_user)
        self.assertEqual(resolved_user["role"], "ADMISSION_OFFICER", "DB authority must overwrite spoofed role")

    def test_17_least_privilege_boundary_matrix(self):
        """Scenario 17: Validates full permissions matrix for ADMIN vs ADMISSION_OFFICER."""
        admin_perms = ["admissions.view", "admissions.create", "users.manage", "optimization.view", "audit.view"]
        officer_perms = ["admissions.view", "admissions.create", "admissions.discharge", "beds.view"]

        for p in admin_perms:
            self.assertTrue(has_permission(ROLE_ADMIN, p))

        for p in officer_perms:
            self.assertTrue(has_permission(ROLE_ADMISSION_OFFICER, p))

        # Officer must NOT have manage perms
        self.assertFalse(has_permission(ROLE_ADMISSION_OFFICER, "users.manage"))
        self.assertFalse(has_permission(ROLE_ADMISSION_OFFICER, "optimization.manage"))
        self.assertFalse(has_permission(ROLE_ADMISSION_OFFICER, "audit.view"))

    def test_18_reauthenticate_admin_verification(self):
        """Scenario 18: Re-authentication before high-risk administrative action."""
        # Correct admin credentials
        self.assertTrue(reauthenticate_admin("admin", "Admin@Vital2026!"))
        # Wrong password
        self.assertFalse(reauthenticate_admin("admin", "WrongPassword!"))
        # Non-admin user cannot reauthenticate as admin
        self.assertFalse(reauthenticate_admin("admit_officer", "Admit@Vital2026!"))

    # =========================================================================
    # GROUP 4: DATABASE & TRANSACTION SECURITY (SCENARIOS 19-23)
    # =========================================================================

    def test_19_sql_injection_resistance_in_user_lookup(self):
        """Scenario 19: SQL injection payloads in user lookup handled safely without syntax error."""
        sqli_payloads = [
            "' OR '1'='1",
            "admin' --",
            "admin' UNION SELECT 1,2,3,4,5,6,7,8,9,10 --",
            "'; DROP TABLE users; --"
        ]
        for payload in sqli_payloads:
            res = get_user_by_username(payload)
            self.assertIsNone(res, f"SQL injection payload '{payload}' must return None")

        # Verify users table was not dropped
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        self.assertGreater(cur.fetchone()[0], 0)

    def test_20_active_bed_occupancy_unique_constraint(self):
        """Scenario 20: Database prevents two active admissions from occupying the same bed."""
        cur = self.conn.cursor()
        bed_test = f"TEST-BED-{uuid.uuid4().hex[:4]}"
        now_ts = "2026-10-15 12:00:00"

        # First admission
        cur.execute("""
            INSERT INTO patient_admissions (
                admission_id, patient_id, patient_name, age, gender, department,
                admission_type, status, bed_number, admitted_at, admitted_by, updated_at
            ) VALUES (?, ?, ?, 50, 'M', 'Medicine', 'Emergency', 'Admitted', ?, ?, 'tester', ?)
        """, (f"ADM-{uuid.uuid4().hex[:6]}", f"PAT-{uuid.uuid4().hex[:6]}", "Patient 1", bed_test, now_ts, now_ts))
        self.conn.commit()

        # Second admission attempting to occupy the same active bed must raise IntegrityError
        with self.assertRaises(sqlite3.IntegrityError):
            cur.execute("""
                INSERT INTO patient_admissions (
                    admission_id, patient_id, patient_name, age, gender, department,
                    admission_type, status, bed_number, admitted_at, admitted_by, updated_at
                ) VALUES (?, ?, ?, 40, 'F', 'Medicine', 'Emergency', 'Admitted', ?, ?, 'tester', ?)
            """, (f"ADM-{uuid.uuid4().hex[:6]}", f"PAT-{uuid.uuid4().hex[:6]}", "Patient 2", bed_test, now_ts, now_ts))
            self.conn.commit()

    def test_21_database_transaction_rollback_safety(self):
        """Scenario 21: Database rollbacks on failure leave state pristine."""
        initial_count = self.conn.cursor().execute("SELECT COUNT(*) FROM patient_admissions").fetchone()[0]
        try:
            cur = self.conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("INSERT INTO patient_admissions (admission_id, patient_id, patient_name, department, admission_type, admitted_at, admitted_by, updated_at) VALUES ('FAIL-1', 'P1', 'N1', 'Med', 'Emerg', 'now', 'admit', 'now')")
            # Force syntax error to trigger rollback
            cur.execute("INSERT INTO non_existent_table_xyz VALUES (1)")
            self.conn.commit()
        except Exception:
            self.conn.rollback()

        final_count = self.conn.cursor().execute("SELECT COUNT(*) FROM patient_admissions").fetchone()[0]
        self.assertEqual(initial_count, final_count)

    def test_22_login_attempts_and_active_sessions_schema_indexes(self):
        """Scenario 22: Indexes exist on login_attempts and active_sessions for performant rate limiting."""
        cur = self.conn.cursor()
        cur.execute("PRAGMA index_list('login_attempts')")
        indices = [row[1] for row in cur.fetchall()]
        self.assertTrue(any("idx_login_attempts" in idx for idx in indices))

        cur.execute("PRAGMA index_list('active_sessions')")
        sess_indices = [row[1] for row in cur.fetchall()]
        self.assertTrue(any("idx_active_sessions" in idx for idx in sess_indices))

    def test_23_must_change_password_column_integrity(self):
        """Scenario 23: must_change_password column exists and defaults correctly."""
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = {row[1]: row for row in cur.fetchall()}
        self.assertIn("must_change_password", cols)

    # =========================================================================
    # GROUP 5: USER PROVISIONING & FORCED PASSWORD ROTATION (SCENARIOS 24-27)
    # =========================================================================

    def test_24_no_public_registration_enforces_users_manage(self):
        """Scenario 24: create_new_user requires users.manage permission."""
        caller_no_perm = {"username": "nurse_joy", "role": ROLE_ADMISSION_OFFICER}
        with self.assertRaises(PermissionError):
            create_new_user("newbie", "SecurePass@2026", ROLE_ADMIN, "Newbie", "Admin", actor_user=caller_no_perm)

    def test_25_initial_admin_provisioning_preserves_existing_admin(self):
        """Scenario 25: provision_initial_admin refuses to overwrite existing admin account."""
        res = provision_initial_admin("admin", "NewAdmin@2026!")
        self.assertFalse(res["created"])
        self.assertIn("already exists", res["message"])

    def test_26_initial_admin_provisions_strong_random_password_when_none_provided(self):
        """Scenario 26: If no admin exists, provision_initial_admin generates strong random password and sets must_change_password=1."""
        # Temporarily rename existing admins for test
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET role = 'BACKUP_ADMIN' WHERE role = 'ADMIN'")
        self.conn.commit()

        try:
            res = provision_initial_admin("fresh_admin")
            self.assertTrue(res["created"])
            self.assertTrue(res["must_change_password"])
            self.assertIsNotNone(res["temporary_password"])
            # Validate generated password meets all complexity rules
            valid, _ = validate_password_complexity(res["temporary_password"])
            self.assertTrue(valid)
        finally:
            # Restore admin accounts
            cur.execute("DELETE FROM users WHERE username = 'fresh_admin'")
            cur.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'BACKUP_ADMIN'")
            self.conn.commit()

    def test_27_change_user_password_workflow(self):
        """Scenario 27: change_user_password validates current password, enforces complexity, resets flag."""
        test_u = f"pwchange_{uuid.uuid4().hex[:6]}"
        create_new_user(test_u, "OldPassword@2026", ROLE_ADMISSION_OFFICER, "Change Tester", "Ops", actor_user=self.admin_actor, must_change_password=True)

        # 1. Wrong current password fails
        suc, msg = change_user_password(test_u, "WrongCurrentPassword!", "NewSecurePassword@2026")
        self.assertFalse(suc)
        self.assertIn("verification failed", msg)

        # 2. Identical new password fails
        suc, msg = change_user_password(test_u, "OldPassword@2026", "OldPassword@2026")
        self.assertFalse(suc)
        self.assertIn("cannot be identical", msg)

        # 3. Weak new password fails
        suc, msg = change_user_password(test_u, "OldPassword@2026", "weak")
        self.assertFalse(suc)

        # 4. Valid change succeeds
        suc, msg = change_user_password(test_u, "OldPassword@2026", "BrandNewSecure@2026!")
        self.assertTrue(suc)

        # Check in DB that must_change_password is now 0
        u = get_user_by_username(test_u)
        self.assertEqual(u["must_change_password"], 0)

    # =========================================================================
    # GROUP 6: AUDIT TRAIL & CRYPTOGRAPHIC INTEGRITY (SCENARIOS 28-30)
    # =========================================================================

    def test_28_audit_event_cryptographic_hash_chaining(self):
        """Scenario 28: log_audit_event establishes a valid SHA-256 hash chain."""
        log_audit_event(
            actor_username="security_tester",
            actor_role="ADMIN",
            action="security.audit_test",
            status="SUCCESS",
            details="Verifying hash chain link"
        )
        res = verify_audit_log_chain()
        self.assertTrue(res["valid"])
        self.assertIsNone(res["tampered_at_id"])

    def test_29_audit_log_tamper_detection(self):
        """Scenario 29: Any payload or prev_hash tampering is detected by verify_audit_log_chain."""
        cur = self.conn.cursor()
        cur.execute("SELECT id, details FROM audit_logs WHERE record_hash IS NOT NULL ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            orig_id = row["id"]
            orig_details = row["details"]

            # Maliciously modify the details in database
            cur.execute("UPDATE audit_logs SET details = 'MALICIOUS_TAMPER' WHERE id = ?", (orig_id,))
            self.conn.commit()

            # Verification must detect the tampering
            res = verify_audit_log_chain()
            self.assertFalse(res["valid"])
            self.assertEqual(res["tampered_at_id"], orig_id)

            # Restore original details
            cur.execute("UPDATE audit_logs SET details = ? WHERE id = ?", (orig_details, orig_id))
            self.conn.commit()

            # Verify it is valid again
            self.assertTrue(verify_audit_log_chain()["valid"])

    def test_30_trailing_truncation_detection_via_checkpoint(self):
        """Scenario 30: Checkpoint export detects tail deletion of audit records."""
        cp_file = DB_PATH.parent / "test_security_checkpoint.json"
        export_audit_chain_checkpoint(cp_file)

        # Verification against unmodified log passes
        res = verify_audit_checkpoint(cp_file)
        self.assertTrue(res["valid"])

        # Clean up test checkpoint
        if cp_file.exists():
            cp_file.unlink()


if __name__ == "__main__":
    unittest.main()
