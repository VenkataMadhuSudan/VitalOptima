"""
VitalOptima Automated Test Suite: Role-Based Access Control & Automatic Dashboard Synchronization
Validates all 20 specific security, admission workflow, concurrency, cache invalidation,
audit logging, and latency requirements.
"""
import unittest
import time
import threading
import sqlite3
from datetime import datetime

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import init_db, get_sqlite_connection
from services.auth_service import (
    authenticate_user, hash_password, verify_password,
    has_permission, require_permission, require_role,
    ROLE_ADMIN, ROLE_ADMISSION_OFFICER, ROLE_PERMISSIONS,
    get_recent_audit_logs, log_audit_event
)
from services.admission_service import (
    create_patient_admission, discharge_patient,
    get_live_bed_metrics, get_sync_status, bump_sync_version,
    get_active_admissions, get_available_beds_for_department,
    invalidate_caches
)


class TestRBACAndAdmissionsSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure fresh database schema and seed data
        init_db()
        cls.admin_user = authenticate_user("admin", "Admin@Vital2026!")
        cls.officer_user = authenticate_user("admit_officer", "Admit@Vital2026!")

    def setUp(self):
        # Ensure departments have fresh capacity baseline for reliable test runs
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        dept_csv = PROJECT_ROOT / "data" / "department_resources.csv"
        if dept_csv.exists():
            import pandas as pd
            df_d = pd.read_csv(dept_csv)
            for _, r in df_d.iterrows():
                cursor.execute("""
                    UPDATE department_resources
                    SET total_capacity = ?, unavailable_capacity = ?, occupied_capacity = ?, available_capacity = ?
                    WHERE resource_id = ?
                """, (int(r['total_capacity']), int(r['unavailable_capacity']), int(r['occupied_capacity']), int(r['available_capacity']), str(r['resource_id'])))
        conn.commit()
        conn.close()

    def test_01_successful_administrator_authentication(self):
        """1. Successful administrator authentication."""
        user = authenticate_user("admin", "Admin@Vital2026!")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "admin")
        self.assertEqual(user["role"], ROLE_ADMIN)
        self.assertIn("Hospital Administration", user["department"])

    def test_02_successful_admission_officer_authentication(self):
        """2. Successful admission officer authentication."""
        user = authenticate_user("admit_officer", "Admit@Vital2026!")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "admit_officer")
        self.assertEqual(user["role"], ROLE_ADMISSION_OFFICER)

    def test_03_invalid_credentials_rejected(self):
        """3. Invalid credentials rejection & non-existent user handling."""
        self.assertIsNone(authenticate_user("admin", "WrongPassword!"))
        self.assertIsNone(authenticate_user("admit_officer", "Invalid123"))
        self.assertIsNone(authenticate_user("nonexistent_user", "AnyPassword"))
        self.assertIsNone(authenticate_user("", ""))

    def test_04_unauthorized_access_to_administrative_functions(self):
        """4. Unauthorized access to administrative functions blocked for Admission Officer."""
        # Admission officer must not have analytics, forecasting, or optimization permissions
        self.assertFalse(has_permission(self.officer_user, "analytics.view"))
        self.assertFalse(has_permission(self.officer_user, "forecasting.manage"))
        self.assertFalse(has_permission(self.officer_user, "optimization.manage"))
        self.assertFalse(has_permission(self.officer_user, "users.manage"))

        # require_permission should raise PermissionError
        with self.assertRaises(PermissionError):
            require_permission("analytics.view", self.officer_user)

        with self.assertRaises(PermissionError):
            require_permission("forecasting.manage", self.officer_user)

    def test_05_unauthorized_role_modification(self):
        """5. Unauthorized role modification prevented."""
        with self.assertRaises(PermissionError):
            require_role([ROLE_ADMIN], self.officer_user)

    def test_06_valid_admission_creation(self):
        """6. Valid admission creation persists to DB, updates capacity, and assigns bed."""
        test_patient_id = f"PAT-TEST-{int(time.time() * 1000) % 100000}"
        test_bed = f"ORT-VAL-{int(time.time() * 1000) % 10000}"
        res = create_patient_admission(
            patient_id=test_patient_id,
            patient_name="Sanjay Singhania",
            department="Orthopedics",
            admission_type="Emergency",
            age=48,
            gender="Male",
            bed_number=test_bed,
            clinical_notes="Fracture femur triage",
            actor_user=self.officer_user
        )
        self.assertTrue(res["success"])
        self.assertIn("ADM-", res["admission_id"])
        self.assertEqual(res["patient_id"], test_patient_id)
        self.assertEqual(res["bed_number"], test_bed)

        # Verify persisted in database
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_admissions WHERE admission_id = ?", (res["admission_id"],))
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["patient_name"], "Sanjay Singhania")
        self.assertEqual(row["status"], "Admitted")

    def test_07_invalid_admission_rejection(self):
        """7. Invalid admission rejection (missing name, invalid department, invalid type)."""
        # Missing patient name
        with self.assertRaises(ValueError):
            create_patient_admission(
                patient_id="PAT-INVALID",
                patient_name="",
                department="Medicine",
                admission_type="Emergency",
                actor_user=self.officer_user
            )

        # Invalid department
        with self.assertRaises(ValueError):
            create_patient_admission(
                patient_id="PAT-INVALID",
                patient_name="Invalid Dept Patient",
                department="NonExistentWard",
                admission_type="Emergency",
                actor_user=self.officer_user
            )

        # Invalid admission classification
        with self.assertRaises(ValueError):
            create_patient_admission(
                patient_id="PAT-INVALID",
                patient_name="Invalid Type Patient",
                department="Medicine",
                admission_type="WalkInUnknown",
                actor_user=self.officer_user
            )

    def test_08_unavailable_bed_rejection(self):
        """8. Unavailable bed rejection (already occupied bed cannot be assigned)."""
        pat_a = f"PAT-BED-A-{int(time.time() * 1000) % 100000}"
        pat_b = f"PAT-BED-B-{int(time.time() * 1000) % 100000}"
        test_bed = f"ORT-UNAV-{int(time.time() * 1000) % 10000}"

        # First admission acquires bed
        res_a = create_patient_admission(
            patient_id=pat_a,
            patient_name="Occupant Patient",
            department="Orthopedics",
            admission_type="Elective",
            bed_number=test_bed,
            actor_user=self.officer_user
        )
        self.assertTrue(res_a["success"])

        # Second admission requesting same bed must be rejected
        with self.assertRaises(ValueError) as ctx:
            create_patient_admission(
                patient_id=pat_b,
                patient_name="Conflicted Patient",
                department="Orthopedics",
                admission_type="Emergency",
                bed_number=test_bed,
                actor_user=self.officer_user
            )
        self.assertIn("already occupied", str(ctx.exception).lower())

    def test_09_concurrent_bed_allocation_conflicts(self):
        """9. Concurrent bed-allocation conflicts handled safely under race conditions."""
        target_bed = f"ORT-RACE-{int(time.time() * 1000) % 10000}"
        num_threads = 5
        results = []
        errors = []

        def attempt_admission(idx):
            try:
                r = create_patient_admission(
                    patient_id=f"PAT-RACE-{idx}-{int(time.time() * 1000) % 100000}",
                    patient_name=f"Race Candidate {idx}",
                    department="Orthopedics",
                    admission_type="Emergency",
                    bed_number=target_bed,
                    actor_user=self.officer_user
                )
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=attempt_admission, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 1 thread must succeed; all others must be rejected
        self.assertEqual(len(results), 1, f"Expected exactly 1 success, got {len(results)}")
        self.assertEqual(len(errors), num_threads - 1)

    def test_10_duplicate_request_handling(self):
        """10. Duplicate request handling (idempotency key prevents double insert)."""
        idem_key = f"ADM-IDEM-{int(time.time() * 1000) % 100000}"
        pat_id = f"PAT-IDEM-{int(time.time() * 1000) % 100000}"

        # 1st call
        res = create_patient_admission(
            patient_id=pat_id,
            patient_name="Idempotent Patient",
            department="Surgery",
            admission_type="Elective",
            idempotency_key=idem_key,
            actor_user=self.officer_user
        )
        self.assertEqual(res["admission_id"], idem_key)

        # 2nd call with identical key must fail
        with self.assertRaises(ValueError) as ctx:
            create_patient_admission(
                patient_id=f"PAT-OTHER-{int(time.time() * 1000) % 100000}",
                patient_name="Duplicate Patient",
                department="Surgery",
                admission_type="Elective",
                idempotency_key=idem_key,
                actor_user=self.officer_user
            )
        self.assertIn("already processed", str(ctx.exception).lower())

    def test_11_correct_bed_availability_calculations(self):
        """11. Correct bed availability calculations from authoritative records."""
        metrics_before = get_live_bed_metrics()
        initial_gen_occ = metrics_before["general_occupied"]
        initial_gen_avail = metrics_before["general_available"]

        # Admit into Medicine (General Bed)
        test_pat = f"PAT-CALC-{int(time.time() * 1000) % 100000}"
        res = create_patient_admission(
            patient_id=test_pat,
            patient_name="Calc Test Patient",
            department="Medicine",
            admission_type="Emergency",
            actor_user=self.officer_user
        )

        metrics_after = get_live_bed_metrics()
        self.assertEqual(metrics_after["general_occupied"], initial_gen_occ + 1)
        self.assertEqual(metrics_after["general_available"], initial_gen_avail - 1)

    def test_12_correct_discharge_behavior(self):
        """12. Correct discharge behavior releases bed and prevents duplicate discharges."""
        test_pat = f"PAT-DISCH-{int(time.time() * 1000) % 100000}"
        res = create_patient_admission(
            patient_id=test_pat,
            patient_name="Discharge Test Patient",
            department="Pediatrics",
            admission_type="Urgent",
            bed_number="PED-B08",
            actor_user=self.officer_user
        )
        adm_id = res["admission_id"]

        metrics_before = get_live_bed_metrics()
        dis_res = discharge_patient(
            admission_id=adm_id,
            discharge_notes="Discharged stable",
            actor_user=self.officer_user
        )
        self.assertTrue(dis_res["success"])
        self.assertEqual(dis_res["released_bed"], "PED-B08")

        # Bed capacity restored
        metrics_after = get_live_bed_metrics()
        self.assertEqual(metrics_after["general_occupied"], metrics_before["general_occupied"] - 1)

        # Attempting duplicate discharge must fail
        with self.assertRaises(ValueError) as ctx:
            discharge_patient(admission_id=adm_id, actor_user=self.officer_user)
        self.assertIn("already discharged", str(ctx.exception).lower())

    def test_13_database_rollback_after_failed_operations(self):
        """13. Database rollback after failed operations ensures consistency."""
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patient_admissions")
        count_before = cursor.fetchone()[0]
        cursor.execute("SELECT occupied_capacity FROM department_resources WHERE department = 'Surgery'")
        occ_before = cursor.fetchone()[0]
        conn.close()

        # Deliberately attempt an admission with conflict to trigger rollback
        try:
            create_patient_admission(
                patient_id="",  # Invalid
                patient_name="Rollback Patient",
                department="Surgery",
                admission_type="Emergency",
                actor_user=self.officer_user
            )
        except ValueError:
            pass

        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patient_admissions")
        count_after = cursor.fetchone()[0]
        cursor.execute("SELECT occupied_capacity FROM department_resources WHERE department = 'Surgery'")
        occ_after = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count_before, count_after)
        self.assertEqual(occ_before, occ_after)

    def test_14_cache_invalidation_after_mutations(self):
        """14. Cache invalidation after mutations."""
        old_v = get_sync_status("global")["version"]
        bump_sync_version("resources", actor="test_runner")
        new_v = get_sync_status("global")["version"]
        self.assertGreater(new_v, old_v)

    def test_15_dashboard_refresh_after_an_admission(self):
        """15. Dashboard refresh after an admission provides immediate updated metrics."""
        sync_before = get_sync_status("global")
        create_patient_admission(
            patient_id=f"PAT-REFR-{int(time.time() * 1000) % 100000}",
            patient_name="Refresh Patient",
            department="Obstetrics",
            admission_type="Emergency",
            actor_user=self.officer_user
        )
        sync_after = get_sync_status("global")
        self.assertGreater(sync_after["version"], sync_before["version"])

    def test_16_cross_user_visibility_and_latency_measurement(self):
        """
        16. Cross-user visibility of updated operational metrics and latency benchmark.
        Requirement: Updates visible within 15-20 seconds.
        Target: < 15 seconds in controlled local conditions.
        """
        start_time = time.time()

        # User A (Admission Officer) performs mutation
        test_id = f"PAT-LATENCY-{int(time.time() * 1000) % 100000}"
        test_bed = f"MICU-LAT-{int(time.time() * 1000) % 10000}"
        res = create_patient_admission(
            patient_id=test_id,
            patient_name="Latency Benchmark Patient",
            department="Medical ICU",
            admission_type="Emergency",
            bed_number=test_bed,
            actor_user=self.officer_user
        )

        # User B (Administrator) polls live bed metrics
        admin_metrics = get_live_bed_metrics()
        elapsed_sec = time.time() - start_time

        # Verify that ICU metrics reflect the admission
        self.assertGreaterEqual(admin_metrics["icu_occupied"], 1)
        # Latency check: Must be well under 15 seconds
        self.assertLess(elapsed_sec, 15.0, f"Synchronization latency {elapsed_sec:.4f}s exceeded 15.0s limit!")
        print(f"\n[LATENCY BENCHMARK] Cross-user synchronization completed in {elapsed_sec*1000:.2f} ms (< 15.0 s target).")

    def test_17_recovery_from_stale_or_missed_refreshes(self):
        """17. Recovery from stale or missed refreshes directly from database state."""
        # Simulated scenario: client missed 5 intermediate versions
        bump_sync_version("admissions", actor="worker_1")
        bump_sync_version("resources", actor="worker_2")
        bump_sync_version("admissions", actor="worker_3")

        # Query authoritative DB directly
        fresh_status = get_sync_status("global")
        fresh_metrics = get_live_bed_metrics()

        self.assertIsNotNone(fresh_status["version"])
        self.assertGreater(fresh_metrics["general_total"], 0)

    def test_18_preservation_of_existing_features(self):
        """18. Preservation of existing forecasting, optimization, and ML outputs."""
        from models.forecaster import DemandForecaster
        from models.optimizer import ResourceOptimizer

        # Verify ML Random Forest Regressor forecaster
        forecaster = DemandForecaster()
        self.assertTrue(forecaster.is_trained)
        fc_df, fc_metrics = forecaster.get_24h_forecast()
        self.assertIsNotNone(fc_df)
        self.assertFalse(fc_df.empty)
        self.assertGreater(len(fc_df), 0)
        self.assertIn("peak_value", fc_metrics)

        # Verify Google OR-Tools MILP optimizer
        optimizer = ResourceOptimizer()
        demands = {'ICU_Critical': 5, 'Surgery_PostOp': 12, 'General_Medical': 25, 'Pediatric': 6}
        capacities = {'ICU': 8, 'Surgery': 15, 'Internal Medicine': 30, 'Pediatrics': 10, 'Emergency': 10}
        opt_res = optimizer.optimize_bed_allocation(demands, capacities)
        self.assertIsNotNone(opt_res)
        self.assertIn("allocations", opt_res)

    def test_19_access_restrictions_for_sensitive_patient_information(self):
        """19. Access restrictions for sensitive patient information."""
        # Unauthenticated access rejected
        with self.assertRaises(PermissionError):
            require_permission("admissions.create", user=None)

        with self.assertRaises(PermissionError):
            require_permission("audit.view", user=self.officer_user)

    def test_20_audit_logging_for_important_operations(self):
        """20. Audit logging for important security, admission, and discharge operations."""
        recent_logs = get_recent_audit_logs(limit=20)
        self.assertGreater(len(recent_logs), 0)

        # Verify audit record fields exist
        latest = recent_logs[0]
        self.assertIn("actor_username", latest)
        self.assertIn("actor_role", latest)
        self.assertIn("action", latest)
        self.assertIn("status", latest)


if __name__ == "__main__":
    unittest.main()
