#!/usr/bin/env python3
"""
VitalOptima Automated Database Backup Utility
Performs an atomic, zero-downtime backup of the active SQLite database
using the SQLite Online Backup API, verifies file integrity, and computes SHA-256 hash.
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

from db.database import backup_database
from config import BASE_DIR


def sha256_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="VitalOptima Zero-Downtime Database Backup CLI")
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Custom destination path for the backup file (.db)"
    )
    args = parser.parse_args()

    backups_dir = BASE_DIR / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    dest_path = Path(args.output) if args.output else backups_dir / f"vitaloptima_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"

    print(f"[*] Initiating atomic zero-downtime backup to: {dest_path}")
    start_time = datetime.utcnow()

    try:
        created_path = backup_database(dest_path)
    except Exception as e:
        print(f"[!] ERROR: Failed to execute backup: {e}", file=sys.stderr)
        sys.exit(1)

    # Verify integrity of the newly created backup
    try:
        conn = sqlite3.connect(str(created_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        status = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        print(f"[!] ERROR: Backup file failed SQLite integrity check: {e}", file=sys.stderr)
        sys.exit(1)

    if status.lower() != "ok":
        print(f"[!] WARNING: Integrity check returned: {status}", file=sys.stderr)
        sys.exit(2)

    checksum = sha256_file(Path(created_path))
    file_size_kb = round(Path(created_path).stat().st_size / 1024, 2)
    elapsed = (datetime.utcnow() - start_time).total_seconds()

    print("[+] SUCCESS: Database backup created and verified.")
    print(f"    - File: {created_path}")
    print(f"    - Size: {file_size_kb} KB")
    print(f"    - Tables: {table_count}")
    print(f"    - Integrity: {status}")
    print(f"    - SHA-256: {checksum}")
    print(f"    - Duration: {elapsed:.2f}s")


if __name__ == "__main__":
    main()

