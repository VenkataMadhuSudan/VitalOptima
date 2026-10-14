"""
VitalOptima What-If Simulator View
Stress-testing disaster scenarios, capacity shock simulations, and resilience planning.
"""
import streamlit as st
import pandas as pd
import json

from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp
from ui.components import render_top_nav, render_footer, render_metric_card
from db.database import save_scenario, get_scenarios

def show_simulator():
    """What-if disaster and operational stress simulator view."""
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)

    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.2rem; letter-spacing: -0.02em;">
            🎛️ What-If Disaster & Capacity Stress Simulator
        </h2>
        <p style="color: #64748B; font-size: 0.92rem; margin: 0;">
            Simulate the operational impact of mass casualty incidents, ICU facility outages, epidemic nurse absenteeism, and supply chain disruptions.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_sim, tab_saved = st.tabs(["⚡ Configure Simulation", "📁 Saved Simulation Scenarios"])

    with tab_sim:
        st.markdown("#### 1. Choose a Standard Preset or Configure Custom Shock Parameters")

        preset = st.selectbox(
            "Select Pre-configured Incident Profile",
            [
                "Custom Scenario Configuration",
                "Mass Casualty / Emergency Surge (1.5x ED Arrivals)",
                "Critical Infrastructure Outage (8 ICU Beds Offline)",
                "Severe Winter Epidemic (25% Nurse Absenteeism)",
                "Supply Chain Disruption (N95 Respirator Stockout)"
            ]
        )

        # Defaults
        def_surge = 0.0
        def_icu = 0
        def_staff = 0.0
        scenario_name = "Custom Shock Simulation"

        if preset == "Mass Casualty / Emergency Surge (1.5x ED Arrivals)":
            def_surge = 50.0
            def_icu = 2
            def_staff = 0.0
            scenario_name = "Mass Casualty Incident (Level 1 Surge)"
        elif preset == "Critical Infrastructure Outage (8 ICU Beds Offline)":
            def_surge = 0.0
            def_icu = 8
            def_staff = 0.0
            scenario_name = "Medical & Surgical ICU HVAC Outage"
        elif preset == "Severe Winter Epidemic (25% Nurse Absenteeism)":
            def_surge = 20.0
            def_icu = 0
            def_staff = 25.0
            scenario_name = "Epidemic Wave & Staff Sickness"
        elif preset == "Supply Chain Disruption (N95 Respirator Stockout)":
            def_surge = 10.0
            def_icu = 0
            def_staff = 0.0
            scenario_name = "Consumables Supplier Failure"

        col1, col2, col3 = st.columns(3)
        with col1:
            surge_pct = st.slider("Emergency Demand Surge (%)", 0.0, 100.0, float(def_surge), 5.0)
        with col2:
            icu_loss = st.slider("ICU Beds Taken Offline", 0, 15, int(def_icu))
        with col3:
            staff_loss = st.slider("Staff Absenteeism Rate (%)", 0.0, 50.0, float(def_staff), 5.0)

        cust_name = st.text_input("Scenario Name / Code", value=scenario_name)

        if st.button("🚀 Run Full Resilience Simulation", type="primary"):
            # Compute impact
            baseline_occ = 261
            total_beds = 330
            new_usable_beds = total_beds - icu_loss
            
            surge_factor = 1.0 + (surge_pct / 100.0)
            added_admissions = int(round(51 * (surge_factor - 1.0)))
            new_occ = baseline_occ + added_admissions
            new_occ_pct = round(100.0 * new_occ / new_usable_beds, 1)

            displaced_patients = max(0, 23 - (30 - icu_loss))
            staff_deficit = int(round(34 * (staff_loss / 100.0)))

            st.markdown("---")
            st.markdown("### 📊 Simulation Impact & Stress Diagnostics")

            r1, r2, r3, r4 = st.columns(4)
            with r1:
                render_metric_card(
                    "Simulated Bed Occupancy",
                    f"{new_occ} / {new_usable_beds}",
                    f"<strong>{new_occ_pct}%</strong> utilization",
                    card_type="alert" if new_occ_pct >= 90 else "warning",
                    icon="🛏️"
                )
            with r2:
                render_metric_card(
                    "Displaced ICU Patients",
                    f"{displaced_patients} Patients",
                    "Requires emergency relocation",
                    card_type="alert" if displaced_patients > 0 else "success",
                    icon="🚨"
                )
            with r3:
                render_metric_card(
                    "Projected Nurse Deficit",
                    f"-{staff_deficit} Nurses",
                    f"{staff_loss}% staffing absenteeism",
                    card_type="warning" if staff_deficit > 0 else "success",
                    icon="👥"
                )
            with r4:
                breach = new_occ_pct >= 90.0
                render_metric_card(
                    "Overall Hospital Status",
                    "CRITICAL" if breach else "STABLE",
                    "Breach threshold exceeded" if breach else "Within safety margins",
                    card_type="alert" if breach else "success",
                    icon="⚠️"
                )

            # Details
            st.markdown("#### 🔍 Action Protocol Generated for this Scenario")
            if displaced_patients > 0:
                st.error(f"🚨 **Displaced Inpatients:** {displaced_patients} ICU patients must be transferred to PACU or Step-Down beds immediately.")
            if new_occ_pct >= 90.0:
                st.warning(f"⚠️ **Inpatient Bed Exhaustion:** Occupancy reaches {new_occ_pct}%. Postpone elective surgical cases to protect bed pool.")
            if staff_deficit > 0:
                st.info(f"👥 **Staff Contingency:** Activate 12-hour emergency float nurse shifts to cover {staff_deficit} rostered posts.")

            # Save results
            results_dict = {
                "projected_occupancy": new_occ,
                "projected_occupancy_pct": new_occ_pct,
                "displaced_patients": displaced_patients,
                "staff_deficit": staff_deficit,
                "capacity_breach": breach
            }

            if st.button("💾 Save Simulation to Database", key="btn_save_sim"):
                ok = save_scenario(
                    name=cust_name,
                    surge_pct=surge_pct,
                    icu_reduction=icu_loss,
                    staff_loss=staff_loss,
                    results_json=json.dumps(results_dict)
                )
                if ok:
                    st.success(f"Scenario '{cust_name}' permanently archived to Neon PostgreSQL & SQLite!")
                else:
                    st.error("Failed to archive scenario.")

    with tab_saved:
        st.markdown("#### 📁 Archived Scenario Simulations")
        saved_scenarios = get_scenarios(limit=25)
        if saved_scenarios:
            df_scen = pd.DataFrame(saved_scenarios)
            st.dataframe(df_scen, width="stretch", hide_index=True)
        else:
            st.info("No saved simulation scenarios recorded yet. Run and save a simulation above.")

    render_footer()
