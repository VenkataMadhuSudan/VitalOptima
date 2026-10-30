#!/usr/bin/env python3
"""
VitalOptima Automated Database Restore Utility
Safely restores the active SQLite database from a verified backup snapshot
using the SQLite Online Backup API with pre-flight and post-flight integrity checks.
"""
import sys
import argparse
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import restore_database
from config import DB_PATH


def sha256_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="VitalOptima Safe Database Restore CLI")
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to the source backup file (.db)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Bypass interactive confirmation prompt"
    )
    args = parser.parse_args()

    src_path = Path(args.input)
    if not src_path.is_file():
        print(f"[!] ERROR: Backup file not found at: {src_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Pre-flight inspection of backup file: {src_path}")
    try:
        conn = sqlite3.connect(str(src_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        status = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        print(f"[!] ERROR: Source backup failed SQLite integrity check: {e}", file=sys.stderr)
        sys.exit(1)

    if status.lower() != "ok":
        print(f"[!] ERROR: Source backup integrity check failed with: {status}", file=sys.stderr)
        sys.exit(2)

    checksum = sha256_file(src_path)
    print(f"[+] Source backup is healthy ({table_count} tables, integrity OK, SHA-256: {checksum[:16]}...)")
    print(f"[*] Target destination is active database: {DB_PATH}")

    if not args.force:
        confirm = input("[?] Are you sure you want to overwrite active database? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            print("[-] Restore operation aborted by operator.")
            sys.exit(0)

    try:
        restore_database(src_path)
    except Exception as e:
        print(f"[!] ERROR: Database restore failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Post-restore check on DB_PATH
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        post_status = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        print(f"[!] ERROR: Active database verification failed post-restore: {e}", file=sys.stderr)
        sys.exit(1)

    print("[+] SUCCESS: Active database successfully restored from snapshot.")
    print(f"    - Target: {DB_PATH}")
    print(f"    - Active Database Integrity: {post_status}")


if __name__ == "__main__":
    main()

