"""
VitalOptima Automated Test Suite
Validates mathematical optimization, ML forecasting, simulation dynamics, and database integrity.
"""
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

def test_synthetic_data_integrity():
    df_depts = generate_departments_data()
    assert not df_depts.empty
    assert "Total Beds" in df_depts.columns
    assert (df_depts["Occupied"] >= 0).all()
    assert (df_depts["Available"] >= 0).all()
    assert (df_depts["Occupancy"] <= 100).all()

    df_fc = generate_demand_forecast_data()
    assert len(df_fc) == 25
    assert "Predicted_Demand" in df_fc.columns
    assert (df_fc["Predicted_Demand"] > 0).all()

def test_demand_forecaster():
    forecaster = DemandForecaster()
    df_fc, metrics = forecaster.get_24h_forecast(surge_multiplier=1.0)
    assert metrics["peak_value"] >= 90
    assert "15" in str(metrics["peak_hour"])
    assert metrics["average_demand"] > 0

    # Test surge multiplier
    df_surge, metrics_surge = forecaster.get_24h_forecast(surge_multiplier=1.5)
    assert metrics_surge["peak_value"] > metrics["peak_value"]

def test_resource_optimizer_feasibility():
    optimizer = ResourceOptimizer()
    recs, res = optimizer.generate_recommendations()
    assert res["status"] in ["Optimal", "Feasible"]
    assert res["total_allocated"] > 0
    assert len(recs) >= 3

def test_scenario_simulator_dynamics():
    sim = ScenarioSimulator()
    baseline = sim.run_simulation(surge_pct=0, icu_loss_beds=0, staff_shortage_pct=0)
    stressed = sim.run_simulation(surge_pct=50, icu_loss_beds=6, staff_shortage_pct=25)

    assert stressed["metrics"]["general_beds"]["rate"] >= baseline["metrics"]["general_beds"]["rate"]
    assert stressed["metrics"]["icu_beds"]["rate"] >= baseline["metrics"]["icu_beds"]["rate"]
    assert len(stressed["bottlenecks"]) > len(baseline["bottlenecks"])
    assert len(stressed["mitigations"]) > 0

def test_database_logging():
    init_db()
    initial_count = len(get_decision_logs())
    log_decision(
        category="Test Category",
        recommendation="Test Recommendation",
        decision="Accepted",
        administrator="Test Admin",
        rationale="Unit test verification"
    )
    new_logs = get_decision_logs()
    assert len(new_logs) == initial_count + 1
    assert new_logs[0]["recommendation"] == "Test Recommendation"

if __name__ == "__main__":
    print("Running tests...")
    test_synthetic_data_integrity()
    test_demand_forecaster()
    test_resource_optimizer_feasibility()
    test_scenario_simulator_dynamics()
    test_database_logging()
    print("All tests passed successfully!")
