"""
VitalOptima - Application Smoke Test & End-to-End Component Initialization
Validates that all core services, computational models, database accessors,
and UI views import and initialize cleanly without runtime syntax or configuration errors.
"""
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestApplicationSmoke(unittest.TestCase):
    def test_core_configuration_and_imports(self):
        """Verifies core configuration, constants, and shift logic."""
        import config
        self.assertTrue(hasattr(config, "HOSPITAL_NAME"))
        self.assertTrue(hasattr(config, "GENERAL_BEDS_TOTAL"))
        self.assertTrue(hasattr(config, "ICU_BEDS_TOTAL"))
        shift = config.get_current_shift()
        self.assertIn("name", shift)
        self.assertIn("hours", shift)
        self.assertIn("lead", shift)

    def test_database_initialization(self):
        """Verifies database initialization and table presence."""
        from db.database import init_db, get_sqlite_connection
        init_db()
        conn = get_sqlite_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()

        required_tables = [
            "hospital_census_daily", "department_resources", "staffing_roster",
            "inventory_supplies", "blood_bank_inventory", "patient_admissions",
            "audit_logs", "users", "decision_log", "sync_outbox"
        ]
        for tbl in required_tables:
            self.assertIn(tbl, tables, f"Expected table '{tbl}' to exist in initialized SQLite database.")

    def test_forecaster_engine_instantiation(self):
        """Verifies that the DemandForecaster initializes and produces predictions."""
        from models.forecaster import DemandForecaster
        fc = DemandForecaster()
        self.assertTrue(fc.is_trained)
        df_24, m_24 = fc.get_24h_forecast()
        self.assertEqual(len(df_24), 25)
        self.assertGreater(m_24["peak_value"], 0)

    def test_optimizer_engine_instantiation(self):
        """Verifies that the ResourceOptimizer initializes and solves allocations."""
        from models.optimizer import ResourceOptimizer
        opt = ResourceOptimizer()
        res = opt.optimize_bed_allocation({"General_Medical": 10}, {"Internal Medicine": 10})
        self.assertEqual(res["total_allocated"], 10)
        self.assertEqual(res["total_unmet"], 0)
        self.assertTrue(res["is_verified"])

    def test_scenario_simulator_instantiation(self):
        """Verifies that the ScenarioSimulator initializes."""
        from models.simulator import ScenarioSimulator
        sim = ScenarioSimulator()
        self.assertIsNotNone(sim.optimizer)

    def test_ui_view_module_imports(self):
        """Verifies that all Streamlit view modules import without syntax or import errors."""
        import ui.styles
        import ui.components
        import ui.views.dashboard
        import ui.views.admission_workspace
        import ui.views.demand_forecast
        import ui.views.optimization
        import ui.views.simulator
        import ui.views.decision_log
        import ui.views.settings_view
        import ui.views.ai_insights
        import ui.views.postgres_explorer

        self.assertTrue(callable(ui.views.dashboard.show_dashboard))
        self.assertTrue(callable(ui.views.admission_workspace.show_admission_workspace))
        self.assertTrue(callable(ui.views.demand_forecast.show_demand_forecast))
        self.assertTrue(callable(ui.views.optimization.show_optimization))
        self.assertTrue(callable(ui.views.simulator.show_simulator))
        self.assertTrue(callable(ui.views.decision_log.show_decision_log))
        self.assertTrue(callable(ui.views.settings_view.show_settings_view))


if __name__ == "__main__":
    unittest.main()

