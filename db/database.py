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
