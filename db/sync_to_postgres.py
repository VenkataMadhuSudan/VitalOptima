"""
VitalOptima - Data Sync and Schema Migration Script for PostgreSQL
Initializes all PostgreSQL tables on Neon and syncs all CSV datasets.
"""
import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.postgres import test_connection, sync_csvs_to_postgres, get_table_summary

def main():
    print("=" * 60)
    print("VitalOptima - Neon PostgreSQL Migration & Data Sync")
    print("=" * 60)
    
    print("\n[Step 1/3] Testing PostgreSQL Cloud Connectivity...")
    ok, info = test_connection()
    if not ok:
        print(f"FAILED Connection error: {info.get('error')}")
        sys.exit(1)
        
    print(f"SUCCESS! Connected to Neon PostgreSQL:")
    print(f"   Database : {info.get('database')}")
    print(f"   User     : {info.get('user')}")
    print(f"   Latency  : {info.get('latency_ms')} ms")
    print(f"   Version  : {info.get('version')[:40]}...")

    print("\n[Step 2/3] Mapping Schemas & Ingesting Datasets from CSVs...")
    results = sync_csvs_to_postgres()
    print("Ingestion Report:")
    for table_name, count in results.items():
        print(f"   * {table_name:<25}: {count:>5} records")

    print("\n[Step 3/3] Inspecting PostgreSQL Database Catalog...")
    summary = get_table_summary()
    for tbl, meta in summary.items():
        cols = ", ".join(meta["columns"][:4]) + ("..." if len(meta["columns"]) > 4 else "")
        print(f"   Table: {tbl:<25} | Rows: {meta['row_count']:>5} | Cols: {meta['column_count']:>2} ({cols})")

    print("\n" + "=" * 60)
    print("All tables mapped and live in Neon PostgreSQL!")
    print("=" * 60)

if __name__ == "__main__":
    main()
