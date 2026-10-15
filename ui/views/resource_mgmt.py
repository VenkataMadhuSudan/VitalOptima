"""
VitalOptima Resource Management View
Data-driven view based on official department capacity matrix and clinical shift roster.
"""
import streamlit as st
import pandas as pd
from config import DATA_DIR, HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp
from ui.components import render_top_nav, render_footer
from db.postgres import load_department_resources_dataset, load_staffing_roster_dataset

def show_resource_mgmt():
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)
    
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.25rem;">Resource Management</h2>
        <p style="color: #64748B;">Official capacity matrix, department bed allocations, and clinical shift rosters.</p>
    </div>
    """, unsafe_allow_html=True)

    # Load department resources directly from PostgreSQL with CSV fallback
    df_resources = load_department_resources_dataset()
    if df_resources.empty:
        res_csv = DATA_DIR / "department_resources.csv"
        if res_csv.exists():
            df_resources = pd.read_csv(res_csv)

    tab1, tab2, tab3 = st.tabs(["🛏️ Bed Capacity & Wards", "👥 Nursing & Staff Roster", "🏥 Operating Suites"])

    with tab1:
        st.markdown("#### Inpatient Ward & Critical Care Capacity Matrix")
        
        # Calculate real totals from department_resources.csv
        bed_rows = df_resources[df_resources["resource_type"].isin(["General Bed", "ICU Bed"])]
        total_beds = int(bed_rows["total_capacity"].sum())
        occupied_beds = int(bed_rows["occupied_capacity"].sum())
        avail_beds = int(bed_rows["available_capacity"].sum())
        unavail_beds = int(bed_rows["unavailable_capacity"].sum())
        occ_rate = round((occupied_beds / total_beds) * 100, 1) if total_beds > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Licensed Beds", f"{total_beds}", delta="300 Gen + 30 ICU")
        with c2:
            st.metric("Occupied Inpatients", f"{occupied_beds}", delta=f"{occ_rate}% Census", delta_color="inverse")
        with c3:
            st.metric("Available Clean Beds", f"{avail_beds}", delta="Buffer Available", delta_color="normal")
        with c4:
            st.metric("Unavailable / Maint.", f"{unavail_beds}", delta="Sanitization Hold", delta_color="inverse")

        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
        
        # Formatted presentation table
        display_df = df_resources.copy()
        display_df["Utilization %"] = ((display_df["occupied_capacity"] / display_df["total_capacity"]) * 100).round(1).astype(str) + "%"
        display_df = display_df.rename(columns={
            "resource_id": "ID",
            "resource_type": "Resource Type",
            "department": "Department / Service",
            "total_capacity": "Total Capacity",
            "unavailable_capacity": "Unavailable",
            "occupied_capacity": "Occupied",
            "available_capacity": "Available",
            "staffed_capacity": "Staffed Beds",
            "forecast_demand": "Forecast Demand"
        })
        
        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True
        )

    with tab2:
        st.markdown("#### Clinical Staffing Allocation by Shift")
        df_roster = load_staffing_roster_dataset()
        if not df_roster.empty:
            df_roster["date"] = df_roster["date"].astype(str)
            dates = sorted(df_roster["date"].unique())
            
            sc1, sc2 = st.columns([1.5, 3.5])
            with sc1:
                selected_date = st.selectbox("Select Roster Schedule Date:", options=dates, index=0)
                
            day_roster = df_roster[df_roster["date"] == selected_date]
            
            # Shift summaries
            morning_df = day_roster[day_roster["shift"] == "Morning"]
            evening_df = day_roster[day_roster["shift"] == "Evening"]
            night_df = day_roster[day_roster["shift"] == "Night"]
            
            m_avail, m_req = int(morning_df["available_count"].sum()), int(morning_df["required_count"].sum())
            e_avail, e_req = int(evening_df["available_count"].sum()), int(evening_df["required_count"].sum())
            n_avail, n_req = int(night_df["available_count"].sum()), int(night_df["required_count"].sum())
            
            s1, s2, s3 = st.columns(3)
            with s1:
                delta_m = f"{m_avail - m_req} Deficit" if m_avail < m_req else "Full Coverage"
                st.metric("Morning Shift (07:00 - 15:00)", f"{m_avail} / {m_req} Staff", delta=delta_m, delta_color="normal" if m_avail >= m_req else "inverse")
            with s2:
                delta_e = f"{e_avail - e_req} Deficit" if e_avail < e_req else "Full Coverage"
                st.metric("Evening Shift (15:00 - 23:00)", f"{e_avail} / {e_req} Staff", delta=delta_e, delta_color="normal" if e_avail >= e_req else "inverse")
            with s3:
                delta_n = f"{n_avail - n_req} Deficit" if n_avail < n_req else "Full Coverage"
                st.metric("Night Shift (23:00 - 07:00)", f"{n_avail} / {n_req} Staff", delta=delta_n, delta_color="normal" if n_avail >= n_req else "inverse")
            
            st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
            
            # Detailed roster table
            formatted_roster = day_roster[[
                "shift", "department", "staff_role", "available_count", "required_count",
                "maximum_permitted_working_hours", "minimum_rest_hours_between_shifts"
            ]].rename(columns={
                "shift": "Shift",
                "department": "Department",
                "staff_role": "Staff Role",
                "available_count": "Available",
                "required_count": "Required",
                "maximum_permitted_working_hours": "Max Hours/Wk",
                "minimum_rest_hours_between_shifts": "Min Rest (Hrs)"
            })
            
            st.dataframe(formatted_roster, width="stretch", hide_index=True)
            
            if n_avail < n_req:
                st.warning(f"⚠️ **Night Shift Staffing Deficit ({selected_date}):** Night shift has {n_req - n_avail} unstaffed positions. Review OR and ICU float nurse allocations.")
        else:
            st.warning("Staffing roster dataset not found.")

    with tab3:
        st.markdown("#### Operating Suite Utilization & Scheduling")
        or_rows = df_resources[df_resources["resource_type"] == "Operating Room"]
        
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            st.metric("Total Operating Theatres", "12 Suites", delta="Main (8), Day (2), Emergency (2)")
        with oc2:
            st.metric("Suites In Active Surgery", "8 Active", delta="66.7% Utilization")
        with oc3:
            st.metric("Available Urgent Slots", "3 Standby", delta="1 Maintenance hold", delta_color="normal")
            
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        
        # Room by room breakdown
        or_schedule = pd.DataFrame([
            {"Suite ID": "OR-MAIN-1", "Department": "Main Theatre", "Specialty": "Cardiothoracic", "Status": "🔴 In Surgery", "Occupied": "Yes", "Staffed": "Yes", "Forecast Demand": "High"},
            {"Suite ID": "OR-MAIN-2", "Department": "Main Theatre", "Specialty": "Neurosurgery", "Status": "🔴 In Surgery", "Occupied": "Yes", "Staffed": "Yes", "Forecast Demand": "High"},
            {"Suite ID": "OR-MAIN-3", "Department": "Main Theatre", "Specialty": "General Surgery", "Status": "🔴 In Surgery", "Occupied": "Yes", "Staffed": "Yes", "Forecast Demand": "Normal"},
            {"Suite ID": "OR-MAIN-4", "Department": "Main Theatre", "Specialty": "Orthopedic Trauma", "Status": "🔴 In Surgery", "Occupied": "Yes", "Staffed": "Yes", "Forecast Demand": "Normal"},
            {"Suite ID": "OR-MAIN-5", "Department": "Main Theatre", "Specialty": "Vascular", "Status": "🔴 In Surgery", "Occupied": "Yes", "Staffed": "Yes", "Forecast Demand": "Normal"},
            {"Suite ID": "OR-MAIN-6", "Department": "Main Theatre", "Specialty": "Urology", "Status": "🔴 In Surgery", "Occupied": "Yes", "Staffed": "Yes", "Forecast Demand": "Low"},
            {"Suite ID": "OR-MAIN-7", "Department": "Main Theatre", "Specialty": "Elective / Buffer", "Status": "🟢 Available Slot", "Occupied": "No", "Staffed": "Yes", "Forecast Demand": "Normal"},
            {"Suite ID": "OR-MAIN-8", "Department": "Main Theatre", "Specialty": "HVAC Filter Cert", "Status": "⚪ Maintenance Hold", "Occupied": "No", "Staffed": "No", "Forecast Demand": "N/A"},
            {"Suite ID": "OR-DAY-1", "Department": "Day Surgery", "Specialty": "Ambulatory Surgery", "Status": "🔴 In Surgery", "Occupied": "Yes", "Staffed": "Yes", "Forecast Demand": "Normal"},
            {"Suite ID": "OR-DAY-2", "Department": "Day Surgery", "Specialty": "Endoscopy", "Status": "🟢 Available Slot", "Occupied": "No", "Staffed": "Yes", "Forecast Demand": "Low"},
            {"Suite ID": "OR-EMG-1", "Department": "Emergency Theatre", "Specialty": "Acute Trauma", "Status": "🔴 In Surgery", "Occupied": "Yes", "Staffed": "Yes", "Forecast Demand": "High (Surge)"},
            {"Suite ID": "OR-EMG-2", "Department": "Emergency Theatre", "Specialty": "Emergency Standby", "Status": "🟢 Standby Ready", "Occupied": "No", "Staffed": "Yes", "Forecast Demand": "Surge Reserve"}
        ])
        st.dataframe(or_schedule, width="stretch", hide_index=True)

    render_footer()
