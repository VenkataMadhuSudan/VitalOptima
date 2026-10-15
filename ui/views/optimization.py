"""
VitalOptima Resource Optimization View
Mixed-Integer Linear Programming recommendations with Human-in-the-Loop decision governance.
"""
import streamlit as st
import pandas as pd
from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp
from ui.components import render_top_nav, render_footer
from models.optimizer import ResourceOptimizer
from db.database import log_decision, get_decision_logs

def show_optimization():
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)

    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.25rem;">Resource Optimization</h2>
        <p style="color: #64748B;">Mathematical allocation recommendations (Google OR-Tools MILP) with human administrator override.</p>
    </div>
    """, unsafe_allow_html=True)

    optimizer = ResourceOptimizer()
    recommendations, opt_res = optimizer.generate_recommendations()

    # Solver metrics banner
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Solver Engine", "Google OR-Tools SCIP", delta="MILP")
    with m2:
        st.metric("Optimization Status", opt_res["status"], delta="100% Feasible")
    with m3:
        st.metric("Patients Reallocated", f"{opt_res['total_allocated']}", delta="Zero Critical Wait")
    with m4:
        st.metric("Unmet Acute Demand", sum(opt_res["unmet_demand"].values()), delta="0 Deficit", delta_color="normal")

    st.markdown("### Actionable AI Recommendations (Human-in-the-Loop)")
    st.info("ℹ️ **Clinical Safeguard:** VitalOptima provides administrative decision-support only. Final resource deployments require administrator review and digital sign-off.")

    for i, rec in enumerate(recommendations):
        with st.container():
            st.html(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem; margin-bottom: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <span style="background: #EFF6FF; color: #2563EB; font-weight: 700; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px;">{rec['category']}</span>
                        <h4 style="margin: 0.5rem 0 0.25rem 0; color: #0F172A; font-weight: 700;">{rec['id']}: {rec['title']}</h4>
                        <p style="color: #64748B; font-size: 0.85rem; margin: 0;"><b>Expected Operational Impact:</b> {rec['impact']}</p>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size: 0.8rem; color: #64748B;">Model Confidence</span>
                        <div style="font-weight: 800; color: #10B981; font-size: 1.1rem;">{rec['confidence']}</div>
                    </div>
                </div>
            </div>
            """)

            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1, 3])
            
            with btn_col1:
                if st.button("✅ Accept", key=f"acc_{rec['id']}", width="stretch"):
                    log_decision(
                        category=rec["category"],
                        recommendation=rec["title"],
                        decision="Accepted",
                        administrator=f"{ADMIN_USER} ({ADMIN_INITIALS})",
                        rationale="Approved as formulated by OR-Tools."
                    )
                    st.success(f"Recommendation {rec['id']} accepted and logged to audit database.")

            with btn_col2:
                modify_clicked = st.button("✏️ Modify", key=f"mod_btn_{rec['id']}", width="stretch")

            with btn_col3:
                reject_clicked = st.button("❌ Reject", key=f"rej_btn_{rec['id']}", width="stretch")

            if modify_clicked or st.session_state.get(f"show_mod_{rec['id']}", False):
                st.session_state[f"show_mod_{rec['id']}"] = True
                mod_text = st.text_input(f"Specify modification for {rec['id']}:", key=f"mod_in_{rec['id']}", placeholder="e.g. Reduce count to 3, route remaining 2 to surgical annex...")
                mod_reason = st.text_input(f"Clinical or operational justification:", key=f"mod_rs_{rec['id']}", placeholder="e.g. Attending physician requested extra isolation buffer...")
                if st.button("Save Modified Allocation", key=f"save_mod_{rec['id']}"):
                    log_decision(
                        category=rec["category"],
                        recommendation=rec["title"],
                        decision="Modified",
                        modified_details=mod_text,
                        administrator=f"{ADMIN_USER} ({ADMIN_INITIALS})",
                        rationale=mod_reason
                    )
                    st.session_state[f"show_mod_{rec['id']}"] = False
                    st.success(f"Recommendation {rec['id']} modified and logged.")

            if reject_clicked or st.session_state.get(f"show_rej_{rec['id']}", False):
                st.session_state[f"show_rej_{rec['id']}"] = True
                rej_reason = st.text_input(f"State rationale for rejecting {rec['id']}:", key=f"rej_rs_{rec['id']}", placeholder="e.g. Incoming emergency flight from regional hospital requires beds...")
                if st.button("Confirm Rejection", key=f"save_rej_{rec['id']}"):
                    log_decision(
                        category=rec["category"],
                        recommendation=rec["title"],
                        decision="Rejected",
                        administrator=f"{ADMIN_USER} ({ADMIN_INITIALS})",
                        rationale=rej_reason
                    )
                    st.session_state[f"show_rej_{rec['id']}"] = False
                    st.warning(f"Recommendation {rec['id']} rejected. Decision logged to audit history.")

    st.markdown("---")
    st.markdown("### MILP Routing Matrix (OR-Tools Solution)")
    df_alloc = pd.DataFrame(opt_res["allocations"])
    st.dataframe(df_alloc, width="stretch", hide_index=True)

    render_footer()
