"""
VitalOptima Decision Log & Audit Trail View
Legally auditable trail of all optimization approvals, human modifications, and clinical overrides.
"""
import streamlit as st
import pandas as pd
from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp
from ui.components import render_top_nav, render_footer
from db.database import get_decision_logs

def show_decision_log():
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)

    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.25rem;">Administrator Decision Log</h2>
        <p style="color: #64748B;">Legally auditable trail of all optimization approvals, human modifications, and clinical overrides.</p>
    </div>
    """, unsafe_allow_html=True)

    rows = get_decision_logs()
    
    # Compute summary metrics
    total_decisions = len(rows) if rows else 0
    accepted_count = sum(1 for r in rows if r["decision"] == "Accepted") if rows else 0
    modified_count = sum(1 for r in rows if r["decision"] == "Modified") if rows else 0
    rejected_count = sum(1 for r in rows if r["decision"] == "Rejected") if rows else 0
    approval_rate = round((accepted_count / max(1, total_decisions)) * 100, 1) if rows else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Decisions Logged", f"{total_decisions}", delta="Recorded")
    with m2:
        st.metric("Approval Rate", f"{approval_rate}%", delta=f"{accepted_count} Accepted")
    with m3:
        st.metric("Human Modifications", f"{modified_count}", delta="Clinician Adjusted")
    with m4:
        st.metric("Clinical Overrides / Rejections", f"{rejected_count}", delta="Safeguarded")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    if rows:
        data = []
        for r in rows:
            data.append({
                "ID": r["id"],
                "Timestamp": r["timestamp"],
                "Category": r["category"],
                "Recommendation": r["recommendation"],
                "Decision": r["decision"],
                "Modifications": r["modified_details"] if r["modified_details"] else "None (Full Approval)",
                "Administrator": r["administrator"],
                "Rationale": r["rationale"]
            })
        df = pd.DataFrame(data)

        # Add filters for audit log
        f_col1, f_col2 = st.columns([1, 1])
        with f_col1:
            categories = ["All Categories"] + sorted(list(df["Category"].unique()))
            selected_cat = st.selectbox("Filter by Resource Category", categories)
        with f_col2:
            statuses = ["All Statuses"] + sorted(list(df["Decision"].unique()))
            selected_status = st.selectbox("Filter by Decision Outcome", statuses)

        filtered_df = df.copy()
        if selected_cat != "All Categories":
            filtered_df = filtered_df[filtered_df["Category"] == selected_cat]
        if selected_status != "All Statuses":
            filtered_df = filtered_df[filtered_df["Decision"] == selected_status]

        # Format Decision with crisp emoji status badges
        display_df = filtered_df.copy()
        display_df["Decision"] = display_df["Decision"].apply(
            lambda d: f"🟢 {d}" if d == "Accepted" else (f"🟡 {d}" if d == "Modified" else f"🔴 {d}")
        )

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True
        )

        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Filtered Audit Trail (CSV)",
            data=csv,
            file_name=f"vitaloptima_audit_log_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No decisions logged yet. Run optimization recommendations to record decisions.")

    st.markdown("---")
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; font-size: 0.8rem; color: #475569;">
        <b>Compliance & Non-Clinical Scope Notice:</b> In accordance with hospital operational governance, HIPAA synthetic simulation validation, and clinical safety standards, all machine learning resource suggestions require affirmative human sign-off before operational execution. VitalOptima does not execute autonomous clinical triage.
    </div>
    """, unsafe_allow_html=True)

    render_footer()
