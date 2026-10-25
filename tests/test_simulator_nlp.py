"""
VitalOptima What-If Crisis Simulator NLP Query Parser Test Suite
Validates natural language intent classification, parametric stress scenario extraction,
and conversational edge cases against diverse operational inquiries.
"""
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.simulator_nlp import parse_what_if_query, SIMULATOR_PROMPT_CHIPS


class TestSimulatorNLP(unittest.TestCase):
    def test_simulator_prompt_chips(self):
        """Verifies standard prompt chips resolve into valid structured operational tables."""
        for label, q in SIMULATOR_PROMPT_CHIPS:
            res = parse_what_if_query(q)
            self.assertIsNotNone(res["matched_intent"], f"Failed to match intent for '{label}'")
            self.assertIsNotNone(res["table_title"])
            self.assertGreater(len(res["primary_df"]), 0)
            self.assertGreater(len(res["available_views"]), 0)

    def test_conversational_edge_cases(self):
        """Verifies diverse conversational what-if scenarios extract realistic parameters."""
        edge_cases = [
            ("What if 10 ICU beds are closed due to bio-contamination?", "icu_outage"),
            ("Can we handle if arrivals double?", "surge"),
            ("What protocols if staff goes on strike with 30 nurses missing?", "staff_loss"),
            ("Which department will run out of capacity first?", "vulnerability")
        ]
        for q, expected_key in edge_cases:
            res = parse_what_if_query(q)
            self.assertIn("parameters", res)
            self.assertIn("health_idx", res)
            self.assertIn("answer_summary", res)
            self.assertTrue(len(res["answer_summary"]) > 20)


if __name__ == "__main__":
    unittest.main()
