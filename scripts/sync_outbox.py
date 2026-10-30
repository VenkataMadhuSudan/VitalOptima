#!/usr/bin/env python3
"""
VitalOptima Transactional Outbox Synchronization CLI
Replays pending mutations from SQLite `sync_outbox` journal to PostgreSQL
with idempotency guarantees and exponential retry tracking.
"""
import sys
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import sync_pending_outbox, get_sqlite_connection


def inspect_outbox():
    conn = get_sqlite_connection()
    c = conn.cursor()
    c.execute("""
        SELECT status, count(*) 
        FROM sync_outbox 
        GROUP BY status
    """)
    rows = c.fetchall()
    conn.close()
    return dict(rows)


def main():
    parser = argparse.ArgumentParser(description="VitalOptima Outbox Journal Replay CLI")
    parser.add_argument(
        "--status-only", "-s",
        action="store_true",
        help="Only display pending outbox event counts without executing sync"
    )
    args = parser.parse_args()

    print("[*] Inspecting transactional outbox journal...")
    counts = inspect_outbox()
    print(f"    - Current Outbox Status: {counts or 'Empty (0 events)'}")

    if args.status_only:
        sys.exit(0)

    pending_cnt = counts.get("PENDING", 0)
    failed_cnt = counts.get("FAILED", 0)

    if pending_cnt == 0 and failed_cnt == 0:
        print("[+] No pending or failed outbox events to replay. Everything is in sync.")
        sys.exit(0)

    print(f"[*] Initiating outbox replay for {pending_cnt} pending / {failed_cnt} failed events...")
    start_time = datetime.utcnow()
    result = sync_pending_outbox()
    elapsed = (datetime.utcnow() - start_time).total_seconds()

    print(f"[+] Outbox Replay Result: {result.get('status')}")
    print(f"    - Synced: {result.get('synced_count', 0)}")
    print(f"    - Failed: {result.get('failed_count', 0)}")
    print(f"    - Duration: {elapsed:.2f}s")


if __name__ == "__main__":
    main()

