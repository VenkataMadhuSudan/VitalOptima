"""
VitalOptima What-If Scenario Simulator NLP Engine
Domain-Trained Natural Language Query (NLQ) & Conversational Stress Simulation Assistant.
Interprets hypothetical English crisis inquiries, extracts mathematical stress parameters,
computes departmental vulnerabilities, resilience scores, staffing deficits, and generates
query-specific analytical tables tailored to the user's clinical inquiry intent.
"""
import os
import json
import re
import pandas as pd
from typing import Dict, Any, List, Tuple

# Baseline hospital capacities and occupancies (calibrated to VitalOptima command center)
BASE_ED, CAP_ED = 45, 45
BASE_GEN, CAP_GEN = 150, 160
BASE_ICU, CAP_ICU = 33, 26
BASE_OR, CAP_OR = 15, 18
BASE_NURSES = 75.0

# Curated Quick Scenario Inquiries
SIMULATOR_PROMPT_CHIPS = [
    ("💥 Mass Casualty Trauma Surge", "What happens if there is an 80% patient surge from a mass casualty incident?"),
    ("🦠 Severe Staff Viral Outbreak", "Simulate a severe respiratory outbreak causing 35% staff absenteeism and 40% surge"),
    ("☣️ Critical ICU Bio-Contamination", "What if HVAC contamination shuts down 50% of ICU beds with a 20% patient influx?"),
    ("❄️ Winter Epidemic Emergency", "Can our hospital handle a 65% winter respiratory epidemic with 25% ICU loss?"),
    ("👥 Extra Nurses Needed (+50%)", "How many extra nurses do we need if patient volume surges by 50%?"),
    ("🛏️ Total Bed Deficit (+75% Surge)", "What is the total bed deficit across all wards during a 75% patient surge?"),
    ("🛡️ Recommended HICS Protocols", "What emergency protocols and mitigations should we activate for a 90% disaster surge?"),
    ("📉 Hospital Resilience Breakdown", "Which department collapses first if emergency arrivals increase by 60%?")
]

PRESET_SCENARIOS = {
    "mass casualty": {
        "name": "Mass Casualty Incident (MCI)",
        "surge": 85, "icu": 10, "staff": 5,
        "context": "Severe external multi-casualty trauma wave impacting emergency and surgical suites."
    },
    "mci": {
        "name": "Mass Casualty Incident (MCI)",
        "surge": 85, "icu": 10, "staff": 5,
        "context": "Severe external multi-casualty trauma wave impacting emergency and surgical suites."
    },
    "trauma surge": {
        "name": "Mass Casualty Incident (MCI)",
        "surge": 85, "icu": 10, "staff": 5,
        "context": "Severe external multi-casualty trauma wave impacting emergency and surgical suites."
    },
    "contamination": {
        "name": "ICU Contamination & Unit Lockdown",
        "surge": 15, "icu": 50, "staff": 15,
        "context": "HVAC bio-contamination forcing acute isolation and temporary bed closure in critical care units."
    },
    "lockdown": {
        "name": "ICU Contamination & Unit Lockdown",
        "surge": 15, "icu": 50, "staff": 15,
        "context": "Biohazard lockdown forcing acute isolation and temporary bed closure."
    },
    "absenteeism": {
        "name": "Severe Viral Staff Absenteeism",
        "surge": 40, "icu": 15, "staff": 35,
        "context": "Widespread community respiratory illness causing sudden acute clinical staffing dropouts."
    },
    "staff shortage": {
        "name": "Severe Viral Staff Absenteeism",
        "surge": 40, "icu": 15, "staff": 35,
        "context": "Acute healthcare worker shortages straining active shift rosters."
    },
    "nurse strike": {
        "name": "Severe Viral Staff Absenteeism",
        "surge": 20, "icu": 10, "staff": 40,
        "context": "Workforce withdrawal causing critical nursing coverage deficits."
    },
    "winter": {
        "name": "Winter Respiratory Surge (Epidemic)",
        "surge": 65, "icu": 25, "staff": 15,
        "context": "Seasonal epidemic wave straining general inpatient beds and emergency triage throughput."
    },
    "epidemic": {
        "name": "Winter Respiratory Surge (Epidemic)",
        "surge": 65, "icu": 25, "staff": 15,
        "context": "Seasonal epidemic wave straining general inpatient beds and emergency triage throughput."
    },
    "pandemic": {
        "name": "Catastrophic Pandemic Wave",
        "surge": 90, "icu": 40, "staff": 30,
        "context": "Unprecedented regional health emergency testing operational limits."
    },
    "baseline": {
        "name": "Baseline Operations",
        "surge": 0, "icu": 0, "staff": 0,
        "context": "Standard historical operating parameters with no external crises."
    }
}


# =============================================================================
# INTENT-SPECIFIC DYNAMIC TABLE GENERATORS
# =============================================================================

def _build_staffing_table(surge: float, staff_absenteeism: float) -> pd.DataFrame:
    """Generates query-specific Clinical Staffing & Shift Acuity Roster Breakdown."""
    roles = [
        ("Emergency Department (Triage & Trauma RN)", 24, 0.75, "1:3 Emergency Acuity"),
        ("Intensive Care Unit (Critical Care RN)", 20, 0.85, "1:1.5 Critical Care Acuity"),
        ("General Inpatient Wards (Med-Surg Floor RN)", 22, 0.60, "1:4 Ward Patient Ratio"),
        ("Surgical OR Suites & PACU Recovery Staff", 9, 0.45, "1:1 Sterile Surgical Field")
    ]
    rows = []
    for role_name, base_count, surge_factor, acuity_target in roles:
        req = int(round(base_count * (1.0 + (surge * surge_factor) / 100.0)))
        absent = int(round(base_count * (staff_absenteeism / 100.0)))
        net_avail = max(1, base_count - absent)
        deficit = max(0, req - net_avail)
        cov_pct = round((net_avail / max(1, req)) * 100, 1)

        if deficit > 5 or cov_pct < 65:
            status = "🚨 Critical Shortage (Overtime Mandate)"
        elif deficit > 0 or cov_pct < 90:
            status = "⚠️ Moderate Deficit (Float Pool Deployed)"
        else:
            status = "✅ Full Shift Coverage"

        rows.append({
            "Clinical Unit / Staff Role": role_name,
            "Baseline Roster": base_count,
            "Required Under Surge": req,
            "Absenteeism Loss": absent,
            "Net Available Staff": net_avail,
            "Staff Deficit / Gap": f"+{deficit}" if deficit > 0 else "0",
            "Coverage %": f"{cov_pct}%",
            "Safe Acuity Target": acuity_target,
            "Roster Operational Status": status
        })
    return pd.DataFrame(rows)


