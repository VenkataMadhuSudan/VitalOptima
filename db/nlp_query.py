"""
VitalOptima Advanced Natural Language Query (NLQ) & Conversational Assistant
Trained Domain-Specific NL2SQL Engine for Hospital Operations, Census, Staffing, and Inventory.
Translates human English inquiries into optimized, schema-aware SQL queries with automated executive insights.
"""
import os
import json
import re
import pandas as pd
from datetime import datetime
from db.postgres import run_custom_query, fetch_table_df, test_connection

SAMPLE_PROMPT_CHIPS = [
    "🩸 How much blood is available in our blood bank reserves?",
    "🚨 Which blood groups have critical shortages or low stock?",
    "🅾️ Show O negative universal donor blood availability",
    "📈 How many patients arrived on Mondays?",
    "🚨 Which medical supplies are running low or out of stock?",
    "🛏️ Which hospital departments currently have highest occupancy?",
    "👥 Show staff shortages and nurse deficits for night shifts",
    "📅 What is the average length of stay by day of week?",
    "🩺 What is the total number of surgeries scheduled?",
    "⚠️ List all active high severity hospital alerts",
    "⚖️ What administrative decisions were recently accepted or modified?",
    "📦 Which consumables have a supplier lead time over 5 days?",
    "🎛️ Show saved what-if disaster simulation scenarios",
    "📊 Compare emergency arrivals vs inpatient admissions",
    "🏥 Show general bed and ICU bed capacity for Pediatrics"
]

# Blood group & component entity mappings
BLOOD_GROUPS = {
    "o-": "O-",
    "o negative": "O-",
    "o neg": "O-",
    "o+": "O+",
    "o positive": "O+",
    "o pos": "O+",
    "a-": "A-",
    "a negative": "A-",
    "a neg": "A-",
    "a+": "A+",
    "a positive": "A+",
    "a pos": "A+",
    "b-": "B-",
    "b negative": "B-",
    "b neg": "B-",
    "b+": "B+",
    "b positive": "B+",
    "b pos": "B+",
    "ab-": "AB-",
    "ab negative": "AB-",
    "ab neg": "AB-",
    "ab+": "AB+",
    "ab positive": "AB+",
    "ab pos": "AB+",
    "universal donor": "O-",
    "universal recipient": "AB+"
}

BLOOD_COMPONENTS = {
    "prbc": "PRBC",
    "packed red": "PRBC",
    "red blood cells": "PRBC",
    "red cells": "PRBC",
    "ffp": "FFP",
    "plasma": "FFP",
    "fresh frozen plasma": "FFP",
    "platelet": "Platelet",
    "platelets": "Platelet",
    "rdp": "Platelet",
    "sdp": "Platelet",
    "cryo": "Cryoprecipitate",
    "cryoprecipitate": "Cryoprecipitate",
    "whole blood": "Whole Blood"
}

# Domain synonym & entity dictionaries
DEPARTMENTS = {
    "emergency": "Emergency",
    "ed": "Emergency",
    "er": "Emergency",
    "casualty": "Emergency",
    "trauma": "Emergency",
    "icu": "ICU",
    "intensive care": "ICU",
    "ccu": "ICU",
    "critical care": "ICU",
    "general ward": "General Ward",
    "general": "General Ward",
    "med-surg": "General Ward",
    "inpatient ward": "General Ward",
    "surgery": "Surgery",
    "surgical": "Surgery",
    "operating room": "Surgery",
    "operating rooms": "Surgery",
    "or theater": "Surgery",
    "pediatrics": "Pediatrics",
    "pediatric": "Pediatrics",
    "peds": "Pediatrics",
    "children": "Pediatrics",
    "maternity": "Maternity",
    "obgyn": "Maternity",
    "labor": "Maternity",
    "internal medicine": "Internal Medicine",
    "medicine": "Internal Medicine"
}

DAYS_OF_WEEK = {
    "monday": "Monday",
    "mondays": "Monday",
    "tuesday": "Tuesday",
    "tuesdays": "Tuesday",
    "wednesday": "Wednesday",
    "wednesdays": "Wednesday",
    "thursday": "Thursday",
    "thursdays": "Thursday",
    "friday": "Friday",
    "fridays": "Friday",
    "saturday": "Saturday",
    "saturdays": "Saturday",
    "sunday": "Sunday",
    "sundays": "Sunday"
}

SHIFTS = {
    "morning": "Morning",
    "day": "Morning",
    "evening": "Evening",
    "afternoon": "Evening",
    "night": "Night",
    "graveyard": "Night",
    "overnight": "Night"
}

STAFF_ROLES = {
    "nurse": "Nurse",
    "nurses": "Nurse",
    "rn": "Nurse",
    "doctor": "Doctor",
    "doctors": "Doctor",
    "physician": "Doctor",
    "physicians": "Doctor",
    "surgeon": "Doctor",
    "operating room staff": "Operating Room Staff"
}


def run_gemini_nl2sql(user_text: str, api_key: str):
    """
    Translates complex natural language English inquiries into optimized SQL queries
    and executive summaries using Google Gemini 1.5 Flash.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        schema_prompt = f"""You are the Chief Data Architect and Clinical Informatics AI for VitalOptima Command Center.
Translate this hospital operational inquiry into a clean, valid PostgreSQL query:
User Inquiry: "{user_text}"

Hospital Schema:
1. hospital_census_daily(date DATE, day_of_week VARCHAR, emergency_arrivals INT, admissions INT, icu_admissions INT, discharges INT, general_beds_occupied INT, icu_beds_occupied INT, surgeries_scheduled INT, average_length_of_stay_days NUMERIC)
2. department_resources(id INT, resource_id VARCHAR, resource_type VARCHAR, department VARCHAR, total_capacity INT, occupied_capacity INT, available_capacity INT, unavailable_capacity INT, staffed_capacity INT, forecast_demand INT)
   - Departments: 'ED Adult', 'ED Pediatric', 'ED Resuscitation', 'Medicine', 'Surgery', 'Orthopedics', 'Pediatrics', 'Obstetrics', 'Medical ICU', 'Surgical ICU', 'Main Theatre', 'Emergency Theatre'
