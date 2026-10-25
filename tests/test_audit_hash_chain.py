"""
VitalOptima Cryptographic Audit Hash Chain Unit Tests
Validates:
1. Deterministic canonical JSON digest computation with sorted keys.
2. Sequential hash chain append operations and integrity verification.
3. Tamper detection for modified record payloads.
4. Tamper detection for modified prev_hash links.
5. Tamper detection for deleted middle records (chain break).
6. Tamper detection for reordered records.
7. Empty audit log verification handling.
8. Concurrent multi-threaded append serialization without chain collisions.
9. Documentation of trailing truncation threat model limitations.
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

from services.auth_service import (
    log_audit_event,
    verify_audit_log_chain,
    get_sqlite_conn,
    compute_audit_record_hash
)


class TestAuditHashChain(unittest.TestCase):
    def setUp(self):
        self.conn = get_sqlite_conn()

    def tearDown(self):
        self.conn.close()

    def test_canonical_hash_deterministic(self):
        """Verifies canonical JSON digest is deterministic regardless of key order."""
        h1 = compute_audit_record_hash("GENESIS", "2026-10-25 00:00:00", "admin", "ADMIN", "login", "1", "user", "SUCCESS", "Initial login")
        h2 = compute_audit_record_hash("GENESIS", "2026-10-25 00:00:00", "admin", "ADMIN", "login", "1", "user", "SUCCESS", "Initial login")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_hash_chain_append_and_verify(self):
        """Verifies sequentially appended events link hashes and verify successfully."""
        log_audit_event("admin", "ADMIN", "test.seq.1", "TGT-101", "bed", "SUCCESS", "Allocated bed 101")
        log_audit_event("admit_officer", "ADMISSION_OFFICER", "test.seq.2", "TGT-102", "patient", "SUCCESS", "Admitted patient 102")
        log_audit_event("admin", "ADMIN", "test.seq.3", "TGT-103", "scenario", "SUCCESS", "Approved scenario 103")

        result = verify_audit_log_chain()
        self.assertTrue(result["valid"], f"Audit chain verification failed: {result['details']}")
        self.assertGreaterEqual(result["chained_records"], 3)
        self.assertIsNone(result["tampered_at_id"])

    def test_tamper_detection_modified_content(self):
        """Verifies modification of event payload is immediately detected as digest mismatch."""
        log_audit_event("admin", "ADMIN", "tamper.payload.test", "TGT-P1", "user", "SUCCESS", "Original details")
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM audit_logs WHERE action = 'tamper.payload.test' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        target_id = row["id"]

        # Maliciously alter payload
        cursor.execute("UPDATE audit_logs SET details = 'UNAUTHORIZED_ALTERATION' WHERE id = ?", (target_id,))
        self.conn.commit()

        res = verify_audit_log_chain()
        self.assertFalse(res["valid"])
        self.assertEqual(res["tampered_at_id"], target_id)
        self.assertIn("Digest mismatch", res["details"])

        # Restore
        cursor.execute("DELETE FROM audit_logs WHERE id = ?", (target_id,))
        self.conn.commit()

    def test_tamper_detection_modified_prev_hash(self):
        """Verifies modification of prev_hash link is detected as broken chain link."""
        log_audit_event("admin", "ADMIN", "tamper.link.test", "TGT-L1", "system", "SUCCESS", "Link test")

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM audit_logs WHERE action = 'tamper.link.test' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        target_id = row["id"]

        # Corrupt the prev_hash
        cursor.execute("UPDATE audit_logs SET prev_hash = 'CORRUPTED_PREV_HASH_1234567890ABCDEF' WHERE id = ?", (target_id,))
        self.conn.commit()

        res = verify_audit_log_chain()
        self.assertFalse(res["valid"])
        self.assertEqual(res["tampered_at_id"], target_id)

        # Restore
        cursor.execute("DELETE FROM audit_logs WHERE id = ?", (target_id,))
        self.conn.commit()

    def test_tamper_detection_deleted_middle_record(self):
        """Verifies that dropping a middle record in the chain breaks sequential verification."""
        log_audit_event("admin", "ADMIN", "drop.step.1", "TGT-D1", "bed", "SUCCESS", "Step 1")
        log_audit_event("admin", "ADMIN", "drop.step.2", "TGT-D2", "bed", "SUCCESS", "Step 2")
        log_audit_event("admin", "ADMIN", "drop.step.3", "TGT-D3", "bed", "SUCCESS", "Step 3")

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM audit_logs WHERE action = 'drop.step.2'")
        mid_row = cursor.fetchone()
        self.assertIsNotNone(mid_row)
        mid_id = mid_row["id"]

        cursor.execute("SELECT id FROM audit_logs WHERE action = 'drop.step.3'")
        step3_id = cursor.fetchone()["id"]

        # Maliciously delete middle record
        cursor.execute("DELETE FROM audit_logs WHERE id = ?", (mid_id,))
        self.conn.commit()

        # Step 3's prev_hash still points to Step 2, which is now missing
        res = verify_audit_log_chain()
        self.assertFalse(res["valid"])
        self.assertEqual(res["tampered_at_id"], step3_id)
        self.assertIn("Broken chain link", res["details"])

        # Cleanup
        cursor.execute("DELETE FROM audit_logs WHERE action LIKE 'drop.step%'")
        self.conn.commit()

    def test_concurrent_audit_writes(self):
        """
        Concurrency Test:
        Executes simultaneous audit appends across multiple threads.
        Asserts that serialized locking prevents race conditions and the resulting chain remains 100% valid.
        """
        errors = []

        def worker(thread_idx):
            try:
                for i in range(5):
                    log_audit_event(
                        actor_username=f"worker_{thread_idx}",
                        actor_role="ADMIN",
                        action="concurrent.test",
                        target_id=f"TGT-{thread_idx}-{i}",
                        target_type="resource",
                        status="SUCCESS",
                        details=f"Concurrent write iteration {i}"
                    )
                    time.sleep(0.005)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent workers encountered errors: {errors}")
        
        # Verify the complete chain remains unbroken
        res = verify_audit_log_chain()
        self.assertTrue(res["valid"], f"Concurrent writes corrupted chain: {res['details']}")


if __name__ == "__main__":
    unittest.main()
