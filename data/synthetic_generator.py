"""
VitalOptima Synthetic Data Generator
Generates realistic, de-identified synthetic hospital telemetry, census logs,
and arrival distributions for the 24-hour command center operations.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
from config import DATA_DIR

def generate_departments_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / "departments.csv"
    
    data = [
        {"Department": "Emergency", "Total Beds": 60, "Occupied": 52, "Available": 6, "Unavailable": 2, "Occupancy": 87, "Color": "#EF4444"},
        {"Department": "Internal Medicine", "Total Beds": 80, "Occupied": 64, "Available": 12, "Unavailable": 4, "Occupancy": 80, "Color": "#F59E0B"},
        {"Department": "Surgery", "Total Beds": 70, "Occupied": 56, "Available": 10, "Unavailable": 4, "Occupancy": 80, "Color": "#F59E0B"},
        {"Department": "Pediatrics", "Total Beds": 40, "Occupied": 28, "Available": 8, "Unavailable": 4, "Occupancy": 70, "Color": "#10B981"},
        {"Department": "ICU", "Total Beds": 40, "Occupied": 34, "Available": 6, "Unavailable": 0, "Occupancy": 85, "Color": "#EF4444"},
        {"Department": "Maternity", "Total Beds": 30, "Occupied": 24, "Available": 4, "Unavailable": 2, "Occupancy": 80, "Color": "#F59E0B"},
    ]
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    return df

def generate_demand_forecast_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / "demand_forecast.csv"

    # 25 hourly points from Now (0h) to 24h
    hours = [
        "Now", "1h", "2h", "3h", "4h", "5h", "6h", "7h", "8h", "9h", "10h", 
        "11h", "12h", "13h", "14h", "15h", "16h", "17h", "18h", "19h", "20h", "21h", "22h", "23h", "24h"
    ]
    
    # Exact curve matching the dashboard mockup:
    # Starts around 40-45, dips to ~38 at 3h, climbs to 70 at 8h, peak at 92 at 15h, then settles to 68-70 at 24h
    predicted_arrivals = [
        42, 48, 52, 46, 44, 42, 40, 52, 68, 62, 59, 
        72, 65, 78, 84, 92, 85, 76, 68, 62, 65, 72, 70, 68, 66
    ]
    
    # Historical average (slightly lower/smoother)
    historical_arrivals = [
        38, 41, 45, 42, 40, 39, 36, 45, 55, 54, 52, 
        60, 58, 66, 70, 75, 70, 64, 58, 54, 56, 60, 58, 55, 54
    ]
    
    # Capacity limit for ED
    capacity_limit = [100] * len(hours)
    
    # Available total hospital capacity for the Demand vs Capacity graph (approx 100 rising to 155, then easing)
    available_capacity = [
        100, 102, 106, 112, 118, 124, 132, 142, 148, 150, 152,
        155, 152, 150, 146, 140, 138, 136, 134, 130, 128, 126, 128, 130, 132
    ]

    df = pd.DataFrame({
        "Hour": hours,
        "Hour_Index": list(range(len(hours))),
        "Predicted_Demand": predicted_arrivals,
        "Historical_Demand": historical_arrivals,
        "Emergency_Capacity": capacity_limit,
        "Available_Capacity": available_capacity
    })
    df.to_csv(csv_path, index=False)
    return df

def get_alerts():
    active_alerts = [
        {
            "id": 1,
            "title": "ICU capacity constraint",
            "desc": "ICU beds at 85% utilization",
            "time": "14:15",
            "severity": "High",
            "category": "Active"
        },
        {
            "id": 2,
            "title": "Operating room bottleneck",
            "desc": "OR utilization at 92%",
            "time": "13:50",
            "severity": "Medium",
            "category": "Active"
        },
        {
            "id": 3,
            "title": "General bed shortage",
            "desc": "Only 52 beds available",
            "time": "12:30",
            "severity": "Medium",
            "category": "Active"
        }
    ]

    shortage_alerts = [
        {
            "id": 4,
            "title": "Staff shortage - Night shift",
            "desc": "2 nurses short in Surgical Dept",
            "time": "11:40",
            "severity": "High",
            "category": "Shortage"
        },
        {
            "id": 5,
            "title": "ED demand forecast",
            "desc": "+20% expected in next 6 hours",
            "time": "10:15",
            "severity": "Medium",
            "category": "Shortage"
        },
        {
            "id": 6,
            "title": "Pediatrics bed gap",
            "desc": "5 beds needed",
            "time": "09:20",
            "severity": "Medium",
            "category": "Shortage"
        },
        {
            "id": 7,
            "title": "IV fluids stock (forecast)",
            "desc": "Shortage in 3 days",
            "time": "08:45",
            "severity": "Low",
            "category": "Shortage"
        }
    ]
    return active_alerts, shortage_alerts

if __name__ == "__main__":
    generate_departments_data()
    generate_demand_forecast_data()
    print("Synthetic data generated successfully.")
