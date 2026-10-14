#!/usr/bin/env python3
"""
Predefined VitalOptima test scenarios. Reads ./data and writes modified copies of
the CSVs to ./data/scenarios/<name>/ plus scenario_manifest.json.
Baseline files are never overwritten.   Run:  python scenarios.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from validate_dataset import validate_inventory, validate_resources, validate_staff

DATA = Path("data")
FILES = {"daily": "hospital_daily_data.csv", "resources": "hospital_resources.csv",
         "staff": "staff_availability.csv", "inventory": "medical_inventory.csv"}


def load(data_dir=DATA):
    return {k: pd.read_csv(Path(data_dir) / f) for k, f in FILES.items()}


def _recompute_available(res):
    res["available_capacity"] = res["total_capacity"] - res["unavailable_capacity"] - res["occupied_capacity"]
    return res


# 1 ---------------------------------------------------------------- surge
def emergency_surge(dfs, ed_x=1.5, bed_x=1.25, icu_x=1.35):
    res = dfs["resources"]
    mult = {"ED Treatment Space": ed_x, "General Bed": bed_x, "ICU Bed": icu_x}
    for rtype, m in mult.items():
        mask = res["resource_type"] == rtype
        res.loc[mask, "forecast_demand"] = (res.loc[mask, "forecast_demand"] * m).apply(math.ceil)
    return dfs, {
        "description": "5-day emergency surge: demand inputs scaled up for ED, general beds, ICU.",
        "parameters": {"ed_multiplier": ed_x, "general_bed_multiplier": bed_x, "icu_multiplier": icu_x},
        "forecasting_overlay": "python ml_forecast.py --surge-multiplier 1.5 --surge-days 5",
    }


# 2 ------------------------------------------------------ ICU capacity loss
def icu_capacity_loss(dfs, loss_by_id=None):
    loss_by_id = loss_by_id or {"ICU-MICU": 5, "ICU-SICU": 3}   # e.g. ward closed for repairs
    res, displaced = dfs["resources"], 0
    for rid, loss in loss_by_id.items():
        i = res.index[res.resource_id == rid][0]
        res.loc[i, "unavailable_capacity"] = min(res.loc[i, "unavailable_capacity"] + loss, res.loc[i, "total_capacity"])
        usable = res.loc[i, "total_capacity"] - res.loc[i, "unavailable_capacity"]
        displaced += max(0, res.loc[i, "occupied_capacity"] - usable)
        res.loc[i, "occupied_capacity"] = min(res.loc[i, "occupied_capacity"], usable)
        res.loc[i, "staffed_capacity"] = min(res.loc[i, "staffed_capacity"], usable)
    _recompute_available(res)
    return dfs, {
        "description": "Temporary loss of ICU beds. Patients that no longer fit are removed from "
                       "occupied_capacity and counted as displaced (optimizer must re-place them).",
        "parameters": {"beds_lost": loss_by_id}, "displaced_patients": int(displaced),
        "note": "forecast_demand is unchanged, so demand now exceeds in-service ICU beds.",
    }


# 3 --------------------------------------------------------- staffing shortage
def staffing_shortage(dfs, factor=0.75, day_indices=(1, 2, 3), bed_staff_factor=0.8):
    staff, res = dfs["staff"], dfs["resources"]
    dates = sorted(staff["date"].unique())
    hit = staff["date"].isin([dates[i] for i in day_indices]) & staff["staff_role"].isin(
        ["General Ward Nurse", "ICU Nurse", "Emergency Department Staff"])
    staff.loc[hit, "available_count"] = (staff.loc[hit, "required_count"] * factor).apply(math.floor)
    bed = res["resource_type"].isin(["General Bed", "ICU Bed"])
    usable = res["total_capacity"] - res["unavailable_capacity"]
    res.loc[bed, "staffed_capacity"] = (usable[bed] * bed_staff_factor).apply(math.floor)
    return dfs, {
        "description": "Nurse / ED staff availability cut on 3 consecutive days; staffed bed capacity reduced.",
        "parameters": {"availability_factor": factor, "affected_dates": [dates[i] for i in day_indices],
                       "bed_staffed_factor": bed_staff_factor},
    }


# 4 ------------------------------------------------------ inventory shortage
def inventory_shortage(dfs, items=("MSK-N95", "IV-NS500", "SYR-5ML"), start_day=20, demand_x=1.6):
    inv = dfs["inventory"].sort_values(["item_id", "date"]).reset_index(drop=True)
    for item in items:
        idx = inv.index[inv.item_id == item]
        stock = inv.loc[idx[0], "opening_stock"]
        for n, i in enumerate(idx):
            demand = inv.loc[i, "daily_consumption"]
            incoming = inv.loc[i, "incoming_stock"]
            if n >= start_day:                      # supplier disruption + demand spike
                demand, incoming = math.ceil(demand * demand_x), 0
            avail = stock + incoming
            used = min(demand, avail)
            inv.loc[i, ["opening_stock", "incoming_stock", "daily_consumption", "closing_stock"]] = \
                [stock, incoming, used, avail - used]
            stock = avail - used
    dfs["inventory"] = inv
    return dfs, {
        "description": "From day 21 deliveries stop and consumption rises 60% for three items.",
        "parameters": {"items": list(items), "start_day_index": start_day, "demand_multiplier": demand_x},
    }


SCENARIOS = {"emergency_surge": emergency_surge, "icu_capacity_loss": icu_capacity_loss,
             "staffing_shortage": staffing_shortage, "inventory_shortage": inventory_shortage}


def main():
    manifest = {}
    for name, fn in SCENARIOS.items():
        dfs, info = fn(load())
        errs = (validate_resources(dfs["resources"]) + validate_staff(dfs["staff"], require_shortage=False)
                + validate_inventory(dfs["inventory"], require_stockout=False))
        folder = DATA / "scenarios" / name
        folder.mkdir(parents=True, exist_ok=True)
        for k, f in FILES.items():
            dfs[k].to_csv(folder / f, index=False)
        info["validation_errors"] = errs
        manifest[name] = info
        print(f"[{'PASS' if not errs else 'FAIL'}] {name} -> {folder.resolve()}")
        for e in errs:
            print("   -", e)
    (DATA / "scenarios" / "scenario_manifest.json").write_text(json.dumps(manifest, indent=2, default=int))


if __name__ == "__main__":
    main()
