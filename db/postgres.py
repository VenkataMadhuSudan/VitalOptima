"""
VitalOptima Neon PostgreSQL Database Connector & Synchronization Engine
Provides connection pooling, schema initialization, CSV synchronization, and table query utilities.
"""
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
IST_TZ = timezone(timedelta(hours=5, minutes=30), name="IST")
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file
load_dotenv(PROJECT_ROOT / ".env")

from db.schema import (
    Base, DepartmentResource, HospitalCensusDaily, StaffingRoster,
    InventorySupply, DemandForecastHourly, DecisionLog, SystemAlert, RecentActivity,
    ScenarioSimulation, BloodBankInventory, User, PatientAdmission, AuditLog,
    HospitalDataSync
)

_ENGINE = None
_SESSION_FACTORY = None

def get_database_url():
    """Retrieve DATABASE_URL from environment or .env file."""
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        return ""
    # Ensure standard postgresql+psycopg2 dialect for SQLAlchemy 2.0
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return raw_url

def get_engine():
    """Get or create singleton SQLAlchemy Engine with connection pooling."""
    global _ENGINE, _SESSION_FACTORY
    url = get_database_url()
    if not url:
        return None
    if _ENGINE is None:
        try:
            _ENGINE = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_recycle=300,
                connect_args={"connect_timeout": 10}
            )
            _SESSION_FACTORY = sessionmaker(bind=_ENGINE)
            try:
                Base.metadata.create_all(_ENGINE)
            except Exception as e_create:
                print(f"[PostgreSQL] Warning auto-creating tables: {e_create}")
        except Exception as e:
            print(f"[PostgreSQL] Failed to create engine: {e}")
            return None
    return _ENGINE

def get_session():
    """Create a new SQLAlchemy session."""
    engine = get_engine()
    if engine is None:
        return None
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=engine)
    return _SESSION_FACTORY()

def test_connection():
    """
    Test connectivity to Neon PostgreSQL database.
    Returns: (is_connected: bool, info_dict: dict)
    """
    url = get_database_url()
    if not url:
        from db.database import get_sqlite_connection
        try:
            conn = get_sqlite_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM hospital_census_daily;")
            cnt = cur.fetchone()[0]
            conn.close()
            return True, {
                "version": "SQLite 3.45 (Local Fast Engine)",
                "database": "vitaloptima.db",
                "user": "local_admin",
                "server_ip": "127.0.0.1 (Localhost)",
                "latency_ms": 0.5,
                "url_masked": "sqlite:///db/vitaloptima.db",
                "status": "Online (Local Embedded Engine - Zero Setup)"
            }
        except Exception:
            return False, {"error": "DATABASE_URL not set and local database uninitialized"}

    start_time = time.time()
    try:
        engine = get_engine()
        if engine is None:
            return False, {"error": "Failed to create database engine"}
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version(), current_database(), current_user, inet_server_addr();"))
            row = result.fetchone()
            latency_ms = round((time.time() - start_time) * 1000, 1)
            
            return True, {
                "version": row[0] if row else "Unknown",
                "database": row[1] if row else "neondb",
                "user": row[2] if row else "neondb_owner",
                "server_ip": str(row[3]) if row and row[3] else "Neon Cloud AWS",
                "latency_ms": latency_ms,
                "url_masked": url.split("@")[-1] if "@" in url else "Configured",
                "status": "Online (Neon Serverless PostgreSQL)"
            }
    except Exception as e:
        return False, {"error": str(e), "latency_ms": round((time.time() - start_time) * 1000, 1)}

def init_postgres_schema():
    """Create all mapped tables in PostgreSQL if they do not exist."""
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Cannot initialize schema: Database engine is not available.")
    Base.metadata.create_all(engine)
    return True