3. staffing_roster(date DATE, shift VARCHAR, department VARCHAR, staff_role VARCHAR, required_count INT, available_count INT)
4. inventory_supplies(date DATE, item_id VARCHAR, item_name VARCHAR, item_category VARCHAR, closing_stock INT, reorder_threshold INT, daily_consumption INT, supplier_lead_time_days INT)
5. decision_log(id INT, timestamp TIMESTAMP, category VARCHAR, decision VARCHAR, recommendation TEXT, modified_details TEXT, administrator VARCHAR, rationale TEXT)
6. system_alerts(id INT, timestamp TIMESTAMP, category VARCHAR, severity VARCHAR, title VARCHAR, acknowledged INT)
7. scenarios(id INT, timestamp TIMESTAMP, name VARCHAR, surge_pct NUMERIC, icu_reduction NUMERIC, staff_loss NUMERIC, results_json TEXT)
8. blood_bank_inventory(id INT, blood_group VARCHAR, component_type VARCHAR, units_available INT, units_reserved INT, net_available_units INT, critical_threshold INT, daily_consumption NUMERIC, days_of_supply NUMERIC, shelf_life_days INT, storage_temp VARCHAR, rh_factor VARCHAR, status VARCHAR)

Return strictly valid JSON matching this schema:
{{
    "sql": "SELECT ... valid PostgreSQL query",
    "table_name": "table name queried",
    "summary": "1-2 sentence clinical executive summary of what this query reveals",
    "insights": [
        "Key analytical takeaway 1",
        "Key analytical takeaway 2"
    ]
}}
Only return the JSON.
"""
        response = model.generate_content(schema_prompt)
        text = response.text.strip()
        data = json.loads(text)
        sql = data.get("sql", "").strip()
        table_name = data.get("table_name", "hospital_records")
        summary = data.get("summary", "Query generated by Google Gemini AI.")
        insights = data.get("insights", [])

        if not sql:
            return None

        # Execute query
        try:
            df = run_custom_query(sql)
        except Exception:
            from db.database import get_sqlite_connection
            conn = get_sqlite_connection()
            sqlite_clean = re.sub(r'::NUMERIC\(\d+,\d+\)', '', sql)
            sqlite_clean = re.sub(r'::NUMERIC', '', sqlite_clean)
            df = pd.read_sql_query(sqlite_clean, conn)
            conn.close()

        return {
            "success": True,
            "engine": "Google Gemini AI",
            "answer_summary": f"🤖 **Google Gemini AI**: {summary} ({len(df)} records retrieved)",
            "sql_query": sql,
            "table_name": table_name,
            "df": df,
            "insights": insights if insights else _generate_insights(df, user_text.lower()),
            "error": None
        }
    except Exception as e:
        print(f"Gemini NL2SQL notice: {e}. Defaulting to deterministic hospital NL2SQL engine.")
        return None


def process_natural_language_query(user_text: str, api_key: str = None):
    """
    Parses natural language English questions using domain-specific entity extraction,
    synthesizes optimized SQL, and generates conversational clinical insights.
    Uses Google Gemini AI if API key is provided, with seamless fallback to deterministic physics model.
    """
    raw_query = user_text.strip()
    query_clean = raw_query.lower()

    if not query_clean:
        return {
            "success": False,
            "answer_summary": "Please enter a question to search hospital records.",
            "sql_query": "",
            "table_name": "",
            "df": pd.DataFrame(),
            "insights": [],
            "error": "Empty query"
        }

    # Step 0: Try Google Gemini AI if API key is present
    effective_key = api_key or os.environ.get("GEMINI_API_KEY")
    if effective_key and str(effective_key).strip():
        gemini_result = run_gemini_nl2sql(raw_query, str(effective_key).strip())
        if gemini_result and gemini_result.get("success"):
            return gemini_result

    # Normalize written number words (e.g. "twenty percent", "thirty percent", "eighty percent")
    num_words = {
        r'\bten\b': '10', r'\btwenty\b': '20', r'\bthirty\b': '30',
        r'\bforty\b': '40', r'\bfifty\b': '50', r'\bsixty\b': '60',
        r'\bseventy\b': '70', r'\beighty\b': '80', r'\bninety\b': '90',
        r'\bhundred\b': '100'
    }
    for nw_pat, nw_val in num_words.items():
        query_clean = re.sub(nw_pat, nw_val, query_clean)

    PCT = r'(?:%|percent(?:age)?|pct)'

    # Extract Entities & Parameters
    detected_dept = _extract_department(query_clean)
    detected_day = _extract_day_of_week(query_clean)
    detected_shift = _extract_shift(query_clean)
    detected_role = _extract_staff_role(query_clean)
    detected_blood_group = _extract_blood_group(query_clean)
    detected_blood_comp = _extract_blood_component(query_clean)
    is_weekend = "weekend" in query_clean
    is_weekday = "weekday" in query_clean
    has_total_intent = any(w in query_clean for w in ["total", "sum", "overall", "combined", "how many", "all together"])
    has_avg_intent = any(w in query_clean for w in ["average", "avg", "mean", "typically", "per day"])
    has_busiest_intent = any(w in query_clean for w in ["busiest", "highest", "peak", "maximum", "max", "most", "top"])
    has_lowest_intent = any(w in query_clean for w in ["lowest", "minimum", "min", "least", "slowest", "calmest", "fewest"])
    has_grouped_day = any(p in query_clean for p in ["by day", "by day of week", "each day", "per day of week"])
    has_grouped_dept = any(p in query_clean for p in ["by department", "each department", "per department", "all departments"])
    has_grouped_shift = any(p in query_clean for p in ["by shift", "each shift", "per shift"])
    limit = _extract_limit(query_clean, default=10)
    numeric_threshold = _extract_number_threshold(query_clean)

    # Check for Surge / Capacity Stress inquiry (e.g. "can we handle 20 percent increase in emergency cases?")
    m_surge = re.search(r'(\d+(?:\.\d+)?)\s*' + PCT, query_clean)
    has_surge_words = any(w in query_clean for w in ["handle", "absorb", "increase", "surge", "rise", "influx", "more arrivals", "more cases", "patient surge", "cases increase", "accommodate", "manage", "impact of"])
    is_surge_query = bool(m_surge and has_surge_words)

    sql = ""
    table_name = ""
    summary = ""
    insights = []

    # =========================================================================
    # ROUTE 0: DYNAMIC SURGE & CAPACITY STRESS EVALUATION (WHAT-IF RECORD PROJECTION)
    # =========================================================================
    if is_surge_query:
        table_name = "department_resources"
        surge_pct = float(m_surge.group(1))

        if detected_dept == "Emergency" or any(w in query_clean for w in ["emergency", "ed", "er", "triage", "arrival", "arrivals"]):
            where_dept = "WHERE (department ILIKE '%ED %' OR department ILIKE '%Emergency%')"
            dept_scope_name = "Emergency Department (ED Triage & Trauma Bays)"
        elif detected_dept == "ICU" or any(w in query_clean for w in ["icu", "critical care", "ventilator"]):
            where_dept = "WHERE department ILIKE '%ICU%'"
            dept_scope_name = "Critical Care Units (ICU Beds)"
        elif detected_dept == "General Ward" or any(w in query_clean for w in ["ward", "medicine", "surgical"]):
            where_dept = "WHERE (department ILIKE '%Medicine%' OR department ILIKE '%Surgery%' OR department ILIKE '%Orthopedics%')"
            dept_scope_name = "General Inpatient Medical & Surgical Wards"
        elif detected_dept:
            where_dept = f"WHERE department ILIKE '%{detected_dept}%'"
            dept_scope_name = f"{detected_dept} Department"
        else:
            where_dept = ""
            dept_scope_name = "All Hospital Clinical Departments"

        sql = f"""SELECT 
    department, 
    resource_type, 
    total_capacity, 
    occupied_capacity, 
    available_capacity,
    CAST(ROUND(occupied_capacity * (1.0 + {surge_pct} / 100.0)) AS INTEGER) AS projected_crisis_demand,
    CASE 
        WHEN ROUND(occupied_capacity * (1.0 + {surge_pct} / 100.0)) > total_capacity 
        THEN CAST(ROUND((occupied_capacity * (1.0 + {surge_pct} / 100.0)) - total_capacity) AS INTEGER)
        ELSE 0 
    END AS capacity_deficit,
    ROUND((occupied_capacity * (1.0 + {surge_pct} / 100.0) * 100.0 / NULLIF(total_capacity, 0)), 1) AS crisis_occupancy_pct,
    CASE 
        WHEN ROUND(occupied_capacity * (1.0 + {surge_pct} / 100.0)) > total_capacity 
        THEN '🔴 Capacity Breach (+{int(surge_pct)}% Exceeds)'
        WHEN ROUND(occupied_capacity * (1.0 + {surge_pct} / 100.0)) >= total_capacity * 0.9 
        THEN '⚠️ Near Saturation (Tight Margin)'
        ELSE '✅ Buffer Stable & Absorbed'
    END AS absorption_verdict
