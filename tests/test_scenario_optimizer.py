"""
VitalOptima Scenario-Based & Stochastic Optimizer Verification Suite
Validates mathematical formulation, scenario derivation from conformal intervals,
first-stage non-anticipativity, and independent stochastic allocation checks.
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.scenario_optimizer import (
    DemandScenario,
    ScenarioGenerator,
    StochasticResourceOptimizer,
    validate_stochastic_allocation
)


class TestScenarioOptimizerRigor(unittest.TestCase):
    def setUp(self):
        self.base_demands = {
            "General_Medical": 25,
            "Emergency_Trauma": 12,
            "ICU_Critical": 5,
            "Surgery_PostOp": 8,
            "Pediatric": 6
        }
        self.capacities = {
            "Internal Medicine": 35,
            "Emergency": 25,
            "ICU": 12,
            "Surgery": 20,
            "Pediatrics": 15
        }
        self.conformal_q = 14.5
        self.optimizer = StochasticResourceOptimizer()

    def test_scenario_generation_rigor(self):
        """Verifies scenario generator creates probability-weighted scenarios strictly increasing in demand."""
        scenarios = ScenarioGenerator.generate_scenarios_from_forecast(
            self.base_demands, conformal_halfwidth=self.conformal_q
        )
        self.assertEqual(len(scenarios), 3)

        # Probabilities must sum to 1.0
        tot_prob = sum(s.probability for s in scenarios)
        self.assertAlmostEqual(tot_prob, 1.0, places=3)

        # Demand must strictly increase monotonically with uncertainty level
        exp_dem = sum(scenarios[0].demands.values())
        high_dem = sum(scenarios[1].demands.values())
        surge_dem = sum(scenarios[2].demands.values())

        self.assertGreater(high_dem, exp_dem)
        self.assertGreater(surge_dem, high_dem)

    def test_two_stage_stochastic_optimization_solves(self):
        """Verifies two-stage stochastic MILP solves and returns complete decision structures."""
        scenarios = ScenarioGenerator.generate_scenarios_from_forecast(
            self.base_demands, conformal_halfwidth=self.conformal_q
        )
        res = self.optimizer.optimize_stochastic(
            scenarios=scenarios,
            available_capacities=self.capacities,
            total_regular_nurses=24,
            base_nurse_cost=50.0,
            overtime_nurse_cost=120.0
        )

        self.assertIn(res["status"], ["Optimal", "Feasible"])
        self.assertIn("first_stage_decisions", res)
        self.assertIn("expected_metrics", res)
        self.assertIn("scenarios_evaluated", res)

        # First stage staffing check
        first_stage = res["first_stage_decisions"]
        self.assertLessEqual(first_stage["total_committed_nurses"], 24)
        self.assertGreater(first_stage["total_committed_nurses"], 0)

        # 3 scenarios evaluated
        self.assertEqual(len(res["scenarios_evaluated"]), 3)

    def test_first_stage_non_anticipativity(self):
        """Verifies Stage 1 base nurse staffing decisions are identical across all scenarios."""
        scenarios = ScenarioGenerator.generate_scenarios_from_forecast(
            self.base_demands, conformal_halfwidth=self.conformal_q
        )
        res = self.optimizer.optimize_stochastic(
            scenarios=scenarios,
            available_capacities=self.capacities,
            total_regular_nurses=22
        )

        base_staffing = res["first_stage_decisions"]["base_nurse_staffing"]
        # Must cover all departments
        for dept in self.capacities:
            self.assertIn(dept, base_staffing)
            self.assertGreaterEqual(base_staffing[dept], 0)

        # Independent validator check
        is_valid, violations = validate_stochastic_allocation(res, self.capacities)
        self.assertTrue(is_valid, f"Validation failed with: {violations}")

    def test_stochastic_validator_catches_violations(self):
        """Verifies independent validator catches invalid assignments and capacity violations."""
        # Intentionally invalid result with incompatible placement
        corrupt_res = {
            "first_stage_decisions": {
                "base_nurse_staffing": {"Internal Medicine": 5, "ICU": 3}
            },
            "scenarios_evaluated": [
                {
                    "scenario_name": "Test Scenario",
                    "probability": 1.0,
                    "allocations": [
                        {
                            "Patient_Group": "ICU_Critical",
                            "Assigned_Department": "Pediatrics",  # Incompatible!
                            "Count": 5
                        }
                    ]
                }
            ]
        }
        is_valid, violations = validate_stochastic_allocation(corrupt_res, self.capacities)
        self.assertFalse(is_valid)
        self.assertTrue(any("Incompatible assignment" in v for v in violations))

    def test_stochastic_heuristic_fallback(self):
        """Verifies deterministic heuristic fallback executes and is truthfully labeled."""
        scenarios = ScenarioGenerator.generate_scenarios_from_forecast(
            self.base_demands, conformal_halfwidth=self.conformal_q
        )
        res = self.optimizer._solve_stochastic_fallback(
            scenarios=scenarios,
            capacities=self.capacities,
            total_regular_nurses=20,
            base_nurse_cost=50.0,
            overtime_nurse_cost=120.0,
            start_time=0.0
        )
        self.assertEqual(res["status"], "Feasible")
        self.assertFalse(res["is_proven_optimal"])
        self.assertIn("Heuristic", res["solver_backend"])
        self.assertIn("first_stage_decisions", res)

    def test_stochastic_sensitivity_artifact_integrity(self):
        """Verifies multi-seed sensitivity analysis results artifact and stability bounds."""
        import json
        artifact = PROJECT_ROOT / "evaluation" / "stochastic_sensitivity_results.json"
        self.assertTrue(artifact.exists(), "stochastic_sensitivity_results.json not found")
        with open(artifact, "r") as f:
            data = json.load(f)

        summary = data["multi_seed_stability"]
        self.assertEqual(summary["num_seeds"], 10)
        self.assertEqual(summary["total_evaluations"], 150)
        self.assertGreater(summary["cost_reduction_mean_pct"], 10.0)
        self.assertGreater(summary["surge_unmet_reduction_mean_pct"], 5.0)

    def test_compound_disaster_stress_scenario(self):
        """Verifies solver handles compound disaster (+50% surge, 6 damaged ICU beds, 27% staff loss)."""
        stressed_demands = {k: int(round(v * 1.5)) for k, v in self.base_demands.items()}
        scenarios = ScenarioGenerator.generate_scenarios_from_forecast(stressed_demands, conformal_halfwidth=25.22)
        res = self.optimizer.optimize_stochastic(
            scenarios=scenarios,
            available_capacities=self.capacities,
            total_regular_nurses=18,
            damaged_beds={"ICU": 6}
        )
        self.assertEqual(res["status"], "Optimal")
        self.assertTrue(res.get("is_proven_optimal", False))
        is_valid, violations = validate_stochastic_allocation(res, self.capacities, damaged_beds={"ICU": 6})
        self.assertTrue(is_valid, f"Validation failed with: {violations}")


if __name__ == "__main__":
    unittest.main()