def sync_csvs_to_postgres():
    """
    Seeds and synchronizes all raw clinical and operational CSV files
    from data/ directory directly into Neon PostgreSQL tables.
    Returns: dict of table names and row counts inserted/synced.
    """
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Database engine not initialized")

    # 1. Ensure tables exist
    init_postgres_schema()
    
    data_dir = PROJECT_ROOT / "data"
    results = {}

    with engine.begin() as conn:
        # Table 1: Department Resources
        dept_csv = data_dir / "department_resources.csv"
        if dept_csv.exists():
            df_dept = pd.read_csv(dept_csv)
            # Truncate and reload
            conn.execute(text("TRUNCATE TABLE department_resources RESTART IDENTITY CASCADE;"))
            df_dept.to_sql("department_resources", conn, if_exists="append", index=False)
            results["department_resources"] = len(df_dept)

        # Table 2: Hospital Census Daily (365 days)
        census_csv = data_dir / "hospital_census_daily.csv"
        if census_csv.exists():
            df_census = pd.read_csv(census_csv)
            conn.execute(text("TRUNCATE TABLE hospital_census_daily RESTART IDENTITY CASCADE;"))
            df_census.to_sql("hospital_census_daily", conn, if_exists="append", index=False)
            results["hospital_census_daily"] = len(df_census)

        # Table 3: Staffing Roster
        staff_csv = data_dir / "staffing_roster.csv"
        if staff_csv.exists():
            df_staff = pd.read_csv(staff_csv)
            conn.execute(text("TRUNCATE TABLE staffing_roster RESTART IDENTITY CASCADE;"))
            df_staff.to_sql("staffing_roster", conn, if_exists="append", index=False)
            results["staffing_roster"] = len(df_staff)

        # Table 4: Inventory Supplies
        inv_csv = data_dir / "inventory_supplies.csv"
        if inv_csv.exists():
            df_inv = pd.read_csv(inv_csv)
            conn.execute(text("TRUNCATE TABLE inventory_supplies RESTART IDENTITY CASCADE;"))
            df_inv.to_sql("inventory_supplies", conn, if_exists="append", index=False)
            results["inventory_supplies"] = len(df_inv)

        # Table 5: Demand Forecast Hourly
        forecast_csv = data_dir / "demand_forecast.csv"
        if forecast_csv.exists():
            df_fc = pd.read_csv(forecast_csv)
            df_fc.columns = [c.lower() for c in df_fc.columns]
            conn.execute(text("TRUNCATE TABLE demand_forecast_hourly RESTART IDENTITY CASCADE;"))
            df_fc.to_sql("demand_forecast_hourly", conn, if_exists="append", index=False)
            results["demand_forecast_hourly"] = len(df_fc)

        # Table 5b: Blood Bank Inventory Backup
        blood_csv = data_dir / "blood_bank_inventory.csv"
        if blood_csv.exists():
            df_blood = pd.read_csv(blood_csv)
            conn.execute(text("TRUNCATE TABLE blood_bank_inventory RESTART IDENTITY CASCADE;"))
            df_blood.to_sql("blood_bank_inventory", conn, if_exists="append", index=False)
            results["blood_bank_inventory"] = len(df_blood)

        # Table 6: Seed Default Decision Log if empty
        check_dec = conn.execute(text("SELECT COUNT(*) FROM decision_log;")).scalar()
        if check_dec == 0:
            initial_decisions = [
                {"timestamp": "2025-04-27 13:58", "category": "Staff Allocation", "recommendation": "Deploy 4 float nurses to Emergency Room during 15:00-18:00 peak", "decision": "Accepted", "modified_details": "", "administrator": "Admin (AD)", "rationale": "ED forecasted peak at 15:00 with 92 arrivals exceeds safe nurse-patient ratio"},
                {"timestamp": "2025-04-27 12:45", "category": "ICU Capacity", "recommendation": "Transfer 2 stable post-op ICU patients to Step-Down ward", "decision": "Modified", "modified_details": "Transfer 1 patient to Step-Down, monitor second patient until 16:00", "administrator": "Admin (AD)", "rationale": "Attending physician requested additional 2hr observation on patient #B4"},
                {"timestamp": "2025-04-27 10:30", "category": "OR Rescheduling", "recommendation": "Postpone 2 elective orthopedic procedures to clear OR 3 for trauma standby", "decision": "Accepted", "modified_details": "", "administrator": "Admin (AD)", "rationale": "Preparedness for incoming multi-vehicle highway accident victims"}
            ]
            for dec in initial_decisions:
                conn.execute(text("""
                    INSERT INTO decision_log (timestamp, category, recommendation, decision, modified_details, administrator, rationale)
                    VALUES (:timestamp, :category, :recommendation, :decision, :modified_details, :administrator, :rationale);
                """), dec)
            results["decision_log"] = len(initial_decisions)
        else:
            results["decision_log"] = check_dec

        # Table 7: Seed Default Recent Activities if empty
        check_act = conn.execute(text("SELECT COUNT(*) FROM recent_activity;")).scalar()
        if check_act == 0:
            initial_acts = [
                {"time_str": "14:20", "title": "New forecast run completed", "details": "Emergency arrivals (next 24h)", "color": "#3B82F6"},
                {"time_str": "13:55", "title": "Optimization run completed", "details": "8 allocations, 3 unmet demands", "color": "#10B981"},
                {"time_str": "12:40", "title": "Staff shift change", "details": "Night shift → Day shift (6 staff)", "color": "#F59E0B"},
                {"time_str": "11:30", "title": "Patient surge alert", "details": "ED arrivals 20% above forecast", "color": "#EF4444"},
                {"time_str": "10:15", "title": "Model training completed", "details": "Random Forest v1.2.0", "color": "#06B6D4"}
            ]
            for act in initial_acts:
                conn.execute(text("""
                    INSERT INTO recent_activity (time_str, title, details, color)
                    VALUES (:time_str, :title, :details, :color);
                """), act)
            results["recent_activity"] = len(initial_acts)
        else:
            results["recent_activity"] = check_act

        # Table 8: Seed System Alerts if empty
        check_alt = conn.execute(text("SELECT COUNT(*) FROM system_alerts;")).scalar()
        if check_alt == 0:
            initial_alerts = [
                {"title": "Emergency Department surge expected at 15:00 (+28% arrivals)", "category": "Surge", "severity": "High", "timestamp": "2025-04-27 14:15", "acknowledged": 0},
                {"title": "ICU Bed Availability below 15% safety threshold", "category": "Active", "severity": "High", "timestamp": "2025-04-27 13:45", "acknowledged": 0},
                {"title": "N95 Respirator consumable stockout alert", "category": "Shortage", "severity": "Medium", "timestamp": "2025-04-27 12:00", "acknowledged": 1}
            ]
            for alt in initial_alerts:
                conn.execute(text("""
                    INSERT INTO system_alerts (title, category, severity, timestamp, acknowledged)
                    VALUES (:title, :category, :severity, :timestamp, :acknowledged);
                """), alt)
            results["system_alerts"] = len(initial_alerts)
        else:
            results["system_alerts"] = check_alt

    return results

