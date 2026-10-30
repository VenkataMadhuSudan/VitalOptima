"""
VitalOptima Safe Agentic Tool Registry
Exposes a bounded, allowlisted set of strictly read-only tools for Grok agentic execution.
No arbitrary code execution, shell commands, or database writes are permitted.
"""
from __future__ import annotations

import json
from typing import Dict, Any, Optional
from src.ai_analytics import (
    get_census_analytics,
    get_capacity_bottlenecks,
    get_staffing_shortages,
    get_inventory_health,
    get_forecast_evaluation_summary,
    run_deterministic_what_if,
)

# =========================================================================
# Read-Only Agent Tools
# =========================================================================

def get_historical_trends(metric: str = "occupancy", department: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve historical patient arrival patterns, peak periods, and day-of-week demand trends."""
    census = get_census_analytics()
    if census.get("status") != "available":
        return census

    result = {
        "date_range": census["date_range"],
        "mean_occupancy_pct": census["mean_occupancy_pct"],
        "peak_occupancy": {
            "date": census["peak_occupancy_date"],
            "patients": census["peak_occupancy_patients"],
            "occupancy_pct": census["peak_occupancy_pct"]
        },
        "days_above_90pct_risk_barrier": census["days_above_90pct_risk"],
        "day_of_week_ed_arrivals": census["day_of_week_ed_arrivals"],
        "day_of_week_admissions": census["day_of_week_admissions"],
        "mean_length_of_stay_days": census["mean_alos_days"]
    }
    return result


def get_forecast_summary(horizon_days: int = 7) -> Dict[str, Any]:
    """Retrieve the multi-day hospital demand forecast and projected bed census trajectory."""
    fc_info = get_forecast_evaluation_summary()
    if fc_info.get("status") != "available":
        return fc_info

    projections = fc_info["daily_forward_projections"][:min(horizon_days, 7)]
    return {
        "horizon_days": len(projections),
        "selected_model": fc_info["selected_architecture"],
        "peak_projected_occupancy_pct": fc_info["peak_projected_occupancy_pct"],
        "capacity_risk_days": fc_info["capacity_risk_days"],
        "projections": projections
    }


def get_forecast_evaluation(target: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve model evaluation metrics (MAE, RMSE, WAPE) and historical large-error events."""
    eval_info = get_forecast_evaluation_summary()
    benchmarks = eval_info.get("benchmarks", {})
    if target and target in benchmarks:
        benchmarks = {target: benchmarks[target]}

    return {
        "evaluated_targets": benchmarks,
        "selected_architecture": eval_info.get("selected_architecture"),
        "top_prediction_error_events": eval_info.get("high_prediction_error_events", [])
    }


def check_capacity_risks() -> Dict[str, Any]:
    """Check departmental bed shortages, understaffed wards, and physical bottlenecks."""
    cap = get_capacity_bottlenecks()
    if cap.get("status") != "available":
        return cap

    return {
        "total_in_service_beds": cap["total_in_service_beds"],
        "total_occupied_census": cap["total_occupied_census"],
        "immediately_available_beds": cap["total_physically_available_beds"],
        "understaffed_units": cap["understaffed_units"],
        "demand_bottlenecks": cap["demand_bottlenecks"]
    }


def check_staffing_shortages(department: Optional[str] = None) -> Dict[str, Any]:
    """Audit upcoming 7-day shift rosters for nurse, doctor, and technician deficits."""
    staff = get_staffing_shortages()
    if staff.get("status") != "available":
        return staff

    events = staff["shortage_events"]
    if department:
        events = [e for e in events if department.lower() in e["department"].lower()]

    return {
        "schedule_period": staff["schedule_period"],
        "total_shortfall_shifts": len(events),
        "shortage_events": events,
        "labor_policy": {
            "max_working_hours": staff["max_permitted_working_hours"],
            "min_rest_hours_between_shifts": staff["minimum_rest_hours_between_shifts"]
        }
    }


def check_inventory_alerts(only_stockouts: bool = False) -> Dict[str, Any]:
    """Inspect medical supplies for zero-stock stockouts, reorder triggers, and burn rates."""
    inv = get_inventory_health()
    if inv.get("status") != "available":
        return inv

    result = {
        "snapshot_date": inv["snapshot_date"],
        "critical_stockouts": inv["stockout_items"],
    }
    if not only_stockouts:
        result["reorder_triggered_items"] = inv["reorder_triggered_items"]
    return result


def run_demand_what_if(
    surge_multiplier: float = 1.25,
    surge_days: int = 3,
    icu_beds_lost: int = 0
) -> Dict[str, Any]:
    """Simulate hospital bed occupancy impact under hypothetical demand spikes or ICU bed losses."""
    # Strict parameter bounds
    surge_multiplier = max(0.5, min(float(surge_multiplier), 3.0))
    surge_days = max(1, min(int(surge_days), 7))
    icu_beds_lost = max(0, min(int(icu_beds_lost), 25))

    return run_deterministic_what_if(surge_multiplier, surge_days, icu_beds_lost)


# =========================================================================
# Tool Metadata for Grok Function Calling
# =========================================================================

TOOL_REGISTRY = {
    "get_historical_trends": get_historical_trends,
    "get_forecast_summary": get_forecast_summary,
    "get_forecast_evaluation": get_forecast_evaluation,
    "check_capacity_risks": check_capacity_risks,
    "check_staffing_shortages": check_staffing_shortages,
    "check_inventory_alerts": check_inventory_alerts,
    "run_demand_what_if": run_demand_what_if,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_historical_trends",
            "description": "Retrieve 365-day historical hospital arrival rhythms, peak census periods, and day-of-week trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["occupancy", "admissions", "arrivals"], "description": "Metric to analyze"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast_summary",
            "description": "Retrieve future 7-day multi-target forecast (admissions, ED arrivals, discharges, ICU demand, projected bed census).",
            "parameters": {
                "type": "object",
                "properties": {
                    "horizon_days": {"type": "integer", "description": "Number of forecast days (1-7)", "default": 7}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast_evaluation",
            "description": "Inspect out-of-sample hold-out model performance (MAE, RMSE, WAPE) comparing Random Forest and Ridge, plus top historical error dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Specific target variable to evaluate"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_capacity_risks",
            "description": "Inspect unit-level bed capacity, physical available beds, and active staffing bottlenecks across all 13 departments.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_staffing_shortages",
            "description": "Audit upcoming 7-day clinical staff schedules for nurse, doctor, and technician shift shortages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {"type": "string", "description": "Optional department filter (e.g. ICU, General Ward, Emergency Department)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_inventory_alerts",
            "description": "Audit clinical consumables and critical supplies for zero-stock stockouts, reorder thresholds, and burn rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "only_stockouts": {"type": "boolean", "description": "If true, returns only items with zero closing stock"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_demand_what_if",
            "description": "Run a deterministic forward simulation testing the impact of emergency demand surges or lost ICU beds on hospital capacity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "surge_multiplier": {"type": "number", "description": "Emergency arrivals multiplier (e.g. 1.25 for +25%)", "default": 1.25},
                    "surge_days": {"type": "integer", "description": "Number of days the surge lasts (1-7)", "default": 3},
                    "icu_beds_lost": {"type": "integer", "description": "Number of ICU beds offline", "default": 0}
                }
            }
        }
    }
]


def execute_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Safely executes an allowlisted read-only tool with argument validation and bounded output."""
    if name not in TOOL_REGISTRY:
        return {"error": f"Tool '{name}' is not in the allowlist of safe analytical tools."}

    if arguments is None or not isinstance(arguments, dict):
        arguments = {}

    try:
        import inspect
        fn = TOOL_REGISTRY[name]
        sig = inspect.signature(fn)
        # Filter arguments to strictly allowed parameters to prevent unexpected keyword errors
        valid_args = {k: v for k, v in arguments.items() if k in sig.parameters}
        return fn(**valid_args)
    except Exception as exc:
        return {"error": f"Tool execution failed for '{name}': {str(exc)}"}
