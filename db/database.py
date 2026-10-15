"""
VitalOptima Database Access Layer
Seamless dual-engine: Neon PostgreSQL (primary cloud) with automatic local SQLite fallback.
Stores administrator decisions, alert logs, scenarios, and audit trails.
"""
import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_PATH, get_ist_now

# Try importing PostgreSQL engine
try:
    from db.postgres import (
        get_engine, test_connection, log_decision_pg,
        fetch_table_df, get_table_summary,
        save_scenario_pg, get_scenarios_pg
    )
    POSTGRES_AVAILABLE = True
except Exception:
    POSTGRES_AVAILABLE = False


def get_sqlite_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize local SQLite schema for fallback and seed default values."""
    conn = get_sqlite_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decision_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        category TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        decision TEXT NOT NULL,
        modified_details TEXT,
        administrator TEXT NOT NULL,
        rationale TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        acknowledged INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recent_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time_str TEXT NOT NULL,
        title TEXT NOT NULL,
        details TEXT NOT NULL,
        color TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scenarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        name TEXT NOT NULL,
        surge_pct REAL,
        icu_reduction INTEGER,
        staff_loss REAL,
        results_json TEXT
    )
    """)

    # Seed operational tables from CSVs if not present
    import pandas as pd
    data_dir = PROJECT_ROOT / "data"
    table_csv_map = {
        "hospital_census_daily": ["hospital_census_daily.csv", "hospital_daily_data.csv"],
        "hospital_daily_data": ["hospital_daily_data.csv", "hospital_census_daily.csv"],
        "department_resources": ["department_resources.csv", "hospital_resources.csv"],
        "hospital_resources": ["hospital_resources.csv", "department_resources.csv"],
        "staffing_roster": ["staffing_roster.csv", "staff_availability.csv"],
        "staff_availability": ["staff_availability.csv", "staffing_roster.csv"],
        "inventory_supplies": ["inventory_supplies.csv", "medical_inventory.csv"],
        "medical_inventory": ["medical_inventory.csv", "inventory_supplies.csv"],
        "demand_forecast_hourly": ["demand_forecast.csv"],
        "demand_forecast": ["demand_forecast.csv"],
        "departments": ["departments.csv"],
    }

    for tbl, fnames in table_csv_map.items():
        cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        if cursor.fetchone()[0] == 0:
            for fname in fnames:
                csv_p = data_dir / fname
                if csv_p.exists():
                    try:
                        df = pd.read_csv(csv_p)
                        df.to_sql(tbl, conn, if_exists="replace", index=False)
                        break
                    except Exception:
                        pass

    # Ensure system_alerts exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        acknowledged INTEGER DEFAULT 0
    )
    """)
    cursor.execute("SELECT COUNT(*) FROM system_alerts")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO system_alerts (title, category, severity, timestamp, acknowledged) VALUES (?, ?, ?, ?, ?)",
            [
                ("Emergency Department surge expected at 15:00 (+28% arrivals)", "Surge", "High", "2025-04-27 14:15", 0),
                ("ICU Bed Availability below 15% safety threshold", "Active", "High", "2025-04-27 13:45", 0),
                ("N95 Respirator consumable stockout alert", "Shortage", "Medium", "2025-04-27 12:00", 1)
            ]
        )

    cursor.execute("SELECT COUNT(*) FROM recent_activity")
    if cursor.fetchone()[0] == 0:
        initial_activities = [
            ("14:20", "New forecast run completed", "Emergency arrivals (next 24h)", "#3B82F6"),
            ("13:55", "Optimization run completed", "8 allocations, 3 unmet demands", "#10B981"),
            ("12:40", "Staff shift change", "Night shift → Day shift (6 staff)", "#F59E0B"),
            ("11:30", "Patient surge alert", "ED arrivals 20% above forecast", "#EF4444"),
            ("10:15", "Model training completed", "Random Forest v1.2.0", "#06B6D4")
        ]
        cursor.executemany(
            "INSERT INTO recent_activity (time_str, title, details, color) VALUES (?, ?, ?, ?)",
            initial_activities
        )

    cursor.execute("SELECT COUNT(*) FROM decision_log")
    if cursor.fetchone()[0] == 0:
        initial_decisions = [
            ("2025-04-27 13:58", "Staff Allocation", "Deploy 4 float nurses to Emergency Room during 15:00-18:00 peak", "Accepted", "", "Admin (AD)", "ED forecasted peak at 15:00 with 92 arrivals exceeds safe nurse-patient ratio"),
            ("2025-04-27 12:45", "ICU Capacity", "Transfer 2 stable post-op ICU patients to Step-Down ward", "Modified", "Transfer 1 patient to Step-Down, monitor second patient until 16:00", "Admin (AD)", "Attending physician requested additional 2hr observation on patient #B4"),
            ("2025-04-27 10:30", "OR Rescheduling", "Postpone 2 elective orthopedic procedures to clear OR 3 for trauma standby", "Accepted", "", "Admin (AD)", "Preparedness for incoming multi-vehicle highway accident victims")
        ]
        cursor.executemany(
            "INSERT INTO decision_log (timestamp, category, recommendation, decision, modified_details, administrator, rationale) VALUES (?, ?, ?, ?, ?, ?, ?)",
            initial_decisions
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blood_bank_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blood_group TEXT NOT NULL,
        component_type TEXT NOT NULL,
        units_available INTEGER NOT NULL DEFAULT 0,
        units_reserved INTEGER NOT NULL DEFAULT 0,
        net_available_units INTEGER NOT NULL DEFAULT 0,
        critical_threshold INTEGER NOT NULL DEFAULT 0,
        daily_consumption REAL NOT NULL DEFAULT 0.0,
        days_of_supply REAL NOT NULL DEFAULT 0.0,
        shelf_life_days INTEGER NOT NULL DEFAULT 0,
        storage_temp TEXT NOT NULL,
        rh_factor TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM blood_bank_inventory")
    if cursor.fetchone()[0] == 0:
        csv_path = PROJECT_ROOT / "data" / "blood_bank_inventory.csv"
        if csv_path.exists():
            import pandas as pd
            df_b = pd.read_csv(csv_path)
            for _, r in df_b.iterrows():
                cursor.execute("""
                    INSERT INTO blood_bank_inventory (
                        blood_group, component_type, units_available, units_reserved,
                        net_available_units, critical_threshold, daily_consumption,
                        days_of_supply, shelf_life_days, storage_temp, rh_factor, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(r['blood_group']), str(r['component_type']), int(r['units_available']),
                    int(r['units_reserved']), int(r['net_available_units']), int(r['critical_threshold']),
                    float(r['daily_consumption']), float(r['days_of_supply']), int(r['shelf_life_days']),
                    str(r['storage_temp']), str(r['rh_factor']), str(r['status'])
                ))

    # --- 1. Users Table (RBAC) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'ADMISSION_OFFICER',
        full_name TEXT NOT NULL,
        department TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        last_login TEXT
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        from services.auth_service import hash_password
        admin_hash, admin_salt = hash_password("Admin@Vital2026!")
        officer_hash, officer_salt = hash_password("Admit@Vital2026!")
        now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        default_users = [
            ("admin", admin_hash, admin_salt, "ADMIN", "Dr. Rajesh Sharma (Medical Director)", "Hospital Administration", 1, now_ts),
            ("admit_officer", officer_hash, officer_salt, "ADMISSION_OFFICER", "Priya Nair (Lead Admission Officer)", "Central Admissions & Triage", 1, now_ts)
        ]
        cursor.executemany("""
            INSERT INTO users (username, password_hash, salt, role, full_name, department, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, default_users)

    # Sync default admin users to Postgres if available
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine is not None:
            with engine.begin() as pg_conn:
                from services.auth_service import hash_password
                admin_hash, admin_salt = hash_password("Admin@Vital2026!")
                officer_hash, officer_salt = hash_password("Admit@Vital2026!")
                pg_conn.execute(text("""
                    INSERT INTO users (username, password_hash, salt, role, full_name, department, is_active, created_at)
                    VALUES 
                    ('admin', :ah, :as, 'ADMIN', 'Dr. Rajesh Sharma (Medical Director)', 'Hospital Administration', true, NOW()),
                    ('admit_officer', :oh, :os, 'ADMISSION_OFFICER', 'Priya Nair (Lead Admission Officer)', 'Central Admissions & Triage', true, NOW())
                    ON CONFLICT (username) DO NOTHING;
                """), {"ah": admin_hash, "as": admin_salt, "oh": officer_hash, "os": officer_salt})
    except Exception as e:
        print(f"[DB] Notice syncing default users to Postgres: {e}")

    # --- 2. Patient Admissions Table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_admissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admission_id TEXT UNIQUE NOT NULL,
        patient_id TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        department TEXT NOT NULL,
        admission_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Admitted',
        bed_number TEXT,
        admitted_at TEXT NOT NULL,
        discharged_at TEXT,
        admitted_by TEXT NOT NULL,
        discharged_by TEXT,
        clinical_notes TEXT,
        updated_at TEXT NOT NULL
    )
    """)

    # Seed initial active admissions if empty
    cursor.execute("SELECT COUNT(*) FROM patient_admissions")
    if cursor.fetchone()[0] == 0:
        now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        initial_admissions = [
            ("ADM-20261015-001", "PAT-10842", "Arjun Mehra", 54, "Male", "Medicine", "Emergency", "Admitted", "MED-B12", "2026-10-15 06:30:00", None, "admit_officer", None, "Acute exacerbation of COPD with respiratory distress", now_ts),
            ("ADM-20261015-002", "PAT-10843", "Sunita Verma", 42, "Female", "Surgery", "Elective", "Admitted", "SUR-B08", "2026-10-15 07:15:00", None, "admit_officer", None, "Post-op laparoscopic cholecystectomy monitoring", now_ts),
            ("ADM-20261015-003", "PAT-10844", "David Fernandes", 68, "Male", "Medical ICU", "Emergency", "Admitted", "MICU-B03", "2026-10-15 05:00:00", None, "admit_officer", None, "Septic shock requiring arterial line & vasopressors", now_ts),
            ("ADM-20261015-004", "PAT-10845", "Ananya Roy", 29, "Female", "Obstetrics", "Urgent", "Admitted", "OBS-B05", "2026-10-15 08:00:00", None, "admit_officer", None, "Active labor, fetal monitoring unremarkable", now_ts),
            ("ADM-20261015-005", "PAT-10846", "Rohan Kapoor", 11, "Male", "Pediatrics", "Elective", "Admitted", "PED-B04", "2026-10-15 08:30:00", None, "admit_officer", None, "Acute asthma exacerbation, nebulization ongoing", now_ts)
        ]
        cursor.executemany("""
            INSERT INTO patient_admissions (
                admission_id, patient_id, patient_name, age, gender, department,
                admission_type, status, bed_number, admitted_at, discharged_at,
                admitted_by, discharged_by, clinical_notes, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, initial_admissions)

    # --- 3. Audit Logs Table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        actor_username TEXT NOT NULL,
        actor_role TEXT NOT NULL,
        action TEXT NOT NULL,
        target_id TEXT,
        target_type TEXT,
        status TEXT NOT NULL DEFAULT 'SUCCESS',
        details TEXT
    )
    """)

    # --- 4. Hospital Data Sync Telemetry ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hospital_data_sync (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT UNIQUE NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        last_updated_at TEXT NOT NULL,
        updated_by TEXT
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM hospital_data_sync")
    if cursor.fetchone()[0] == 0:
        now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO hospital_data_sync (entity_type, version, last_updated_at, updated_by) VALUES (?, ?, ?, ?)",
                       ("admissions", 1, now_ts, "system"))
        cursor.execute("INSERT INTO hospital_data_sync (entity_type, version, last_updated_at, updated_by) VALUES (?, ?, ?, ?)",
                       ("resources", 1, now_ts, "system"))
        cursor.execute("INSERT INTO hospital_data_sync (entity_type, version, last_updated_at, updated_by) VALUES (?, ?, ?, ?)",
                       ("global", 1, now_ts, "system"))

    # --- 5. Department Resources Table (authoritative capacity baseline) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS department_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_id TEXT UNIQUE NOT NULL,
        resource_type TEXT NOT NULL,
        department TEXT NOT NULL,
        total_capacity INTEGER NOT NULL DEFAULT 0,
        unavailable_capacity INTEGER NOT NULL DEFAULT 0,
        occupied_capacity INTEGER NOT NULL DEFAULT 0,
        available_capacity INTEGER NOT NULL DEFAULT 0,
        staffed_capacity INTEGER NOT NULL DEFAULT 0,
        forecast_demand INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM department_resources")
    if cursor.fetchone()[0] == 0:
        dept_csv = PROJECT_ROOT / "data" / "department_resources.csv"
        if dept_csv.exists():
            import pandas as pd
            df_d = pd.read_csv(dept_csv)
            now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            for _, r in df_d.iterrows():
                cursor.execute("""
                    INSERT INTO department_resources (
                        resource_id, resource_type, department, total_capacity,
                        unavailable_capacity, occupied_capacity, available_capacity,
                        staffed_capacity, forecast_demand, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(r['resource_id']), str(r['resource_type']), str(r['department']),
                    int(r['total_capacity']), int(r['unavailable_capacity']), int(r['occupied_capacity']),
                    int(r['available_capacity']), int(r['staffed_capacity']), int(r['forecast_demand']),
                    now_ts
                ))

    conn.commit()
    conn.close()


def log_decision(category, recommendation, decision, modified_details="", administrator="Admin (AD)", rationale=""):
    """Logs an administrator decision into Neon PostgreSQL, with fallback to SQLite."""
    now_str = get_ist_now().strftime("%Y-%m-%d %H:%M")
    
    # Try PostgreSQL first
    pg_success = False
    if POSTGRES_AVAILABLE:
        try:
            pg_success = log_decision_pg(
                category=category,
                recommendation=recommendation,
                decision=decision,
                modified_details=modified_details,
                administrator=administrator,
                rationale=rationale
            )
        except Exception:
            pg_success = False

    # Also record in SQLite for local durability/fallback
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO decision_log (timestamp, category, recommendation, decision, modified_details, administrator, rationale)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (now_str, category, recommendation, decision, modified_details, administrator, rationale))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SQLite] Failed to write fallback log: {e}")


def get_decision_logs():
    """Retrieves all decision logs, preferring live PostgreSQL."""
    if POSTGRES_AVAILABLE:
        try:
            df = fetch_table_df("decision_log", limit=500)
            if not df.empty:
                # Sort by id desc
                df = df.sort_values(by="id", ascending=False)
                return df.to_dict(orient="records")
        except Exception as e:
            print(f"[PostgreSQL] Failed to fetch decision logs: {e}")

    # Fallback to SQLite
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM decision_log ORDER BY id DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[SQLite] Failed to fetch decision logs: {e}")
        return []


def get_recent_activities():
    """Retrieves recent activities, preferring live PostgreSQL."""
    if POSTGRES_AVAILABLE:
        try:
            df = fetch_table_df("recent_activity", limit=100)
            if not df.empty:
                df = df.sort_values(by="id", ascending=True)
                return df.to_dict(orient="records")
        except Exception as e:
            print(f"[PostgreSQL] Failed to fetch recent activities: {e}")

    # Fallback to SQLite
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recent_activity ORDER BY id ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[SQLite] Failed to fetch recent activities: {e}")
        return []


def save_scenario(name, surge_pct, icu_reduction, staff_loss, results_json=""):
    """Saves a simulation scenario into PostgreSQL with SQLite fallback."""
    now_str = get_ist_now().strftime("%Y-%m-%d %H:%M")
    
    # Try PostgreSQL first
    if POSTGRES_AVAILABLE:
        try:
            ok = save_scenario_pg(name, surge_pct, icu_reduction, staff_loss, results_json)
            if ok:
                return True
        except Exception as e:
            print(f"[PostgreSQL] Failed to save scenario: {e}")

    # Fallback to SQLite
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO scenarios (timestamp, name, surge_pct, icu_reduction, staff_loss, results_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (now_str, name, float(surge_pct), int(icu_reduction), float(staff_loss), results_json))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[SQLite] Failed to save scenario: {e}")
        return False


def get_scenarios(limit=50):
    """Retrieves saved scenarios, preferring live PostgreSQL."""
    if POSTGRES_AVAILABLE:
        try:
            df = get_scenarios_pg(limit=limit)
            if not df.empty:
                return df.to_dict(orient="records")
        except Exception as e:
            print(f"[PostgreSQL] Failed to fetch scenarios: {e}")

    # Fallback to SQLite
    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scenarios ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"[SQLite] Failed to fetch scenarios: {e}")
        return []


# Initialize fallback database on module load
init_db()
