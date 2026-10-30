"""
VitalOptima Operational Failure & Edge-Case Robustness Test Suite
Validates application resilience under extreme clinical crises:
1. Zero available ICU beds (safe overflow prevention and transparent unmet demand reporting).
2. Total nurse absenteeism (refusal to over-allocate beyond legal staffing ratios).
3. External LLM network outage (deterministic offline fallback verification).
4. Corrupted/invalid patient admission records and database constraint violations.
5. Solver timeout and priority heuristic fallback integrity.
"""
import unittest
import sqlite3
import tempfile
from pathlib import Path

from models.optimizer import ResourceOptimizer, validate_allocation
from models.scenario_optimizer import StochasticResourceOptimizer
from src.ai_provider import DeterministicProvider, GrokProvider
from db.database import get_sqlite_connection


class TestOperationalFailures(unittest.TestCase):

    def setUp(self):
        self.optimizer = ResourceOptimizer()
        self.stochastic_opt = StochasticResourceOptimizer()

    def test_zero_available_icu_beds_prevents_unsafe_misallocation(self):
        """
        In extreme mass-casualty or structural failure where ICU capacity is 0,
        verify that ICU_Critical patients are NEVER misallocated to unapproved general wards,
        and are transparently reported as unmet demand.
        """
        demands = {
            "ICU_Critical": 12,
            "General_Medical": 20,
            "Surgery_PostOp": 5
        }
        # Zero ICU beds available, but general and surgery have ample capacity
        capacities = {
            "ICU": 0,
            "Internal Medicine": 40,
            "Surgery": 25,
            "Pediatrics": 10,
            "Emergency": 15
        }

        result = self.optimizer.optimize_bed_allocation(
            pending_demands=demands,
            available_capacities=capacities,
            allow_float_pool=True
        )

        self.assertEqual(result["status"], "Optimal")
        self.assertTrue(result["is_verified"])
        self.assertEqual(len(result["verification_violations"]), 0)

        # ICU patients MUST NOT be placed in Internal Medicine or Emergency
        allocations = result["allocations"]
        icu_allocs = [a for a in allocations if a["Patient_Group"] == "ICU Critical"]
        self.assertEqual(len(icu_allocs), 0, "No ICU patient should be allocated when ICU capacity is 0")

        # All 12 ICU patients must be accounted for as unmet demand
        self.assertEqual(result["unmet_demand"]["ICU_Critical"], 12)

        # General and Surgery patients should still be accommodated
        gen_allocs = sum(a["Count"] for a in allocations if a["Patient_Group"] == "General Medical")
        self.assertEqual(gen_allocs, 20)

    def test_total_nurse_absenteeism_refuses_unsafe_staffing_overload(self):
        """
        When a department experiences 100% nurse absenteeism (0 nurses) and
        supplemental float nurses are unavailable (capped at 0), the solver
        must refuse to allocate patients to unstaffed beds, preventing fatal staffing violations.
        """
        demands = {
            "General_Medical": 30,
            "Surgery_PostOp": 10
        }
        # Ample beds
        capacities = {
            "Internal Medicine": 50,
            "Surgery": 20
        }
        # 0 nurses in Internal Medicine, 5 nurses in Surgery
        staffing = {
            "Internal Medicine": 0,
            "Surgery": 5
        }

        result = self.optimizer.optimize_bed_allocation(
            pending_demands=demands,
            available_capacities=capacities,
            staffing_availability=staffing,
            max_supplemental_nurses=0
        )

        self.assertTrue(result["is_verified"])
        allocations = result["allocations"]

        # Internal Medicine has 0 nurses, so with nurse-to-patient ratio 0.20,
        # it can safely care for 0 patients (0 * 0.20 <= 0).
        med_allocs = sum(a["Count"] for a in allocations if a["Assigned_Department"] == "Internal Medicine")
        self.assertEqual(med_allocs, 0, "Zero nurses must result in zero patients admitted to Internal Medicine")

        # Unallocated patients must be recorded in unmet demand
        total_unmet = result["total_unmet"]
        self.assertGreaterEqual(total_unmet, 20)

    def test_external_llm_api_outage_deterministic_fallback(self):
        """
        When external LLM APIs (xAI Grok / OpenAI) are unavailable, offline,
        or configured with an invalid key, the system must deterministically
        fall back to grounded rule-based analytics without throwing unhandled exceptions.
        """
        # Test 1: DeterministicProvider is always available
        det_provider = DeterministicProvider()
        self.assertTrue(det_provider.is_available())

        det_insights, err = det_provider.generate_insights()
        self.assertIsNone(err)
        self.assertIsInstance(det_insights, dict)
        self.assertIn("executive_summary", det_insights)

        # Test 2: GrokProvider with completely invalid/dummy API key
        grok_provider = GrokProvider(api_key="sk-invalid-nonexistent-key-999999999999")
        # Generate insights should gracefully fallback to deterministic metrics
        insights, err_or_note = grok_provider.generate_insights()
        self.assertIsInstance(insights, dict)
        self.assertIn("executive_summary", insights)

    def test_patient_bed_uniqueness_and_discharge_invariant(self):
        """
        Validates that partial unique index idx_active_bed_occupancy strictly rejects
        double-allocation of beds for active admissions, while permitting reassignment
        once the previous occupant is discharged.
        """
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            temp_db = Path(tf.name)

        conn = None
        try:
            conn = sqlite3.connect(str(temp_db))
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    triage_category TEXT NOT NULL,
                    status TEXT NOT NULL,
                    bed_number TEXT NOT NULL,
                    admitted_at TEXT NOT NULL,
                    discharged_at TEXT
                );
            """)
            cur.execute("""
                CREATE UNIQUE INDEX idx_active_bed_occupancy 
                ON patients(bed_number) 
                WHERE status = 'Admitted';
            """)
            conn.commit()

            # Record 1: Valid active admission to BED-ICU-01
            cur.execute("""
                INSERT INTO patients (patient_id, name, age, triage_category, status, bed_number, admitted_at)
                VALUES ('P101', 'Alice Green', 52, 'ICU', 'Admitted', 'BED-ICU-01', '2026-10-31 08:00:00')
            """)
            conn.commit()

            # Record 2: Colliding admission on the same active bed (must trigger IntegrityError)
            with self.assertRaises(sqlite3.IntegrityError):
                cur.execute("""
                    INSERT INTO patients (patient_id, name, age, triage_category, status, bed_number, admitted_at)
                    VALUES ('P102', 'Bob Smith', 61, 'ICU', 'Admitted', 'BED-ICU-01', '2026-10-31 08:30:00')
                """)
                conn.commit()

            # Discharge patient P101
            cur.execute("""
                UPDATE patients 
                SET status = 'Discharged', discharged_at = '2026-10-31 12:00:00'
                WHERE patient_id = 'P101'
            """)
            conn.commit()

            # Now patient P102 can safely occupy BED-ICU-01
            cur.execute("""
                INSERT INTO patients (patient_id, name, age, triage_category, status, bed_number, admitted_at)
                VALUES ('P102', 'Bob Smith', 61, 'ICU', 'Admitted', 'BED-ICU-01', '2026-10-31 12:15:00')
            """)
            conn.commit()

            # Verify active patient count is exactly 1
            cur.execute("SELECT COUNT(*) FROM patients WHERE status = 'Admitted' AND bed_number = 'BED-ICU-01'")
            active_count = cur.fetchone()[0]
            self.assertEqual(active_count, 1)

            conn.close()
            conn = None
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            if temp_db.exists():
                temp_db.unlink()

    def test_solver_timeout_and_heuristic_fallback_integrity(self):
        """
        When solver fallback is explicitly forced, the priority heuristic must:
        1. Accurately report solver_backend as Priority Greedy Heuristic.
        2. Set is_proven_optimal to False.
        3. Satisfy demand conservation (Allocated + Unmet == Initial Demand).
        4. Pass independent allocation validation.
        """
        demands = {
            "ICU_Critical": 5,
            "General_Medical": 15,
            "Surgery_PostOp": 8
        }
        capacities = {
            "ICU": 4,
            "Internal Medicine": 10,
            "Surgery": 5
        }

        # Force heuristic execution directly
        fallback_res = self.optimizer._solve_priority_fallback(
            clean_demands=demands,
            clean_capacities=capacities,
            allow_float_pool=True,
            start_time=0.0,
            damaged_beds={}
        )

        self.assertEqual(fallback_res["solver_backend"], "Python Priority Heuristic")
        self.assertFalse(fallback_res["is_proven_optimal"])
        self.assertTrue(fallback_res["is_verified"])
        self.assertEqual(len(fallback_res["verification_violations"]), 0)

        # Verify exact demand conservation
        total_initial = sum(demands.values())
        total_allocated = fallback_res["total_allocated"]
        total_unmet = fallback_res["total_unmet"]
        self.assertEqual(total_allocated + total_unmet, total_initial)


if __name__ == "__main__":
    unittest.main()
