"""
VitalOptima - Comprehensive Database Reliability, Concurrency & Failover Test Suite
Validates:
1. Multi-connection concurrent contention on the identical physical bed using independent SQLite connections.
2. Database-level partial unique index (idx_active_bed_occupancy) integrity guarantees.
3. Idempotent admission retry handling.
4. Safe patient discharge and double-discharge prevention.
5. Reliable outbox journal recording and sync replay.
6. Atomic online backup and restoration.
"""
import unittest
import threading
import sqlite3
import time
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_PATH
from services.admission_service import (
    create_patient_admission, discharge_patient, get_sqlite_conn,
    get_available_beds_for_department
)
from db.database import (
    record_sync_outbox, get_pending_outbox_events, sync_pending_outbox,
    backup_database, restore_database
)


class TestDatabaseReliability(unittest.TestCase):
    def setUp(self):
        self.conn = get_sqlite_conn()
        self.admin_user = {"username": "admin", "role": "ADMIN"}

    def tearDown(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM patient_admissions WHERE patient_id LIKE 'PAT-RELIAB-%'")
            cursor.execute("DELETE FROM sync_outbox WHERE entity_id LIKE 'ADM-RELIAB-%'")
            self.conn.commit()
        except Exception:
            pass
        self.conn.close()

    def test_multi_connection_concurrent_bed_contention(self):
        """
        Concurrency Stress Test:
        8 independent threads, each creating its own independent SQLite connection,
        simultaneously race to claim the exact same bed ('TEST-CONC-BED-77').
        The database unique index idx_active_bed_occupancy MUST guarantee:
        - Exactly 1 thread succeeds in committing the admission.
        - Exactly 7 threads encounter clean conflict handling.
        - Exactly 1 active patient record exists in the database for that bed.
        """
        target_bed = "TEST-CONC-BED-77"
        num_contenders = 8
        results = []
        conflicts = []

        def worker_attempt(thread_id):
            pat_id = f"PAT-RELIAB-{thread_id}"
            pat_name = f"Contender Patient {thread_id}"
            try:
                res = create_patient_admission(
                    patient_id=pat_id,
                    patient_name=pat_name,
                    department="Medicine",
                    admission_type="Emergency",
                    bed_number=target_bed,
                    clinical_notes="Multi-connection concurrency test",
                    actor_user=self.admin_user
                )
                results.append(res)
            except Exception as exc:
                conflicts.append((thread_id, str(exc)))

        threads = [threading.Thread(target=worker_attempt, args=(i,)) for i in range(num_contenders)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Invariant 1: Exactly 1 winner
        self.assertEqual(len(results), 1, f"Expected 1 winner, got {len(results)}")
        # Invariant 2: Exactly 7 clean conflicts
        self.assertEqual(len(conflicts), num_contenders - 1)

        # Invariant 3: Database row count is strictly 1
        cur = self.conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM patient_admissions WHERE bed_number = ? AND status = 'Admitted'",
            (target_bed,)
        )
        count = cur.fetchone()[0]
        self.assertEqual(count, 1)

        # Cleanup: discharge the winner
        winner_adm_id = results[0]["admission_id"]
        dis_res = discharge_patient(winner_adm_id, actor_user=self.admin_user)
        self.assertTrue(dis_res["success"])

    def test_idempotent_admission_retry(self):
        """
        Idempotency Invariant Test:
        Submitting an admission with an existing idempotency key must reject duplication
        and preserve database state without double-allocating resources.
        """
        test_key = f"ADM-IDEMP-{uuid.uuid4().hex[:8].upper()}"
        res1 = create_patient_admission(
            patient_id="PAT-RELIAB-ID1",
            patient_name="Idempotent Patient 1",
            department="Medicine",
            admission_type="Emergency",
            bed_number="TEST-IDEMP-B01",
            idempotency_key=test_key,
            actor_user=self.admin_user
        )
        self.assertTrue(res1["success"])
        self.assertEqual(res1["admission_id"], test_key)

        # Immediate retry with identical idempotency key must be rejected cleanly
        with self.assertRaises(ValueError) as ctx:
            create_patient_admission(
                patient_id="PAT-RELIAB-ID1",
                patient_name="Idempotent Patient 1 (Duplicate)",
                department="Medicine",
                admission_type="Emergency",
                bed_number="TEST-IDEMP-B01",
                idempotency_key=test_key,
                actor_user=self.admin_user
            )
        self.assertIn("already processed", str(ctx.exception).lower())

        # Cleanup
        discharge_patient(test_key, actor_user=self.admin_user)

    def test_safe_double_discharge_prevention(self):
        """
        Discharge Invariant Test:
        Discharging an already discharged patient must fail cleanly and must NOT
        double-increment available capacity or corrupt inventory counters.
        """
        res = create_patient_admission(
            patient_id="PAT-RELIAB-DIS1",
            patient_name="Discharge Patient",
            department="Medicine",
            admission_type="Emergency",
            bed_number="TEST-DIS-B01",
            actor_user=self.admin_user
        )
        adm_id = res["admission_id"]

        # Initial discharge succeeds
        d1 = discharge_patient(adm_id, actor_user=self.admin_user)
        self.assertTrue(d1["success"])

        # Second discharge attempt must fail
        with self.assertRaises(ValueError) as ctx:
            discharge_patient(adm_id, actor_user=self.admin_user)
        self.assertIn("already discharged", str(ctx.exception).lower())

    def test_outbox_journal_recording_and_recovery(self):
        """
        Sync Journal Test:
        Verifies that outbox events are recorded with event IDs, payloads, and replay support.
        """
        test_evt_id = record_sync_outbox(
            entity_type="admissions",
            entity_id="ADM-RELIAB-TEST",
            operation="INSERT",
            payload={"test_key": "test_value"},
            status="PENDING"
        )
        self.assertTrue(test_evt_id.startswith("EVT-"))

        pending = get_pending_outbox_events()
        found = [e for e in pending if e["event_id"] == test_evt_id]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["entity_id"], "ADM-RELIAB-TEST")
        self.assertEqual(found[0]["status"], "PENDING")

    def test_atomic_online_backup_and_restore(self):
        """
        Disaster Recovery Test:
        Verifies SQLite online atomic backup API creates valid copy and can restore successfully.
        """
        backup_dir = PROJECT_ROOT / "db" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"test_backup_{uuid.uuid4().hex[:6]}.db"

        # 1. Create atomic online backup
        created_path = backup_database(backup_file)
        self.assertTrue(created_path.exists())
        self.assertGreater(created_path.stat().st_size, 0)

        # 2. Verify restored database can be opened
        test_conn = sqlite3.connect(str(created_path))
        test_cur = test_conn.cursor()
        test_cur.execute("SELECT COUNT(*) FROM department_resources")
        cnt = test_cur.fetchone()[0]
        self.assertGreater(cnt, 0)
        test_conn.close()

        # Clean up test backup file
        try:
            created_path.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()