def _build_mitigations_table(surge: float, icu_outage: float, staff_absenteeism: float,
                             crisis_ed: int, crisis_gen: int, crisis_icu: int,
                             eff_ed: int, eff_gen: int, eff_icu: int,
                             total_bed_deficit: int, nursing_deficit: float) -> pd.DataFrame:
    """Generates query-specific Disaster Mitigation & HICS Action Protocol Matrix."""
    protocols = [
        {
            "Protocol Code": "HICS-CMD-01",
            "Emergency Action Measure": "Activate Hospital Incident Command System (HICS) Level 2",
            "Activation Trigger": "Surge >= 25% or Multiple Unit Crisis",
            "Operational Lead": "Chief Medical Officer",
            "Target Resource Gain": "Unified Command & 4-Hour Briefings",
            "Urgency Level": "Immediate (< 1 Hour)",
            "Status": "🚨 Mandatory Activation" if surge >= 25.0 else "📋 Standby Readiness"
        },
        {
            "Protocol Code": "HICS-TRI-04",
            "Emergency Action Measure": "Emergency Fast-Track & Ambulatory Triage Diversion",
            "Activation Trigger": "ED Census > 45 Bays (100% Saturation)",
            "Operational Lead": "ED Medical Director",
            "Target Resource Gain": "+15 Low-Acuity ESI 4-5 Decants",
            "Urgency Level": "Immediate (< 2 Hours)",
            "Status": "🚨 Mandatory Activation" if crisis_ed > eff_ed else "📋 Standby Readiness"
        },
        {
            "Protocol Code": "HICS-ICU-08",
            "Emergency Action Measure": "Post-Anesthesia Care Unit (PACU) ICU Surge Annex Conversion",
            "Activation Trigger": "ICU Outage >= 10% or ICU Occupancy > 100%",
            "Operational Lead": "Director of Critical Care",
            "Target Resource Gain": "+8 Ventilated Critical Care Beds",
            "Urgency Level": "Urgent (< 4 Hours)",
            "Status": "🚨 Mandatory Activation" if (icu_outage >= 10.0 or crisis_icu > eff_icu) else "📋 Standby Readiness"
        },
        {
            "Protocol Code": "HICS-STF-12",
            "Emergency Action Measure": "Elective Surgery Postponement & Staff Float Deployment",
            "Activation Trigger": "Staff Absenteeism >= 15% or Nurse Deficit > 8",
            "Operational Lead": "Chief Nursing Officer",
            "Target Resource Gain": "+12 Floor RNs Reallocated from Elective",
            "Urgency Level": "Within 12 Hours",
            "Status": "🚨 Mandatory Activation" if (staff_absenteeism >= 15.0 or nursing_deficit > 8.0) else "📋 Standby Readiness"
        },
        {
            "Protocol Code": "HICS-DIS-15",
            "Emergency Action Measure": "Discharge Lounge Rapid Decant & Step-Down Acceleration",
            "Activation Trigger": "General Ward Occupancy >= 95%",
            "Operational Lead": "Inpatient Bed Czar",
            "Target Resource Gain": "+25 General Bed Turnovers per Day",
            "Urgency Level": "Within 6 Hours",
            "Status": "🚨 Mandatory Activation" if crisis_gen > eff_gen else "📋 Standby Readiness"
        },
        {
            "Protocol Code": "HICS-REG-19",
            "Emergency Action Measure": "Regional Mutual Aid Compact & Ambulance Trauma Diversion",
            "Activation Trigger": "Hospital-Wide Bed Deficit > 20 Beds",
            "Operational Lead": "Incident Commander",
            "Target Resource Gain": "Ambulance Diversion to Partner Hubs",
            "Urgency Level": "Immediate (< 1 Hour)",
            "Status": "🚨 Mandatory Activation" if total_bed_deficit > 20 else "📋 Standby Readiness"
        }
    ]
    return pd.DataFrame(protocols)