FROM department_resources
{where_dept}
ORDER BY crisis_occupancy_pct DESC;"""

        summary = f"Capacity stress evaluation for a **+{int(surge_pct)}% patient volume increase** across **{dept_scope_name}**."

    # =========================================================================
    # ROUTE 1A: HOSPITAL BLOOD BANK & TRANSFUSION BACKUP RESERVES
    # =========================================================================
    elif any(k in query_clean for k in ["blood", "prbc", "plasma", "platelet", "platelets", "cryo", "transfusion", "blood bank", "blood group", "blood type", "o negative", "o-", "o+", "a+", "b+", "ab-", "universal donor", "rh factor"]):
        table_name = "blood_bank_inventory"

        # Sub-intent: Specific blood group requested (e.g. O-, O+, A+, etc.)
        if detected_blood_group:
            sql = f"""SELECT 
    blood_group, 
    component_type, 
    units_available, 
    units_reserved, 
    net_available_units, 
    critical_threshold, 
    daily_consumption, 
    days_of_supply, 
    shelf_life_days, 
    storage_temp, 
    status 
FROM blood_bank_inventory 
WHERE blood_group ILIKE '%{detected_blood_group}%'
ORDER BY units_available ASC;"""
            summary = f"Blood bank backup reserves and component status for **Blood Group {detected_blood_group}**."

        # Sub-intent: Specific component requested (e.g. Platelets, Plasma, PRBC)
        elif detected_blood_comp:
            sql = f"""SELECT 
    blood_group, 
    component_type, 
    units_available, 
    units_reserved, 
    net_available_units, 
    critical_threshold, 
    daily_consumption, 
    days_of_supply, 
    shelf_life_days, 
    storage_temp, 
    status 
FROM blood_bank_inventory 
WHERE component_type ILIKE '%{detected_blood_comp}%'
ORDER BY units_available ASC;"""
            summary = f"Blood bank backup units for **{detected_blood_comp}** components across hospital blood groups."

        # Sub-intent: Critical deficit or low stock
        elif any(k in query_clean for k in ["shortage", "deficit", "low", "critical", "insufficient", "depleted", "emergency"]):
            sql = """SELECT 
    blood_group, 
    component_type, 
    units_available, 
    units_reserved, 
    net_available_units, 
    critical_threshold, 
    daily_consumption, 
    days_of_supply, 
    status 
FROM blood_bank_inventory 
WHERE units_available <= critical_threshold OR status ILIKE '%Critical%' OR status ILIKE '%Low%'
ORDER BY units_available ASC;"""
            summary = "Blood groups and components currently below safety critical thresholds or on low reserve."

        # Sub-intent: Component aggregate breakdown
        elif has_total_intent and any(k in query_clean for k in ["by component", "per component", "each component"]):
            sql = """SELECT 
    component_type, 
    SUM(units_available) AS total_units_available, 
    SUM(units_reserved) AS total_units_reserved, 
    SUM(net_available_units) AS net_unreserved_units, 
    ROUND(CAST(AVG(days_of_supply) AS NUMERIC), 1) AS avg_days_of_supply,
    COUNT(*) AS blood_group_varieties
FROM blood_bank_inventory 
GROUP BY component_type
ORDER BY total_units_available DESC;"""
            summary = "Aggregate blood bank reserves summarized by clinical component type."

        # Default: Full blood bank inventory overview
        else:
            sql = """SELECT 
    blood_group, 
    component_type, 
    units_available, 
    units_reserved, 
    net_available_units, 
    critical_threshold, 
    daily_consumption, 
    days_of_supply, 
    shelf_life_days, 
    storage_temp, 
    status 
