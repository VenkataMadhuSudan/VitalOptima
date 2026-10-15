"""
VitalOptima — Automated Test Suite for Blood Bank Backup Inventory & NLP Engine
Validates blood bank inventory data loading, PostgreSQL / SQLite table synchronization,
NLP natural language query routing, sub-intent detection (O-, Platelets, Shortages),
and AI assistant contextual response generation.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.postgres import load_blood_bank_dataset, test_connection, run_custom_query
from db.database import get_sqlite_connection, init_db
from db.nlp_query import process_natural_language_query
from services.dashboard_summarizer import handle_dashboard_qa_request


class TestBloodBankNLP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_csv_dataset_exists_and_valid(self):
        """Test 1: blood_bank_inventory.csv exists and has correct columns and row count."""
        csv_path = PROJECT_ROOT / "data" / "blood_bank_inventory.csv"
        self.assertTrue(csv_path.exists(), "blood_bank_inventory.csv must exist in data/")

        df = load_blood_bank_dataset()
        self.assertFalse(df.empty, "Blood bank dataset should not be empty")
        self.assertGreaterEqual(len(df), 20, "Should contain at least 20 blood inventory rows")

        expected_cols = [
            "blood_group", "component_type", "units_available", "units_reserved",
            "net_available_units", "critical_threshold", "daily_consumption",
            "days_of_supply", "shelf_life_days", "storage_temp", "rh_factor", "status"
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns, f"Column '{col}' must exist in blood bank dataset")

    def test_02_sqlite_table_exists_and_populated(self):
        """Test 2: blood_bank_inventory table exists and has rows in SQLite."""
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM blood_bank_inventory")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreaterEqual(count, 20, f"SQLite blood_bank_inventory should have >= 20 rows, got {count}")

    def test_03_nlp_general_blood_availability_query(self):
        """Test 3: Querying general blood availability routes to blood_bank_inventory."""
        res = process_natural_language_query("How much blood is available in the hospital?")
        self.assertTrue(res["success"])
        self.assertEqual(res["table_name"], "blood_bank_inventory")
        self.assertFalse(res["df"].empty)
        self.assertIn("units_available", res["df"].columns)
        self.assertGreater(len(res["insights"]), 0)

    def test_04_nlp_specific_blood_group_o_negative(self):
        """Test 4: Specific blood group query (O-) filters for O- records."""
        res = process_natural_language_query("How many units of O negative blood do we have?")
        self.assertTrue(res["success"])
        self.assertEqual(res["table_name"], "blood_bank_inventory")
        self.assertFalse(res["df"].empty)
        # All returned rows should be O-
        unique_groups = res["df"]["blood_group"].unique()
        for g in unique_groups:
            self.assertIn("O-", g)

    def test_05_nlp_blood_shortage_query(self):
        """Test 5: Querying blood shortages returns critical/low inventory rows."""
        res = process_natural_language_query("Is there a blood shortage?")
        self.assertTrue(res["success"])
        self.assertEqual(res["table_name"], "blood_bank_inventory")
        self.assertFalse(res["df"].empty)
        # Verify critical or low status is captured
        statuses = " ".join(res["df"]["status"].tolist())
        self.assertTrue("Critical" in statuses or "Low" in statuses)

    def test_06_nlp_platelet_component_query(self):
        """Test 6: Querying specific component (Platelet) filters platelet rows."""
        res = process_natural_language_query("Show platelet availability")
        self.assertTrue(res["success"])
        self.assertEqual(res["table_name"], "blood_bank_inventory")
        self.assertFalse(res["df"].empty)
        for comp in res["df"]["component_type"]:
            self.assertIn("Platelet", comp)

    def test_07_dashboard_assistant_qa_blood_intent(self):
        """Test 7: Floating AI dashboard assistant handles blood bank follow-up questions."""
        auth = {"user_id": "admin_test", "role": "hospital_admin"}
        res = handle_dashboard_qa_request(auth, "What is our blood bank backup and O- reserve?")
        self.assertEqual(res["status"], "success")
        self.assertIn("Blood Bank", res["answer"])
        self.assertIn("O- Universal Donor", res["answer"])


if __name__ == "__main__":
    unittest.main()