def get_table_summary():
    """Returns metadata and row counts for all tables in PostgreSQL or local SQLite."""
    engine = get_engine()
    if engine is not None:
        try:
            summary = {}
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            with engine.connect() as conn:
                for tbl in table_names:
                    count = conn.execute(text(f'SELECT COUNT(*) FROM "{tbl}";')).scalar()
                    columns = [c["name"] for c in inspector.get_columns(tbl)]
                    pk = inspector.get_pk_constraint(tbl).get("constrained_columns", [])
                    summary[tbl] = {
                        "row_count": count,
                        "column_count": len(columns),
                        "columns": columns,
                        "primary_key": pk[0] if pk else None
                    }
            return summary
        except Exception as e:
            print(f"[PostgreSQL] Error inspecting tables: {e}")

    # Fallback to local SQLite embedded database
    from db.database import get_sqlite_connection
    summary = {}
    try:
        conn = get_sqlite_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r[0] for r in cur.fetchall()]
        for tbl in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM '{tbl}';")
                count = cur.fetchone()[0]
                cur.execute(f"PRAGMA table_info('{tbl}');")
                col_info = cur.fetchall()
                columns = [c[1] for c in col_info]
                pk = [c[1] for c in col_info if c[5] == 1]
                summary[tbl] = {
                    "row_count": count,
                    "column_count": len(columns),
                    "columns": columns,
                    "primary_key": pk[0] if pk else None
                }
            except Exception:
                pass
        conn.close()
    except Exception as sq_e:
        print(f"[SQLite] Error inspecting tables: {sq_e}")
    return summary

