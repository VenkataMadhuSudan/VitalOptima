#!/usr/bin/env python3
"""
VitalOptima - synthetic hospital operations dataset generator.

ALL DATA IS SYNTHETIC. It is not clinically validated and does not represent
any real hospital. Run:  python generate_dataset.py

Outputs (./data):
    hospital_daily_data.csv      (File A, 365 rows)
    hospital_resources.csv       (File B, snapshot)
    staff_availability.csv       (File C, 7 days x 3 shifts)
    medical_inventory.csv        (File D, 30 days x 11 items)
    ground_truth_surge_events.csv   (generator metadata, NOT a model feature)
    dataset_metadata.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from schemas import (DAILY_COLUMNS, INVENTORY_COLUMNS, RESOURCES_COLUMNS,
                     STAFF_COLUMNS)

# ----------------------------------------------------------------- config
SEED = 42
START_DATE = "2025-01-01"
N_DAYS = 365
BURN_IN_DAYS = 30            # simulated then discarded so day 1 is not a cold start
INVENTORY_DAYS = 30
STAFF_DAYS = 7
OUT_DIR = Path("data")

GENERAL_BEDS_TOTAL = 300
ICU_BEDS_TOTAL = 30

# Per-day-of-week multipliers, Monday=0 ... Sunday=6 (illustrative, invented)
ED_DOW = np.array([1.08, 1.02, 1.00, 1.00, 1.03, 0.96, 0.95])
ELECTIVE_MEAN = np.array([17, 18, 17, 16, 13, 2.5, 1.0])      # elective admits/day
DISCHARGE_DOW = np.array([1.00, 1.00, 1.02, 1.05, 1.25, 0.80, 0.65])
DISCHARGE_DOW = DISCHARGE_DOW / DISCHARGE_DOW.mean()
STAFF_BASE_DOW = np.array([420, 420, 420, 420, 410, 380, 370])

ED_BASE_ARRIVALS = 170       # mean ED arrivals/day before seasonality
ED_ADMIT_PROB = 0.20         # share of ED arrivals admitted
ICU_ADMIT_PROB = 0.10        # share of admissions going straight to ICU
GEN_DISCHARGE_RATE = 0.20    # daily discharge hazard for general-ward census
ICU_EXIT_PROB = 0.20         # daily ICU exit (step-down) hazard

# ---------------------------------------------------------- File A: daily
def _build_surge_events(rng, total_days):
    """Four demand surges (one per quarter); triangular ramp up/down."""
    mult = np.ones(total_days)
    events = []
    first_date = pd.Timestamp(START_DATE) - pd.Timedelta(days=BURN_IN_DAYS)
    quarter = N_DAYS // 4
    for q in range(4):
        lo = BURN_IN_DAYS + q * quarter + 10
        hi = BURN_IN_DAYS + (q + 1) * quarter - 15
        start = int(rng.integers(lo, hi))
        dur = int(rng.integers(4, 8))
        peak = float(rng.uniform(1.30, 1.60))
        for k in range(dur):
            shape = 1 - abs(2 * (k + 0.5) / dur - 1)
            mult[start + k] = max(mult[start + k], 1 + (peak - 1) * shape)
        events.append({
            "event_type": "emergency_surge",
            "start_date": (first_date + pd.Timedelta(days=start)).strftime("%Y-%m-%d"),
            "end_date": (first_date + pd.Timedelta(days=start + dur - 1)).strftime("%Y-%m-%d"),
            "duration_days": dur,
            "peak_multiplier": round(peak, 3),
        })
    return mult, events


def generate_daily_data(rng):
    """Simulate hospital flow day by day.

    Accounting (simplified, no explicit transfer column):
      * admissions = elective_admissions + emergency admissions (admitted ED patients)
      * icu_admissions are the subset of admissions placed directly in ICU
      * every ICU exit is a step-down transfer to the general ward (no ICU deaths /
        direct ICU discharges are modelled)
      * every discharge leaves from the general ward ('discharges' = all hospital exits)
      * general_t = general_{t-1} + (admissions - icu_admissions) - discharges + icu_exits
      * icu_t     = icu_{t-1} + icu_admissions - icu_exits
      * hence total_occupied_t = total_occupied_{t-1} + admissions_t - discharges_t
      * If beds are full, elective cases are cancelled first, then ED admissions are
        diverted; those diverted patients are NOT counted in 'admissions'.
    """
    total_days = BURN_IN_DAYS + N_DAYS
    first_date = pd.Timestamp(START_DATE) - pd.Timedelta(days=BURN_IN_DAYS)
    surge_mult, events = _build_surge_events(rng, total_days)

    rows = []
    gen_prev, icu_prev = 215, 22          # arbitrary start; erased by burn-in
    for i in range(total_days):
        date = first_date + pd.Timedelta(days=i)
        dow = date.dayofweek
        surge = surge_mult[i]
        season = 1 + 0.08 * math.cos(2 * math.pi * (date.dayofyear - 20) / 365.25)

        arrivals = int(rng.poisson(ED_BASE_ARRIVALS * ED_DOW[dow] * season * surge))
        admit_p = min(0.35, ED_ADMIT_PROB * (1 + 0.25 * (surge - 1)))
        em_adm = int(rng.binomial(arrivals, admit_p))
        elective = int(rng.poisson(ELECTIVE_MEAN[dow]))

        # discharges depend on yesterday's general census; pressure speeds them up
        pressure = (gen_prev + icu_prev) / (GENERAL_BEDS_TOTAL + ICU_BEDS_TOTAL)
        rate = GEN_DISCHARGE_RATE * DISCHARGE_DOW[dow]
        if pressure > 0.90:
            rate *= 1 + (pressure - 0.90) * 3
        disch = int(rng.binomial(gen_prev, min(0.5, rate)))

        icu_exits = int(rng.binomial(icu_prev, ICU_EXIT_PROB))
        icu_exits = min(icu_exits, GENERAL_BEDS_TOTAL - (gen_prev - disch))

        # ICU admissions limited by free ICU beds
        icu_p = min(0.5, ICU_ADMIT_PROB * (1 + 0.8 * (surge - 1)))
        icu_desired = int(rng.binomial(em_adm + elective, icu_p))
        icu_free = ICU_BEDS_TOTAL - (icu_prev - icu_exits)
        icu_adm = max(0, min(icu_desired, icu_free))

        # general-ward capacity cap: cancel electives first, then divert ED admits
        free_general = GENERAL_BEDS_TOTAL - (gen_prev - disch + icu_exits)
        excess = (em_adm + elective - icu_adm) - free_general
        if excess > 0:
            cut = min(elective, excess)
            elective -= cut
            em_adm -= excess - cut
        admissions = em_adm + elective

        gen = gen_prev - disch + icu_exits + (admissions - icu_adm)
        icu = icu_prev - icu_exits + icu_adm

        base_staff = int(STAFF_BASE_DOW[dow])
        sick = int(rng.binomial(base_staff, 0.04 + 0.05 * (surge - 1)))
        surgeries = int(rng.poisson(0.9 * elective) + rng.poisson(2.5))

        rows.append({
            "date": date, "day_of_week": date.day_name(),
            "admissions": admissions, "emergency_arrivals": arrivals,
            "discharges": disch, "icu_admissions": icu_adm,
            "elective_admissions": elective,
            "general_beds_occupied": gen, "icu_beds_occupied": icu,
            "general_beds_total": GENERAL_BEDS_TOTAL, "icu_beds_total": ICU_BEDS_TOTAL,
            "staff_available": base_staff - sick, "surgeries_scheduled": surgeries,
        })
        gen_prev, icu_prev = gen, icu

    df = pd.DataFrame(rows)
    # ALOS via Little's law over a trailing 7-day window: mean census / mean admissions
    census = df["general_beds_occupied"] + df["icu_beds_occupied"]
    df["average_length_of_stay_days"] = (
        census.rolling(7, min_periods=1).mean()
        / df["admissions"].rolling(7, min_periods=1).mean()
    ).round(2)
    df = df.iloc[BURN_IN_DAYS:].reset_index(drop=True)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df[DAILY_COLUMNS], pd.DataFrame(events)


# ------------------------------------------------------- File B: resources
GENERAL_DEPTS = [("GB-MED", "Medicine", 120), ("GB-SUR", "Surgery", 80),
                 ("GB-ORT", "Orthopedics", 40), ("GB-PED", "Pediatrics", 30),
                 ("GB-OBS", "Obstetrics", 30)]
ICU_DEPTS = [("ICU-MICU", "Medical ICU", 18), ("ICU-SICU", "Surgical ICU", 12)]
OR_DEPTS = [("OR-MAIN", "Main Theatre", 8), ("OR-DAY", "Day Surgery", 2),
            ("OR-EMG", "Emergency Theatre", 2)]
ED_DEPTS = [("ED-ADULT", "ED Adult", 28), ("ED-PEDS", "ED Pediatric", 8),
            ("ED-RESUS", "ED Resuscitation", 6)]
assert sum(c for *_, c in GENERAL_DEPTS) == GENERAL_BEDS_TOTAL
assert sum(c for *_, c in ICU_DEPTS) == ICU_BEDS_TOTAL


def _allocate(total, caps, rng):
    """Split an integer `total` across buckets, never exceeding each cap."""
    caps = np.asarray(caps, dtype=int)
    if total > caps.sum():
        raise ValueError("total exceeds summed capacity")
    alloc = np.minimum(np.floor(total * caps / caps.sum()).astype(int), caps)
    remaining = int(total - alloc.sum())
    while remaining > 0:
        room = np.flatnonzero(alloc < caps)
        pick = int(rng.choice(room, p=caps[room] / caps[room].sum()))
        alloc[pick] += 1
        remaining -= 1
    return alloc


def generate_resources(daily, rng):
    """Snapshot at the last date of the daily file (illustrative 08:00 view).

    Convention:
      usable_capacity    = total_capacity - unavailable_capacity
      available_capacity = usable_capacity - occupied_capacity   (physically free, in service)
      staffed_capacity   <= usable_capacity  (units staff can safely operate right now)
      occupied_capacity  <= usable_capacity  (always)
      staffing gap       = max(0, occupied - staffed)  (allowed; shows understaffed units)
    forecast_demand is an ILLUSTRATIVE placeholder for optimizer testing, NOT a model
    prediction. Replace it with real model output downstream.
    """
    last = daily.iloc[-1]
    gen_occ, icu_occ = int(last["general_beds_occupied"]), int(last["icu_beds_occupied"])

    gen_unav = int(min(rng.integers(8, 15), GENERAL_BEDS_TOTAL - gen_occ))
    icu_unav = int(min(rng.integers(0, 3), ICU_BEDS_TOTAL - icu_occ))

    groups = [
        ("General Bed", GENERAL_DEPTS, _allocate(gen_unav, [c for *_, c in GENERAL_DEPTS], rng), gen_occ),
        ("ICU Bed", ICU_DEPTS, _allocate(icu_unav, [c for *_, c in ICU_DEPTS], rng), icu_occ),
        ("Operating Room", OR_DEPTS, np.array([1, 0, 0]), None),   # 1 theatre in maintenance
        ("ED Treatment Space", ED_DEPTS, np.array([2, 0, 0]), None),  # 2 adult bays out of service
    ]

    rows = []
    for rtype, depts, unav, total_occ in groups:
        caps = np.array([c for *_, c in depts])
        usable = caps - unav
        if total_occ is not None:
            occ = _allocate(total_occ, usable, rng)
        else:
            occ = np.array([int(round(u * rng.uniform(0.5, 0.9))) for u in usable])
        for (rid, dept, cap), un, us, oc in zip(depts, unav, usable, occ):
            gap = int(rng.integers(0, 3))
            staffed = max(int(us) - gap, int(oc))
            demand = int(round(int(oc) * rng.uniform(0.98, 1.08)))
            rows.append({"resource_id": rid, "resource_type": rtype, "department": dept,
                         "total_capacity": cap, "unavailable_capacity": int(un),
                         "occupied_capacity": int(oc), "staffed_capacity": staffed,
                         "forecast_demand": demand, "_usable": int(us)})

    # Illustrative shortage scenarios for optimizer testing
    by_id = {r["resource_id"]: r for r in rows}
    r = by_id["ICU-SICU"]; r["forecast_demand"] = r["_usable"] + 2        # capacity shortage
    r["staffed_capacity"] = max(r["_usable"] - 2, 0)
    r = by_id["GB-MED"]; r["staffed_capacity"] = max(r["occupied_capacity"] - 4, 0)  # staffing shortage
    r["forecast_demand"] = r["occupied_capacity"] + 5
    r = by_id["ED-ADULT"]; r["forecast_demand"] = r["_usable"] + 3        # ED crowding
    r["staffed_capacity"] = max(r["_usable"] - 3, 0)
    r = by_id["OR-EMG"]; r["forecast_demand"] = r["_usable"] + 1          # emergency OR shortage
    r["staffed_capacity"] = max(r["_usable"] - 1, 0)

    out = pd.DataFrame(rows)
    out["available_capacity"] = out["_usable"] - out["occupied_capacity"]
    return out[RESOURCES_COLUMNS]


# ------------------------------------------------------- File C: staffing
SHIFTS = ["Morning", "Evening", "Night"]   # 07-15, 15-23, 23-07 (8 h each, illustrative)
# (department, role): (max hours per 7-day period, min rest hours between shifts)
ROLE_POLICY = {
    "General Ward Nurse": (40, 11), "ICU Nurse": (40, 11), "Doctor": (48, 11),
    "Emergency Department Staff": (40, 11), "Operating Room Staff": (40, 11),
}
# ILLUSTRATIVE patients-per-nurse planning parameters - NOT clinical standards.
ASSUMED_PATIENTS_PER_NURSE = {
    ("General Ward", "Morning"): 7, ("General Ward", "Evening"): 8, ("General Ward", "Night"): 12,
    ("ICU", "Morning"): 2, ("ICU", "Evening"): 2, ("ICU", "Night"): 2,
}
FIXED_REQUIRED = {  # (department, role, shift): headcount, invented for demonstration
    ("General Ward", "Doctor", "Morning"): 6, ("General Ward", "Doctor", "Evening"): 4,
    ("General Ward", "Doctor", "Night"): 2,
    ("ICU", "Doctor", "Morning"): 3, ("ICU", "Doctor", "Evening"): 3, ("ICU", "Doctor", "Night"): 2,
    ("Emergency Department", "Doctor", "Morning"): 5, ("Emergency Department", "Doctor", "Evening"): 5,
    ("Emergency Department", "Doctor", "Night"): 3,
    ("Emergency Department", "Emergency Department Staff", "Morning"): 14,
    ("Emergency Department", "Emergency Department Staff", "Evening"): 14,
    ("Emergency Department", "Emergency Department Staff", "Night"): 10,
    ("Operating Room", "Operating Room Staff", "Morning"): 30,
    ("Operating Room", "Operating Room Staff", "Evening"): 9,
    ("Operating Room", "Operating Room Staff", "Night"): 6,
}
# Planned shortages: (day_index, shift, department, role) -> missing headcount
INJECTED_STAFF_SHORTFALLS = {
    (2, "Night", "ICU", "ICU Nurse"): 5,
    (3, "Evening", "Emergency Department", "Emergency Department Staff"): 4,
    (4, "Morning", "General Ward", "General Ward Nurse"): 6,
    (5, "Night", "ICU", "Doctor"): 1,
    (5, "Morning", "Operating Room", "Operating Room Staff"): 6,
}
STAFF_UNITS = [("General Ward", "General Ward Nurse"), ("ICU", "ICU Nurse"),
               ("General Ward", "Doctor"), ("ICU", "Doctor"),
               ("Emergency Department", "Doctor"),
               ("Emergency Department", "Emergency Department Staff"),
               ("Operating Room", "Operating Room Staff")]


def generate_staff(daily, rng):
    """Roster for the 7 days AFTER the last daily date. Only head-counts are
    generated (no individual staff IDs), so shift-overlap checks do not apply."""
    last = daily.iloc[-1]
    census = {"General Ward": int(last["general_beds_occupied"]), "ICU": int(last["icu_beds_occupied"])}
    start = pd.Timestamp(last["date"]) + pd.Timedelta(days=1)
    rows = []
    for d in range(STAFF_DAYS):
        date = start + pd.Timedelta(days=d)
        weekend = date.dayofweek >= 5
        for shift in SHIFTS:
            for dept, role in STAFF_UNITS:
                if role.endswith("Nurse"):
                    required = math.ceil(census[dept] / ASSUMED_PATIENTS_PER_NURSE[(dept, shift)])
                else:
                    required = FIXED_REQUIRED[(dept, role, shift)]
                    if role == "Operating Room Staff" and weekend and shift != "Night":
                        required = int(round(required * 0.35))
                available = max(0, int(round(required * rng.normal(1.02, 0.04))))
                short = INJECTED_STAFF_SHORTFALLS.get((d, shift, dept, role))
                if short:
                    available = max(0, required - short)
                max_h, rest_h = ROLE_POLICY[role]
                rows.append({"date": date.strftime("%Y-%m-%d"), "shift": shift,
                             "department": dept, "staff_role": role,
                             "available_count": available, "required_count": required,
                             "maximum_permitted_working_hours": max_h,
                             "minimum_rest_hours_between_shifts": rest_h})
    return pd.DataFrame(rows)[STAFF_COLUMNS]


# ----------------------------------------------------- File D: inventory
# (id, name incl. unit, category, driver, rate per driver unit per day, lead days)
ITEMS = [
    ("IV-NS500", "Normal saline 0.9% 500 mL (bag)", "IV Fluids", "patient_days", 0.80, 3),
    ("IV-RL500", "Ringer's lactate 500 mL (bag)", "IV Fluids", "patient_days", 0.35, 3),
    ("GLV-EXM", "Nitrile exam gloves (pair)", "Gloves", "patient_days", 14.0, 4),
    ("GLV-STR", "Sterile surgical gloves (pair)", "Gloves", "surgeries", 2.2, 5),
    ("SYR-5ML", "Syringe 5 mL (unit)", "Syringes", "patient_days", 2.5, 4),
    ("SYR-10ML", "Syringe 10 mL (unit)", "Syringes", "patient_days", 1.2, 4),
    ("MSK-SURG", "Surgical mask (unit)", "Masks", "staff", 2.5, 5),
    ("MSK-N95", "N95 respirator (unit)", "Masks", "staff", 0.35, 7),
    ("OTC-PARA500", "Paracetamol 500 mg tablet, OTC (tablet)", "Non-prescription Consumables", "patient_days", 1.5, 6),
    ("OTC-WIPE", "Antiseptic wipe (unit)", "Non-prescription Consumables", "patient_days", 1.8, 3),
    ("OTC-GAUZE", "Sterile gauze pad (unit)", "Non-prescription Consumables", "patient_days", 2.0, 4),
]
STOCKOUT_RISK_ITEM = "MSK-N95"                 # low threshold + long lead time
SUPPLIER_DELAY = {"IV-NS500": (1, 3)}         # item: (order index, extra days late)


def generate_inventory(daily, rng):
    """Consumption is driven by census / surgeries / staff from the daily file.
    closing = opening + incoming - consumption. If demand exceeds available stock,
    consumption is capped at available stock (unmet demand is not recorded)."""
    tail = daily.tail(INVENTORY_DAYS).reset_index(drop=True)
    drivers = {
        "patient_days": (tail["general_beds_occupied"] + tail["icu_beds_occupied"]).to_numpy(float),
        "surgeries": tail["surgeries_scheduled"].to_numpy(float),
        "staff": tail["staff_available"].to_numpy(float),
    }
    rows = []
    for item_id, name, cat, driver, rate, lead in ITEMS:
        expected = rate * drivers[driver]
        avg = expected.mean()
        demand = np.maximum(0, np.round(expected * rng.normal(1.0, 0.06, INVENTORY_DAYS))).astype(int)
        order_qty = int(math.ceil(avg * 10 / 10) * 10)
        if item_id == STOCKOUT_RISK_ITEM:
            threshold = int(math.ceil(avg * lead * 0.80))
            stock = int(math.ceil(avg * lead * 1.07))
        else:
            threshold = int(math.ceil(avg * (lead + 1.5)))
            stock = threshold + int(math.ceil(avg * 4))
        pipeline, n_orders = [], 0
        for d in range(INVENTORY_DAYS):
            opening = stock
            incoming = sum(q for a, q in pipeline if a == d)
            pipeline = [(a, q) for a, q in pipeline if a != d]
            available = opening + incoming
            used = min(int(demand[d]), available)
            closing = available - used
            if closing + sum(q for _, q in pipeline) <= threshold:
                late = 0
                if item_id in SUPPLIER_DELAY and n_orders == SUPPLIER_DELAY[item_id][0]:
                    late = SUPPLIER_DELAY[item_id][1]
                pipeline.append((d + lead + late, order_qty))
                n_orders += 1
            rows.append({"date": tail["date"][d], "item_id": item_id, "item_name": name,
                         "item_category": cat, "opening_stock": opening,
                         "daily_consumption": used, "incoming_stock": incoming,
                         "closing_stock": closing, "reorder_threshold": threshold,
                         "supplier_lead_time_days": lead})
            stock = closing
    return pd.DataFrame(rows)[INVENTORY_COLUMNS]


# ------------------------------------------------------------------- main
def main():
    from validate_dataset import validate_all   # local import keeps module standalone-friendly

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # independent child streams -> editing one generator never changes the others
    rngs = {k: np.random.default_rng([SEED, i]) for i, k in enumerate(["daily", "res", "staff", "inv"])}
    daily, events = generate_daily_data(rngs["daily"])
    resources = generate_resources(daily, rngs["res"])
    staff = generate_staff(daily, rngs["staff"])
    inventory = generate_inventory(daily, rngs["inv"])

    outputs = {
        "hospital_daily_data.csv": daily, "hospital_resources.csv": resources,
        "staff_availability.csv": staff, "medical_inventory.csv": inventory,
        "ground_truth_surge_events.csv": events,
    }
    for fname, frame in outputs.items():
        frame.to_csv(OUT_DIR / fname, index=False)

    metadata = {
        "synthetic": True,
        "disclaimer": "Fully synthetic. Not clinically validated; not representative of any real hospital.",
        "seed": SEED, "start_date": START_DATE, "n_days": N_DAYS, "burn_in_days": BURN_IN_DAYS,
        "resources_snapshot_date": daily["date"].iloc[-1],
        "staff_roster_dates": [staff["date"].min(), staff["date"].max()],
        "inventory_dates": [inventory["date"].min(), inventory["date"].max()],
        "units": "all capacities/occupancies in beds, rooms or treatment spaces; staff in head-count per shift",
        "forecast_demand_note": "placeholder inputs for optimizer testing, not model predictions",
        "stockout_risk_item": STOCKOUT_RISK_ITEM, "supplier_delay_scenarios": SUPPLIER_DELAY,
        "injected_staff_shortfalls": [
            {"day_index": k[0], "shift": k[1], "department": k[2], "role": k[3], "missing": v}
            for k, v in INJECTED_STAFF_SHORTFALLS.items()],
    }
    (OUT_DIR / "dataset_metadata.json").write_text(json.dumps(metadata, indent=2))

    print("Generated files:")
    for fname, frame in outputs.items():
        print(f"  {(OUT_DIR / fname).resolve()}  rows={len(frame)}")
    print(f"  {(OUT_DIR / 'dataset_metadata.json').resolve()}")
    print("\nValidation:")
    ok = validate_all(OUT_DIR)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
