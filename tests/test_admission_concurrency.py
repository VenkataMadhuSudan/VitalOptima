"""
VitalOptima Admission Concurrency & Database Safety Test Suite
Validates:
1. Two independent database connections attempting to admit different patients into the exact same bed concurrently.
2. Verification that the database uniqueness invariant (idx_active_bed_occupancy) guarantees exactly ONE succeeds.
3. Verification that the losing connection receives a clean, actionable error ("claimed by a concurrent admission request").
4. Verification that patient discharge correctly frees the bed for subsequent admissions without conflict.
5. Verification of backward-compatible password authentication and rehash-on-login to 600,000 iterations.
"""
import unittest
import threading
import sqlite3
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_PATH
from services.admission_service import create_patient_admission, discharge_patient, get_sqlite_conn
from services.auth_service import (
    authenticate_user, hash_password, verify_password,
    DEFAULT_PBKDF2_ITERATIONS, LEGACY_PBKDF2_ITERATIONS
)


class TestAdmissionConcurrencyAndSecurity(unittest.TestCase):
    def setUp(self):
        self.conn = get_sqlite_conn()
        self.admin_user = {"username": "admin", "role": "ADMIN"}

    def tearDown(self):
        # Clean up any test admissions
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM patient_admissions WHERE patient_id LIKE 'PAT-CONC-%'")
            self.conn.commit()
        except Exception:
            pass
        self.conn.close()

    def test_concurrent_admissions_for_same_bed(self):
        """
        Concurrency Invariant Test:
        Two simultaneous admission attempts targeting the exact same bed (e.g. 'TEST-BED-999')
        must never result in double occupancy. Exactly one must succeed and the other must fail cleanly.
        """
        bed_id = "TEST-BED-999"
        results = []
        errors = []

        def attempt_admission(pat_num):
            try:
                res = create_patient_admission(
                    patient_id=f"PAT-CONC-{pat_num}",
                    patient_name=f"Concurrent Patient {pat_num}",
                    department="Medicine",
                    admission_type="Emergency",
                    bed_number=bed_id,
                    clinical_notes="Concurrency stress test admission",
                    actor_user=self.admin_user
                )
                results.append(res)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=attempt_admission, args=(1,))
        t2 = threading.Thread(target=attempt_admission, args=(2,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly 1 success, exactly 1 failure
        self.assertEqual(len(results), 1, f"Expected exactly 1 success, got {len(results)}: {results}")
        self.assertEqual(len(errors), 1, f"Expected exactly 1 error, got {len(errors)}: {errors}")

        # The error must be actionable and informative
        err_msg = str(errors[0])
        self.assertTrue(
            "already occupied" in err_msg.lower() or "claimed by a concurrent admission" in err_msg.lower(),
            f"Error message should mention bed occupancy conflict, got: '{err_msg}'"
        )

        # Confirm in SQLite table that only 1 active record exists for this bed
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM patient_admissions WHERE bed_number = ? AND status = 'Admitted'", (bed_id,))
        active_count = cur.fetchone()[0]
        self.assertEqual(active_count, 1)

        # Discharge the admitted patient
        winning_adm_id = results[0]["admission_id"]
        discharge_res = discharge_patient(winning_adm_id, discharge_notes="Discharged after test", actor_user=self.admin_user)
        self.assertTrue(discharge_res["success"])

        # Bed is now free: confirm another patient can now claim this bed
        re_admit = create_patient_admission(
            patient_id="PAT-CONC-3",
            patient_name="Post-Discharge Patient",
            department="Medicine",
            admission_type="Elective",
            bed_number=bed_id,
            actor_user=self.admin_user
        )
        self.assertTrue(re_admit["success"])

    def test_password_rehash_on_login(self):
        """
        Security Test:
        Verifies that an account with a legacy 100,000-iteration hash successfully authenticates
        and is transparently rehashed to the modern 600,000-iteration standard on login.
        """
        test_uname = "temp_legacy_user"
        test_pwd = "Legacy@Password2026!"
        
        # Create user with legacy 100,000 iterations
        legacy_hash, legacy_salt = hash_password(test_pwd, iterations=LEGACY_PBKDF2_ITERATIONS)
        cur = self.conn.cursor()
        cur.execute("DELETE FROM users WHERE username = ?", (test_uname,))
        cur.execute("""
            INSERT INTO users (username, password_hash, salt, role, full_name, department, is_active, created_at)
            VALUES (?, ?, ?, 'ADMISSION_OFFICER', 'Legacy Test User', 'Triage', 1, '2026-10-25 00:00:00')
        """, (test_uname, legacy_hash, legacy_salt))
        self.conn.commit()

        # Confirm initial hash was verified with legacy
        self.assertTrue(verify_password(test_pwd, legacy_hash, legacy_salt))

        # Authenticate user: triggers transparent rehash
        auth_profile = authenticate_user(test_uname, test_pwd)
        self.assertIsNotNone(auth_profile)
        self.assertEqual(auth_profile["username"], test_uname)

        # Inspect updated database row
        cur.execute("SELECT password_hash, salt FROM users WHERE username = ?", (test_uname,))
        row = cur.fetchone()
        new_hash = row["password_hash"]
        new_salt = row["salt"]

        # The hash should have changed from the legacy 100k hash
        self.assertNotEqual(new_hash, legacy_hash)

        # Verify the new hash conforms to the 600k standard
        import hashlib, secrets
        recheck_600k = hashlib.pbkdf2_hmac('sha256', test_pwd.encode('utf-8'), new_salt.encode('utf-8'), DEFAULT_PBKDF2_ITERATIONS).hex()
        self.assertTrue(secrets.compare_digest(recheck_600k, new_hash))

        # Cleanup
        cur.execute("DELETE FROM users WHERE username = ?", (test_uname,))
        self.conn.commit()


if __name__ == "__main__":
    unittest.main()
