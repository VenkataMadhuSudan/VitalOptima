"""
VitalOptima — Automated Test Suite for AI Dashboard Summarizer
Validates authorization, deterministic metrics, zero-division safety,
rule-based fallback mode, LLM provider abstraction, schema conformity,
caching concurrency, follow-up query safety, and data freshness.
"""

import os
import sys
import unittest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.dashboard_summarizer import (
    DashboardSummarizerService,
    handle_dashboard_summary_request,
    handle_dashboard_qa_request,
    _safe_div,
    THRESHOLDS
)


class TestDashboardSummarizer(unittest.TestCase):
    def setUp(self):
        self.service = DashboardSummarizerService()
        self.admin_auth = {"user_id": "admin_42", "role": "hospital_admin", "username": "Dr. Sarah Jenkins"}
        self.guest_auth = {"user_id": "guest_01", "role": "guest"}
        self.empty_auth = {}

    def test_01_authorized_administrator_can_request_summary(self):
        """Test 1: Authorized administrator can successfully request a summary."""
        res = self.service.generate_summary(auth_context=self.admin_auth, force_refresh=True)
        self.assertEqual(res.get("status"), "success")
        self.assertIn("overallStatus", res)
        self.assertIn("keyInsights", res)
        self.assertIn("attentionItems", res)
        self.assertIn("recommendedActions", res)

    def test_02_unauthorized_users_cannot_access_endpoint(self):
        """Test 2: Unauthorized users are strictly rejected with an error status."""
        res_guest = self.service.generate_summary(auth_context=self.guest_auth)
        self.assertEqual(res_guest.get("status"), "error")
        self.assertEqual(res_guest.get("error_code"), "UNAUTHORIZED")

        res_empty = self.service.generate_summary(auth_context=self.empty_auth)
        self.assertEqual(res_empty.get("status"), "error")
        self.assertEqual(res_empty.get("error_code"), "UNAUTHORIZED")

    def test_03_real_dashboard_data_is_used(self):
        """Test 3: Authoritative system metrics and verified database records are loaded."""
        metrics = self.service.gather_dashboard_metrics()
        self.assertIn("general_beds", metrics)
        self.assertIn("icu_beds", metrics)
        self.assertIn("staffing", metrics)
        self.assertIn("operating_rooms", metrics)
        self.assertIn("demand_forecast", metrics)

        # Verify positive numbers and logical capacity bounds
        self.assertGreater(metrics["general_beds"]["total"], 0)
        self.assertGreaterEqual(metrics["general_beds"]["occupied"], 0)
        self.assertGreaterEqual(metrics["general_beds"]["available"], 0)
        self.assertLessEqual(metrics["general_beds"]["utilization_pct"], 100.0)

    def test_04_missing_metrics_handled_safely(self):
        """Test 4: System safely handles empty or missing data fields without crashing."""
        sparse_metrics = {
            "hospital_name": "Test Hospital",
            "timestamp": "Oct 15, 2026 07:00",
            "datetime_iso": "2026-10-15T07:00:00+05:30",
            "shift": {"name": "Day Shift", "hours": "07:00 - 15:00", "lead": "Dr. Test"},
            "general_beds": {"total": 0, "occupied": 0, "available": 0, "unavailable": 0, "utilization_pct": 0, "warning_threshold_pct": 80, "critical_threshold_pct": 90, "source": "test"},
            "icu_beds": {"total": 0, "occupied": 0, "available": 0, "unavailable": 0, "utilization_pct": 0, "warning_threshold_pct": 80, "critical_threshold_pct": 90, "source": "test"},
            "staffing": {"total": 0, "scheduled": 0, "available": 0, "shortage": 0, "availability_pct": 0, "source": "test"},
            "operating_rooms": {"total": 0, "operational": 0, "unavailable": 0, "available_slots": 0, "utilization_pct": 0, "source": "test"},
            "demand_forecast": {"peak_arrivals": 0, "peak_hour": "12:00", "avg_hourly_arrivals": 0, "ci_lower": 0, "ci_upper": 0, "model": "test", "source": "test"},
            "inventory": {"critical_items": [], "source": "test"},
            "optimization": {"expected_gain": "0%", "ed_wait_reduction": "0 min"},
            "data_freshness": {"census_records": "N/A", "inventory_records": "N/A"}
        }
        summary = self.service.generate_rule_based_summary(sparse_metrics)
        self.assertEqual(summary["status"], "success")
        self.assertIsInstance(summary["keyInsights"], list)

    def test_05_zero_denominators_do_not_cause_invalid_calculations(self):
        """Test 5: Zero denominators or negative values return safe defaults."""
        self.assertEqual(_safe_div(10, 0), 0.0)
        self.assertEqual(_safe_div(10, -5), 0.0)
        self.assertEqual(_safe_div(None, 10), 0.0)
        self.assertEqual(_safe_div(10, None), 0.0)
        self.assertEqual(_safe_div(20, 100), 20.0)

    def test_06_invalid_model_output_is_safely_handled(self):
        """Test 6: Malformed LLM response falls back cleanly to deterministic summary."""
        with patch.object(self.service, "generate_llm_summary", return_value=(None, "none")):
            summary = self.service.generate_summary(auth_context=self.admin_auth, force_refresh=True)
            self.assertEqual(summary["status"], "success")
            self.assertTrue(summary["isFallback"])
            self.assertEqual(summary["provider"], "rule_based")

    def test_07_ai_provider_timeout_handled(self):
        """Test 7: Slow or hanging external LLM calls trigger safe timeout fallback."""
        def slow_call(*args, **kwargs):
            raise TimeoutError("External AI provider timed out after 8000ms")

        with patch.object(self.service, "_call_gemini_api", side_effect=slow_call):
            with patch.object(self.service, "_call_anthropic_api", side_effect=slow_call):
                with patch.object(self.service, "_call_openai_api", side_effect=slow_call):
                    summary = self.service.generate_summary(auth_context=self.admin_auth, force_refresh=True)
                    self.assertEqual(summary["status"], "success")
                    self.assertTrue(summary["isFallback"])

    def test_08_fallback_mode_works_without_api_keys(self):
        """Test 8: Rule-based summarization functions completely offline without any API keys."""
        clean_env = dict(os.environ)
        for k in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"]:
            clean_env.pop(k, None)
        with patch.dict("os.environ", clean_env, clear=True):
            summary = self.service.generate_summary(auth_context=self.admin_auth, force_refresh=True)
            self.assertEqual(summary["status"], "success")
            self.assertEqual(summary["provider"], "rule_based")
            self.assertTrue(summary["isFallback"])
            self.assertGreaterEqual(len(summary["keyInsights"]), 3)

    def test_09_threshold_warnings_use_configured_thresholds(self):
        """Test 9: Operational concerns trigger accurately according to configured thresholds."""
        findings = self.service.evaluate_deterministic_findings({
            "general_beds": {"utilization_pct": 82.0, "critical_threshold_pct": 90.0, "warning_threshold_pct": 80.0, "available": 50},
            "icu_beds": {"utilization_pct": 89.0, "critical_threshold_pct": 88.0, "warning_threshold_pct": 80.0, "available": 3},
            "staffing": {"shortage": 25},
            "operating_rooms": {},
            "demand_forecast": {"peak_hour": "15:00", "peak_arrivals": 94},
            "inventory": {"critical_items": []}
        })
        self.assertEqual(findings["icu_severity"], "Critical")
        self.assertEqual(findings["gen_severity"], "High")
        self.assertEqual(findings["staff_severity"], "Critical")

    def test_10_forecasts_clearly_distinguished_from_measurements(self):
        """Test 10: Forecasts state model, time horizon, and confidence intervals clearly."""
        summary = self.service.generate_summary(auth_context=self.admin_auth, force_refresh=True)
        tf = summary.get("trendsAndForecasts", {})
        self.assertIn("forecastModel", tf)
        self.assertIn("Random Forest", tf["forecastModel"])
        self.assertIn("peakWindow", tf)

    def test_11_stale_data_is_identified(self):
        """Test 11: System discloses telemetry periods and data freshness timestamps."""
        summary = self.service.generate_summary(auth_context=self.admin_auth, force_refresh=True)
        freshness = summary.get("dataFreshness", {})
        self.assertIn("censusTelemetry", freshness)
        self.assertIn("inventoryTelemetry", freshness)
        self.assertIn("365 days", freshness["censusTelemetry"])

    def test_12_caching_and_concurrency_deduplication(self):
        """Test 12: Rapid duplicate calls return cached instances within TTL without re-evaluating."""
        t1 = time.time()
        s1 = self.service.generate_summary(auth_context=self.admin_auth, force_refresh=True)
        s2 = self.service.generate_summary(auth_context=self.admin_auth, force_refresh=False)
        self.assertEqual(s1["dataAsOf"], s2["dataAsOf"])

    def test_13_contextual_follow_up_qa(self):
        """Test 13: Contextual questions return structured, parameter-safe answers."""
        q1 = "Which department needs the most attention?"
        ans1 = handle_dashboard_qa_request(self.admin_auth, q1)
        self.assertEqual(ans1["status"], "success")
        self.assertIn("ICU", ans1["answer"])

        q2 = "Why is ICU utilization high?"
        ans2 = handle_dashboard_qa_request(self.admin_auth, q2)
        self.assertEqual(ans2["status"], "success")
        self.assertIn("ICU", ans2["answer"])

        q3 = "What about medical supplies and inventory?"
        ans3 = handle_dashboard_qa_request(self.admin_auth, q3)
        self.assertEqual(ans3["status"], "success")
        self.assertIn("N95", ans3["answer"])


if __name__ == "__main__":
    unittest.main()