def _build_vulnerability_table(surge: float, icu_outage: float, staff_absenteeism: float,
                               crisis_ed: int, crisis_gen: int, crisis_icu: int, crisis_or: int,
                               eff_ed: int, eff_gen: int, eff_icu: int, eff_or: int) -> pd.DataFrame:
    """Generates query-specific Department Saturation & Failure Sequence Analysis."""
    # Calculated exact surge trigger percentage where unit hits 100% capacity
    # ED: 45 / 45 = 100% at surge 0.0%
    # ICU: baseline 33 vs 26 capacity -> already 127% at surge 0.0%
    # General Ward: baseline 150 vs 160 capacity -> hits 160 at surge = (160/150 - 1) / 0.010175 ~ 6.5%
    # OR: baseline 15 vs 18 capacity -> hits 18 at surge = (18/15 - 1) / 0.00491 ~ 40.7%
    items = [
        {
            "Failure Rank": "#1 (Immediate Saturation)",
            "Department": "Emergency Department (ED)",
            "Baseline Occupancy": f"{BASE_ED} / {CAP_ED} (100.0%)",
            "Failure Surge Threshold": "+0.0% Surge (Baseline Limit)",
            "Crisis Saturation": f"{round((crisis_ed / eff_ed) * 100, 1)}%",
            "Bed Shortfall": max(0, crisis_ed - eff_ed),
            "Time to Boarding Exhaustion": "< 1 Hour",
            "Primary Vulnerability Point": "Triage bay overflow and hallway boarding queues",
            "Risk Rating": "🚨 Critical Failure Point"
        },
        {
            "Failure Rank": "#2 (Critical Deficit)",
            "Department": "Intensive Care Unit (ICU)",
            "Baseline Occupancy": f"{BASE_ICU} / {eff_icu} ({round((BASE_ICU / eff_icu) * 100, 1)}%)",
            "Failure Surge Threshold": "+0.0% Surge (Outage Impact)",
            "Crisis Saturation": f"{round((crisis_icu / eff_icu) * 100, 1)}%",
            "Bed Shortfall": max(0, crisis_icu - eff_icu),
            "Time to Boarding Exhaustion": "< 2 Hours",
            "Primary Vulnerability Point": "Ventilator exhaustion and loss of step-down telemetry",
            "Risk Rating": "🚨 Critical Failure Point"
        },
        {
            "Failure Rank": "#3 (Inpatient Saturation)",
            "Department": "General Inpatient Ward",
            "Baseline Occupancy": f"{BASE_GEN} / {eff_gen} ({round((BASE_GEN / eff_gen) * 100, 1)}%)",
            "Failure Surge Threshold": "+6.5% Patient Surge",
            "Crisis Saturation": f"{round((crisis_gen / eff_gen) * 100, 1)}%",
            "Bed Shortfall": max(0, crisis_gen - eff_gen),
            "Time to Boarding Exhaustion": "< 6 Hours",
            "Primary Vulnerability Point": "Slow patient discharge turnover blocking admissions",
            "Risk Rating": "🚨 Critical Failure Point" if crisis_gen > eff_gen else "⚠️ Elevated Strain"
        },
        {
            "Failure Rank": "#4 (Delayed Bottleneck)",
            "Department": "Operating Room Suites (OR)",
            "Baseline Occupancy": f"{BASE_OR} / {eff_or} ({round((BASE_OR / eff_or) * 100, 1)}%)",
            "Failure Surge Threshold": "+40.7% Patient Surge",
            "Crisis Saturation": f"{round((crisis_or / eff_or) * 100, 1)}%",
            "Bed Shortfall": max(0, crisis_or - eff_or),
            "Time to Boarding Exhaustion": "12 - 24 Hours",
            "Primary Vulnerability Point": "Post-op holding delay and elective block congestion",
            "Risk Rating": "🚨 Bottleneck" if crisis_or > eff_or else "✅ Stable Buffer"
        }
    ]
    return pd.DataFrame(items)


def _build_icu_table(surge: float, icu_outage: float) -> pd.DataFrame:
    """Generates query-specific Critical Care & ICU Sub-Unit Capacity Stress Breakdown."""
    subunits = [
        ("Medical ICU (MICU)", 15, 13, 0.45, 12),
        ("Surgical CCU (SICU)", 12, 10, 0.35, 10),
        ("Cardiac Critical Care (CCU)", 6, 3, 0.20, 6),
        ("PACU ICU Surge Annex (Emergency Buffer)", 0, 8, 0.0, 8)
    ]
    rows = []
    for unit_name, base_beds, cap_beds, share, vents in subunits:
        outage_loss = int(round(cap_beds * (icu_outage / 100.0))) if base_beds > 0 else 0
        eff_cap = max(1, cap_beds - outage_loss) if base_beds > 0 else cap_beds
        add_demand = int(round(base_beds * (surge * 0.8939 / 100.0))) if base_beds > 0 else 0
        crisis_occ = base_beds + add_demand
        deficit = max(0, crisis_occ - eff_cap)
        util = round((crisis_occ / eff_cap) * 100, 1)

        rows.append({
            "Critical Care Sub-Unit": unit_name,
            "Baseline Census": base_beds,
            "Effective Beds (Post-Outage)": eff_cap,
            "Crisis Projected Demand": crisis_occ,
            "Critical Bed Deficit": f"+{deficit}" if deficit > 0 else "0",
            "Utilization Rate": f"{util}%",
            "Ventilator Buffer": f"{vents} Units",
            "Sub-Unit Status": "🚨 Saturated / Divert" if deficit > 0 else ("⚠️ Reserve Margin Tight" if util >= 85 else "✅ Normal Operating")
        })
    return pd.DataFrame(rows)


def _build_emergency_table(surge: float) -> pd.DataFrame:
    """Generates query-specific Emergency Department Triage & Boarding Stress Breakdown."""
    zones = [
        ("Resuscitation & Trauma Bays (Red Zone / ESI 1-2)", 8, 8, 1.15, "0 Min (Immediate)"),
        ("Acute Monitored Treatment Bays (Yellow Zone / ESI 3)", 25, 25, 1.05, "45 - 90 Min Delay"),
        ("Fast-Track Ambulatory Urgent Bays (Green Zone / ESI 4-5)", 12, 12, 0.85, "120 - 180 Min Delay"),
        ("Emergency Boarding Hallway Inpatient Overflow", 0, 15, 0.0, "Extended Boarding Queue")
    ]
    rows = []
    for zone_name, base_load, bay_cap, surge_mult, delay in zones:
        crisis_load = int(round(base_load * (1.0 + (surge * surge_mult) / 100.0))) if base_load > 0 else int(round(surge * 0.25))
        overflow = max(0, crisis_load - bay_cap)
        util = round((crisis_load / max(1, bay_cap)) * 100, 1)

        rows.append({
            "Triage Acuity Zone": zone_name,
            "Baseline Patient Census": base_load,
            "Crisis Surge Load": crisis_load,
            "Available Triage Bays": bay_cap,
            "Bay Overflow / Boarding Deficit": f"+{overflow}" if overflow > 0 else "0",
            "Acuity Utilization": f"{util}%",
            "Projected Triage Delay": delay,
            "Diversion Status": "🚨 Immediate Overflow Diversion" if overflow > 0 else "✅ Triage Flow Managed"
        })
    return pd.DataFrame(rows)


