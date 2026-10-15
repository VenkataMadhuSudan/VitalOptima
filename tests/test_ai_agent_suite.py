"""
VitalOptima Automated Test Suite for AI Insights & Grok Agent
Tests analytics layer, tool execution, schema compliance, missing-key resilience,
and what-if simulation.
"""
import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_analytics import (
    load_daily_census,
    load_hospital_resources,
    load_staff_roster,
    load_inventory,
    load_forecast_outputs,
    get_census_analytics,
    get_capacity_bottlenecks,
    get_staffing_shortages,
    get_inventory_health,
    get_forecast_evaluation_summary,
    build_evidence_package,
    run_deterministic_what_if,
)
from src.agent_tools import (
    TOOL_REGISTRY,
    TOOL_DEFINITIONS,
    execute_tool,
    get_historical_trends,
    get_forecast_summary,
    get_forecast_evaluation,
    check_capacity_risks,
    check_staffing_shortages,
    check_inventory_alerts,
    run_demand_what_if,
)
from src.grok_client import (
    generate_deterministic_insights,
    generate_grok_insights,
    answer_agent_question,
    is_grok_available,
    get_api_key,
)


class TestVitalOptimaAnalytics(unittest.TestCase):
    """Verifies that the analytics layer accurately extracts real hospital facts."""

    def test_census_loading_and_metrics(self):
        df = load_daily_census()
        self.assertFalse(df.empty, "Daily census DataFrame should not be empty")
        self.assertEqual(len(df), 365, "Expected 365 days of hospital census")

        analytics = get_census_analytics()
        self.assertEqual(analytics["status"], "available")
        self.assertGreater(analytics["mean_occupancy_pct"], 70.0)
        self.assertLess(analytics["mean_occupancy_pct"], 85.0)
        self.assertIn("peak_occupancy_pct", analytics)
        self.assertIn("days_above_90pct_risk", analytics)

    def test_capacity_bottlenecks(self):
        cap = get_capacity_bottlenecks()
        self.assertEqual(cap["status"], "available")
        self.assertEqual(cap["nominal_total_beds"], 330)
        self.assertEqual(cap["total_in_service_beds"], 316)
        # Check identified real bottlenecks
        understaffed = cap["understaffed_units"]
        self.assertTrue(any(u["resource_id"] == "GB-MED" for u in understaffed), "GB-MED should be detected as understaffed")
        bottlenecks = cap["demand_bottlenecks"]
        self.assertTrue(any(b["resource_id"] == "ICU-SICU" for b in bottlenecks), "ICU-SICU should be detected as demand bottleneck")

    def test_staffing_shortages(self):
        staff = get_staffing_shortages()
        self.assertEqual(staff["status"], "available")
        events = staff["shortage_events"]
        self.assertGreater(len(events), 0, "Expected at least 1 staffing deficit event")
        # Check for Day 3 Night ICU shortage of 5 nurses
        icu_shortage = [e for e in events if e["department"] == "ICU" and e["shift_type"].lower() == "night"]
        self.assertTrue(len(icu_shortage) > 0, "Expected ICU night shift shortage")

    def test_inventory_health_and_stockout(self):
        inv = get_inventory_health()
        self.assertEqual(inv["status"], "available")
        stockouts = inv["stockout_items"]
        self.assertTrue(any(item["item_id"] == "MSK-N95" for item in stockouts), "MSK-N95 should be detected as 0 stockout")

    def test_forecast_evaluation_summary(self):
        fc = get_forecast_evaluation_summary()
        self.assertEqual(fc["status"], "available")
        self.assertEqual(fc["forecast_horizon_days"], 7)
        self.assertIn("benchmarks", fc)
        self.assertTrue(any("admissions" in k for k in fc["benchmarks"]), "Expected admissions target in benchmarks")
        self.assertIn("high_prediction_error_events", fc)


class TestAgentTools(unittest.TestCase):
    """Verifies that all 7 allowlisted tools execute safely with bounded outputs."""

    def test_allowlisted_tools_present(self):
        expected_tools = [
            "get_historical_trends",
            "get_forecast_summary",
            "get_forecast_evaluation",
            "check_capacity_risks",
            "check_staffing_shortages",
            "check_inventory_alerts",
            "run_demand_what_if",
        ]
        for t in expected_tools:
            self.assertIn(t, TOOL_REGISTRY, f"Tool '{t}' must be in allowlist")

    def test_tool_definitions_schema(self):
        self.assertEqual(len(TOOL_DEFINITIONS), 7)
        for defn in TOOL_DEFINITIONS:
            self.assertEqual(defn["type"], "function")
            self.assertIn("name", defn["function"])
            self.assertIn("description", defn["function"])
            self.assertIn("parameters", defn["function"])

    def test_execute_tool_dispatcher(self):
        # Valid tool
        res = execute_tool("check_capacity_risks", {})
        self.assertNotIn("error", res)
        self.assertIn("total_in_service_beds", res)

        # Disallowed tool execution attempt
        bad_res = execute_tool("arbitrary_command", {})
        self.assertIn("error", bad_res)

    def test_run_demand_what_if_bounds(self):
        # Test extreme inputs are safely clamped
        res = run_demand_what_if(surge_multiplier=10.0, surge_days=20, icu_beds_lost=100)
        self.assertEqual(res["parameters"]["surge_multiplier"], 3.0)
        self.assertEqual(res["parameters"]["surge_days"], 7)
        self.assertEqual(res["parameters"]["icu_beds_lost"], 25)
        self.assertTrue(res["peak_simulated_occupancy_pct"] > 0)


class TestGrokClientAndInsightsSchema(unittest.TestCase):
    """Verifies structured 9-field schema, offline fallback, and Q&A engine."""

    def test_deterministic_insights_schema(self):
        insights = generate_deterministic_insights()
        required_keys = [
            "executive_summary",
            "key_findings",
            "historical_patterns",
            "forecast_interpretation",
            "risk_assessments",
            "improvement_opportunities",
            "recommended_actions",
            "data_limitations",
            "forecast_limitations",
        ]
        for k in required_keys:
            self.assertIn(k, insights, f"Missing required schema field: {k}")

        self.assertIsInstance(insights["executive_summary"], str)
        self.assertGreater(len(insights["executive_summary"]), 50)
        self.assertIsInstance(insights["key_findings"], list)
        self.assertGreaterEqual(len(insights["key_findings"]), 3)
        self.assertIsInstance(insights["risk_assessments"], list)
        self.assertGreaterEqual(len(insights["risk_assessments"]), 3)

    def test_missing_api_key_graceful_handling(self):
        # Force missing key
        data, err = generate_grok_insights(api_key="")
        self.assertEqual(err, "NO_API_KEY")
        self.assertIn("executive_summary", data)
        self.assertIn("key_findings", data)

    def test_interactive_qa_what_if(self):
        answer, tools = answer_agent_question("What happens if demand increases by 15% for 3 days?")
        self.assertIn("Deterministic Simulation Results", answer)
        self.assertTrue(len(tools) >= 1)
        self.assertEqual(tools[0]["tool"], "run_demand_what_if")

    def test_interactive_qa_inventory(self):
        answer, tools = answer_agent_question("Which inventory items are stocked out?")
        self.assertIn("MSK-N95", answer)
        self.assertTrue(any(t["tool"] == "check_inventory_alerts" for t in tools))


if __name__ == "__main__":
    unittest.main()
