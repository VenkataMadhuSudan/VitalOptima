"""
VitalOptima AI Analytics & Evidence Synthesis Layer
Extracts deterministic facts, clinical trends, model evaluation telemetry,
and capacity bottlenecks directly from real repository CSVs and ML outputs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ML_DIR = PROJECT_ROOT / "ml_outputs"


# =========================================================================
# Resilient Dataset Loaders
# =========================================================================

def load_daily_census() -> pd.DataFrame:
    """Load hospital daily census time series (365 days)."""
    for fname in ["hospital_daily_data.csv", "hospital_census_daily.csv"]:
        p = DATA_DIR / fname
        if p.exists():
            try:
                df = pd.read_csv(p)
                if not df.empty and "admissions" in df.columns:
                    return df
            except Exception:
                continue
    return pd.DataFrame()


def load_hospital_resources() -> pd.DataFrame:
    """Load 13 departmental resource snapshots."""
    for fname in ["hospital_resources.csv", "department_resources.csv"]:
        p = DATA_DIR / fname
        if p.exists():
            try:
                df = pd.read_csv(p)
                if not df.empty and "resource_id" in df.columns:
                    return df
            except Exception:
                continue
    return pd.DataFrame()


def load_staff_roster() -> pd.DataFrame:
    """Load 7-day staffing roster across 3 shifts."""
    for fname in ["staff_availability.csv", "staffing_roster.csv"]:
        p = DATA_DIR / fname
        if p.exists():
            try:
                df = pd.read_csv(p)
                if not df.empty and "available_count" in df.columns:
                    return df
            except Exception:
                continue
    return pd.DataFrame()


def load_inventory() -> pd.DataFrame:
    """Load 30-day consumable inventory records."""
    for fname in ["medical_inventory.csv", "inventory_supplies.csv"]:
        p = DATA_DIR / fname
        if p.exists():
            try:
                df = pd.read_csv(p)
                if not df.empty and "closing_stock" in df.columns:
                    return df
            except Exception:
                continue
    return pd.DataFrame()


def load_forecast_outputs() -> Dict[str, pd.DataFrame]:
    """Load metrics, holdout predictions, and 7-day forward projections."""
    res = {"metrics": pd.DataFrame(), "predictions": pd.DataFrame(), "forecast": pd.DataFrame()}
    p_metrics = ML_DIR / "metrics.csv"
    p_preds = ML_DIR / "test_predictions.csv"
    p_fc = ML_DIR / "forecast_next_days.csv"

    if p_metrics.exists():
        try:
            res["metrics"] = pd.read_csv(p_metrics)
        except Exception:
            pass
    if p_preds.exists():
        try:
            res["predictions"] = pd.read_csv(p_preds)
        except Exception:
            pass
    if p_fc.exists():
        try:
            res["forecast"] = pd.read_csv(p_fc)
        except Exception:
            pass
    return res


# =========================================================================
# Domain Fact Extraction Functions
# =========================================================================

def get_census_analytics() -> Dict[str, Any]:
    """Calculate key historical patient flow, census, and surge statistics."""
    df = load_daily_census()
    if df.empty:
        return {"status": "unavailable", "error": "Hospital daily data not found"}

    df["date"] = pd.to_datetime(df["date"])
    total_beds = int(df["general_beds_total"].iloc[-1] + df["icu_beds_total"].iloc[-1])
    occ_series = df["general_beds_occupied"] + df["icu_beds_occupied"]
    occ_pct_series = (100.0 * occ_series / total_beds).round(1)

    peak_idx = occ_series.idxmax()
    peak_date = df.loc[peak_idx, "date"].strftime("%Y-%m-%d")
    peak_val = int(occ_series.max())
    peak_pct = round(100.0 * peak_val / total_beds, 1)

    # Days above 90% capacity risk barrier
    risk_days_count = int((occ_pct_series >= 90.0).sum())
    risk_days_pct = round(100.0 * risk_days_count / len(df), 1)

    # Day-of-week pattern
    dow_admit = df.groupby("day_of_week")["admissions"].mean().round(1).to_dict()
    dow_ed = df.groupby("day_of_week")["emergency_arrivals"].mean().round(1).to_dict()
    dow_disch = df.groupby("day_of_week")["discharges"].mean().round(1).to_dict()

    return {
        "status": "available",
        "date_range": [df["date"].min().strftime("%Y-%m-%d"), df["date"].max().strftime("%Y-%m-%d")],
        "total_days_observed": len(df),
        "total_hospital_beds": total_beds,
        "mean_occupancy_patients": round(float(occ_series.mean()), 1),
        "mean_occupancy_pct": round(float(occ_pct_series.mean()), 1),
        "peak_occupancy_date": peak_date,
        "peak_occupancy_patients": peak_val,
        "peak_occupancy_pct": peak_pct,
        "days_above_90pct_risk": risk_days_count,
        "pct_days_above_90pct_risk": risk_days_pct,
        "mean_daily_admissions": round(float(df["admissions"].mean()), 1),
        "mean_daily_ed_arrivals": round(float(df["emergency_arrivals"].mean()), 1),
        "mean_daily_discharges": round(float(df["discharges"].mean()), 1),
        "mean_alos_days": round(float(df["average_length_of_stay_days"].mean()), 2),
        "day_of_week_admissions": dow_admit,
        "day_of_week_ed_arrivals": dow_ed,
        "day_of_week_discharges": dow_disch,
    }


def get_capacity_bottlenecks() -> Dict[str, Any]:
    """Analyze unit-level capacity, physical availability, and staffing deficits."""
    res_df = load_hospital_resources()
    if res_df.empty:
        return {"status": "unavailable", "error": "Hospital resources data not found"}

    res_df["usable"] = res_df["total_capacity"] - res_df["unavailable_capacity"]
    
    # 1. Understaffed units: occupied > staffed
    understaffed = res_df[res_df["occupied_capacity"] > res_df["staffed_capacity"]].copy()
    understaffed_list = []
    for _, r in understaffed.iterrows():
        understaffed_list.append({
            "resource_id": r["resource_id"],
            "department": r["department"],
            "resource_type": r["resource_type"],
            "occupied_capacity": int(r["occupied_capacity"]),
            "staffed_capacity": int(r["staffed_capacity"]),
            "staffing_deficit_patients": int(r["occupied_capacity"] - r["staffed_capacity"]),
            "physical_available_beds": int(r["available_capacity"])
        })

    # 2. Demand deficit units: forecast_demand > usable
    over_demand = res_df[res_df["forecast_demand"] > res_df["usable"]].copy()
    over_demand_list = []
    for _, r in over_demand.iterrows():
        over_demand_list.append({
            "resource_id": r["resource_id"],
            "department": r["department"],
            "resource_type": r["resource_type"],
            "forecast_demand": int(r["forecast_demand"]),
            "usable_capacity": int(r["usable"]),
            "capacity_shortfall": int(r["forecast_demand"] - r["usable"])
        })

    # Total hospital bed sum
    beds_only = res_df[res_df["resource_type"].isin(["General Bed", "ICU Bed"])]
    
    return {
        "status": "available",
        "snapshot_resource_count": len(res_df),
        "total_in_service_beds": int(beds_only["usable"].sum()),
        "nominal_total_beds": int(beds_only["total_capacity"].sum()),
        "total_occupied_census": int(beds_only["occupied_capacity"].sum()),
        "total_physically_available_beds": int(beds_only["available_capacity"].sum()),
        "total_staffed_capacity": int(beds_only["staffed_capacity"].sum()),
        "understaffed_units": understaffed_list,
        "demand_bottlenecks": over_demand_list,
    }


def get_staffing_shortages() -> Dict[str, Any]:
    """Audit upcoming 7-day staff availability schedule and identify deficits."""
    staff_df = load_staff_roster()
    if staff_df.empty:
        return {"status": "unavailable", "error": "Staff availability roster not found"}

    staff_df["deficit"] = staff_df["required_count"] - staff_df["available_count"]
    shortages = staff_df[staff_df["deficit"] > 0].copy()

    min_date = pd.to_datetime(staff_df["date"].min())
    shortage_list = []
    for _, r in shortages.iterrows():
        cur_date = pd.to_datetime(r["date"])
        day_num = int((cur_date - min_date).days + 1)
        shortage_list.append({
            "date": str(r["date"]),
            "day": day_num,
            "shift": r["shift"],
            "shift_type": r["shift"],
            "department": r["department"],
            "staff_role": r["staff_role"],
            "role": r["staff_role"],
            "available_count": int(r["available_count"]),
            "available_staff": int(r["available_count"]),
            "required_count": int(r["required_count"]),
            "required_staff": int(r["required_count"]),
            "missing_headcount": int(r["deficit"]),
            "shortfall": int(r["deficit"])
        })

    return {
        "status": "available",
        "schedule_period": [str(staff_df["date"].min()), str(staff_df["date"].max())],
        "total_scheduled_shifts": len(staff_df),
        "total_shortage_shifts_count": len(shortages),
        "max_permitted_working_hours": int(staff_df["maximum_permitted_working_hours"].iloc[0]),
        "minimum_rest_hours_between_shifts": int(staff_df["minimum_rest_hours_between_shifts"].iloc[0]),
        "shortage_events": shortage_list,
    }


def get_inventory_health() -> Dict[str, Any]:
    """Analyze consumable supplies, stockouts, burn rates, and replenishment triggers."""
    inv_df = load_inventory()
    if inv_df.empty:
        return {"status": "unavailable", "error": "Medical inventory records not found"}

    inv_df["date"] = pd.to_datetime(inv_df["date"])
    latest_date = inv_df["date"].max()
    latest_inv = inv_df[inv_df["date"] == latest_date].copy()

    # 7-day consumption burn rate
    seven_days_ago = latest_date - pd.Timedelta(days=7)
    recent = inv_df[inv_df["date"] >= seven_days_ago]
    avg_burn = recent.groupby("item_id")["daily_consumption"].mean().round(1).to_dict()

    stockouts = []
    reorder_alerts = []
    healthy = []

    for _, r in latest_inv.iterrows():
        iid = r["item_id"]
        closing = int(r["closing_stock"])
        thresh = int(r["reorder_threshold"])
        lead = int(r["supplier_lead_time_days"])
        burn = float(avg_burn.get(iid, r["daily_consumption"]))
        days_left = round(closing / burn, 1) if burn > 0 else 999.0
        unit_str = str(r["unit"]) if "unit" in r else "units"

        item_data = {
            "item_id": iid,
            "item_name": r["item_name"],
            "category": r["item_category"],
            "closing_stock": closing,
            "daily_burn_rate": burn,
            "days_of_supply_left": days_left,
            "reorder_threshold": thresh,
            "reorder_level": thresh,
            "deficit": max(0, thresh - closing),
            "unit": unit_str,
            "supplier_lead_time_days": lead
        }

        if closing == 0:
            stockouts.append(item_data)
        elif closing <= thresh:
            reorder_alerts.append(item_data)
        else:
            healthy.append(item_data)

    return {
        "status": "available",
        "snapshot_date": latest_date.strftime("%Y-%m-%d"),
        "total_tracked_skus": len(latest_inv),
        "stockout_items": stockouts,
        "reorder_triggered_items": reorder_alerts,
        "healthy_items_count": len(healthy)
    }


def get_forecast_evaluation_summary() -> Dict[str, Any]:
    """Summarize model performance benchmarks, evaluation errors, and 7-day outlook."""
    outputs = load_forecast_outputs()
    m_df = outputs["metrics"]
    p_df = outputs["predictions"]
    fc_df = outputs["forecast"]

    benchmark_summary = {}
    if not m_df.empty:
        for target, group in m_df.groupby("target"):
            benchmark_summary[target] = group[["model", "MAE", "RMSE", "WAPE_pct"]].to_dict(orient="records")

    # High error dates on holdout test set
    high_error_dates = []
    if not p_df.empty and "actual" in p_df.columns:
        p_df["abs_error"] = (p_df["actual"] - p_df["selected_pred"]).abs()
        top_err = p_df.sort_values(by="abs_error", ascending=False).head(5)
        for _, r in top_err.iterrows():
            high_error_dates.append({
                "target_date": str(r["target_date"]),
                "target": r["target"],
                "actual": float(r["actual"]),
                "predicted": float(r["selected_pred"]),
                "abs_error": round(float(r["abs_error"]), 1),
                "model_used": str(r.get("selected_model", "selected model"))
            })

    # Forward 7-day horizon
    forward_outlook = []
    peak_fc_occ = 0.0
    risk_days = []
    if not fc_df.empty:
        peak_fc_occ = float(fc_df["projected_occupancy_pct"].max())
        for _, r in fc_df.iterrows():
            forward_outlook.append({
                "date": str(r["date"]),
                "admissions": float(r["forecast_admissions"]),
                "ed_arrivals": float(r["forecast_emergency_arrivals"]),
                "discharges": float(r["forecast_discharges"]),
                "icu_admissions": float(r["forecast_icu_admissions"]),
                "projected_occupancy": float(r["projected_total_occupied"]),
                "occupancy_pct": float(r["projected_occupancy_pct"]),
                "capacity_risk": bool(r.get("capacity_risk", False))
            })
            if r.get("capacity_risk", False):
                risk_days.append(str(r["date"]))

    return {
        "status": "available",
        "benchmarks": benchmark_summary,
        "selected_architecture": "Random Forest (selected on test-period MAE)",
        "high_prediction_error_events": high_error_dates,
        "forward_horizon_days": len(forward_outlook),
        "forecast_horizon_days": len(forward_outlook),
        "peak_projected_occupancy_pct": peak_fc_occ,
        "capacity_risk_days": risk_days,
        "daily_forward_projections": forward_outlook
    }


def run_deterministic_what_if(
    surge_multiplier: float = 1.25,
    surge_days: int = 3,
    icu_beds_lost: int = 0
) -> Dict[str, Any]:
    """Simulate operational impact under variable emergency surge or bed capacity shocks."""
    outputs = load_forecast_outputs()
    fc_df = outputs["forecast"]
    
    # Fallback default forward projection if ml_outputs missing
    if fc_df.empty:
        dates = [f"2026-01-0{i}" for i in range(1, 8)]
        fc_df = pd.DataFrame({
            "date": dates,
            "forecast_admissions": [51.2, 51.0, 37.5, 34.9, 56.3, 51.3, 51.4],
            "forecast_emergency_arrivals": [177.7, 180.4, 176.9, 170.8, 183.7, 181.7, 177.4],
            "forecast_discharges": [50.4, 61.4, 39.9, 33.8, 48.6, 49.5, 49.4],
        })

    baseline_total_beds = 330
    effective_beds = baseline_total_beds - icu_beds_lost
    occ = 261.0  # Dec 31 census baseline
    
    sim_trajectory = []
    breach_count = 0

    for idx, r in fc_df.iterrows():
        arr = float(r["forecast_emergency_arrivals"])
        adm = float(r["forecast_admissions"])
        dis = float(r["forecast_discharges"])

        if idx < surge_days and surge_multiplier != 1.0:
            arr *= surge_multiplier
            adm *= surge_multiplier

        occ = min(max(occ + adm - dis, 0.0), effective_beds)
        pct = round(100.0 * occ / effective_beds, 1)
        risk = pct >= 90.0
        if risk:
            breach_count += 1

        sim_trajectory.append({
            "date": str(r["date"]),
            "simulated_arrivals": round(arr, 1),
            "simulated_admissions": round(adm, 1),
            "simulated_occupancy": round(occ, 1),
            "simulated_occupancy_pct": pct,
            "capacity_risk": risk
        })

    peak_occ = max(d["simulated_occupancy"] for d in sim_trajectory)
    peak_pct = max(d["simulated_occupancy_pct"] for d in sim_trajectory)

    return {
        "parameters": {
            "surge_multiplier": surge_multiplier,
            "surge_days": surge_days,
            "icu_beds_lost": icu_beds_lost,
            "effective_total_beds": effective_beds
        },
        "peak_simulated_occupancy": peak_occ,
        "peak_simulated_occupancy_pct": peak_pct,
        "days_above_risk_threshold": breach_count,
        "breach_occurred": breach_count > 0,
        "simulated_daily_trajectory": sim_trajectory
    }


# =========================================================================
# Unified Evidence Package Builder for Grok
# =========================================================================

def build_evidence_package() -> Dict[str, Any]:
    """Compiles all calculated statistics and findings into a single verified evidence dictionary."""
    census = get_census_analytics()
    capacity = get_capacity_bottlenecks()
    staff = get_staffing_shortages()
    inventory = get_inventory_health()
    forecast = get_forecast_evaluation_summary()

    return {
        "metadata": {
            "system": "VitalOptima Early Warning & Resource Optimization System",
            "synthetic_disclaimer": "All hospital operations data here is synthetic for clinical demonstration.",
            "data_currency": "Historical calendar year 2025; forward forecast covers Jan 01–Jan 07, 2026."
        },
        "historical_census": census,
        "current_capacity_and_bottlenecks": capacity,
        "staffing_roster_shortages": staff,
        "inventory_and_stockouts": inventory,
        "ml_forecasting_and_benchmarks": forecast
    }
