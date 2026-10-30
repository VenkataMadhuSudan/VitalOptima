"""
VitalOptima Multi-Process Concurrency & OS-Level Lock Contention Test Suite
Validates that database-level partial unique index invariants hold across
separate operating system processes (multiprocessing.Process), not merely Python threads.
"""
import os
import sys
import time
import sqlite3
import unittest
import multiprocessing
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _worker_attempt_admission(db_path: str, patient_id: str, bed_number: str, result_queue: multiprocessing.Queue):
    """Worker function executed inside an independent operating system process."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        c = conn.cursor()
        c.execute("""
            INSERT INTO patients (patient_id, name, age, triage_category, status, bed_number, admitted_at)
            VALUES (?, ?, ?, ?, 'Admitted', ?, CURRENT_TIMESTAMP);
        """, (patient_id, f"Patient {patient_id}", 45, "ICU", bed_number))
        conn.commit()
        conn.close()
        result_queue.put({"worker": patient_id, "status": "SUCCESS"})
    except sqlite3.IntegrityError as e:
        result_queue.put({"worker": patient_id, "status": "CONFLICT", "error": str(e)})
    except Exception as e:
        result_queue.put({"worker": patient_id, "status": "ERROR", "error": str(e)})


def _worker_discharge_and_reassign(db_path: str, action: str, patient_id: str, bed_number: str, result_queue: multiprocessing.Queue):
    """Executes either discharge or admission in a separate process."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        c = conn.cursor()
        if action == "discharge":
            c.execute("""
                UPDATE patients 
                SET status = 'Discharged', discharged_at = CURRENT_TIMESTAMP
                WHERE patient_id = ?;
            """, (patient_id,))
            conn.commit()
            conn.close()
            result_queue.put({"worker": patient_id, "action": action, "status": "SUCCESS"})
        elif action == "admit":
            # Brief delay to test race
            time.sleep(0.05)
            c.execute("""
                INSERT INTO patients (patient_id, name, age, triage_category, status, bed_number, admitted_at)
                VALUES (?, ?, ?, ?, 'Admitted', ?, CURRENT_TIMESTAMP);
            """, (patient_id, f"Patient {patient_id}", 30, "Emergency", bed_number))
            conn.commit()
            conn.close()
            result_queue.put({"worker": patient_id, "action": action, "status": "SUCCESS"})
    except sqlite3.IntegrityError as e:
        result_queue.put({"worker": patient_id, "action": action, "status": "CONFLICT", "error": str(e)})
    except Exception as e:
        result_queue.put({"worker": patient_id, "action": action, "status": "ERROR", "error": str(e)})


class TestMultiProcessConcurrency(unittest.TestCase):
    def setUp(self):
        self.test_db = PROJECT_ROOT / "tests" / "test_multiprocess.db"
        if self.test_db.exists():
            self.test_db.unlink()

        conn = sqlite3.connect(str(self.test_db))
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("""
            CREATE TABLE patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                age INTEGER,
                triage_category TEXT,
                status TEXT NOT NULL,
                bed_number TEXT,
                admitted_at TIMESTAMP,
                discharged_at TIMESTAMP
            );
        """)
        # Create database-level partial unique index
        c.execute("""
            CREATE UNIQUE INDEX idx_mp_active_bed 
            ON patients (bed_number) 
            WHERE status = 'Admitted' AND bed_number IS NOT NULL;
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        if self.test_db.exists():
            try:
                self.test_db.unlink()
            except Exception:
                pass

    def test_multiprocess_bed_collision(self):
        """
        Verifies 4 separate OS processes attempting to book the same bed concurrently
        result in exactly 1 winner and 3 clean database-level partial index rejections.
        """
        num_processes = 4
        target_bed = "ICU-BED-99"
        queue = multiprocessing.Queue()
        processes = []

        for i in range(num_processes):
            pid = f"PAT-MP-{i+1}"
            p = multiprocessing.Process(
                target=_worker_attempt_admission,
                args=(str(self.test_db), pid, target_bed, queue)
            )
            processes.append(p)

        # Launch all processes simultaneously
        for p in processes:
            p.start()

        for p in processes:
            p.join(timeout=10.0)

        results = []
        while not queue.empty():
            results.append(queue.get())

        self.assertEqual(len(results), num_processes)
        successes = [r for r in results if r["status"] == "SUCCESS"]
        conflicts = [r for r in results if r["status"] == "CONFLICT"]

        self.assertEqual(len(successes), 1, f"Expected exactly 1 winner, got {len(successes)}")
        self.assertEqual(len(conflicts), num_processes - 1, f"Expected {num_processes - 1} rejections, got {len(conflicts)}")

        # Verify database state
        conn = sqlite3.connect(str(self.test_db))
        c = conn.cursor()
        c.execute("SELECT patient_id, status FROM patients WHERE bed_number = ?", (target_bed,))
        active_records = c.fetchall()
        conn.close()

        self.assertEqual(len(active_records), 1)
        self.assertEqual(active_records[0][1], "Admitted")

    def test_multiprocess_discharge_and_reassignment(self):
        """Verifies safe inter-process discharge followed by bed reassignment."""
        target_bed = "ER-BED-10"
        conn = sqlite3.connect(str(self.test_db))
        c = conn.cursor()
        c.execute("""
            INSERT INTO patients (patient_id, name, age, triage_category, status, bed_number, admitted_at)
            VALUES ('INITIAL-PAT', 'Initial Patient', 50, 'Emergency', 'Admitted', ?, CURRENT_TIMESTAMP);
        """, (target_bed,))
        conn.commit()
        conn.close()

        queue = multiprocessing.Queue()
        p1 = multiprocessing.Process(
            target=_worker_discharge_and_reassign,
            args=(str(self.test_db), "discharge", "INITIAL-PAT", target_bed, queue)
        )
        p2 = multiprocessing.Process(
            target=_worker_discharge_and_reassign,
            args=(str(self.test_db), "admit", "NEXT-PAT", target_bed, queue)
        )

        p1.start()
        p2.start()
        p1.join(timeout=10.0)
        p2.join(timeout=10.0)

        results = []
        while not queue.empty():
            results.append(queue.get())

        self.assertEqual(len(results), 2)
        # Verify exactly one active patient on ER-BED-10
        conn = sqlite3.connect(str(self.test_db))
        c = conn.cursor()
        c.execute("SELECT patient_id, status FROM patients WHERE bed_number = ? AND status = 'Admitted'", (target_bed,))
        active = c.fetchall()
        conn.close()

        self.assertEqual(len(active), 1)
        self.assertEqual(active[0][0], "NEXT-PAT")


if __name__ == "__main__":
    unittest.main()