FROM blood_bank_inventory 
ORDER BY units_available ASC;"""
            summary = "Hospital-wide blood bank backup reserves, cross-matched units, and component availability."

    # =========================================================================
    # ROUTE 1B: INVENTORY & MEDICAL CONSUMABLES
    # =========================================================================
    elif any(k in query_clean for k in ["inventory", "supplies", "supply", "stock", "consumable", "reorder", "n95", "mask", "glove", "ppe", "saline", "lead time", "burn rate"]):
        table_name = "inventory_supplies"

        # Sub-intent: Out of stock / zero stock
        if any(k in query_clean for k in ["out of stock", "zero stock", "0 stock", "exhausted", "stockout", "no stock"]):
            sql = """SELECT 
    item_id, 
    item_name, 
    item_category, 
    closing_stock, 
    reorder_threshold, 
    supplier_lead_time_days,
    '🔴 Out of Stock - Critical Replenishment' AS stock_status
FROM inventory_supplies
WHERE closing_stock = 0
ORDER BY supplier_lead_time_days DESC;"""
            summary = "Found consumable items with zero closing stock requiring emergency PO replenishment."

        # Sub-intent: Low stock / Reorder needed
        elif any(k in query_clean for k in ["low", "reorder", "shortage", "below threshold", "critical"]):
            sql = """SELECT 
    item_id, 
    item_name, 
    item_category, 
    closing_stock, 
    reorder_threshold, 
    daily_consumption,
    supplier_lead_time_days,
    CASE 
        WHEN closing_stock = 0 THEN '🔴 Out of Stock'
        WHEN closing_stock <= reorder_threshold THEN '⚠️ Reorder Triggered'
        ELSE '✅ Stock Adequate'
    END AS restock_status
FROM inventory_supplies
WHERE closing_stock <= reorder_threshold
ORDER BY closing_stock ASC;"""
            summary = "Identified critical medical consumables at or below safety reorder threshold."

        # Sub-intent: Lead time filter
        elif "lead time" in query_clean or "supplier" in query_clean:
            gt_days = numeric_threshold if numeric_threshold is not None else 5
            sql = f"""SELECT 
    item_id, 
    item_name, 
    item_category, 
    closing_stock, 
    reorder_threshold, 
    supplier_lead_time_days
FROM inventory_supplies
WHERE supplier_lead_time_days >= {gt_days}
ORDER BY supplier_lead_time_days DESC;"""
            summary = f"Consumables with extended supplier lead times ({gt_days}+ days)."

        # Sub-intent: Daily burn / consumption
        elif any(k in query_clean for k in ["burn", "consumption", "usage", "highest usage"]):
            sql = """SELECT 
    item_id, 
    item_name, 
    item_category, 
    ROUND(CAST(AVG(daily_consumption) AS NUMERIC), 1) AS avg_daily_burn,
    MAX(daily_consumption) AS peak_daily_burn,
    MIN(closing_stock) AS lowest_recorded_stock
FROM inventory_supplies
GROUP BY item_id, item_name, item_category
ORDER BY avg_daily_burn DESC;"""
            summary = "Average daily consumable consumption (burn rate) ranked from highest to lowest."

        else:
            sql = f"""SELECT 
    date, 
    item_id, 
    item_name, 
    item_category, 
    closing_stock, 
    reorder_threshold, 
    daily_consumption
FROM inventory_supplies
ORDER BY date DESC, closing_stock ASC
LIMIT {limit};"""
            summary = f"Latest consumable telemetry records (showing top {limit} records)."

    # =========================================================================
    # ROUTE 2: STAFFING ROSTER, NURSES, DOCTORS & SHIFTS
    # =========================================================================
    elif any(k in query_clean for k in ["staff", "staffing", "nurse", "nurses", "doctor", "doctors", "physician", "physicians", "shift", "roster", "on duty"]):
        table_name = "staffing_roster"

        where_clauses = []
        if detected_shift:
            where_clauses.append(f"shift ILIKE '{detected_shift}'")
        if detected_dept:
            where_clauses.append(f"department ILIKE '%{detected_dept}%'")
        if detected_role:
            where_clauses.append(f"staff_role ILIKE '%{detected_role}%'")

        # Sub-intent: Shortage / deficit
        if any(k in query_clean for k in ["shortage", "deficit", "lacking", "gap", "insufficient", "understaffed"]):
            where_clauses.append("available_count < required_count")
            where_str = " AND ".join(where_clauses)
            if where_str:
                where_str = "WHERE " + where_str
            
            if has_grouped_dept or "by department" in query_clean:
                sql = f"""SELECT 
    department, 
    SUM(required_count - available_count) AS total_staff_shortage,
    COUNT(*) AS understaffed_shift_slots
FROM staffing_roster
{where_str}
GROUP BY department
ORDER BY total_staff_shortage DESC;"""
                summary = "Aggregated staff shortage by hospital department."
            else:
                sql = f"""SELECT 
    date, 
    shift, 
    department, 
    staff_role, 
    available_count, 
    required_count, 
    (required_count - available_count) AS staff_shortage
FROM staffing_roster
{where_str}
ORDER BY staff_shortage DESC, date DESC
LIMIT {limit};"""
                summary = f"Staffing deficit allocations (required > available, showing top {limit})."

        # Sub-intent: Aggregate count
        elif has_total_intent or has_avg_intent:
            agg_fn = "AVG" if has_avg_intent else "SUM"
            agg_label = "average_available" if has_avg_intent else "total_available_staff"
            where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            sql = f"""SELECT 
    shift, 
    department, 
    ROUND({agg_fn}(available_count), 1) AS {agg_label},
    ROUND({agg_fn}(required_count), 1) AS total_required
FROM staffing_roster
{where_str}
GROUP BY shift, department
ORDER BY {agg_label} DESC;"""
            summary = f"Aggregated clinical staffing availability ({agg_fn.lower()} counts)."

        else:
            where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            sql = f"""SELECT 
    date, 
    shift, 
    department, 
    staff_role, 
    available_count, 
    required_count,
    (required_count - available_count) AS shortage