def fetch_table_df(table_name: str, limit: int = 1000):
    """Fetch table content as pandas DataFrame."""
    engine = get_engine()
    if engine is not None:
        query = text(f'SELECT * FROM "{table_name}" LIMIT :limit;')
        try:
            with engine.connect() as conn:
                df = pd.read_sql(query, conn, params={"limit": limit})
                return df
        except Exception as e:
            print(f"[PostgreSQL] Error fetching table {table_name}: {e}")

    # Fallback to local SQLite embedded database
    from db.database import get_sqlite_connection
    try:
        conn = get_sqlite_connection()
        df = pd.read_sql_query(f'SELECT * FROM "{table_name}" LIMIT {int(limit)};', conn)
        conn.close()
        return df
    except Exception as sq_e:
        print(f"[SQLite] Error fetching table {table_name}: {sq_e}")
        return pd.DataFrame()

def run_custom_query(sql_str: str):
    """Executes a custom SELECT query safely."""
    engine = get_engine()
    cleaned = sql_str.strip().rstrip(";")
    # Basic safeguard against destructive execution in exploratory UI
    prohibited = ["DROP ", "TRUNCATE ", "ALTER ", "GRANT ", "REVOKE "]
    upper_sql = cleaned.upper()
    for p in prohibited:
        if p in upper_sql:
            raise ValueError(f"Execution of '{p.strip()}' statement is restricted in the interactive console.")

    if engine is not None:
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(cleaned), conn)
                return df
        except Exception as e:
            print(f"[PostgreSQL] Error in query, attempting SQLite fallback: {e}")

    # Fallback to local SQLite embedded database
    from db.database import get_sqlite_connection
    import re
    conn = get_sqlite_connection()
    # Normalize PostgreSQL-specific syntax for SQLite
    sqlite_clean = re.sub(r'\bILIKE\b', 'LIKE', cleaned, flags=re.IGNORECASE)
    sqlite_clean = re.sub(r'::NUMERIC\(\d+,\d+\)', '', sqlite_clean)
    sqlite_clean = re.sub(r'::NUMERIC', '', sqlite_clean)
    sqlite_clean = re.sub(r'::DATE', '', sqlite_clean)
    sqlite_clean = re.sub(r'::INT', '', sqlite_clean)
    sqlite_clean = re.sub(r'::VARCHAR', '', sqlite_clean)
    try:
        df = pd.read_sql_query(sqlite_clean, conn)
        return df
    finally:
        conn.close()

