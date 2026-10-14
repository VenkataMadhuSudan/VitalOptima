"""Exact CSV schemas for the VitalOptima synthetic dataset (single source of truth)."""

DAILY_COLUMNS = [
    "date", "day_of_week", "admissions", "emergency_arrivals", "discharges",
    "icu_admissions", "elective_admissions", "general_beds_occupied",
    "icu_beds_occupied", "general_beds_total", "icu_beds_total",
    "staff_available", "surgeries_scheduled", "average_length_of_stay_days",
]
DAILY_INT_COLUMNS = [c for c in DAILY_COLUMNS
                     if c not in ("date", "day_of_week", "average_length_of_stay_days")]

RESOURCES_COLUMNS = [
    "resource_id", "resource_type", "department", "total_capacity",
    "unavailable_capacity", "occupied_capacity", "available_capacity",
    "staffed_capacity", "forecast_demand",
]
RESOURCES_INT_COLUMNS = RESOURCES_COLUMNS[3:]

STAFF_COLUMNS = [
    "date", "shift", "department", "staff_role", "available_count",
    "required_count", "maximum_permitted_working_hours",
    "minimum_rest_hours_between_shifts",
]
STAFF_INT_COLUMNS = STAFF_COLUMNS[4:]

INVENTORY_COLUMNS = [
    "date", "item_id", "item_name", "item_category", "opening_stock",
    "daily_consumption", "incoming_stock", "closing_stock",
    "reorder_threshold", "supplier_lead_time_days",
]
INVENTORY_INT_COLUMNS = INVENTORY_COLUMNS[4:]