FROM staffing_roster
{where_str}
ORDER BY date DESC, shift ASC
LIMIT {limit};"""
            summary = f"Staffing schedules for {detected_dept or 'all departments'} {detected_shift or ''} shift."

    # =========================================================================
    # ROUTE 3: DECISION LOG & CLINICAL OVERRIDES
    # =========================================================================
    elif any(k in query_clean for k in ["decision", "decisions", "admin", "approval", "approved", "accepted", "modified", "rejected", "audit", "override", "rationale"]):
        table_name = "decision_log"

        if any(k in query_clean for k in ["rejected", "override", "denied"]):
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
            summary = "Auditable records of clinical overrides and rejected optimization proposals."
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
            summary = "Administrative decisions where recommendations were customized by a clinician."
        elif has_total_intent or "by decision" in query_clean:
            sql = """SELECT 
    decision, 
    COUNT(*) AS decision_count,
    ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM decision_log)), 1) AS percentage
FROM decision_log
GROUP BY decision
ORDER BY decision_count DESC;"""
            summary = "Executive breakdown of administrative optimization decisions."
        else:
            sql = f"""SELECT 
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
LIMIT {limit};"""
            summary = f"Recent administrative optimization decision audit logs (latest {limit})."

    # =========================================================================
    # ROUTE 4: SYSTEM ALERTS & INCIDENT ALARMS
    # =========================================================================
    elif any(k in query_clean for k in ["alert", "alerts", "warning", "warnings", "alarm", "alarms", "severity"]):
        table_name = "system_alerts"

        where_clauses = []
        if "high" in query_clean:
            where_clauses.append("severity ILIKE 'High'")
        elif "medium" in query_clean:
            where_clauses.append("severity ILIKE 'Medium'")
        elif "low" in query_clean:
            where_clauses.append("severity ILIKE 'Low'")

        if "unacknowledged" in query_clean or "active" in query_clean:
            where_clauses.append("acknowledged = 0")

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"""SELECT 
    id, 
    title, 
    category, 
    severity, 
    timestamp, 
    CASE WHEN acknowledged = 1 THEN '✅ Acknowledged' ELSE '🚨 Active Action Needed' END AS status
FROM system_alerts
{where_str}
ORDER BY id DESC;"""
        summary = "Hospital safety alerts and operational constraint notifications."

    # =========================================================================
    # ROUTE 5: DEPARTMENT CAPACITY, BED OCCUPANCY & WARDS
    # =========================================================================
    elif any(k in query_clean for k in ["department", "departments", "ward", "wards", "occupancy", "utilization", "capacity", "available bed", "free bed", "vacant bed"]) or (detected_dept and not any(k in query_clean for k in ["arrival", "arrivals", "census"])):
        table_name = "department_resources"

        if detected_dept == "Emergency":
            where_clause = "WHERE (department ILIKE '%ED %' OR department ILIKE '%Emergency%')"
        elif detected_dept == "ICU":
            where_clause = "WHERE department ILIKE '%ICU%'"
        elif detected_dept == "General Ward":
            where_clause = "WHERE (department ILIKE '%Medicine%' OR department ILIKE '%Surgery%')"
        elif detected_dept:
            where_clause = f"WHERE department ILIKE '%{detected_dept}%'"
        else:
            where_clause = ""

        if numeric_threshold is not None and any(w in query_clean for w in ["occupancy", "utilization", "capacity", "full", "exceed", "%", "percent", "over", "above", "greater"]):
            op = "<=" if any(w in query_clean for w in ["under", "less than", "below", "<", "fewer"]) else ">="
            where_parts = []
            if where_clause:
                where_parts.append(where_clause.replace("WHERE ", ""))
            where_parts.append(f"ROUND((occupied_capacity * 100.0 / NULLIF(total_capacity, 0)), 1) {op} {numeric_threshold}")
            cond_str = "WHERE " + " AND ".join(where_parts)
            sql = f"""SELECT 
    department, 
    resource_type, 
    total_capacity, 
    occupied_capacity, 
    available_capacity, 
    unavailable_capacity,
    staffed_capacity,
    ROUND((occupied_capacity * 100.0 / NULLIF(total_capacity, 0)), 1) AS occupancy_pct
FROM department_resources
{cond_str}
ORDER BY occupancy_pct DESC;"""
            summary = f"Departments with bed occupancy {op} {numeric_threshold}%."

        elif any(k in query_clean for k in ["available", "free", "vacant", "unoccupied"]):
            sql = f"""SELECT 
    department, 
    resource_type, 
    total_capacity, 
    occupied_capacity, 
    available_capacity, 
    ROUND((available_capacity * 100.0 / NULLIF(total_capacity, 0)), 1) AS availability_pct
FROM department_resources
{where_clause}
ORDER BY available_capacity DESC;"""
            summary = "Hospital departments ranked by available vacant bed buffers."

        elif any(k in query_clean for k in ["highest", "high", "most occupied", "critical", "full", "exceed", "surge"]):
            sql = f"""SELECT 
    department, 
    resource_type, 
    total_capacity, 
    occupied_capacity, 
    available_capacity, 
    ROUND((occupied_capacity * 100.0 / NULLIF(total_capacity, 0)), 1) AS occupancy_pct
FROM department_resources
{where_clause}
ORDER BY occupancy_pct DESC;"""
            summary = "Departmental capacity ranked by highest bed utilization percentage."

        else:
            sql = f"""SELECT 
    department, 
    resource_type, 
    total_capacity, 
    occupied_capacity, 
    available_capacity, 
    unavailable_capacity,
    staffed_capacity,
    ROUND((occupied_capacity * 100.0 / NULLIF(total_capacity, 0)), 1) AS occupancy_pct
FROM department_resources
{where_clause}
ORDER BY department ASC, resource_type ASC;"""
            summary = f"Departmental bed capacity status for {detected_dept or 'all clinical departments'}."

    # =========================================================================
    # ROUTE 6: WHAT-IF SCENARIOS & STRESS TESTS
    # =========================================================================
    elif any(k in query_clean for k in ["scenario", "scenarios", "simulation", "simulator", "stress test", "disaster"]):
        table_name = "scenarios"
        sql = f"""SELECT 
    id, 
    timestamp, 
    name, 
    surge_pct, 
    icu_reduction, 
    staff_loss, 
    results_json
