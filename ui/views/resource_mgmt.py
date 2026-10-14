"""
VitalOptima Resource Management View
Operational telemetry for physical bed allocations, department capacities, and clinical staff rosters.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp, DATA_DIR
from ui.components import render_top_nav, render_footer, render_metric_card
from db.postgres import load_department_resources_dataset, load_staffing_roster_dataset

def show_resource_mgmt():
    """Resource management view for beds and staffing."""
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)

    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.2rem; letter-spacing: -0.02em;">
            🛏️ Hospital Resource & Staffing Operations
        </h2>
        <p style="color: #64748B; font-size: 0.92rem; margin: 0;">
            Comprehensive tracking of departmental physical bed capacity, clinical nurse-to-patient staffing, and roster compliance.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Load datasets
    res_df = load_department_resources_dataset()
    if res_df.empty and (DATA_DIR / "hospital_resources.csv").exists():
        res_df = pd.read_csv(DATA_DIR / "hospital_resources.csv")

    staff_df = load_staffing_roster_dataset()
    if staff_df.empty and (DATA_DIR / "staff_availability.csv").exists():
        staff_df = pd.read_csv(DATA_DIR / "staff_availability.csv")

    tab1, tab2 = st.tabs(["🏥 Departmental Bed Capacity", "👥 Clinical Staff Rosters & Shifts"])

    # --- TAB 1: BEDS & RESOURCES ---
    with tab1:
        if not res_df.empty:
            res_df["usable_capacity"] = res_df["total_capacity"] - res_df["unavailable_capacity"]
            res_df["utilization_pct"] = (100.0 * res_df["occupied_capacity"] / res_df["usable_capacity"]).round(1)

            # High-level stats
            m1, m2, m3, m4 = st.columns(4)
            tot_beds = int(res_df[res_df["resource_type"].isin(["General Bed", "ICU Bed"])]["total_capacity"].sum())
            tot_occ = int(res_df[res_df["resource_type"].isin(["General Bed", "ICU Bed"])]["occupied_capacity"].sum())
            tot_staffed = int(res_df[res_df["resource_type"].isin(["General Bed", "ICU Bed"])]["staffed_capacity"].sum())
            tot_avail = int(res_df[res_df["resource_type"].isin(["General Bed", "ICU Bed"])]["available_capacity"].sum())

            with m1:
                render_metric_card("Total In-Service Beds", f"{tot_beds} Beds", "300 Ward + 30 ICU", card_type="default", icon="🏥")
            with m2:
                render_metric_card("Current Census Occupancy", f"{tot_occ} Patients", f"{round(100*tot_occ/tot_beds, 1)}% of total beds", card_type="warning", icon="🛏️")
            with m3:
                render_metric_card("Staffed Bed Capacity", f"{tot_staffed} Beds", "Clinically covered beds", card_type="default", icon="🩺")
            with m4:
                render_metric_card("Immediately Free Beds", f"{tot_avail} Beds", "Physical & clean beds", card_type="success", icon="✅")

            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

            # Filter controls
            f_col1, f_col2 = st.columns([1, 2])
            with f_col1:
                type_options = ["All Resource Types"] + sorted(res_df["resource_type"].unique().tolist())
                selected_type = st.selectbox("Filter Resource Type", type_options)

            filtered_res = res_df.copy()
            if selected_type != "All Resource Types":
                filtered_res = filtered_res[filtered_res["resource_type"] == selected_type]

            # Highlight conditions
            def highlight_rows(row):
                # Understaffed
                if row["occupied_capacity"] > row["staffed_capacity"]:
                    return ['background-color: #FEF2F2; color: #991B1B'] * len(row)
                # Over-demand
                elif row["forecast_demand"] > row["usable_capacity"]:
                    return ['background-color: #FFFBEB; color: #92400E'] * len(row)
                return [''] * len(row)

            # Display table
            display_cols = [
                "resource_id", "resource_type", "department", "total_capacity",
                "unavailable_capacity", "occupied_capacity", "available_capacity",
                "staffed_capacity", "forecast_demand", "utilization_pct"
            ]

            st.dataframe(
                filtered_res[display_cols].style.apply(highlight_rows, axis=1),
                width="stretch",
                hide_index=True
            )

            st.caption("🔴 Red rows indicate units where patient census exceeds staffed capacity (understaffed). 🟡 Yellow rows indicate where forecasted demand exceeds physical capacity.")
        else:
            st.error("Hospital resources dataset not found.")

    # --- TAB 2: STAFF ROSTERS ---
    with tab2:
        if not staff_df.empty:
            staff_df["deficit"] = staff_df["required_count"] - staff_df["available_count"]
            shortages = staff_df[staff_df["deficit"] > 0]

            s1, s2, s3, s4 = st.columns(4)
            with s1:
                render_metric_card("Total Roster Rows", f"{len(staff_df)} Shifts", "7 Days • 3 Daily Shifts", card_type="default", icon="📅")
            with s2:
                render_metric_card("Identified Shortfalls", f"{len(shortages)} Shift Deficits", "Available < Required", card_type="alert", icon="⚠️")
            with s3:
                render_metric_card("Max Weekly Hours", "40h / 48h", "Nurses: 40h • Doctors: 48h", card_type="default", icon="⏱️")
            with s4:
                render_metric_card("Mandatory Shift Rest", "11 Hours", "Full labor compliance", card_type="success", icon="🛡️")

            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

            # Shortfall alert table
            if not shortages.empty:
                st.markdown("#### 🚨 Urgent Shift Staffing Deficits")
                short_display = shortages[["date", "shift", "department", "staff_role", "available_count", "required_count", "deficit"]]
                st.dataframe(short_display, width="stretch", hide_index=True)

            st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
            st.markdown("#### 📋 Full Staff Availability Schedule")

            # Filters
            c_f1, c_f2, c_f3 = st.columns(3)
            with c_f1:
                dates = ["All Dates"] + sorted(staff_df["date"].unique().tolist())
                sel_date = st.selectbox("Filter Date", dates)
            with c_f2:
                shifts = ["All Shifts"] + sorted(staff_df["shift"].unique().tolist())
                sel_shift = st.selectbox("Filter Shift", shifts)
            with c_f3:
                depts = ["All Departments"] + sorted(staff_df["department"].unique().tolist())
                sel_dept = st.selectbox("Filter Department", depts)

            view_df = staff_df.copy()
            if sel_date != "All Dates":
                view_df = view_df[view_df["date"] == sel_date]
            if sel_shift != "All Shifts":
                view_df = view_df[view_df["shift"] == sel_shift]
            if sel_dept != "All Departments":
                view_df = view_df[view_df["department"] == sel_dept]

            st.dataframe(view_df, width="stretch", hide_index=True)
        else:
            st.error("Staff availability dataset not found.")

    render_footer()
