"""
Validation suite for the 4 official hospital datasets provided by the user.
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from config import DATA_DIR
from models.forecaster import DemandForecaster

def test_census_daily_dataset():
    census_file = DATA_DIR / "hospital_census_daily.csv"
    assert census_file.exists(), "hospital_census_daily.csv missing"
    df = pd.read_csv(census_file)
    assert len(df) == 365, f"Expected 365 records, got {len(df)}"
    assert (df["general_beds_total"] == 300).all(), "General beds total should be 300"
    assert (df["icu_beds_total"] == 30).all(), "ICU beds total should be 30"
    assert df["emergency_arrivals"].min() >= 130
    assert df["emergency_arrivals"].max() <= 310

def test_department_resources_dataset():
    res_file = DATA_DIR / "department_resources.csv"
    assert res_file.exists(), "department_resources.csv missing"
    df = pd.read_csv(res_file)
    assert len(df) == 13, f"Expected 13 resources, got {len(df)}"
    
    gen_beds = df[df["resource_type"] == "General Bed"]
    assert gen_beds["total_capacity"].sum() == 300
    assert gen_beds["occupied_capacity"].sum() == 238
    assert gen_beds["available_capacity"].sum() == 50
    assert gen_beds["unavailable_capacity"].sum() == 12
    
    icu_beds = df[df["resource_type"] == "ICU Bed"]
    assert icu_beds["total_capacity"].sum() == 30
    assert icu_beds["occupied_capacity"].sum() == 23
    assert icu_beds["available_capacity"].sum() == 5
    assert icu_beds["unavailable_capacity"].sum() == 2
    
    ors = df[df["resource_type"] == "Operating Room"]
    assert ors["total_capacity"].sum() == 12
    assert ors["occupied_capacity"].sum() == 8
    assert ors["available_capacity"].sum() == 3
    assert ors["unavailable_capacity"].sum() == 1

def test_inventory_supplies_dataset():
    inv_file = DATA_DIR / "inventory_supplies.csv"
    assert inv_file.exists(), "inventory_supplies.csv missing"
    df = pd.read_csv(inv_file)
    assert len(df["item_id"].unique()) == 11, "Expected 11 unique medical supply items"
    assert "MSK-N95" in df["item_id"].values
    latest_n95 = df[df["item_id"] == "MSK-N95"].iloc[-1]
    assert latest_n95["closing_stock"] == 0, "N95 should reflect stockout on Dec 31"

def test_staffing_roster_dataset():
    roster_file = DATA_DIR / "staffing_roster.csv"
    assert roster_file.exists(), "staffing_roster.csv missing"
    df = pd.read_csv(roster_file)
    assert len(df["date"].unique()) == 7, "Expected 7-day staffing roster"
    assert set(df["shift"].unique()) == {"Morning", "Evening", "Night"}
    assert (df["maximum_permitted_working_hours"] >= 40).all()

def test_forecaster_trained_on_real_data():
    fc = DemandForecaster()
    assert fc.is_trained
    assert fc.metrics["dataset_rows"] == 365
    assert fc.metrics["r2"] > 0.5
    assert len(fc.feature_importances) > 0

if __name__ == "__main__":
    test_census_daily_dataset()
    test_department_resources_dataset()
    test_inventory_supplies_dataset()
    test_staffing_roster_dataset()
    test_forecaster_trained_on_real_data()
    print("All 4 user datasets verified and ML forecaster verified successfully!")