FROM scenarios
ORDER BY id DESC
LIMIT {limit};"""
        summary = f"Saved What-if emergency stress test simulations in PostgreSQL."

    # =========================================================================
    # ROUTE 7: HOURLY DEMAND FORECAST
    # =========================================================================
    elif any(k in query_clean for k in ["hourly", "hour", "upcoming 24", "forecast hour", "next 24"]):
        table_name = "demand_forecast_hourly"
        sql = """SELECT 
    hour, 
    predicted_demand, 
    historical_demand, 
    emergency_capacity, 
    available_capacity,
    CASE 
        WHEN predicted_demand > emergency_capacity THEN '🔴 Surge Over Capacity'
        WHEN predicted_demand > emergency_capacity * 0.85 THEN '⚠️ High Volume'
        ELSE '✅ Normal Flow'
    END AS surge_status
FROM demand_forecast_hourly
ORDER BY hour_index ASC;"""
        summary = "24-hour predictive hourly patient demand projection with threshold ceilings."

    # =========================================================================
    # ROUTE 8: HOSPITAL CENSUS, PATIENT ARRIVALS & INPATIENT ANALYTICS
    # =========================================================================
    else:
        table_name = "hospital_census_daily"

        # Where conditions: Day of week or weekend or numeric threshold
        where_conds = []
        if detected_day:
            where_conds.append(f"day_of_week ILIKE '{detected_day}'")
        elif is_weekend:
            where_conds.append("day_of_week IN ('Saturday', 'Sunday')")
        elif is_weekday:
            where_conds.append("day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')")

        if numeric_threshold is not None:
            if "admission" in query_clean:
                where_conds.append(f"admissions >= {numeric_threshold}")
            elif "surgery" in query_clean or "surgeries" in query_clean:
                where_conds.append(f"surgeries_scheduled >= {numeric_threshold}")
            else:
                where_conds.append(f"emergency_arrivals >= {numeric_threshold}")

        # Specific metric queries
        if any(k in query_clean for k in ["surgeries", "surgery", "operation"]):
            if has_total_intent or has_avg_intent:
                sql = """SELECT 
    SUM(surgeries_scheduled) AS total_surgeries_scheduled,
    ROUND(CAST(AVG(surgeries_scheduled) AS NUMERIC), 1) AS avg_daily_surgeries,
    MAX(surgeries_scheduled) AS max_surgeries_single_day,
    MIN(surgeries_scheduled) AS min_surgeries_single_day
FROM hospital_census_daily;"""
                summary = "Aggregate surgery volume statistics across historical census."
            else:
                sql = f"""SELECT 
    date, 
    day_of_week, 
    surgeries_scheduled, 
    general_beds_occupied, 
    icu_beds_occupied
FROM hospital_census_daily
ORDER BY surgeries_scheduled DESC
LIMIT {limit};"""
                summary = f"Scheduled surgery census records ranked by highest volume (top {limit})."

        elif any(k in query_clean for k in ["length of stay", "los", "stay"]):
            if has_grouped_day:
                sql = """SELECT 
    day_of_week, 
    ROUND(CAST(AVG(average_length_of_stay_days) AS NUMERIC), 2) AS avg_length_of_stay_days,
    ROUND(CAST(AVG(admissions) AS NUMERIC), 1) AS avg_daily_admissions
FROM hospital_census_daily
GROUP BY day_of_week
ORDER BY avg_length_of_stay_days DESC;"""
                summary = "Average patient length of stay (LOS) grouped by day of the week."
            else:
                sql = """SELECT 
    ROUND(CAST(AVG(average_length_of_stay_days) AS NUMERIC), 2) AS hospital_avg_length_of_stay_days,
    ROUND(CAST(MIN(average_length_of_stay_days) AS NUMERIC), 2) AS min_recorded_los_days,
    ROUND(CAST(MAX(average_length_of_stay_days) AS NUMERIC), 2) AS max_recorded_los_days,
    ROUND(CAST(AVG(general_beds_occupied) AS NUMERIC), 1) AS avg_occupied_general_beds,
    ROUND(CAST(AVG(emergency_arrivals) AS NUMERIC), 1) AS avg_daily_emergency_arrivals
FROM hospital_census_daily;"""
                summary = "Hospital inpatient length of stay (LOS) summary metrics."

        # Specific Day / Day of week aggregation (e.g. "How many patients arrived on Mondays?")
        elif detected_day and (has_total_intent or has_avg_intent or "how many" in query_clean):
            sql = f"""SELECT 
    day_of_week, 
    COUNT(*) AS total_recorded_days,
    SUM(emergency_arrivals) AS total_emergency_arrivals,
    ROUND(CAST(AVG(emergency_arrivals) AS NUMERIC), 1) AS avg_arrivals_per_day,
    SUM(admissions) AS total_inpatient_admissions,
    ROUND(CAST(AVG(admissions) AS NUMERIC), 1) AS avg_admissions_per_day,
    MAX(emergency_arrivals) AS peak_single_day_arrivals
FROM hospital_census_daily
WHERE day_of_week ILIKE '{detected_day}'
GROUP BY day_of_week;"""
            summary = f"Complete statistical breakdown of patient arrivals and admissions on **{detected_day}s**."

        # Group by day of week
        elif has_grouped_day:
            sql = """SELECT 
    day_of_week, 
    COUNT(*) AS days_count,
    SUM(emergency_arrivals) AS total_arrivals,
    ROUND(CAST(AVG(emergency_arrivals) AS NUMERIC), 1) AS avg_daily_arrivals,
    SUM(admissions) AS total_admissions,
    ROUND(CAST(AVG(general_beds_occupied) AS NUMERIC), 1) AS avg_beds_occupied
