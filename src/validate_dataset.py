"""Validation functions for the VitalOptima synthetic dataset.
Each validate_* returns a list of error strings (empty list = pass)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from schemas import (DAILY_COLUMNS, DAILY_INT_COLUMNS, INVENTORY_COLUMNS,
                     INVENTORY_INT_COLUMNS, RESOURCES_COLUMNS,
                     RESOURCES_INT_COLUMNS, STAFF_COLUMNS, STAFF_INT_COLUMNS)


def _basic(df, columns, int_columns, name):
    errs = []
    if list(df.columns) != columns:
        return [f"{name}: columns differ from schema: {list(df.columns)}"]
    if df.isna().any().any():
        errs.append(f"{name}: missing values in {df.columns[df.isna().any()].tolist()}")
    if df.duplicated().any():
        errs.append(f"{name}: duplicate rows")
    for c in int_columns:
        if not pd.api.types.is_integer_dtype(df[c]):
            errs.append(f"{name}: {c} is not an integer dtype")
        elif (df[c] < 0).any():
            errs.append(f"{name}: negative values in {c}")
    return errs


def validate_daily(df, expected_days=None):
    errs = _basic(df, DAILY_COLUMNS, DAILY_INT_COLUMNS, "daily")
    if errs and list(df.columns) != DAILY_COLUMNS:
        return errs
    if expected_days and len(df) != expected_days:
        errs.append(f"daily: expected {expected_days} rows, found {len(df)}")
    dates = pd.to_datetime(df["date"])
    if df["date"].duplicated().any():
        errs.append("daily: duplicate dates")
    if not (dates.diff().dropna() == pd.Timedelta(days=1)).all():
        errs.append("daily: dates are not consecutive")
    if not (dates.dt.day_name() == df["day_of_week"]).all():
        errs.append("daily: day_of_week does not match date")
    if (df["admissions"] < df["elective_admissions"]).any():
        errs.append("daily: elective_admissions > admissions")
    if (df["admissions"] < df["icu_admissions"]).any():
        errs.append("daily: icu_admissions > admissions")
    if (df["emergency_arrivals"] < df["admissions"] - df["elective_admissions"]).any():
        errs.append("daily: emergency admissions exceed emergency_arrivals")
    if (df["general_beds_occupied"] > df["general_beds_total"]).any():
        errs.append("daily: general beds occupied > total")
    if (df["icu_beds_occupied"] > df["icu_beds_total"]).any():
        errs.append("daily: ICU beds occupied > total")
    if (df["average_length_of_stay_days"] <= 0).any():
        errs.append("daily: non-positive average_length_of_stay_days")
    # flow accounting (rows 1..n; day 0's predecessor is not stored)
    occ = df["general_beds_occupied"] + df["icu_beds_occupied"]
    if not (occ.diff().iloc[1:] == (df["admissions"] - df["discharges"]).iloc[1:]).all():
        errs.append("daily: total occupancy change != admissions - discharges")
    icu_exits = df["icu_beds_occupied"].shift(1) + df["icu_admissions"] - df["icu_beds_occupied"]
    if (icu_exits.iloc[1:] < 0).any():
        errs.append("daily: implied ICU step-downs are negative")
    if (df["discharges"].iloc[1:] > df["general_beds_occupied"].shift(1).iloc[1:]).any():
        errs.append("daily: discharges exceed previous-day general census")
    return errs


def validate_resources(df, daily=None):
    errs = _basic(df, RESOURCES_COLUMNS, RESOURCES_INT_COLUMNS, "resources")
    if errs and list(df.columns) != RESOURCES_COLUMNS:
        return errs
    if df["resource_id"].duplicated().any():
        errs.append("resources: duplicate resource_id")
    usable = df["total_capacity"] - df["unavailable_capacity"]
    if (df["unavailable_capacity"] > df["total_capacity"]).any():
        errs.append("resources: unavailable > total")
    if (df["occupied_capacity"] > df["total_capacity"]).any():
        errs.append("resources: occupied > physical capacity")
    if (df["occupied_capacity"] > usable).any():
        errs.append("resources: occupied > usable (total - unavailable)")
    if (df["available_capacity"] != usable - df["occupied_capacity"]).any():
        errs.append("resources: available != total - unavailable - occupied")
    if (df["staffed_capacity"] > usable).any():
        errs.append("resources: staffed > usable")
    if daily is not None:
        last = daily.iloc[-1]
        for rtype, col in [("General Bed", "general_beds_occupied"), ("ICU Bed", "icu_beds_occupied")]:
            if df.loc[df.resource_type == rtype, "occupied_capacity"].sum() != last[col]:
                errs.append(f"resources: {rtype} occupancy does not match last daily row")
        for rtype, col in [("General Bed", "general_beds_total"), ("ICU Bed", "icu_beds_total")]:
            if df.loc[df.resource_type == rtype, "total_capacity"].sum() != last[col]:
                errs.append(f"resources: {rtype} total does not match daily file")
    return errs


def validate_staff(df, min_days=7, require_shortage=True):
    errs = _basic(df, STAFF_COLUMNS, STAFF_INT_COLUMNS, "staff")
    if errs and list(df.columns) != STAFF_COLUMNS:
        return errs
    if df["date"].nunique() < min_days:
        errs.append(f"staff: fewer than {min_days} days")
    if not (df.groupby("date")["shift"].nunique() == 3).all():
        errs.append("staff: each date needs exactly 3 shifts")
    if df.duplicated(["date", "shift", "department", "staff_role"]).any():
        errs.append("staff: duplicate date/shift/department/role keys")
    if (df["required_count"] <= 0).any():
        errs.append("staff: required_count must be > 0")
    if require_shortage and not (df["available_count"] < df["required_count"]).any():
        errs.append("staff: no shortage rows present")
    return errs


def validate_inventory(df, expected_days=30, require_stockout=True):
    errs = _basic(df, INVENTORY_COLUMNS, INVENTORY_INT_COLUMNS, "inventory")
    if errs and list(df.columns) != INVENTORY_COLUMNS:
        return errs
    if (df["closing_stock"] != df["opening_stock"] + df["incoming_stock"] - df["daily_consumption"]).any():
        errs.append("inventory: closing != opening + incoming - consumption")
    if df.duplicated(["date", "item_id"]).any():
        errs.append("inventory: duplicate date/item_id")
    if (df["supplier_lead_time_days"] <= 0).any():
        errs.append("inventory: lead time must be > 0")
    for item, g in df.groupby("item_id"):
        g = g.sort_values("date")
        dates = pd.to_datetime(g["date"])
        if len(g) != expected_days or not (dates.diff().dropna() == pd.Timedelta(days=1)).all():
            errs.append(f"inventory: {item} dates are not {expected_days} consecutive days")
        if not (g["opening_stock"].iloc[1:].to_numpy() == g["closing_stock"].iloc[:-1].to_numpy()).all():
            errs.append(f"inventory: {item} opening != previous closing")
    if require_stockout:
        if not (df["closing_stock"] == 0).any():
            errs.append("inventory: no stockout scenario present")
        if not (df["incoming_stock"] > 0).any():
            errs.append("inventory: no reorder deliveries present")
    return errs


def validate_all(data_dir="data"):
    data_dir = Path(data_dir)
    daily = pd.read_csv(data_dir / "hospital_daily_data.csv")
    results = {
        "hospital_daily_data.csv": validate_daily(daily, expected_days=365),
        "hospital_resources.csv": validate_resources(pd.read_csv(data_dir / "hospital_resources.csv"), daily),
        "staff_availability.csv": validate_staff(pd.read_csv(data_dir / "staff_availability.csv")),
        "medical_inventory.csv": validate_inventory(pd.read_csv(data_dir / "medical_inventory.csv")),
    }
    ok = True
    for name, errs in results.items():
        print(f"  [{'PASS' if not errs else 'FAIL'}] {name}")
        for e in errs:
            print(f"        - {e}")
        ok &= not errs
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if validate_all(sys.argv[1] if len(sys.argv) > 1 else "data") else 1)
