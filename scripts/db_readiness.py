#!/usr/bin/env python3
"""
VitalOptima Standalone Database Readiness Probe CLI
Used by container orchestrators (Kubernetes init containers / Docker health checks)
and CI/CD deployment pipelines to verify storage engine liveness, schema completeness,
partial index integrity, and round-trip write latency before traffic routing.
"""
import sys
import time
import json
import argparse
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_PATH

REQUIRED_TABLES = {"users", "patient_admissions", "audit_logs", "scenarios", "decision_log"}


def check_db_readiness(timeout_sec: float = 10.0, verbose: bool = False) -> dict:
    t0 = time.time()
    report = {
        "status": "UNHEALTHY",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "engine": "SQLite",
        "db_path": str(DB_PATH),
        "checks": {}
    }

    # 1. Check file existence and directory permissions
    try:
        report["checks"]["file_exists"] = DB_PATH.exists()
        parent_dir = DB_PATH.parent
        report["checks"]["dir_writable"] = parent_dir.exists() and os_can_write(parent_dir)
    except Exception as e:
        report["checks"]["file_exists"] = False
        report["checks"]["dir_writable"] = False
        report["error"] = f"Filesystem check failed: {str(e)}"
        return report

    # 2. Connection and read latency probe
    try:
        t_conn = time.time()
        conn = sqlite3.connect(str(DB_PATH), timeout=timeout_sec)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        res = cur.fetchone()
        read_latency_ms = round((time.time() - t_conn) * 1000, 2)
        report["checks"]["connection"] = res == (1,)
        report["checks"]["read_latency_ms"] = read_latency_ms
    except Exception as e:
        report["checks"]["connection"] = False
        report["error"] = f"Connection failed: {str(e)}"
        return report

    # 3. Schema completeness: verify required tables exist
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {row[0] for row in cur.fetchall()}
        missing = REQUIRED_TABLES - existing_tables
        report["checks"]["existing_tables"] = sorted(list(existing_tables))
        report["checks"]["missing_tables"] = sorted(list(missing))
        report["checks"]["tables_complete"] = len(missing) == 0
    except Exception as e:
        report["checks"]["tables_complete"] = False
        report["error"] = f"Table inspection failed: {str(e)}"
        conn.close()
        return report

    # 4. Partial Unique Index Invariant Verification
    try:
        cur.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_active_bed_occupancy';")
        idx_row = cur.fetchone()
        index_valid = idx_row is not None and "WHERE status = 'Admitted'" in idx_row[0]
        report["checks"]["bed_index_present"] = index_valid
    except Exception as e:
        report["checks"]["bed_index_present"] = False
        report["error"] = f"Index check failed: {str(e)}"
        conn.close()
        return report

    # 5. Round-trip write latency probe
    try:
        t_write = time.time()
        cur.execute("CREATE TABLE IF NOT EXISTS _health_probe (id INTEGER PRIMARY KEY, ts TEXT);")
        cur.execute("INSERT INTO _health_probe (ts) VALUES (CURRENT_TIMESTAMP);")
        cur.execute("DELETE FROM _health_probe WHERE id = last_insert_rowid();")
        conn.commit()
        write_latency_ms = round((time.time() - t_write) * 1000, 2)
        report["checks"]["write_latency_ms"] = write_latency_ms
        report["checks"]["write_functional"] = True
    except Exception as e:
        report["checks"]["write_functional"] = False
        report["checks"]["write_error"] = str(e)
    finally:
        conn.close()

    # PostgreSQL optional secondary check
    try:
        from db.postgres import get_engine
        from sqlalchemy import text
        pg_engine = get_engine()
        if pg_engine is not None:
            t_pg = time.time()
            with pg_engine.connect() as pg_conn:
                pg_conn.execute(text("SELECT 1;"))
            report["checks"]["postgres_available"] = True
            report["checks"]["postgres_latency_ms"] = round((time.time() - t_pg) * 1000, 2)
        else:
            report["checks"]["postgres_available"] = False
    except Exception as e:
        report["checks"]["postgres_available"] = False
        report["checks"]["postgres_notice"] = str(e)

    total_latency_ms = round((time.time() - t0) * 1000, 2)
    report["total_check_time_ms"] = total_latency_ms

    # Final readiness determination
    is_ready = (
        report["checks"].get("connection", False)
        and report["checks"].get("tables_complete", False)
        and report["checks"].get("bed_index_present", False)
        and report["checks"].get("write_functional", False)
    )
    report["status"] = "READY" if is_ready else "UNHEALTHY"
    return report


def os_can_write(directory: Path) -> bool:
    test_file = directory / ".write_probe.tmp"
    try:
        with open(test_file, "w") as f:
            f.write("probe")
        test_file.unlink()
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="VitalOptima Database Readiness CLI")
    parser.add_argument("--timeout", type=float, default=10.0, help="Connection timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress output; exit code only")
    args = parser.parse_args()

    result = check_db_readiness(timeout_sec=args.timeout)

    if not args.quiet:
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status_symbol = "[OK]" if result["status"] == "READY" else "[FAIL]"
            print(f"{status_symbol} Database Readiness: {result['status']} ({result.get('total_check_time_ms')} ms)")
            print(f"  - Read Latency: {result['checks'].get('read_latency_ms')} ms")
            print(f"  - Write Latency: {result['checks'].get('write_latency_ms')} ms")
            print(f"  - Tables Present: {result['checks'].get('tables_complete')} ({len(result['checks'].get('existing_tables', []))} tables)")
            print(f"  - Bed Concurrency Index: {result['checks'].get('bed_index_present')}")
            if result.get("checks", {}).get("postgres_available"):
                print(f"  - PostgreSQL Secondary Sync: READY ({result['checks'].get('postgres_latency_ms')} ms)")

    sys.exit(0 if result["status"] == "READY" else 1)


if __name__ == "__main__":
    main()