FROM hospital_census_daily
GROUP BY day_of_week
ORDER BY avg_daily_arrivals DESC;"""
            summary = "Patient volume patterns aggregated by day of the week across the 365-day census."

        # Total / Aggregation intent
        elif has_total_intent or has_avg_intent:
            sql = """SELECT 
    COUNT(*) AS total_recorded_days,
    SUM(emergency_arrivals) AS total_emergency_arrivals,
    ROUND(CAST(AVG(emergency_arrivals) AS NUMERIC), 1) AS avg_daily_arrivals,
    SUM(admissions) AS total_admissions,
    ROUND(CAST(AVG(admissions) AS NUMERIC), 1) AS avg_daily_admissions,
    SUM(icu_admissions) AS total_icu_admissions,
    ROUND(CAST(AVG(general_beds_occupied) AS NUMERIC), 1) AS avg_general_beds_occupied
FROM hospital_census_daily;"""
            summary = "Overall summary metrics for hospital arrivals, admissions, and bed occupancy."

        # Busiest / Peak arrivals
        elif has_busiest_intent:
            metric_col = "admissions" if "admission" in query_clean else ("icu_admissions" if "icu" in query_clean else "emergency_arrivals")
            where_str = f"WHERE {' AND '.join(where_conds)}" if where_conds else ""
            sql = f"""SELECT 
    date, 
    day_of_week, 
    emergency_arrivals, 
    admissions, 
    icu_admissions, 
    general_beds_occupied, 
    average_length_of_stay_days
FROM hospital_census_daily
{where_str}
ORDER BY {metric_col} DESC
LIMIT {limit};"""
            summary = f"Peak historical operational days ranked by {metric_col.replace('_', ' ')} (top {limit})."

        # Lowest / Calmest arrivals
        elif has_lowest_intent:
            where_str = f"WHERE {' AND '.join(where_conds)}" if where_conds else ""
            sql = f"""SELECT 
    date, 
    day_of_week, 
    emergency_arrivals, 
    admissions, 
    discharges,
    general_beds_occupied
FROM hospital_census_daily
{where_str}
ORDER BY emergency_arrivals ASC
LIMIT {limit};"""
            summary = f"Lowest volume days recorded in census history (top {limit})."

        # Standard census filter
        else:
            where_str = f"WHERE {' AND '.join(where_conds)}" if where_conds else ""
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
{where_str}
ORDER BY date DESC
LIMIT {limit};"""
            summary = f"Recent daily census records for {detected_day or ('weekend' if is_weekend else 'all days')} (showing {limit} records)."

    # Execute generated SQL query with safe SQLite fallback
    try:
        df = run_custom_query(sql)
        row_count = len(df)

        # Build dynamic executive takeaways
        insights = _generate_insights(df, query_clean)

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
        # Attempt fallback query on SQLite if PostgreSQL is unreachable or errored
        try:
            from db.database import get_sqlite_connection
            conn = get_sqlite_connection()
            # Clean PostgreSQL specific syntax like ::NUMERIC for SQLite
            sqlite_clean = re.sub(r'::NUMERIC\(\d+,\d+\)', '', sql)
            sqlite_clean = re.sub(r'::NUMERIC', '', sqlite_clean)
            df = pd.read_sql_query(sqlite_clean, conn)
            conn.close()

            insights = _generate_insights(df, query_clean)
            return {
                "success": True,
                "answer_summary": f"{summary} (Retrieved {len(df)} records via Local Fallback)",
                "sql_query": sqlite_clean,
                "table_name": table_name,
                "df": df,
                "insights": insights,
                "error": None
            }
        except Exception as sq_err:
            return {
                "success": False,
                "answer_summary": f"Could not execute query: {e}",
                "sql_query": sql,
                "table_name": table_name,
                "df": pd.DataFrame(),
                "insights": [],
                "error": str(e)
            }


def _extract_department(text: str) -> str:
    """Extracts known hospital department entity."""
    for key, val in DEPARTMENTS.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text):
            return val
    return ""


def _extract_day_of_week(text: str) -> str:
    """Extracts day of week entity."""
    for key, val in DAYS_OF_WEEK.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text):
            return val
    return ""


def _extract_shift(text: str) -> str:
    """Extracts clinical shift entity."""
    for key, val in SHIFTS.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text):
            return val
    return ""


def _extract_staff_role(text: str) -> str:
    """Extracts staff role entity."""
    for key, val in STAFF_ROLES.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text):
            return val
    return ""


def _extract_blood_group(text: str) -> str:
    """Extracts blood group entity (e.g. O-, A+, AB-, O negative)."""
    # Try exact multi-word first
    for key, val in sorted(BLOOD_GROUPS.items(), key=lambda x: -len(x[0])):
        if re.search(r'(?:\b|\s)' + re.escape(key) + r'(?:\b|\s|$)', text):
            return val
    return ""


def _extract_blood_component(text: str) -> str:
    """Extracts blood component entity (e.g. Platelets, FFP, PRBC, Cryo)."""
    for key, val in sorted(BLOOD_COMPONENTS.items(), key=lambda x: -len(x[0])):
        if re.search(r'\b' + re.escape(key) + r'\b', text):
            return val
    return ""


def _extract_limit(text: str, default: int = 10) -> int:
    """Extracts integer limit from 'top 5', 'limit 20', 'first 10'."""
    m = re.search(r'\b(?:top|first|limit|latest)\s+(\d+)\b', text)
    if m:
        try:
            return max(1, min(100, int(m.group(1))))
        except Exception:
            pass
    return default


def _extract_number_threshold(text: str):
    """
    Extracts numeric thresholds like:
    - 'over 80%', 'over 80 percent', 'greater than 75'
    - '> 80', '>= 80', 'exceeding 90%'
    - 'less than 50', 'under 40%', '< 30'
    Returns integer/float value or None.
    """
    PCT = r'(?:%|percent(?:age)?|pct)?'
    # Greater-than / over patterns
    m = re.search(r'(?:>=|>|over|greater than|more than|above|at least|exceeding|higher than)\s*(\d+(?:\.\d+)?)\s*' + PCT, text)
    if m:
        try:
            return float(m.group(1)) if '.' in m.group(1) else int(m.group(1))
        except Exception:
            pass

    # Less-than / under patterns
    m_under = re.search(r'(?:<=|<|under|less than|below|fewer than|at most)\s*(\d+(?:\.\d+)?)\s*' + PCT, text)
    if m_under:
        try:
            return float(m_under.group(1)) if '.' in m_under.group(1) else int(m_under.group(1))
        except Exception:
            pass

    # Generic percentage with occupancy/utilization
    m_pct = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?|pct)\s*(?:occupancy|utilization|capacity|full)?', text)
    if m_pct and any(w in text for w in ["occupancy", "utilization", "capacity", "rate", "full"]):
        try:
            return float(m_pct.group(1)) if '.' in m_pct.group(1) else int(m_pct.group(1))
        except Exception:
            pass

    return None


