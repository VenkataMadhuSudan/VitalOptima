"""
VitalOptima — Global Configuration & System Metadata
Defines constants, paths, timezone defaults, and system identification.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Root paths
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
ML_OUTPUTS_DIR = PROJECT_ROOT / "ml_outputs"
DB_DIR = PROJECT_ROOT / "db"
DB_PATH = DB_DIR / "vitaloptima.db"
ASSETS_DIR = PROJECT_ROOT / "assets"

# System Branding & Admin metadata
HOSPITAL_NAME = "VitalOptima Memorial Hospital & Trauma Center"
ADMIN_USER = "Dr. Sarah Jenkins (Chief Medical Officer)"
ADMIN_INITIALS = "SJ"

# Timezone (Indian Standard Time UTC+5:30)
IST_TZ = timezone(timedelta(hours=5, minutes=30), name="IST")

def get_ist_now() -> datetime:
    """Return the current datetime localized to IST."""
    return datetime.now(IST_TZ)

def get_system_timestamp() -> str:
    """Return a human-readable real-time system clock string in IST."""
    now = get_ist_now()
    return now.strftime("%b %d, %Y • %I:%M %p IST")

# Pre-computed fallback string
SYSTEM_TIMESTAMP = get_system_timestamp()
