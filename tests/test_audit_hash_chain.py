"""
VitalOptima Cryptographic Audit Hash Chain Unit Tests
Tests append-only SHA-256 hash chaining, sequential verification, and tamper detection.
"""
import unittest
import sqlite3
from pathlib import Path
from services.auth_service import (
    log_audit_event,
    verify_audit_log_chain,
    get_sqlite_conn,
    compute_audit_record_hash
)

class TestAuditHashChain(unittest.TestCase):
    def setUp(self):
        # Ensure database is clean or ready
        self.conn = get_sqlite_conn()

    def tearDown(self):
        self.conn.close()

    def test_canonical_hash_deterministic(self):
        h1 = compute_audit_record_hash("GENESIS", "2026-10-25 00:00:00", "admin", "ADMIN", "login", "1", "user", "SUCCESS", "Initial login")
        h2 = compute_audit_record_hash("GENESIS", "2026-10-25 00:00:00", "admin", "ADMIN", "login", "1", "user", "SUCCESS", "Initial login")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_hash_chain_append_and_verify(self):
        # Log a sequence of distinct events
        log_audit_event("admin", "ADMIN", "test.event.1", "TGT-101", "bed", "SUCCESS", "Allocated bed 101")
        log_audit_event("admit_officer", "ADMISSION_OFFICER", "test.event.2", "TGT-102", "patient", "SUCCESS", "Admitted patient 102")
        log_audit_event("admin", "ADMIN", "test.event.3", "TGT-103", "scenario", "SUCCESS", "Approved scenario 103")

        result = verify_audit_log_chain()
        self.assertTrue(result["valid"], f"Audit chain verification failed: {result['details']}")
        self.assertGreaterEqual(result["chained_records"], 3)
        self.assertIsNone(result["tampered_at_id"])

    def test_tamper_detection(self):
        # 1. Log an event
        log_audit_event("admin", "ADMIN", "tamper.test", "TGT-TAMPER", "user", "SUCCESS", "Authentic details")
        
        # Verify valid before tampering
        res_before = verify_audit_log_chain()
        self.assertTrue(res_before["valid"])

        # 2. Tamper with the latest record directly in the database
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM audit_logs WHERE action = 'tamper.test' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        target_id = row["id"]

        cursor.execute("UPDATE audit_logs SET details = 'MALICIOUS_ALTERATION' WHERE id = ?", (target_id,))
        self.conn.commit()

        # 3. Verify that the tamper detector flags this alteration
        res_after = verify_audit_log_chain()
        self.assertFalse(res_after["valid"])
        self.assertEqual(res_after["tampered_at_id"], target_id)
        self.assertIn("Digest mismatch", res_after["details"])

        # 4. Cleanup: restore or delete the test row
        cursor.execute("DELETE FROM audit_logs WHERE id = ?", (target_id,))
        self.conn.commit()


if __name__ == "__main__":
    unittest.main()
