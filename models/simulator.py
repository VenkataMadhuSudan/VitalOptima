"""
VitalOptima What-If Scenario Simulator
Simulates complex stress events: mass casualty surges, infectious outbreaks,
ICU capacity loss, and sudden healthcare worker shortages.
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
from config import (
    GENERAL_BEDS_TOTAL, GENERAL_BEDS_OCCUPIED, GENERAL_BEDS_RATE,
    ICU_BEDS_TOTAL, ICU_BEDS_OCCUPIED, ICU_BEDS_RATE,
    STAFF_TOTAL, STAFF_AVAILABLE, STAFF_RATE,
    OR_TOTAL, OR_OPERATIONAL
)

class ScenarioSimulator:
    def __init__(self):
        pass

    def run_simulation(self, surge_pct=0.0, icu_loss_beds=0, staff_shortage_pct=0.0):
        """
        Runs a what-if stress test based on user sliders.
        surge_pct: percentage increase in patient arrival demand (0 to 100%)
        icu_loss_beds: number of ICU beds taken out of service (0 to 20)
        staff_shortage_pct: sudden loss in available nursing/clinical staff (0 to 50%)
        """
        # Baseline arrivals
        base_arrivals = 63.1  # average hourly
        surge_arrivals = base_arrivals * (1 + surge_pct / 100.0)
        
        # Bed calculations
        # Inpatient conversion rate from arrivals ~ 22%
        additional_admissions = (surge_arrivals - base_arrivals) * 0.22 * 24
        
        sim_gen_occupied = min(GENERAL_BEDS_TOTAL, GENERAL_BEDS_OCCUPIED + int(additional_admissions * 0.85))
        sim_gen_avail = max(0, GENERAL_BEDS_TOTAL - sim_gen_occupied)
        sim_gen_rate = round((sim_gen_occupied / GENERAL_BEDS_TOTAL) * 100, 1)

        # ICU calculations
        sim_icu_total = max(1, ICU_BEDS_TOTAL - icu_loss_beds)
        additional_icu_admissions = int(additional_admissions * 0.15)
        sim_icu_occupied = min(sim_icu_total, ICU_BEDS_OCCUPIED + additional_icu_admissions)
        sim_icu_avail = max(0, sim_icu_total - sim_icu_occupied)
        sim_icu_rate = round((sim_icu_occupied / sim_icu_total) * 100, 1)

        # Staff calculations
        sim_staff_available = int(STAFF_AVAILABLE * (1 - staff_shortage_pct / 100.0))
        # Required staff: 1 nurse per 4 general patients, 1 nurse per 1.5 ICU patients
        required_staff = int((sim_gen_occupied / 4.0) + (sim_icu_occupied / 1.5))
        sim_staff_shortage = max(0, required_staff - sim_staff_available)
        sim_staff_rate = round(min(100.0, (sim_staff_available / max(1, required_staff)) * 100), 1)

        # Bottlenecks and alerts
        bottlenecks = []
        if sim_icu_rate >= 95.0:
            bottlenecks.append({
                "resource": "ICU Capacity",
                "severity": "Critical",
                "message": f"ICU saturation at {sim_icu_rate}%. Immediate overflow diversion required."
            })
        elif sim_icu_rate >= 88.0:
            bottlenecks.append({
                "resource": "ICU Capacity",
                "severity": "High",
                "message": f"ICU at elevated {sim_icu_rate}% capacity. Reserve margin exhausted."
            })

        if sim_gen_rate >= 92.0:
            bottlenecks.append({
                "resource": "General Inpatient Beds",
                "severity": "High",
                "message": f"General bed occupancy at {sim_gen_rate}%. Discharge lounge activation needed."
            })

        if sim_staff_shortage > 0:
            bottlenecks.append({
                "resource": "Clinical Staffing",
                "severity": "Critical" if sim_staff_shortage > 20 else "High",
                "message": f"Estimated deficit of {sim_staff_shortage} nurses to maintain safe acuity ratios."
            })

        # Recommended mitigations
        mitigations = []
        if surge_pct >= 25.0:
            mitigations.append("Activate Hospital Incident Command System (HICS) Level 2.")
            mitigations.append("Implement Fast-Track protocol in ED for low-acuity triage.")
        if icu_loss_beds >= 5 or sim_icu_rate >= 90.0:
            mitigations.append("Designate Post-Anesthesia Care Unit (PACU) as temporary ICU surge annex.")
            mitigations.append("Expedite transfer of step-down ready patients to telemetry floors.")
        if staff_shortage_pct >= 15.0 or sim_staff_shortage > 10:
            mitigations.append("Cancel voluntary elective admissions for next 48 hours to conserve clinical staff.")
            mitigations.append("Authorize overtime and activate voluntary float-pool registry.")

        if not mitigations:
            mitigations.append("Normal operational protocols adequate. Continue routine monitoring.")

        return {
            "inputs": {
                "surge_pct": surge_pct,
                "icu_loss_beds": icu_loss_beds,
                "staff_shortage_pct": staff_shortage_pct
            },
            "metrics": {
                "general_beds": {
                    "total": GENERAL_BEDS_TOTAL,
                    "occupied": sim_gen_occupied,
                    "available": sim_gen_avail,
                    "rate": sim_gen_rate,
                    "delta": round(sim_gen_rate - GENERAL_BEDS_RATE, 1)
                },
                "icu_beds": {
                    "total": sim_icu_total,
                    "occupied": sim_icu_occupied,
                    "available": sim_icu_avail,
                    "rate": sim_icu_rate,
                    "delta": round(sim_icu_rate - ICU_BEDS_RATE, 1)
                },
                "staff": {
                    "available": sim_staff_available,
                    "required": required_staff,
                    "shortage": sim_staff_shortage,
                    "rate": sim_staff_rate,
                    "delta": round(sim_staff_rate - STAFF_RATE, 1)
                }
            },
            "bottlenecks": bottlenecks,
            "mitigations": mitigations
        }

if __name__ == "__main__":
    sim = ScenarioSimulator()
    res = sim.run_simulation(surge_pct=30, icu_loss_beds=5, staff_shortage_pct=20)
    print("Simulation results generated:")
    print("ICU Rate:", res["metrics"]["icu_beds"]["rate"])
    print("Bottlenecks:", len(res["bottlenecks"]))