def _generate_insights(df: pd.DataFrame, query_clean: str) -> list:
    """Generates intelligent analytical bullet points from returned query results."""
    insights = []
    if df.empty:
        return ["No records matched the criteria."]

    cols = df.columns.tolist()

    # Insight 0: Dynamic Surge Capacity Deficits
    if "capacity_deficit" in cols:
        total_def = int(df["capacity_deficit"].sum())
        total_proj = int(df["projected_crisis_demand"].sum()) if "projected_crisis_demand" in cols else 0
        total_cap = int(df["total_capacity"].sum()) if "total_capacity" in cols else 0
        if total_def > 0:
            breached = df[df["capacity_deficit"] > 0]["department"].tolist()
            insights.append(f"🚨 **Surge Capacity Breach**: Hospital faces an immediate shortfall of **+{total_def} treatment beds/bays** across: **{', '.join(breached)}**.")
            insights.append(f"📈 Total projected crisis demand reaches **{total_proj}** against staffed capacity of **{total_cap}**.")
        else:
            insights.append(f"✅ **Surge Buffer Sufficient**: Existing departmental capacity ({total_cap} total spaces) can absorb this projected surge of **{total_proj}** without physical breach.")

    # Insight 1: Total arrivals & admissions
    if "total_emergency_arrivals" in cols:
        total_arr = int(df["total_emergency_arrivals"].iloc[0])
        avg_arr = df.get("avg_arrivals_per_day", df.get("avg_daily_arrivals", [0])).iloc[0]
        insights.append(f"📊 Total emergency volume: **{total_arr:,} patients** (Average: **{avg_arr} arrivals/day**).")

    # Insight 2: Peak arrivals
    if "emergency_arrivals" in cols and len(df) > 1:
        max_arr = df["emergency_arrivals"].max()
        if "date" in cols:
            busiest_date = df.loc[df["emergency_arrivals"].idxmax()]["date"]
            insights.append(f"🔥 Peak emergency surge: **{max_arr} patients** recorded on **{busiest_date}**.")
        else:
            insights.append(f"🔥 Peak emergency surge: **{max_arr} patients**.")

    # Insight 3: Bed occupancy
    if "occupancy_pct" in cols:
        max_row = df.loc[df["occupancy_pct"].astype(float).idxmax()]
        dept = max_row.get("department", "Unknown")
        rate = max_row.get("occupancy_pct", 0)
        insights.append(f"🏥 Highest departmental bed utilization: **{dept}** at **{rate}%** occupancy.")
        if float(rate) >= 85:
            insights.append("⚠️ Critical utilization: Ward exceeds the 85% clinical safety threshold.")

    # Insight 4: Available beds
    if "available_capacity" in cols:
        total_avail = df["available_capacity"].sum()
        insights.append(f"🛏️ Total clean beds currently vacant & available: **{int(total_avail)} beds**.")

    # Insight 5: Consumables & Stockouts
    if "closing_stock" in cols:
        stockouts = (df["closing_stock"] == 0).sum()
        if stockouts > 0:
            insights.append(f"🚨 **Emergency Action**: **{stockouts} item(s)** at zero stock (immediate stockout).")
        else:
            insights.append("✅ All items in this subset have positive closing inventory.")

    # Insight 6: Staff shortages
    if "total_staff_shortage" in cols:
        total_short = df["total_staff_shortage"].sum()
        insights.append(f"👥 Combined departmental staffing deficit: **{int(total_short)} personnel**.")
    elif "shortage" in cols or "staff_shortage" in cols:
        col_s = "shortage" if "shortage" in cols else "staff_shortage"
        total_short = df[col_s].sum()
        if total_short > 0:
            insights.append(f"👥 Clinical staffing shortage: **{int(total_short)} personnel** deficit in this roster slice.")
        else:
            insights.append("✅ Fully staffed: Shift allocations meet or exceed required minimums.")

    # Insight 7: Surgeries
    if "total_surgeries_scheduled" in cols:
        tot_surg = int(df["total_surgeries_scheduled"].iloc[0])
        avg_surg = df["avg_daily_surgeries"].iloc[0]
        insights.append(f"🩺 Total surgical volume: **{tot_surg:,} procedures** (Daily average: **{avg_surg} surgeries/day**).")

    # Insight 8: Length of Stay
    if "hospital_avg_length_of_stay_days" in cols:
        los = df["hospital_avg_length_of_stay_days"].iloc[0]
        insights.append(f"⏱️ Inpatient mean length of stay: **{los} days** per admitted patient.")

    # Insight 9: Blood Bank & Transfusion Backup Reserves
    if "units_available" in cols and ("blood_group" in cols or "component_type" in cols):
        tot_units = int(df["units_available"].sum())
        crit_groups = df[df["status"].str.contains("Critical", case=False, na=False)] if "status" in cols else pd.DataFrame()
        low_groups = df[df["status"].str.contains("Low", case=False, na=False)] if "status" in cols else pd.DataFrame()

        insights.append(f"🩸 Total blood backup in this view: **{tot_units} units** across active blood groups and components.")
        if not crit_groups.empty:
            crit_names = ", ".join(crit_groups["blood_group"].unique().tolist())
            insights.append(f"🚨 **Critical Blood Shortage**: Immediate donor recall needed for blood group(s): **{crit_names}**.")
        elif not low_groups.empty:
            low_names = ", ".join(low_groups["blood_group"].unique().tolist())
            insights.append(f"⚠️ **Low Blood Reserves**: Tight buffer detected for: **{low_names}** (approaching safety reorder limits).")
        else:
            insights.append("✅ Blood backup reserves maintain adequate clinical buffers across selected components.")

    # Default insight if empty
    if not insights:
        insights.append(f"Query returned **{len(df)} records** across **{len(df.columns)} metrics**.")

    return insights