def _build_bed_capacity_table(surge: float, staff_absenteeism: float) -> pd.DataFrame:
    """Generates query-specific Hospital-Wide Inpatient Bed Allocation & Deficit Matrix."""
    wards = [
        ("Emergency Department (ED)", BASE_ED, CAP_ED, 1.006, 0.0),
        ("General Medicine Inpatient Ward", 85, 90, 1.015, 0.3),
        ("General Surgical Inpatient Ward", 45, 50, 1.020, 0.3),
        ("Pediatric & Neonatal Care Ward", 20, 20, 0.750, 0.2),
        ("Intensive Care Unit (Critical Care)", BASE_ICU, CAP_ICU, 0.8939, 0.1),
        ("Operating Room Post-Op Suites (PACU)", BASE_OR, CAP_OR, 0.491, 0.2)
    ]
    rows = []
    for ward_name, base_occ, total_cap, surge_mult, staff_penalty in wards:
        eff_cap = max(5, int(round(total_cap * (1.0 - (staff_absenteeism * staff_penalty) / 100.0))))
        crisis_occ = int(round(base_occ * (1.0 + (surge * surge_mult) / 100.0)))
        deficit = max(0, crisis_occ - eff_cap)
        util = round((crisis_occ / eff_cap) * 100, 1)

        rows.append({
            "Clinical Ward / Service Line": ward_name,
            "Baseline Census": base_occ,
            "Crisis Projected Occupancy": crisis_occ,
            "Staffed Bed Capacity": eff_cap,
            "Bed Deficit / Shortfall": f"+{deficit}" if deficit > 0 else "0",
            "Occupancy %": f"{util}%",
            "Overflow Routing Strategy": "Expedite Step-down to Telemetry" if deficit > 5 else ("Activate Discharge Lounge" if deficit > 0 else "Routine Admission")
        })
    return pd.DataFrame(rows)


def _build_overview_table(crisis_ed: int, crisis_gen: int, crisis_icu: int, crisis_or: int,
                          eff_ed: int, eff_gen: int, eff_icu: int, eff_or: int) -> pd.DataFrame:
    """Generates comprehensive high-level Departmental Bed Occupancy & Saturation Breakdown."""
    dept_stats = [
        {
            "Department": "Emergency Department (ED)",
            "Baseline Occupancy": BASE_ED,
            "Crisis Surge": crisis_ed,
            "Effective Capacity": eff_ed,
            "Bed Deficit": max(0, crisis_ed - eff_ed),
            "Utilization": f"{round((crisis_ed / eff_ed) * 100, 1)}%",
            "Status": "🚨 Saturated / Overflow" if crisis_ed > eff_ed else ("⚠️ Nearing Capacity" if crisis_ed >= eff_ed * 0.9 else "✅ Stable")
        },
        {
            "Department": "General Inpatient Ward",
            "Baseline Occupancy": BASE_GEN,
            "Crisis Surge": crisis_gen,
            "Effective Capacity": eff_gen,
            "Bed Deficit": max(0, crisis_gen - eff_gen),
            "Utilization": f"{round((crisis_gen / eff_gen) * 100, 1)}%",
            "Status": "🚨 Bed Shortage" if crisis_gen > eff_gen else ("⚠️ Nearing Capacity" if crisis_gen >= eff_gen * 0.9 else "✅ Stable")
        },
        {
            "Department": "Intensive Care Unit (ICU)",
            "Baseline Occupancy": BASE_ICU,
            "Crisis Surge": crisis_icu,
            "Effective Capacity": eff_icu,
            "Bed Deficit": max(0, crisis_icu - eff_icu),
            "Utilization": f"{round((crisis_icu / eff_icu) * 100, 1)}%",
            "Status": "🚨 Critical Outage" if crisis_icu > eff_icu else ("⚠️ Nearing Capacity" if crisis_icu >= eff_icu * 0.9 else "✅ Stable")
        },
        {
            "Department": "Operating Room (OR Suites)",
            "Baseline Occupancy": BASE_OR,
            "Crisis Surge": crisis_or,
            "Effective Capacity": eff_or,
            "Bed Deficit": max(0, crisis_or - eff_or),
            "Utilization": f"{round((crisis_or / eff_or) * 100, 1)}%",
            "Status": "🚨 Block Bottleneck" if crisis_or > eff_or else ("⚠️ Nearing Capacity" if crisis_or >= eff_or * 0.9 else "✅ Stable")
        }
    ]
    return pd.DataFrame(dept_stats)


# =============================================================================
# GOOGLE GEMINI GENERATIVE AI INTEGRATION (OPTIONAL CLOUD LLM ENGINE)
# =============================================================================

def run_gemini_what_if_simulation(query: str, api_key: str) -> Dict[str, Any]:
    """
    Executes deep clinical and logistics reasoning using Google Gemini Generative AI.
    Dynamically generates context-specific tables, HICS action plans, and scenario metrics.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        prompt = f"""You are the Chief Incident Commander and Operational AI for VitalOptima Command Center.
A hospital disaster coordinator asks this hypothetical emergency simulation inquiry:
"{query}"

Hospital Operational Baselines:
- Emergency Dept (ED): 45 triage bays (100% occupied at baseline)
- General Inpatient Ward: 160 staffed beds (150 occupied at baseline)
- Intensive Care Unit (ICU): 26 critical care beds (33 demand at baseline)
- Operating Room Suites: 18 surgical suites (15 occupied)
- Shift Nursing Roster: 75 active registered nurses

