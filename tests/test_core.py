"""
VitalOptima Automated Test Suite
Validates mathematical optimization, ML forecasting, simulation dynamics, and database integrity.
"""
import unittest
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.synthetic_generator import generate_departments_data, generate_demand_forecast_data, get_alerts
from models.forecaster import DemandForecaster
from models.optimizer import ResourceOptimizer
from models.simulator import ScenarioSimulator
from db.database import log_decision, get_decision_logs, init_db


class TestCoreFunctionality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.forecaster = DemandForecaster()
        cls.optimizer = ResourceOptimizer()
        cls.simulator = ScenarioSimulator()

    def test_synthetic_data_integrity(self):
        df_depts = generate_departments_data()
        self.assertFalse(df_depts.empty)
        self.assertIn("Total Beds", df_depts.columns)
        self.assertTrue((df_depts["Occupied"] >= 0).all())
        self.assertTrue((df_depts["Available"] >= 0).all())
        self.assertTrue((df_depts["Occupancy"] <= 100).all())

        df_fc = generate_demand_forecast_data()
        self.assertEqual(len(df_fc), 25)
        self.assertIn("Predicted_Demand", df_fc.columns)
        self.assertTrue((df_fc["Predicted_Demand"] > 0).all())

    def test_demand_forecaster(self):
        df_fc, metrics = self.forecaster.get_24h_forecast(surge_multiplier=1.0)
        self.assertGreaterEqual(metrics["peak_value"], 90)
        self.assertIn("15", str(metrics["peak_hour"]))
        self.assertGreater(metrics["average_demand"], 0)

        # Test surge multiplier
        df_surge, metrics_surge = self.forecaster.get_24h_forecast(surge_multiplier=1.5)
        self.assertGreater(metrics_surge["peak_value"], metrics["peak_value"])

    def test_resource_optimizer_feasibility(self):
        recs, res = self.optimizer.generate_recommendations()
        self.assertIn(res["status"], ["Optimal", "Feasible"])
        self.assertGreater(res["total_allocated"], 0)
        self.assertGreaterEqual(len(recs), 3)

    def test_scenario_simulator_dynamics(self):
        baseline = self.simulator.run_simulation(surge_pct=0, icu_loss_beds=0, staff_shortage_pct=0)
        stressed = self.simulator.run_simulation(surge_pct=50, icu_loss_beds=6, staff_shortage_pct=25)

        self.assertGreaterEqual(stressed["metrics"]["general_beds"]["rate"], baseline["metrics"]["general_beds"]["rate"])
        self.assertGreaterEqual(stressed["metrics"]["icu_beds"]["rate"], baseline["metrics"]["icu_beds"]["rate"])
        self.assertGreater(len(stressed["bottlenecks"]), len(baseline["bottlenecks"]))
        self.assertGreater(len(stressed["mitigations"]), 0)

    def test_database_logging(self):
        initial_count = len(get_decision_logs())
        log_decision(
            category="Test Category",
            recommendation="Test Recommendation",
            decision="Accepted",
            administrator="Test Admin",
            rationale="Unit test verification"
        )
        new_logs = get_decision_logs()
        self.assertEqual(len(new_logs), initial_count + 1)
        self.assertEqual(new_logs[0]["recommendation"], "Test Recommendation")


if __name__ == "__main__":
    unittest.main()
