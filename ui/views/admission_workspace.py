"""
VitalOptima Admission Officer Workspace View
Dedicated workspace for Patient Registration, Real-Time Bed Allocation, Active Roster Management,
and Safe Patient Discharge with Automatic Synchronization Telemetry.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config import HOSPITAL_NAME, COLORS, get_system_timestamp, get_current_shift
from services.auth_service import get_current_user, has_permission, require_permission
from services.admission_service import (
    get_all_departments, get_available_beds_for_department,
    create_patient_admission, discharge_patient,
    get_active_admissions, get_all_admission_history,
    get_live_bed_metrics, get_sync_status
)


def render_admission_kpi_cards(metrics: dict, active_count: int):
    """Renders real-time KPI cards for admission officer."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="General Beds Available",
            value=f"{metrics.get('general_available', 0)} Beds",
            delta=f"{metrics.get('general_occupied', 0)} Occupied ({metrics.get('general_rate', 0)}%)",
            delta_color="inverse"
        )
    with c2:
        st.metric(
            label="ICU Beds Available",
            value=f"{metrics.get('icu_available', 0)} Beds",
            delta=f"{metrics.get('icu_occupied', 0)} Occupied ({metrics.get('icu_rate', 0)}%)",
            delta_color="inverse"
        )
    with c3:
        st.metric(
            label="Current Admitted Roster",
            value=f"{active_count} Inpatients",
            delta="Active Admissions",
            delta_color="normal"
        )
    with c4:
        sync_v = metrics.get('sync_version', 1)
        st.metric(
            label="Data Synchronization",
            value=f"v{sync_v} Live",
            delta=f"Auto-Sync: 8s Polling",
            delta_color="normal"
        )