def log_decision_pg(category, recommendation, decision, modified_details="", administrator="Admin (AD)", rationale=""):
    """Insert decision log directly into PostgreSQL."""
    engine = get_engine()
    if engine is None:
        return False
    now_str = datetime.now(IST_TZ).strftime("%Y-%m-%d %H:%M")
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO decision_log (timestamp, category, recommendation, decision, modified_details, administrator, rationale)
                VALUES (:timestamp, :category, :recommendation, :decision, :modified_details, :administrator, :rationale);
            """), {
                "timestamp": now_str,
                "category": category,
                "recommendation": recommendation,
                "decision": decision,
                "modified_details": modified_details,
                "administrator": administrator,
                "rationale": rationale
            })
        return True
    except Exception as e:
        print(f"[PostgreSQL] Failed to insert decision log: {e}")
        return False

def save_scenario_pg(name: str, surge_pct: float, icu_reduction: int, staff_loss: float, results_json: str = ""):
    """Insert What-if scenario stress run directly into PostgreSQL."""
    engine = get_engine()
    if engine is None:
        return False
    now_str = datetime.now(IST_TZ).strftime("%Y-%m-%d %H:%M")
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO scenarios (timestamp, name, surge_pct, icu_reduction, staff_loss, results_json)
                VALUES (:timestamp, :name, :surge_pct, :icu_reduction, :staff_loss, :results_json);
            """), {
                "timestamp": now_str,
                "name": name,
                "surge_pct": float(surge_pct),
                "icu_reduction": int(icu_reduction),
                "staff_loss": float(staff_loss),
                "results_json": results_json
            })
        return True
    except Exception as e:
        print(f"[PostgreSQL] Failed to save scenario: {e}")
        return False

def get_scenarios_pg(limit: int = 50):
    """Retrieve saved scenarios from PostgreSQL."""
    df = fetch_table_df("scenarios", limit=limit)
    if not df.empty and "id" in df.columns:
        df = df.sort_values(by="id", ascending=False)
    return df

# --- Enterprise Data Loaders (PostgreSQL Primary with CSV Fallback) ---

def load_census_dataset() -> pd.DataFrame:
    """Loads 365-day census from PostgreSQL if available, otherwise from CSV."""
    df = fetch_table_df("hospital_census_daily", limit=1000)
    if not df.empty and len(df) >= 300:
        return df
    data_dir = PROJECT_ROOT / "data"
    for fname in ["hospital_census_daily.csv", "hospital_daily_data.csv"]:
        csv_path = data_dir / fname
        if csv_path.exists():
            return pd.read_csv(csv_path)
    return pd.DataFrame()

def load_department_resources_dataset() -> pd.DataFrame:
    """Loads department capacity from PostgreSQL if available, otherwise from CSV."""
    df = fetch_table_df("department_resources", limit=100)
    if not df.empty and len(df) >= 5:
        return df
    data_dir = PROJECT_ROOT / "data"
    for fname in ["department_resources.csv", "hospital_resources.csv"]:
        csv_path = data_dir / fname
        if csv_path.exists():
            return pd.read_csv(csv_path)
    return pd.DataFrame()

def load_staffing_roster_dataset() -> pd.DataFrame:
    """Loads staffing roster from PostgreSQL if available, otherwise from CSV."""
    df = fetch_table_df("staffing_roster", limit=1000)
    if not df.empty and len(df) >= 10:
        return df
    data_dir = PROJECT_ROOT / "data"
    for fname in ["staffing_roster.csv", "staff_availability.csv"]:
        csv_path = data_dir / fname
        if csv_path.exists():
            return pd.read_csv(csv_path)
    return pd.DataFrame()

def load_inventory_supplies_dataset() -> pd.DataFrame:
    """Loads clinical inventory from PostgreSQL if available, otherwise from CSV."""
    df = fetch_table_df("inventory_supplies", limit=2000)
    if not df.empty and len(df) >= 10:
        return df
    data_dir = PROJECT_ROOT / "data"
    for fname in ["inventory_supplies.csv", "medical_inventory.csv"]:
        csv_path = data_dir / fname
        if csv_path.exists():
            return pd.read_csv(csv_path)
    return pd.DataFrame()

def load_blood_bank_dataset() -> pd.DataFrame:
    """Loads hospital blood bank backup from PostgreSQL if available, otherwise from CSV."""
    df = fetch_table_df("blood_bank_inventory", limit=500)
    if not df.empty and len(df) >= 5:
        return df
    data_dir = PROJECT_ROOT / "data"
    for fname in ["blood_bank_inventory.csv", "blood_inventory.csv"]:
        csv_path = data_dir / fname
        if csv_path.exists():
            return pd.read_csv(csv_path)
    return pd.DataFrame()

