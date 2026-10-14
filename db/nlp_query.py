"""
VitalOptima Natural Language Query (NLQ) & Conversational Assistant
Translates human English inquiries into optimized SQL queries against hospital database records.
Provides conversational answers and interactive tabular data for hospital administrators.
"""
import re
import pandas as pd
from datetime import datetime
from db.postgres import run_custom_query, fetch_table_df, test_connection

SAMPLE_PROMPT_CHIPS = [
    "🚨 Which medical supplies are running low or out of stock?",
    "📈 Show the top 5 busiest emergency arrival surge days",
    "🛏️ Which hospital departments currently have highest occupancy?",
    "👥 Show staff shortages and nurse deficits for night shifts",
    "⚖️ What administrative decisions were recently accepted or modified?",
    "⚠️ List all active high severity hospital alerts",
    "🎛️ Show saved what-if disaster simulation scenarios",
    "📅 What was the average patient length of stay across census history?"
]

def process_natural_language_query(user_text: str):
    """
    Parses natural language English questions and executes appropriate SQL queries.
    Returns:
        dict: {
            "success": bool,
            "answer_summary": str,
            "sql_query": str,
            "table_name": str,
            "df": pd.DataFrame,
            "insights": list of str,
            "error": str
        }
    """
    query_clean = user_text.strip().lower()
    if not query_clean:
        return {
            "success": False,
            "error": "Please enter a question to search hospital records."
        }

    sql = ""
    table_name = ""
    summary = ""
    insights = []

    # -------------------------------------------------------------
    # 1. INVENTORY & MEDICAL CONSUMABLES INTENTS
    # -------------------------------------------------------------
    if any(k in query_clean for k in ["inventory", "supplies", "stock", "consumable", "reorder", "n95", "mask", "glove", "ppe", "shortage of supply"]):
        table_name = "inventory_supplies"
        if any(k in query_clean for k in ["low", "out of stock", "shortage", "below", "reorder", "critical", "exhausted"]):
            sql = """SELECT 
    item_id, 
    item_name, 
    item_category, 
    closing_stock, 
    reorder_threshold, 
    supplier_lead_time_days,
    CASE 
        WHEN closing_stock = 0 THEN '🔴 Out of Stock'
        WHEN closing_stock <= reorder_threshold THEN '⚠️ Reorder Triggered'
        ELSE '✅ Stock Adequate'
    END AS restock_status
FROM inventory_supplies
WHERE closing_stock <= reorder_threshold
ORDER BY closing_stock ASC;"""
            summary = "Found critical consumable supplies that are currently at or below their safety reorder threshold."
        elif "daily consumption" in query_clean or "burn" in query_clean or "highest usage" in query_clean:
            sql = """SELECT 
    item_id, 
    item_name, 
    item_category, 
    AVG(daily_consumption)::NUMERIC(10,1) AS avg_daily_burn,
    MAX(daily_consumption) AS peak_daily_burn,
    supplier_lead_time_days
FROM inventory_supplies
GROUP BY item_id, item_name, item_category, supplier_lead_time_days
ORDER BY avg_daily_burn DESC;"""
            summary = "Here is the average daily consumable consumption (burn rate) ranked from highest to lowest."
        else:
            limit = _extract_limit(query_clean, default=15)
            sql = f"""SELECT 
    date, 
    item_id, 
    item_name, 
    item_category, 
    closing_stock, 
    reorder_threshold, 
    daily_consumption
FROM inventory_supplies
ORDER BY date DESC, item_name ASC
LIMIT {limit};"""
            summary = f"Displaying current clinical consumable inventory telemetry (latest {limit} records)."

    # -------------------------------------------------------------
    # 2. HOSPITAL CENSUS, ARRIVALS & INPATIENT INTENTS
    # -------------------------------------------------------------
    elif any(k in query_clean for k in ["arrival", "arrivals", "census", "admission", "admissions", "discharge", "discharges", "busiest", "emergency surge", "length of stay", "los"]):
        table_name = "hospital_census_daily"
        
        # Sub-intent: Top / Busiest surge days
        if any(k in query_clean for k in ["busiest", "highest", "top", "surge", "peak", "max"]):
            limit = _extract_limit(query_clean, default=5)
            sql = f"""SELECT 
    date, 
    day_of_week, 
    emergency_arrivals, 
    admissions, 
    icu_admissions, 
    general_beds_occupied, 
    average_length_of_stay_days
FROM hospital_census_daily
ORDER BY emergency_arrivals DESC
LIMIT {limit};"""
            summary = f"Identified the top {limit} peak emergency arrival days from the 365-day historical census."
        
        # Sub-intent: Length of stay
        elif any(k in query_clean for k in ["length of stay", "los", "stay"]):
            sql = """SELECT 
    ROUND(AVG(average_length_of_stay_days)::NUMERIC, 2) AS hospital_avg_length_of_stay_days,
    ROUND(MIN(average_length_of_stay_days)::NUMERIC, 2) AS min_length_of_stay_days,
    ROUND(MAX(average_length_of_stay_days)::NUMERIC, 2) AS max_length_of_stay_days,
    ROUND(AVG(general_beds_occupied)::NUMERIC, 1) AS avg_occupied_beds,
    ROUND(AVG(emergency_arrivals)::NUMERIC, 1) AS avg_daily_emergency_arrivals
FROM hospital_census_daily;"""
            summary = "Summary statistics for patient inpatient length of stay (LOS) and hospital throughput."
            
        # Sub-intent: Filter by specific month or weekend
        elif "weekend" in query_clean or "sunday" in query_clean or "saturday" in query_clean:
            sql = """SELECT 
    date, 
    day_of_week, 
    emergency_arrivals, 
    admissions, 
    discharges,
    general_beds_occupied
FROM hospital_census_daily
WHERE day_of_week IN ('Saturday', 'Sunday')
ORDER BY emergency_arrivals DESC
LIMIT 15;"""
            summary = "Filtered historical census records for weekend operations (Saturday & Sunday arrivals)."

        else:
            limit = _extract_limit(query_clean, default=10)
            sql = f"""SELECT 
    date, 
    day_of_week, 
    emergency_arrivals, 
    admissions, 
    icu_admissions, 
    discharges, 
    general_beds_occupied, 
    surgeries_scheduled
FROM hospital_census_daily
ORDER BY date DESC
LIMIT {limit};"""
            summary = f"Here are the most recent {limit} daily hospital census records."

    # -------------------------------------------------------------
    # 3. DEPARTMENT CAPACITY & BED OCCUPANCY INTENTS
    # -------------------------------------------------------------
    elif any(k in query_clean for k in ["department", "departments", "bed", "beds", "ward", "wards", "icu bed", "operating room", "or capacity", "occupancy", "utilization"]):
        table_name = "department_resources"
        
        if any(k in query_clean for k in ["icu", "intensive care"]):
            sql = """SELECT 
    resource_id, 
    department, 
    resource_type, 
    total_capacity, 
    occupied_capacity, 
    available_capacity, 
    ROUND((occupied_capacity::NUMERIC / NULLIF(total_capacity, 0)) * 100, 1) AS occupancy_pct
FROM department_resources
WHERE department ILIKE '%ICU%' OR resource_type ILIKE '%ICU%';"""
            summary = "Current ICU critical care unit bed capacity, occupancy, and available clean buffers."
            
        elif any(k in query_clean for k in ["high", "highest", "most occupied", "critical", "full"]):
            sql = """SELECT 
    department, 
    resource_type, 
    total_capacity, 
    occupied_capacity, 
    available_capacity, 
    unavailable_capacity,
    ROUND((occupied_capacity::NUMERIC / NULLIF(total_capacity, 0)) * 100, 1) AS occupancy_pct
FROM department_resources
ORDER BY occupancy_pct DESC;"""
            summary = "Departmental resource allocations ranked by highest percentage bed occupancy."
            
        else:
            sql = """SELECT 
    department, 
    resource_type, 
    total_capacity, 
    occupied_capacity, 
    available_capacity, 
    staffed_capacity,
    forecast_demand
FROM department_resources
ORDER BY department ASC, resource_type ASC;"""
            summary = "Complete hospital department capacity matrix including staffed beds and baseline demand."

    # -------------------------------------------------------------
    # 4. STAFFING, ROSTERS, NURSES & SHIFTS INTENTS
    # -------------------------------------------------------------
    elif any(k in query_clean for k in ["staff", "staffing", "nurse", "nurses", "doctor", "doctors", "physician", "shift", "roster", "shortage"]):
        table_name = "staffing_roster"
        
        if any(k in query_clean for k in ["night", "evening", "morning"]):
            shift = "Night" if "night" in query_clean else ("Evening" if "evening" in query_clean else "Morning")
            sql = f"""SELECT 
    date, 
    shift, 
    department, 
    staff_role, 
    available_count, 
    required_count, 
    (required_count - available_count) AS shortage
FROM staffing_roster
WHERE shift ILIKE '{shift}'
ORDER BY shortage DESC, date DESC
LIMIT 15;"""
            summary = f"Staffing allocations and coverage deficits for the **{shift} Shift**."
            
        elif any(k in query_clean for k in ["shortage", "deficit", "lacking", "gap", "insufficient"]):
            sql = """SELECT 
    date, 
    shift, 
    department, 
    staff_role, 
    available_count, 
    required_count, 
    (required_count - available_count) AS shortage
FROM staffing_roster
WHERE available_count < required_count
ORDER BY shortage DESC
LIMIT 15;"""
            summary = "Identified all shift allocations experiencing staffing deficits (available < required staff)."
            
        else:
            limit = _extract_limit(query_clean, default=15)
            sql = f"""SELECT 
    date, 
    shift, 
    department, 
    staff_role, 
    available_count, 
    required_count
FROM staffing_roster
ORDER BY date DESC, shift ASC
LIMIT {limit};"""
            summary = f"Hospital clinical staffing schedules and nurse-to-patient coverage (showing {limit} records)."

    # -------------------------------------------------------------
    # 5. DECISION LOG & ADMINISTRATIVE AUDIT INTENTS
    # -------------------------------------------------------------
    elif any(k in query_clean for k in ["decision", "decisions", "admin", "approval", "approved", "accepted", "modified", "rejected", "audit", "rationale"]):
        table_name = "decision_log"
        
        if "rejected" in query_clean or "override" in query_clean:
            sql = """SELECT 
    id, 
    timestamp, 
    category, 
    decision, 
    recommendation, 
    administrator, 
    rationale
FROM decision_log
WHERE decision ILIKE 'Rejected'
ORDER BY id DESC;"""
            summary = "Auditable records of all clinical overrides and rejected optimization proposals."
        elif "modified" in query_clean:
            sql = """SELECT 
    id, 
    timestamp, 
    category, 
    decision, 
    recommendation, 
    modified_details, 
    administrator, 
    rationale
FROM decision_log
WHERE decision ILIKE 'Modified'
ORDER BY id DESC;"""
            summary = "Administrative decisions where the recommendation was modified by a supervising clinician."
        else:
            sql = """SELECT 
    id, 
    timestamp, 
    category, 
    decision, 
    recommendation, 
    modified_details, 
    administrator, 
    rationale
FROM decision_log
ORDER BY id DESC
LIMIT 10;"""
            summary = "Recent administrative optimization decision audit logs recorded in PostgreSQL."

    # -------------------------------------------------------------
    # 6. SYSTEM ALERTS & SURGE WARNINGS INTENTS
    # -------------------------------------------------------------
    elif any(k in query_clean for k in ["alert", "alerts", "warning", "warnings", "alarm", "severity"]):
        table_name = "system_alerts"
        sql = """SELECT 
    id, 
    title, 
    category, 
    severity, 
    timestamp, 
    CASE WHEN acknowledged = 1 THEN '✅ Acknowledged' ELSE '🚨 Active Action Needed' END AS status
FROM system_alerts
ORDER BY id DESC;"""
        summary = "Active hospital system alerts, bed threshold alarms, and consumable shortage notices."

    # -------------------------------------------------------------
    # 7. WHAT-IF SCENARIOS & STRESS TESTS INTENTS
    # -------------------------------------------------------------
    elif any(k in query_clean for k in ["scenario", "scenarios", "simulation", "simulator", "stress test", "disaster"]):
        table_name = "scenarios"
        sql = """SELECT 
    id, 
    timestamp, 
    name, 
    surge_pct, 
    icu_reduction, 
    staff_loss, 
    results_json
FROM scenarios
ORDER BY id DESC
LIMIT 10;"""
        summary = "Previously executed What-if emergency stress tests saved in the PostgreSQL database."

    # -------------------------------------------------------------
    # 8. HOURLY DEMAND FORECAST INTENTS
    # -------------------------------------------------------------
    elif any(k in query_clean for k in ["hourly", "hour", "forecast", "prediction", "upcoming 24"]):
        table_name = "demand_forecast_hourly"
        sql = """SELECT 
    hour, 
    predicted_demand, 
    historical_demand, 
    emergency_capacity, 
    available_capacity,
    CASE 
        WHEN predicted_demand > emergency_capacity THEN '🔴 Over Capacity Surge'
        WHEN predicted_demand > emergency_capacity * 0.85 THEN '⚠️ High Volume'
        ELSE '✅ Normal Flow'
    END AS surge_risk
FROM demand_forecast_hourly
ORDER BY hour_index ASC;"""
        summary = "24-hour predictive hourly patient demand forecast with capacity ceiling markers."

    # -------------------------------------------------------------
    # 9. GENERAL / FUZZY KEYWORD SEARCH FALLBACK
    # -------------------------------------------------------------
    else:
        # Default smart search across department resources and census
        tokens = [t for t in re.findall(r'\b[a-zA-Z]{3,}\b', query_clean) if t not in ["show", "give", "tell", "what", "which", "when", "with", "from", "data", "records", "please"]]
        if tokens:
            target_kw = tokens[0]
            table_name = "department_resources"
            sql = f"""SELECT 
    resource_id, 
    department, 
    resource_type, 
    total_capacity, 
    occupied_capacity, 
    available_capacity
FROM department_resources
WHERE department ILIKE '%{target_kw}%' OR resource_type ILIKE '%{target_kw}%'
LIMIT 10;"""
            summary = f"Matching hospital department records found for keyword **'{target_kw}'**."
        else:
            table_name = "hospital_census_daily"
            sql = """SELECT 
    date, 
    day_of_week, 
    emergency_arrivals, 
    admissions, 
    discharges, 
    general_beds_occupied, 
    icu_beds_occupied
FROM hospital_census_daily
ORDER BY date DESC
LIMIT 10;"""
            summary = "Here are the most recent 10 days of hospital operational records."

    # Execute generated SQL query
    try:
        df = run_custom_query(sql)
        row_count = len(df)
        
        # Build quick automatic executive insights based on the returned data
        if not df.empty:
            if "occupancy_pct" in df.columns:
                max_row = df.loc[df["occupancy_pct"].astype(float).idxmax()]
                dept = max_row.get("department", "Unknown")
                rate = max_row.get("occupancy_pct", 0)
                insights.append(f"Highest utilization: **{dept}** at **{rate}%** occupancy.")
            elif "emergency_arrivals" in df.columns:
                max_arr = df["emergency_arrivals"].max()
                busiest_date = df.loc[df["emergency_arrivals"].idxmax()]["date"]
                insights.append(f"Peak recorded arrivals: **{max_arr} patients** on **{busiest_date}**.")
            elif "closing_stock" in df.columns:
                stockouts = (df["closing_stock"] == 0).sum()
                if stockouts > 0:
                    insights.append(f"Critical stockouts detected: **{stockouts} item(s)** at 0 inventory.")
            elif "shortage" in df.columns:
                total_def = df["shortage"].sum()
                insights.append(f"Total shift staffing deficit: **{int(total_def)} personnel** across selected slots.")
        
        return {
            "success": True,
            "answer_summary": f"{summary} ({row_count} records retrieved)",
            "sql_query": sql,
            "table_name": table_name,
            "df": df,
            "insights": insights,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "answer_summary": f"Could not execute query: {e}",
            "sql_query": sql,
            "table_name": table_name,
            "df": pd.DataFrame(),
            "insights": [],
            "error": str(e)
        }

def _extract_limit(text: str, default: int = 10) -> int:
    """Extract integer limit from phrases like 'top 5', 'first 20', 'limit 8'."""
    m = re.search(r'\b(?:top|first|limit|latest)\s+(\d+)\b', text)
    if m:
        try:
            return max(1, min(100, int(m.group(1))))
        except Exception:
            pass
    return default