@st.fragment(run_every=8)
def render_live_admission_workspace(user: dict):
    """
    Auto-refreshing fragment that polls database state every 8 seconds.
    Ensures cross-user updates appear within < 15 seconds without manual page refreshes.
    """
    metrics = get_live_bed_metrics()
    active_admissions = get_active_admissions()
    active_count = len(active_admissions)

    # 1. Roster and Telemetry Banner
    sync_stat = get_sync_status("global")
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 0.55rem 0.95rem; border-radius: 8px; margin-bottom: 1rem; font-size: 0.8rem;">
        <div style="display: flex; align-items: center; gap: 0.5rem; color: #1E293B;">
            <span style="color: #10B981; font-size: 0.95rem;">●</span>
            <b>Live Database Telemetry:</b> Authoritative schema connected. Last sync: <b>{sync_stat.get('last_updated_at', '')}</b> (Sync Cycle #{sync_stat.get('version', 1)})
        </div>
        <div style="color: #64748B;">
            Logged in as: <b style="color: #1E60F2;">{user.get('full_name')}</b> ({user.get('role')})
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. KPI Cards
    render_admission_kpi_cards(metrics, active_count)
    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    # 3. Workspace Navigation Tabs
    tab_admit, tab_roster, tab_matrix = st.tabs([
        "📝 Register New Patient Admission",
        f"🛏️ Active Inpatient Roster & Discharges ({active_count})",
        "📊 Department Capacity & Bed Matrix"
    ])

    # =========================================================================
    # TAB 1: REGISTER NEW PATIENT ADMISSION
    # =========================================================================
    with tab_admit:
        st.markdown("""
        <div style="margin-bottom: 0.85rem;">
            <h4 style="margin: 0; color: #0F172A; font-weight: 700; font-size: 1.15rem;">Patient Admission & Bed Allocation Protocol</h4>
            <p style="margin: 0; font-size: 0.8rem; color: #64748B;">
                Collect required patient details, verify live bed availability, and execute atomic admission.
            </p>
        </div>
        """, unsafe_allow_html=True)

        depts_info = get_all_departments()
        dept_names = [d["department"] for d in depts_info if d.get("total_capacity", 0) > 0]
        if not dept_names:
            dept_names = ["Medicine", "Surgery", "Orthopedics", "Pediatrics", "Obstetrics", "Medical ICU", "Surgical ICU"]

        col_f1, col_f2 = st.columns([1.2, 1.0], gap="medium")

        with col_f1:
            with st.container(border=True):
                st.markdown("<div style='font-size: 0.88rem; font-weight: 700; color: #1E293B; margin-bottom: 0.5rem;'>Patient Demographics & Clinical Intake</div>", unsafe_allow_html=True)

                p_c1, p_c2 = st.columns(2)
                with p_c1:
                    default_mrn = f"PAT-{int(datetime.utcnow().timestamp()) % 100000:05d}"
                    in_patient_id = st.text_input("Patient ID / MRN *", value=default_mrn, help="Hospital Unique Medical Record Number")
                with p_c2:
                    in_patient_name = st.text_input("Patient Full Name *", placeholder="e.g. Ramesh Chandra")

                p_c3, p_c4 = st.columns(2)
                with p_c3:
                    in_age = st.number_input("Age", min_value=0, max_value=120, value=45, step=1)
                with p_c4:
                    in_gender = st.selectbox("Gender", ["Male", "Female", "Other"])

                st.markdown("<div style='margin-top: 0.4rem; font-size: 0.88rem; font-weight: 700; color: #1E293B;'>Department & Admission Workflow</div>", unsafe_allow_html=True)
                
                a_c1, a_c2 = st.columns(2)
                with a_c1:
                    sel_dept = st.selectbox("Admitting Department *", dept_names, key="admit_sel_dept")
                with a_c2:
                    sel_type = st.selectbox("Admission Classification *", ["Emergency", "Elective", "Urgent", "Transfer"])

                # Dynamic available beds for selected department
                available_beds = get_available_beds_for_department(sel_dept)
                bed_options = ["None (Holding / Outpatient)"] + available_beds

                sel_bed_choice = st.selectbox(
                    f"Select Available Bed in {sel_dept} ({len(available_beds)} Free Beds)",
                    bed_options,
                    index=1 if available_beds else 0,
                    help="Only unoccupied beds are selectable to prevent double-allocation"
                )
                allocated_bed = None if sel_bed_choice.startswith("None") else sel_bed_choice

                in_notes = st.text_area("Initial Clinical Notes / Diagnosis", placeholder="Reason for admission, primary symptoms, attending clinician, triage score...")

                st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)
                if st.button("🚀 Confirm Admission & Allocate Bed", type="primary", width="stretch"):
                    if not in_patient_name.strip():
                        st.error("Patient Full Name is required.")
                    elif not in_patient_id.strip():
                        st.error("Patient ID / MRN is required.")
                    else:
                        try:
                            res = create_patient_admission(
                                patient_id=in_patient_id,
                                patient_name=in_patient_name,
                                department=sel_dept,
                                admission_type=sel_type,
                                age=int(in_age),
                                gender=in_gender,
                                bed_number=allocated_bed,
                                clinical_notes=in_notes,
                                actor_user=user
                            )
                            st.success(f"✅ Admission Successfully Recorded! Reference ID: **{res['admission_id']}**")
                            st.info(f"Assigned to **{res['department']}** | Bed: **{res['bed_number'] or 'General Holding'}** | Status: **Admitted**")
                            st.toast(f"Admission #{res['admission_id']} saved to database!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Admission Failed: {str(e)}")

        with col_f2:
            with st.container(border=True):
                st.markdown(f"<div style='font-size: 0.88rem; font-weight: 700; color: #1E293B; margin-bottom: 0.4rem;'>🛏️ Real-Time Availability: {sel_dept}</div>", unsafe_allow_html=True)
                
                # Department stats
                cur_dept_info = next((d for d in depts_info if d["department"].lower() == sel_dept.lower()), None)
                if cur_dept_info:
                    tot_c = int(cur_dept_info.get("total_capacity", 0))
                    occ_c = int(cur_dept_info.get("occupied_capacity", 0))
                    av_c = int(cur_dept_info.get("available_capacity", 0))
                    unav_c = int(cur_dept_info.get("unavailable_capacity", 0))
                    rate_c = round(occ_c / tot_c * 100, 1) if tot_c > 0 else 0

                    c_a, c_b = st.columns(2)
                    with c_a:
                        st.metric("Total Bed Capacity", f"{tot_c} Beds")
                        st.metric("Currently Occupied", f"{occ_c} Beds", f"{rate_c}% Full")
                    with c_b:
                        st.metric("Available for Admission", f"{av_c} Beds")
                        st.metric("Offline / Cleaning", f"{unav_c} Beds")

                    st.progress(min(1.0, max(0.0, rate_c / 100.0)), text=f"Ward Occupancy: {rate_c}%")
                
                st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                st.markdown("""
                <div style="background: #F1F5F9; border-radius: 6px; padding: 0.65rem; font-size: 0.76rem; color: #475569; line-height: 1.45;">
                    <b>🛡️ Concurrency & Integrity Protections Active:</b>
                    <ul style="margin: 0.25rem 0 0 1rem; padding: 0;">
                        <li>Re-entrant locks prevent two officers from booking the same bed simultaneously.</li>
                        <li>Occupancy counts are updated inside atomic SQLite/Postgres transactions.</li>
                        <li>Telemetry automatically updates the Admin Command Center within seconds.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: ACTIVE INPATIENT ROSTER & DISCHARGES
    # =========================================================================
    with tab_roster:
        st.markdown("""
        <div style="margin-bottom: 0.85rem;">
            <h4 style="margin: 0; color: #0F172A; font-weight: 700; font-size: 1.15rem;">Active Inpatient Census & Safe Discharge</h4>
            <p style="margin: 0; font-size: 0.8rem; color: #64748B;">
                Review currently admitted patients across hospital wards and execute clinical discharge with immediate bed release.
            </p>
        </div>
        """, unsafe_allow_html=True)

        f_col1, f_col2 = st.columns([1.5, 2.5])
        with f_col1:
            all_dept_filters = ["All Departments"] + sorted(list(set([a["department"] for a in active_admissions])))
            chosen_dept = st.selectbox("Filter Roster by Department", all_dept_filters, key="roster_filter_dept")
        with f_col2:
            search_query = st.text_input("🔍 Search Active Patient (Name, ID, Bed)", placeholder="Search by name, PAT-ID or bed...")

        filtered_roster = active_admissions
        if chosen_dept != "All Departments":
            filtered_roster = [a for a in filtered_roster if a["department"] == chosen_dept]
        if search_query.strip():
            sq = search_query.strip().lower()
            filtered_roster = [
                a for a in filtered_roster
                if sq in str(a.get("patient_name", "")).lower() or
                   sq in str(a.get("patient_id", "")).lower() or
                   sq in str(a.get("bed_number", "")).lower() or
                   sq in str(a.get("admission_id", "")).lower()
            ]

        if not filtered_roster:
            st.info("No active admissions found matching the selected criteria.")
        else:
            # Display roster table
            roster_df = pd.DataFrame([{
                "Admission ID": a["admission_id"],
                "Patient ID": a["patient_id"],
                "Patient Name": a["patient_name"],
                "Age/Sex": f"{a.get('age', '-')} / {a.get('gender', '-')}",
                "Department": a["department"],
                "Bed Assigned": a.get("bed_number") or "Unassigned",
                "Admission Type": a["admission_type"],
                "Admitted At": a["admitted_at"],
                "Admitted By": a.get("admitted_by", "Officer"),
                "Status": a["status"]
            } for a in filtered_roster])

            st.dataframe(roster_df, width="stretch", hide_index=True)

            # Discharge Action Card
            st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<div style='font-size: 0.88rem; font-weight: 700; color: #1E293B; margin-bottom: 0.35rem;'>🚪 Clinical Discharge & Bed Release Console</div>", unsafe_allow_html=True)
                
                d_c1, d_c2 = st.columns([1.5, 2.5])
                with d_c1:
                    discharge_options = {
                        f"{a['admission_id']} — {a['patient_name']} ({a['department']} | Bed: {a.get('bed_number', 'None')})": a['admission_id']
                        for a in filtered_roster
                    }
                    selected_patient_label = st.selectbox(
                        "Select Patient to Discharge",
                        list(discharge_options.keys()),
                        key="discharge_sel_patient"
                    )
                    target_admission_id = discharge_options.get(selected_patient_label)

                with d_c2:
                    discharge_notes = st.text_input("Discharge Disposition / Clinical Summary", placeholder="Discharged stable to home, prescription given, follow-up scheduled...")

                if st.button("🏁 Process Patient Discharge & Release Bed", type="secondary", width="stretch"):
                    if not target_admission_id:
                        st.error("Please select a patient to discharge.")
                    else:
                        try:
                            dis_res = discharge_patient(
                                admission_id=target_admission_id,
                                discharge_notes=discharge_notes,
                                actor_user=user
                            )
                            st.success(f"✅ Patient **{dis_res['patient_name']}** successfully discharged! Bed **{dis_res['released_bed'] or 'N/A'}** has been released back into hospital inventory.")
                            st.toast(f"Discharge recorded. Operational metrics synchronized.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"❌ Discharge Failed: {str(ex)}")

    # =========================================================================
    # TAB 3: DEPARTMENT CAPACITY & BED MATRIX
    # =========================================================================
    with tab_matrix:
        st.markdown("""
        <div style="margin-bottom: 0.85rem;">
            <h4 style="margin: 0; color: #0F172A; font-weight: 700; font-size: 1.15rem;">Live Departmental Capacity & Bed Matrix</h4>
            <p style="margin: 0; font-size: 0.8rem; color: #64748B;">
                Authoritative real-time occupancy counts maintained by atomic transactional handlers.
            </p>
        </div>
        """, unsafe_allow_html=True)

        dept_matrix = get_all_departments()
        if dept_matrix:
            matrix_df = pd.DataFrame([{
                "Resource Code": d["resource_id"],
                "Department": d["department"],
                "Resource Type": d["resource_type"],
                "Total Capacity": d["total_capacity"],
                "Occupied": d["occupied_capacity"],
                "Available": d["available_capacity"],
                "Offline / Maint": d["unavailable_capacity"],
                "Occupancy Rate": f"{round((d['occupied_capacity'] / d['total_capacity'] * 100), 1)}%" if d['total_capacity'] > 0 else "0.0%"
            } for d in dept_matrix])

            st.dataframe(matrix_df, width="stretch", hide_index=True)


def show_admission_workspace():
    """Main entrypoint for the Admission Officer Workspace view."""
    user = get_current_user()
    if not user:
        st.error("Authentication required. Please sign in.")
        return

    # Check least-privilege permission
    if not has_permission(user, "admissions.view"):
        st.error("⛔ Access Denied: You do not hold permissions to access the Admission Workspace.")
        return

    from ui.components import render_top_nav, render_footer
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), user.get("username", "AD")[:2].upper(), user.get("full_name", "Admission Officer"))

    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <h2 style="font-weight: 800; color: #0F172A; margin: 0;">🏥 Admission & Bed Allocation Workspace</h2>
            <span style="background: #EFF6FF; color: #1E60F2; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px; border: 1px solid #BFDBFE;">
                Admission Officer Portal
            </span>
        </div>
        <p style="color: #64748B; margin-top: 0.25rem; font-size: 0.88rem;">
            Register inpatient admissions, assign clinical beds transactionally, monitor active rosters, and manage discharges.
        </p>
    </div>
    """, unsafe_allow_html=True)

    render_live_admission_workspace(user)
    render_footer()
