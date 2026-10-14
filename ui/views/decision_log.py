"""
VitalOptima Decision Log View
Governance, clinical audit trail, and historical record of administrator authorizations.
"""
import streamlit as st
import pandas as pd

from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp
from ui.components import render_top_nav, render_footer, render_metric_card
from db.database import get_decision_logs, log_decision

def show_decision_log():
    """Decision log audit trail view."""
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)

    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.2rem; letter-spacing: -0.02em;">
            📋 Clinical Governance & Decision Audit Trail
        </h2>
        <p style="color: #64748B; font-size: 0.92rem; margin: 0;">
            Immutable audit record of all AI-generated resource allocation recommendations accepted, modified, or rejected by hospital administrators.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Fetch live logs
    logs = get_decision_logs()
    df_logs = pd.DataFrame(logs) if logs else pd.DataFrame()

    total_decisions = len(df_logs)
    accepted_count = len(df_logs[df_logs["decision"] == "Accepted"]) if not df_logs.empty and "decision" in df_logs.columns else 0
    modified_count = len(df_logs[df_logs["decision"] == "Modified"]) if not df_logs.empty and "decision" in df_logs.columns else 0
    adoption_rate = round(100.0 * (accepted_count + modified_count) / max(total_decisions, 1), 1)

    # 2. Audit KPI Cards
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        render_metric_card("Total Audit Records", f"{total_decisions} Actions", "All logged interventions", card_type="default", icon="📑")
    with d2:
        render_metric_card("Algorithmic Adoption", f"{adoption_rate}%", "Accepted or modified", card_type="success", icon="🤝")
    with d3:
        render_metric_card("Accepted Protocols", f"{accepted_count} Implemented", "Zero-friction adoption", card_type="default", icon="✅")
    with d4:
        render_metric_card("Physician Modifications", f"{modified_count} Tailored", "Clinical adjustments", card_type="warning", icon="✏️")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    tab_table, tab_add = st.tabs(["📜 Historical Decision Audit Records", "➕ Log Administrative Directive"])

    with tab_table:
        if not df_logs.empty:
            # Filters
            f1, f2 = st.columns([1, 1])
            with f1:
                cat_options = ["All Categories"] + sorted(df_logs["category"].dropna().unique().tolist())
                sel_cat = st.selectbox("Filter Category", cat_options)
            with f2:
                dec_options = ["All Outcomes"] + sorted(df_logs["decision"].dropna().unique().tolist())
                sel_dec = st.selectbox("Filter Outcome", dec_options)

            view_df = df_logs.copy()
            if sel_cat != "All Categories":
                view_df = view_df[view_df["category"] == sel_cat]
            if sel_dec != "All Outcomes":
                view_df = view_df[view_df["decision"] == sel_dec]

            st.dataframe(view_df, width="stretch", hide_index=True)

            # Export button
            csv_data = view_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Decision Audit Trail (CSV)",
                data=csv_data,
                file_name="vitaloptima_decision_audit_trail.csv",
                mime="text/csv"
            )
        else:
            st.info("No decision records currently found.")

    with tab_add:
        st.markdown("#### Record a Manual Administrative or Physician Directive")
        with st.form("manual_log_form"):
            c_cat = st.selectbox("Directive Category", ["Staff Allocation", "ICU Capacity", "OR Rescheduling", "Patient Diversion", "Disaster Emergency Policy"])
            c_rec = st.text_input("Operational Context / Recommended Action", placeholder="e.g. Open ambulatory overflow unit for 10 surge patients")
            c_dec = st.selectbox("Authorization Status", ["Accepted", "Modified", "Rejected"])
            c_mod = st.text_input("Clinical Adjustments / Caveats", placeholder="Optional modification notes")
            c_rat = st.text_area("Administrative Rationale", placeholder="e.g. Approved due to multi-vehicle highway accident Code Yellow triage")
            
            submitted = st.form_submit_button("Submit & Authorize Directive", type="primary")
            if submitted:
                if c_rec.strip():
                    log_decision(
                        category=c_cat,
                        recommendation=c_rec,
                        decision=c_dec,
                        modified_details=c_mod,
                        administrator=ADMIN_USER,
                        rationale=c_rat
                    )
                    st.success("Administrative directive successfully recorded into governance audit log!")
                    st.rerun()
                else:
                    st.error("Please provide the operational action description before submitting.")

    render_footer()
