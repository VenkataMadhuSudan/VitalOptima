"""
VitalOptima - Rigorous Operations Research & Optimization Test Suite
Provides comprehensive verification of mathematical optimization models:
1. Normal feasible allocation
2. Zero ICU capacity
3. Insufficient nursing coverage
4. Incompatible patient placement rejection
5. Exhausted float-pool staffing
6. Impossible allocation with demand preservation
7. Multiple feasible allocations with cost minimization
8. Combinatorial brute-force global optimality proof
9. MILP vs Priority Fallback comparative benchmark
"""
import unittest
import sys
import time
import itertools
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.optimizer import (
    ResourceOptimizer, validate_allocation,
    CLINICAL_COMPATIBILITY, UNMET_PENALTIES, TRANSFER_PENALTIES
)


class TestOptimizerRigor(unittest.TestCase):
    def setUp(self):
        self.optimizer = ResourceOptimizer()

    def test_case_1_normal_feasible_allocation(self):
        """Test Case 1: Normal feasible allocation where demands fit into primary units."""
        demands = {"General_Medical": 15, "Emergency_Trauma": 8, "ICU_Critical": 3}
        capacities = {"Internal Medicine": 20, "Emergency": 10, "ICU": 5}
        res = self.optimizer.optimize_bed_allocation(demands, capacities)

        self.assertEqual(res["status"], "Optimal")
        self.assertTrue(res["is_proven_optimal"])
        self.assertEqual(res["total_allocated"], 26)
        self.assertEqual(res["total_unmet"], 0)
        self.assertTrue(res["is_verified"])
        self.assertEqual(res["verification_violations"], [])
        self.assertEqual(res["objective_value"], 0.0)

    def test_case_2_zero_icu_capacity(self):
        """Test Case 2: Zero ICU capacity; critical care patients cannot be placed and become unmet."""
        demands = {"ICU_Critical": 5, "General_Medical": 10}
        capacities = {"Internal Medicine": 15, "ICU": 0, "Emergency": 10}
        res = self.optimizer.optimize_bed_allocation(demands, capacities)

        self.assertEqual(res["total_allocated"], 10)
        self.assertEqual(res["total_unmet"], 5)
        self.assertEqual(res["unmet_demand"]["ICU_Critical"], 5)
        self.assertTrue(res["is_verified"])
        self.assertEqual(res["verification_violations"], [])
        # Objective value must reflect 5 * 1000 = 5000 penalty
        self.assertEqual(res["objective_value"], 5000.0)

    def test_case_3_insufficient_nursing_coverage(self):
        """Test Case 3: Bed available, but nursing coverage restricts placement unless float mobilized."""
        demands = {"ICU_Critical": 4}  # 4 ICU patients require 4 nurses (1:1 ratio)
        capacities = {"ICU": 10}
        staffing = {"ICU": 2}  # Only 2 nurses on duty -> deficit of 2
        
        # When supplemental nurses capped at 1, at most 3 patients can be admitted
        res = self.optimizer.optimize_bed_allocation(
            demands, capacities, staffing_availability=staffing, max_supplemental_nurses=1
        )
        self.assertTrue(res["is_verified"])
        self.assertLessEqual(res["total_allocated"], 3)
        self.assertGreaterEqual(res["total_unmet"], 1)

    def test_case_4_incompatible_placement_rejection(self):
        """Test Case 4: Independent validator rejects clinically incompatible routing."""
        demands = {"Pediatric": 5}
        capacities = {"ICU": 10, "Pediatrics": 0}
        # Attempt an illegal assignment
        illegal_allocations = [{
            "Patient_Group": "Pediatric",
            "Assigned_Department": "ICU",
            "Count": 5,
            "Type": "Illegal"
        }]
        is_valid, violations = validate_allocation(illegal_allocations, demands, capacities, {"Pediatric": 0})
        self.assertFalse(is_valid)
        self.assertTrue(any("Clinical incompatibility" in v for v in violations))

    def test_case_5_exhausted_float_pool(self):
        """Test Case 5: When float pool is disabled, secondary overflow routing is disallowed."""
        demands = {"General_Medical": 20}
        # Internal Medicine has only 10 beds; secondary surgery has 10 beds
        capacities = {"Internal Medicine": 10, "Surgery": 10}
        
        res_no_float = self.optimizer.optimize_bed_allocation(demands, capacities, allow_float_pool=False)
        self.assertEqual(res_no_float["total_allocated"], 10)
        self.assertEqual(res_no_float["total_unmet"], 10)

        res_float = self.optimizer.optimize_bed_allocation(demands, capacities, allow_float_pool=True)
        self.assertEqual(res_float["total_allocated"], 20)
        self.assertEqual(res_float["total_unmet"], 0)

    def test_case_6_impossible_allocation(self):
        """Test Case 6: Total hospital shutdown (zero capacity); all demand is unmet with zero violations."""
        demands = {"General_Medical": 10, "ICU_Critical": 5, "Emergency_Trauma": 8}
        capacities = {"Internal Medicine": 0, "ICU": 0, "Emergency": 0, "Surgery": 0, "Pediatrics": 0}
        res = self.optimizer.optimize_bed_allocation(demands, capacities)

        self.assertEqual(res["total_allocated"], 0)
        self.assertEqual(res["total_unmet"], 23)
        self.assertTrue(res["is_verified"])
        self.assertEqual(res["verification_violations"], [])

    def test_case_7_cost_minimization_across_alternatives(self):
        """Test Case 7: General_Medical can overflow to Surgery (penalty 10) or Emergency (penalty 20). Solver must choose Surgery."""
        demands = {"General_Medical": 15}
        # Primary unit has 10 beds; 5 must overflow. Surgery and Emergency both have 10 beds.
        capacities = {"Internal Medicine": 10, "Surgery": 10, "Emergency": 10}
        res = self.optimizer.optimize_bed_allocation(demands, capacities, allow_float_pool=True)

        self.assertEqual(res["status"], "Optimal")
        self.assertEqual(res["total_allocated"], 15)
        # Check that overflow went to Surgery, not Emergency
        allocs = {a["Assigned_Department"]: a["Count"] for a in res["allocations"]}
        self.assertEqual(allocs.get("Internal Medicine"), 10)
        self.assertEqual(allocs.get("Surgery"), 5)
        self.assertEqual(allocs.get("Emergency", 0), 0)
        # Expected objective = 5 * 10 = 50.0
        self.assertEqual(res["objective_value"], 50.0)

    def test_case_8_brute_force_combinatorial_verification(self):
        """
        Test Case 8: Brute-Force Combinatorial Global Optimality Proof.
        Exhaustively evaluates every integer assignment vector for a small scenario
        and proves that the MILP solver's objective matches the exact global minimum.
        """
        demands = {"General_Medical": 6, "Emergency_Trauma": 4}
        capacities = {"Internal Medicine": 4, "Emergency": 3, "Surgery": 5}
        
        # Candidate placements:
        # GM can go to Internal Medicine (pen=0), Surgery (pen=10), Emergency (pen=20), or unmet (pen=100)
        # ET can go to Emergency (pen=0), or unmet (pen=800)
        min_brute_cost = float("inf")
        best_brute_vector = None

        for gm_med in range(0, min(6, capacities["Internal Medicine"]) + 1):
            for gm_surg in range(0, min(6 - gm_med, capacities["Surgery"]) + 1):
                for gm_ed in range(0, min(6 - gm_med - gm_surg, capacities["Emergency"]) + 1):
                    gm_unmet = 6 - (gm_med + gm_surg + gm_ed)
                    
                    rem_ed_cap = capacities["Emergency"] - gm_ed
                    for et_ed in range(0, min(4, rem_ed_cap) + 1):
                        et_unmet = 4 - et_ed

                        cost = (
                            (gm_med * 0) + (gm_surg * 10) + (gm_ed * 20) + (gm_unmet * 100) +
                            (et_ed * 0) + (et_unmet * 800)
                        )
                        if cost < min_brute_cost:
                            min_brute_cost = cost
                            best_brute_vector = (gm_med, gm_surg, gm_ed, gm_unmet, et_ed, et_unmet)

        # Run MILP solver
        res = self.optimizer.optimize_bed_allocation(demands, capacities)
        self.assertEqual(res["status"], "Optimal")
        self.assertEqual(res["objective_value"], float(min_brute_cost))
        self.assertTrue(res["is_verified"])

    def test_case_9_milp_vs_priority_fallback_benchmark(self):
        """
        Test Case 9: Benchmark comparing Google OR-Tools MILP against Priority Fallback.
        Verifies both produce feasible allocations, documents runtime, and verifies status labeling.
        """
        demands = {"ICU_Critical": 4, "Emergency_Trauma": 8, "General_Medical": 20, "Surgery_PostOp": 6}
        capacities = {"ICU": 5, "Emergency": 10, "Internal Medicine": 15, "Surgery": 10, "Pediatrics": 5}

        # Solve via MILP
        res_milp = self.optimizer.optimize_bed_allocation(demands, capacities)
        
        # Solve via Fallback
        res_fb = self.optimizer._solve_priority_fallback(
            demands, capacities, allow_float_pool=True, start_time=time.time(), damaged_beds={}
        )

        # Both must satisfy hard constraints
        self.assertTrue(res_milp["is_verified"])
        self.assertTrue(res_fb["is_verified"])

        # MILP is proven optimal
        self.assertTrue(res_milp["is_proven_optimal"])
        # Fallback is honest heuristic
        self.assertFalse(res_fb["is_proven_optimal"])
        self.assertIn("Priority-Constrained Greedy Fallback", res_fb["solver_name"])

        # Objective of MILP must be <= objective of heuristic
        self.assertLessEqual(res_milp["objective_value"], res_fb["objective_value"])


if __name__ == "__main__":
    unittest.main()