Analyze this crisis and return strictly valid JSON matching this schema:
{{
    "scenario_name": "Evocative, realistic scenario title (e.g. Mass Casualty Trauma Surge, Viral Respiratory Epidemic)",
    "parameters": {{
        "surge": integer 0-100,
        "icu_outage": integer 0-100,
        "staff_loss": integer 0-50
    }},
    "resilience_score": float 0-100,
    "matched_intent": "one of: staffing, mitigations, vulnerability, icu, emergency, bed_capacity, overview",
    "answer_summary": "Detailed, professional 2-3 paragraph clinical and logistics evaluation of this crisis",
    "table_title": "Descriptive, engaging title for the data table specifically relevant to this crisis",
    "table_rows": [
        {{"Department / Unit": "Emergency Department", "Baseline Census": 45, "Crisis Surge": 80, "Capacity": 45, "Deficit": 35, "Status": "Critical"}}
    ],
    "total_bed_deficit": integer,
    "nursing_deficit": float,
    "critical_departments_count": integer (0 to 4),
    "bottlenecks": [
        {{"severity": "Critical", "unit": "Unit name", "message": "Specific bottleneck details"}}
    ],
    "mitigations": [
        "Actionable HICS mitigation measure 1",
        "Actionable HICS mitigation measure 2",
        "Actionable HICS mitigation measure 3",
        "Actionable HICS mitigation measure 4"
    ],
    "key_insights": [
        "Executive takeaway 1",
        "Executive takeaway 2",
        "Executive takeaway 3"
    ]
}}
"""
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        data = json.loads(raw_text)

        table_rows = data.get("table_rows", [])
        primary_df = pd.DataFrame(table_rows) if table_rows else pd.DataFrame()

        surge = float(data.get("parameters", {}).get("surge", 50))
        icu = float(data.get("parameters", {}).get("icu_outage", 20))
        staff = float(data.get("parameters", {}).get("staff_loss", 10))

        # Build standard lenses for lens switcher
        df_staff = _build_staffing_table(surge, staff)
        df_mitig = _build_mitigations_table(surge, icu, staff, 80, 250, 50, CAP_ED, CAP_GEN, CAP_ICU, int(data.get("total_bed_deficit", 50)), float(data.get("nursing_deficit", 20)))
        df_vuln = _build_vulnerability_table(surge, icu, staff, 80, 250, 50, 20, CAP_ED, CAP_GEN, CAP_ICU, CAP_OR)
        df_icu = _build_icu_table(surge, icu)
        df_ed = _build_emergency_table(surge)
        df_beds = _build_bed_capacity_table(surge, staff)
        df_overview = _build_overview_table(80, 250, 50, 20, CAP_ED, CAP_GEN, CAP_ICU, CAP_OR)

        table_title = data.get("table_title", "🤖 Gemini AI Disaster Impact Breakdown")

        available_views = {
            table_title: primary_df,
            "👥 Clinical Staffing Roster": df_staff,
            "🛏️ Ward Bed Allocation": df_beds,
            "🛡️ Disaster Mitigation Matrix": df_mitig,
            "📉 Failure Sequence Analysis": df_vuln,
            "🚨 ICU Deep Dive": df_icu,
            "🚑 ED Triage Stress": df_ed,
            "🏥 High-Level Overview": df_overview
        }

        return {
            "success": True,
            "engine": "Google Gemini 1.5 Flash (Generative AI)",
            "query": query,
            "matched_intent": data.get("matched_intent", "overview"),
            "table_title": table_title,
            "scenario_name": data.get("scenario_name", "AI Crisis Scenario"),
            "parameters": {
                "surge": int(surge),
                "icu_outage": int(icu),
                "staff_loss": int(staff)
            },
            "answer_summary": data.get("answer_summary", ""),
            "health_idx": round(float(data.get("resilience_score", 50)), 1),
            "total_crisis_occ": int(data.get("total_bed_deficit", 50)) + 249,
            "total_effective_cap": 249,
            "total_bed_deficit": int(data.get("total_bed_deficit", 50)),
            "nursing_deficit": round(float(data.get("nursing_deficit", 20)), 1),
            "crit_depts": int(data.get("critical_departments_count", 3)),
            "primary_df": primary_df,
            "available_views": available_views,
            "dept_stats_df": primary_df,
            "bottlenecks": data.get("bottlenecks", []),
            "mitigations": data.get("mitigations", []),
            "insights": data.get("key_insights", [])
        }
    except Exception as e:
        print(f"Gemini API Execution notice: {e}. Defaulting to deterministic hospital model.")
        return None


# =============================================================================
# MAIN NLP ENGINE PARSER & ORCHESTRATOR
# =============================================================================

def parse_what_if_query(query: str, api_key: str = None) -> Dict[str, Any]:
    """
    Parses natural language English what-if questions, extracts stress parameters,
    identifies clinical inquiry intent, executes simulations, and returns tailored
    intent-specific analytical tables and executive takeaways.
    Uses Google Gemini AI if API key is provided, with seamless fallback to deterministic physics model.
    """
    q_raw = query.strip()
    q = q_raw.lower()

    if not q:
        return {
            "success": False,
            "error": "Please enter a simulation query.",
            "answer_summary": "Empty simulation query.",
            "query": q_raw
        }

    # Step 0: Try Google Gemini API if key is present
    effective_key = api_key or os.environ.get("GEMINI_API_KEY")
    if effective_key and str(effective_key).strip():
        gemini_result = run_gemini_what_if_simulation(q_raw, str(effective_key).strip())
        if gemini_result and gemini_result.get("success"):
            return gemini_result

    # Step 1: Deterministic Physics Model
    surge = 0.0
    icu_outage = 0.0
    staff_loss = 0.0
    detected_preset_name = None

    # Normalize written number words (e.g. "twenty percent", "thirty percent")
    num_words = {
        r'\bten\b': '10', r'\btwenty\b': '20', r'\bthirty\b': '30',
        r'\bforty\b': '40', r'\bfifty\b': '50', r'\bsixty\b': '60',
        r'\bseventy\b': '70', r'\beighty\b': '80', r'\bninety\b': '90',
        r'\bhundred\b': '100'
    }
    for nw_pat, nw_val in num_words.items():
        q = re.sub(nw_pat, nw_val, q)

    # Step 1: Check known preset match
    for key, data in PRESET_SCENARIOS.items():
        if key in q:
            surge = float(data["surge"])
            icu_outage = float(data["icu"])
            staff_loss = float(data["staff"])
            detected_preset_name = data["name"]
            break

    # Step 2: Extract explicit Surge percentages or keywords (supports %, percent, percentage, pct)
    PCT = r'(?:%|percent(?:age)?|pct)'

    m_surge = re.search(r'(\d+(?:\.\d+)?)\s*' + PCT + r'\s*(?:(?:patient|emergency|casualty|inpatient|arrival|volume|demand|case)s?\s+)*(?:surges?|influx|increases?|spikes?|rises?|casualt(?:y|ies)|arrivals?|more arrivals|demands?|volume|cases?|load)', q)
    if not m_surge:
        m_surge = re.search(r'(?:surges?|arrivals?|volumes?|demands?|influx|increases?|rises?|spikes?)\s*(?:of|by|to|\:|\=)?\s*(\d+(?:\.\d+)?)\s*' + PCT, q)
    if not m_surge:
        m_surge = re.search(r'(?:patient\s+volume|emergency\s+arrivals?|emergency\s+cases?|arrivals?|volume|demand|cases?)\s+surges?\s*(?:of|by|to|\:|\=)?\s*(\d+(?:\.\d+)?)\s*' + PCT, q)
    if not m_surge:
        m_surge = re.search(r'(\d+(?:\.\d+)?)\s*' + PCT + r'\s*(?:more|higher|increase|surge|rise|growth|jump)', q)
    if not m_surge:
        m_surge = re.search(r'(?:\+|\b)surges?\s*(?:of|by|to)?\s*(\d+(?:\.\d+)?)', q)
    # Generic percentage when asking about capacity / emergency / arrivals
    if not m_surge and any(w in q for w in ["emergency", "arrival", "arrivals", "patient", "patients", "handle", "absorb", "capacity", "cases"]):
        m_gen_pct = re.search(r'(\d+(?:\.\d+)?)\s*' + PCT, q)
        if m_gen_pct:
            m_surge = m_gen_pct

    if m_surge:
        surge = min(100.0, float(m_surge.group(1)))
    elif "double" in q and ("arrival" in q or "surge" in q or "volume" in q or "demand" in q or "patient" in q):
        surge = 100.0
    elif "triple" in q:
        surge = 100.0

    # Step 3: Extract explicit ICU Outage percentage or absolute bed loss
    m_icu = re.search(r'(\d+(?:\.\d+)?)\s*' + PCT + r'\s*(?:(?:critical\s+care|icu|hospital)\s+)*(?:icu|bed|critical care)\s*(?:outage|loss|reduction|closure|offline|shutdown|shut\s*down|lockdown)', q)
    if not m_icu:
        m_icu = re.search(r'(?:icu|intensive care|critical care)\s*(?:outage|loss|closure|reduction|offline|shutdown|closed|lockdown)\s*(?:of|by|to|\:|\=)?\s*(\d+(?:\.\d+)?)\s*' + PCT, q)
    if not m_icu:
        m_icu = re.search(r'(?:shuts?\s+down|closes?|loses?|outage\s+of)\s*(\d+(?:\.\d+)?)\s*' + PCT + r'\s*(?:of\s+)?(?:the\s+)?(?:icu|critical care|icu beds?)', q)
    if not m_icu:
        m_icu_beds = re.search(r'(\d+)\s*(?:icu beds?|critical care beds?)\s*(?:out|lost|closed|contaminated|offline|damaged|quarantine|shut\s*down)', q)
        if m_icu_beds:
            beds_lost = float(m_icu_beds.group(1))
            icu_outage = min(100.0, round((beds_lost / CAP_ICU) * 100.0, 1))
    if m_icu:
        icu_outage = min(100.0, float(m_icu.group(1)))
    elif "half the icu" in q or "half of icu" in q or "50% icu" in q or "50 percent icu" in q:
        icu_outage = 50.0

    # Step 4: Extract explicit Staff Absenteeism percentage or nurse count
    m_staff = re.search(r'(\d+(?:\.\d+)?)\s*' + PCT + r'\s*(?:(?:clinical|nursing|hospital)\s+)*(?:staff|nurse|personnel|workforce)\s*(?:absenteeism|shortage|loss|illness|sick|deficit|dropout)', q)
    if not m_staff:
        m_staff = re.search(r'(?:staff|nurse|personnel|workforce)\s*(?:absenteeism|shortage|loss|illness|sick|deficit|dropout)\s*(?:of|by|to|\:|\=)?\s*(\d+(?:\.\d+)?)\s*' + PCT, q)
    if not m_staff:
        m_nurses_absent = re.search(r'(\d+)\s*(?:nurses?|staff|personnel)\s*(?:absent|sick|calling in|missing|lost|strike|dropout|deficit)', q)
        if m_nurses_absent:
            count = float(m_nurses_absent.group(1))
            staff_loss = min(50.0, round((count / BASE_NURSES) * 100.0, 1))
    if m_staff:
        staff_loss = min(50.0, float(m_staff.group(1)))

    # Fallback to realistic defaults if user asked a general question without explicit numbers
    if surge == 0.0 and icu_outage == 0.0 and staff_loss == 0.0:
        if "mass casualty" in q or "disaster" in q or "explosion" in q or "trauma" in q:
            surge, icu_outage, staff_loss = 80.0, 15.0, 10.0
            detected_preset_name = "Mass Casualty Trauma Surge"
        elif "icu" in q and ("contamination" in q or "outage" in q or "closure" in q or "quarantine" in q):
            surge, icu_outage, staff_loss = 20.0, 50.0, 15.0
            detected_preset_name = "ICU Bio-Contamination Emergency"
        elif "strike" in q or "absenteeism" in q or "staff" in q or "nurse" in q:
            surge, icu_outage, staff_loss = 30.0, 10.0, 35.0
            detected_preset_name = "Acute Healthcare Workforce Shortage"
        elif "epidemic" in q or "winter" in q or "flu" in q or "covid" in q or "respiratory" in q:
            surge, icu_outage, staff_loss = 65.0, 25.0, 15.0
            detected_preset_name = "Respiratory Epidemic Surge"
        elif "resilience" in q or "break" in q or "fail" in q or "collapse" in q:
            surge, icu_outage, staff_loss = 70.0, 20.0, 20.0
            detected_preset_name = "Catastrophic Stress Vulnerability Scan"
        else:
            surge, icu_outage, staff_loss = 50.0, 20.0, 10.0
            detected_preset_name = "Standard 50% Stress Simulation"

    # Mathematical Simulation Calculations
    eff_ed = CAP_ED
    eff_or = CAP_OR
    eff_icu = max(5, int(round(CAP_ICU * (1.0 - icu_outage / 100.0))))
    eff_gen = max(50, int(round(CAP_GEN * (1.0 - (staff_loss * 0.3) / 100.0))))

    crisis_ed = int(round(BASE_ED * (1.0 + (surge * 1.006) / 100.0)))
    crisis_gen = int(round(BASE_GEN * (1.0 + (surge * 1.0175) / 100.0)))
    crisis_icu = int(round(BASE_ICU * (1.0 + (surge * 0.8939) / 100.0)))
    crisis_or = int(round(BASE_OR * (1.0 + (surge * 0.491) / 100.0)))

    total_crisis_occ = crisis_ed + crisis_gen + crisis_icu + crisis_or
    total_effective_cap = eff_ed + eff_gen + eff_icu + eff_or
    total_bed_deficit = max(0, total_crisis_occ - total_effective_cap)

    avail_nurses = round(BASE_NURSES * (1.0 - staff_loss / 100.0), 1)
    req_nurses = round(BASE_NURSES + (surge * 0.6284) + (staff_loss * 0.2), 1)
    nursing_deficit = max(0.0, round(req_nurses - avail_nurses, 1))

    stress_penalty = (surge * 0.95) + (icu_outage * 1.5) + (staff_loss * 1.2)
    health_idx = max(0.0, round(100.0 - stress_penalty, 1))

    crit_depts = sum([
        crisis_ed > eff_ed,
        crisis_gen > eff_gen,
        crisis_icu > eff_icu,
        crisis_or > eff_or
    ])

    # Build All Intent Tables
    df_staff = _build_staffing_table(surge, staff_loss)
    df_mitig = _build_mitigations_table(surge, icu_outage, staff_loss, crisis_ed, crisis_gen, crisis_icu, eff_ed, eff_gen, eff_icu, total_bed_deficit, nursing_deficit)
    df_vuln = _build_vulnerability_table(surge, icu_outage, staff_loss, crisis_ed, crisis_gen, crisis_icu, crisis_or, eff_ed, eff_gen, eff_icu, eff_or)
    df_icu = _build_icu_table(surge, icu_outage)
    df_ed = _build_emergency_table(surge)
    df_beds = _build_bed_capacity_table(surge, staff_loss)
    df_overview = _build_overview_table(crisis_ed, crisis_gen, crisis_icu, crisis_or, eff_ed, eff_gen, eff_icu, eff_or)

    # Determine Domain Intent & Select Primary Table with Strict Word Boundaries
    if re.search(r'\b(?:nurse|nurses|staff|staffing|personnel|workforce|overtime|shortage|shortages|absenteeism|absent|ratio|ratios|float\s*pool)\b', q):
        matched_intent = "staffing"
        table_title = "👥 Clinical Staffing & Shift Acuity Roster Breakdown"
        primary_df = df_staff
    elif re.search(r'\b(?:protocol|protocols|mitigation|mitigations|recommend|recommendations|hics|action|plan|activate|activation|checklist)\b', q):
        matched_intent = "mitigations"
        table_title = "🛡️ Recommended Disaster Mitigation & HICS Action Protocols"
        primary_df = df_mitig
    elif re.search(r'\b(?:first|break|breaks|fail|fails|collapse|collapses|vulnerability|vulnerabilities|saturation\s*order|exhaustion|sequence)\b', q):
        matched_intent = "vulnerability"
        table_title = "📉 Department Saturation & Failure Sequence Analysis"
        primary_df = df_vuln
    elif re.search(r'\b(?:icu|intensive\s*care|ventilator|ventilators|pacu|critical\s*care|ccu)\b', q):
        matched_intent = "icu"
        table_title = "🚨 Critical Care & ICU Sub-Unit Capacity Stress Breakdown"
        primary_df = df_icu
    elif re.search(r'\b(?:ed|emergency|er|triage|boarding|resus|resuscitation|trauma|trauma\s*bay)\b', q):
        matched_intent = "emergency"
        table_title = "🚑 Emergency Department Triage & Boarding Stress Breakdown"
        primary_df = df_ed
    elif re.search(r'\b(?:bed|beds|deficit|deficits|ward|wards|inpatient|admissions?|bed\s*capacity)\b', q):
        matched_intent = "bed_capacity"
        table_title = "🛏️ Hospital-Wide Inpatient Bed Allocation & Deficit Matrix"
        primary_df = df_beds
    else:
        matched_intent = "overview"
        table_title = "🏥 Comprehensive Hospital Operational Stress Matrix"
        primary_df = df_overview

    # Available lenses dictionary for UI switching
    available_views = {
        table_title: primary_df,
        "👥 Clinical Staffing Roster": df_staff,
        "🛏️ Ward Bed Allocation": df_beds,
        "🛡️ Disaster Mitigation Matrix": df_mitig,
        "📉 Failure Sequence Analysis": df_vuln,
        "🚨 ICU Deep Dive": df_icu,
        "🚑 ED Triage Stress": df_ed,
        "🏥 High-Level Overview": df_overview
    }

    # Generate Executive Summary Text
    scenario_label = detected_preset_name or f"Stress Scenario (+{int(surge)}% Surge, {int(icu_outage)}% ICU Outage, {int(staff_loss)}% Staff Loss)"

    summary_lines = []
    summary_lines.append(f"### 🎛️ Simulation Evaluation: **{scenario_label}**")
    summary_lines.append(
        f"Under **+{int(surge)}% patient surge**, **{int(icu_outage)}% ICU outage**, and **{int(staff_loss)}% staff loss**, "
        f"the hospital operations resilience index drops to **{health_idx}/100**."
    )

    if matched_intent == "staffing":
        summary_lines.append(
            f"\n**👥 Staffing Analysis**: The hospital will face an immediate shortfall of **{nursing_deficit} nurses**. "
            f"Maintaining safe clinical acuity requires **{req_nurses} nurses**, but only **{avail_nurses}** remain available across shifts. "
            f"Overtime authorization and float pool reallocation are mandatory."
        )
    elif matched_intent == "mitigations":
        summary_lines.append(
            f"\n**🛡️ Protocol Recommendations**: Activated **HICS Level 2 Incident Command** with immediate PACU surge annex conversion and elective procedure deferral to conserve clinical resources."
        )
    elif matched_intent == "vulnerability":
        summary_lines.append(
            f"\n**📉 Failure Order Analysis**: The **Emergency Department (ED)** and **ICU** saturate first at **0% surge** (baseline buffers already depleted), followed by the **General Ward** at **+6.5% surge**, and **Operating Rooms** at **+40.7% surge**."
        )
    elif matched_intent == "icu":
        summary_lines.append(
            f"\n**🚨 Critical Care Impact**: ICU demand surges to **{crisis_icu} patients** against **{eff_icu} effective beds** "
            f"({round((crisis_icu / eff_icu) * 100, 1)}% saturation). Emergency transfer of step-down patients and PACU annex readiness required."
        )
    elif matched_intent == "emergency":
        summary_lines.append(
            f"\n**🚑 Emergency Department Impact**: ED patient census reaches **{crisis_ed} patients** against **{eff_ed} triage bays** "
            f"({round((crisis_ed / eff_ed) * 100, 1)}% saturation), creating a boarding overflow of **{max(0, crisis_ed - eff_ed)} patients**."
        )
    elif matched_intent == "bed_capacity":
        summary_lines.append(
            f"\n**🛏️ Bed Shortfall Analysis**: Total hospital-wide deficit is **{total_bed_deficit} beds**. "
            f"Total inpatient crisis demand reaches **{total_crisis_occ} patients** against **{total_effective_cap} staffed beds**."
        )
    else:
        summary_lines.append(
            f"\n**Overall Operational Impact**: Results in a **{total_bed_deficit} total bed deficit**, "
            f"a shortage of **{nursing_deficit} nurses**, and pushes **{crit_depts} of 4 key clinical departments** into critical overflow."
        )

    # Executive Insights
    insights = []
    if health_idx < 30:
        insights.append(f"🚨 **Catastrophic Operational Risk**: Resilience index ({health_idx}/100) requires immediate executive intervention.")
    elif health_idx < 60:
        insights.append(f"⚠️ **Elevated System Strain**: Resilience index at {health_idx}/100; hospital operating near maximum absorption margin.")
    else:
        insights.append(f"✅ **Manageable System Resilience**: Hospital maintains a {health_idx}/100 resilience rating with adequate safety buffers.")

    if matched_intent == "staffing":
        insights.append(f"👥 **Critical Nursing Gap**: Deficit of **{nursing_deficit} nurses** below required nurse-to-patient acuity baselines.")
        insights.append(f"⏱️ **Overtime Hours**: Estimated **{int(nursing_deficit * 8)} overtime clinical hours** needed per 8-hour shift.")
    elif matched_intent == "vulnerability":
        insights.append(f"⚡ **First Collapse**: Emergency Department and ICU breach physical capacity thresholds first.")
        insights.append(f"⏱️ **General Ward Breach**: Inpatient ward capacity exhausts when surge exceeds **+6.5%**.")
    elif matched_intent == "icu":
        insights.append(f"🛏️ **ICU Overflow**: Critical Care bed deficit of **{max(0, crisis_icu - eff_icu)} beds**.")
        insights.append(f"⚡ **PACU Conversion**: Authorize immediate conversion of 8 PACU bays to ventilator-capable beds.")
    else:
        if nursing_deficit > 0:
            insights.append(f"👥 **Nurse Deficit**: Short by **{nursing_deficit} personnel** ({avail_nurses} available vs {req_nurses} required).")
        if total_bed_deficit > 0:
            insights.append(f"🛏️ **Bed Deficit**: Total hospital shortfall of **{total_bed_deficit} inpatient & critical beds**.")

    # Clinical Bottlenecks
    bottlenecks = []
    if crisis_icu > eff_icu:
        bottlenecks.append({
            "severity": "Critical",
            "unit": "Intensive Care Unit (ICU)",
            "message": f"ICU demand exceeds capacity by {crisis_icu - eff_icu} beds ({round((crisis_icu / eff_icu) * 100, 1)}% saturation)."
        })
    if crisis_gen > eff_gen:
        bottlenecks.append({
            "severity": "Critical",
            "unit": "General Inpatient Ward",
            "message": f"Inpatient wards over capacity by {crisis_gen - eff_gen} beds ({round((crisis_gen / eff_gen) * 100, 1)}% occupancy)."
        })
    if crisis_ed > eff_ed:
        bottlenecks.append({
            "severity": "High",
            "unit": "Emergency Department (ED)",
            "message": f"ED boarding exceeds triage bays by {crisis_ed - eff_ed} patients. Hallway boarding diversion required."
        })
    if nursing_deficit > 0:
        bottlenecks.append({
            "severity": "Critical" if nursing_deficit > 15 else "High",
            "unit": "Clinical Nursing Roster",
            "message": f"Severe staffing deficit of {nursing_deficit} nurses below clinical acuity baseline."
        })

    # Mitigations List
    mitigations = []
    if surge >= 25.0:
        mitigations.append("🚨 **Activate Hospital Incident Command System (HICS) Level 2**: Centralized operations briefing every 4 hours.")
        mitigations.append("⚡ **Implement Emergency Fast-Track Protocol**: Triage low-acuity ESI 4-5 cases to urgent care clinics to preserve main ED bays.")
    if icu_outage >= 10.0 or crisis_icu > eff_icu:
        mitigations.append("🛏️ **Designate PACU as ICU Surge Annex**: Convert 8 Post-Anesthesia Care Unit bays into temporary ventilator-capable ICU beds.")
        mitigations.append("🔄 **Accelerated Step-Down Transfers**: Expedite transfer of stable ICU telemetry patients to intermediate care floors.")
    if staff_loss >= 15.0 or nursing_deficit > 8.0:
        mitigations.append("📋 **Elective Surgery Postponement**: Defer voluntary elective procedures for the next 48 hours to redirect OR staff to inpatient units.")
        mitigations.append("👥 **Float Pool & Overtime Activation**: Authorize immediate 1.5x crisis overtime and deploy cross-trained administrative nurses.")
    if total_bed_deficit > 20:
        mitigations.append("🏥 **Activate Regional Mutual Aid Compact**: Notify regional trauma network for patient diversion and inter-hospital ambulance rerouting.")
    if not mitigations:
        mitigations.append("✅ **Standard Operating Threshold**: Existing departmental buffers and nurse float pools are sufficient to absorb this stress scenario.")

    return {
        "success": True,
        "query": q_raw,
        "matched_intent": matched_intent,
        "table_title": table_title,
        "scenario_name": scenario_label,
        "parameters": {
            "surge": int(surge),
            "icu_outage": int(icu_outage),
            "staff_loss": int(staff_loss)
        },
        "answer_summary": "\n".join(summary_lines),
        "health_idx": health_idx,
        "total_crisis_occ": total_crisis_occ,
        "total_effective_cap": total_effective_cap,
        "total_bed_deficit": total_bed_deficit,
        "nursing_deficit": nursing_deficit,
        "crit_depts": crit_depts,
        "primary_df": primary_df,
        "available_views": available_views,
        "dept_stats_df": primary_df,
        "bottlenecks": bottlenecks,
        "mitigations": mitigations,
        "insights": insights
    }
