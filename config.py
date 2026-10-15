"""
VitalOptima Configuration and Constants
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "vitaloptima.db"
ML_OUTPUTS_DIR = BASE_DIR / "ml_outputs"

from datetime import datetime, timezone, timedelta

# IST Timezone (UTC+5:30)
IST_TZ = timezone(timedelta(hours=5, minutes=30), name="IST")

def get_ist_now() -> datetime:
    """Returns the current datetime in Indian Standard Time (IST)."""
    return datetime.now(IST_TZ)

def get_system_timestamp() -> str:
    """Returns current IST timestamp formatted as 'Oct 14, 2026 22:45'."""
    return get_ist_now().strftime("%b %d, %Y %H:%M")

def get_current_shift() -> dict:
    """
    Returns current hospital clinical shift details based on IST hour:
    - Morning Shift: 07:00 - 15:00 IST
    - Evening Shift: 15:00 - 23:00 IST
    - Night Shift: 23:00 - 07:00 IST
    """
    hour = get_ist_now().hour
    if 7 <= hour < 15:
        return {
            "name": "Morning Shift",
            "hours": "07:00 - 15:00 IST",
            "icon": "☀️",
            "lead": "Dr. Ramesh Patel",
            "staff_active": 142
        }
    elif 15 <= hour < 23:
        return {
            "name": "Evening Shift",
            "hours": "15:00 - 23:00 IST",
            "icon": "🌆",
            "lead": "Dr. Priya Sharma",
            "staff_active": 128
        }
    else:
        return {
            "name": "Night Shift",
            "hours": "23:00 - 07:00 IST",
            "icon": "🌙",
            "lead": "Dr. Vikram Sethi",
            "staff_active": 85
        }

def get_greeting(user_name: str = "Admin") -> tuple[str, str]:
    """
    Returns dynamic greeting title and contextual subtitle based on current IST time of day.
    """
    now = get_ist_now()
    hour = now.hour
    shift = get_current_shift()
    
    if 5 <= hour < 12:
        title = f"Good morning, {user_name}"
        subtitle = f"{shift['icon']} {shift['name']} active ({shift['hours']}). Here's your hospital census overview for today."
    elif 12 <= hour < 17:
        title = f"Good afternoon, {user_name}"
        subtitle = f"{shift['icon']} {shift['name']} peak volume underway ({shift['hours']}). Here's what's happening at your hospital today."
    elif 17 <= hour < 22:
        title = f"Good evening, {user_name}"
        subtitle = f"{shift['icon']} {shift['name']} active ({shift['hours']}). Reviewing overnight bed capacity and shift handover."
    else:
        title = f"Good evening, {user_name}"
        subtitle = f"{shift['icon']} {shift['name']} operational ({shift['hours']}). Emergency arrivals, trauma response, and ICU beds tracked live."
    return title, subtitle

# Hospital Metadata
HOSPITAL_NAME = "City General Hospital"
SYSTEM_TIMEZONE = "IST"
ADMIN_USER = "Admin"
ADMIN_INITIALS = "AD"

def __getattr__(name):
    if name == "SYSTEM_TIMESTAMP":
        return get_system_timestamp()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Core Operational Baselines (derived from official 365-day census & department capacity)
GENERAL_BEDS_TOTAL = 300
GENERAL_BEDS_OCCUPIED = 238
GENERAL_BEDS_AVAILABLE = 50
GENERAL_BEDS_RATE = 79

ICU_BEDS_TOTAL = 30
ICU_BEDS_OCCUPIED = 23
ICU_BEDS_AVAILABLE = 5
ICU_BEDS_RATE = 77

STAFF_TOTAL = 410
STAFF_SCHEDULED = 405
STAFF_AVAILABLE = 393
STAFF_ASSIGNED = 393
STAFF_SHORTAGE = 12
STAFF_RATE = 97

OR_TOTAL = 12
OR_OPERATIONAL = 8
OR_UNAVAILABLE = 1
OR_SCHEDULED = 8
OR_AVAILABLE_SLOTS = 3
OR_RATE = 67

# Color Palette
COLORS = {
    "primary": "#1E60F2",
    "primary_dark": "#0B192C",
    "sidebar_bg": "#071426",
    "card_bg": "#FFFFFF",
    "bg_light": "#F4F7FC",
    "text_dark": "#1E293B",
    "text_muted": "#64748B",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "success": "#10B981",
    "info": "#3B82F6",
    "border": "#E2E8F0"
}
