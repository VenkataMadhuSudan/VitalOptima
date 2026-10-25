"""
Validation suite for the 4 official hospital datasets provided by the user.
"""
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from config import DATA_DIR
from models.forecaster import DemandForecaster


class TestRealDatasets(unittest.TestCase):
    def test_census_daily_dataset(self):
        census_file = DATA_DIR / "hospital_census_daily.csv"
        self.assertTrue(census_file.exists(), "hospital_census_daily.csv missing")
        df = pd.read_csv(census_file)
        self.assertEqual(len(df), 365, f"Expected 365 records, got {len(df)}")
        self.assertTrue((df["general_beds_total"] == 300).all(), "General beds total should be 300")
        self.assertTrue((df["icu_beds_total"] == 30).all(), "ICU beds total should be 30")
        self.assertGreaterEqual(df["emergency_arrivals"].min(), 130)
        self.assertLessEqual(df["emergency_arrivals"].max(), 310)

    def test_department_resources_dataset(self):
        res_file = DATA_DIR / "department_resources.csv"
        self.assertTrue(res_file.exists(), "department_resources.csv missing")
        df = pd.read_csv(res_file)
        self.assertEqual(len(df), 13, f"Expected 13 resources, got {len(df)}")
        
        gen_beds = df[df["resource_type"] == "General Bed"]
        self.assertEqual(gen_beds["total_capacity"].sum(), 300)
        self.assertEqual(gen_beds["occupied_capacity"].sum(), 238)
        self.assertEqual(gen_beds["available_capacity"].sum(), 50)
        self.assertEqual(gen_beds["unavailable_capacity"].sum(), 12)
        
        icu_beds = df[df["resource_type"] == "ICU Bed"]
        self.assertEqual(icu_beds["total_capacity"].sum(), 30)
        self.assertEqual(icu_beds["occupied_capacity"].sum(), 23)
        self.assertEqual(icu_beds["available_capacity"].sum(), 5)
        self.assertEqual(icu_beds["unavailable_capacity"].sum(), 2)
        
        ors = df[df["resource_type"] == "Operating Room"]
        self.assertEqual(ors["total_capacity"].sum(), 12)
        self.assertEqual(ors["occupied_capacity"].sum(), 8)
        self.assertEqual(ors["available_capacity"].sum(), 3)
        self.assertEqual(ors["unavailable_capacity"].sum(), 1)

    def test_inventory_supplies_dataset(self):
        inv_file = DATA_DIR / "inventory_supplies.csv"
        self.assertTrue(inv_file.exists(), "inventory_supplies.csv missing")
        df = pd.read_csv(inv_file)
        self.assertEqual(len(df["item_id"].unique()), 11, "Expected 11 unique medical supply items")
        self.assertIn("MSK-N95", df["item_id"].values)
        latest_n95 = df[df["item_id"] == "MSK-N95"].iloc[-1]
        self.assertEqual(latest_n95["closing_stock"], 0, "N95 should reflect stockout on Dec 31")

    def test_staffing_roster_dataset(self):
        roster_file = DATA_DIR / "staffing_roster.csv"
        self.assertTrue(roster_file.exists(), "staffing_roster.csv missing")
        df = pd.read_csv(roster_file)
        self.assertEqual(len(df["date"].unique()), 7, "Expected 7-day staffing roster")
        self.assertEqual(set(df["shift"].unique()), {"Morning", "Evening", "Night"})
        self.assertTrue((df["maximum_permitted_working_hours"] >= 40).all())

    def test_forecaster_trained_on_real_data(self):
        fc = DemandForecaster()
        self.assertTrue(fc.is_trained)
        self.assertEqual(fc.metrics["dataset_rows"], 365)
        self.assertGreater(fc.metrics["mae"], 0)
        self.assertLess(fc.metrics["mae"], 25.0)
        self.assertGreater(len(fc.feature_importances), 0)


if __name__ == "__main__":
    unittest.main()
