"""
VitalOptima Hospital Command Center Dashboard View
Pixel-accurate, zero-gap recreation of the target hospital operations dashboard.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from config import (
    HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER,
    ASSETS_DIR, DATA_DIR,
    get_system_timestamp, get_greeting,
    GENERAL_BEDS_TOTAL, GENERAL_BEDS_OCCUPIED, GENERAL_BEDS_AVAILABLE, GENERAL_BEDS_RATE,
    ICU_BEDS_TOTAL, ICU_BEDS_OCCUPIED, ICU_BEDS_AVAILABLE, ICU_BEDS_RATE,
    STAFF_TOTAL, STAFF_SCHEDULED, STAFF_AVAILABLE, STAFF_ASSIGNED, STAFF_SHORTAGE, STAFF_RATE,
    OR_TOTAL, OR_OPERATIONAL, OR_UNAVAILABLE, OR_SCHEDULED, OR_AVAILABLE_SLOTS, OR_RATE
)
from ui.components import (
    render_top_nav, render_welcome_header, render_kpi_card_compact,
    create_predicted_vs_actual_chart, render_forecast_confidence_panel,
    render_compact_active_alerts, render_compact_ai_recommendation,
    render_before_after_cards, create_optimization_impact_chart,
    render_recent_forecasts_table, render_whatif_simulator_card,
    render_footer
)

from datetime import timedelta
from config import get_ist_now
from db.database import log_decision


@st.dialog("🚨 Hospital Incident Alerts & Active Constraints", width="large")
def show_all_alerts_dialog():
    st.html("""
    <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.75rem;">
        Current real-time constraint telemetry detected across acute clinical services.
    </div>
    """)

    alerts = [
        {"icon": "🔴", "severity": "High", "time": "02:47 IST", "title": "ICU capacity constraint", "desc": "ICU beds at 85% utilization across Medical and Surgical critical care."},
        {"icon": "🟠", "severity": "Medium", "time": "01:19 IST", "title": "ED staff shortage", "desc": "Only 5 registered nurses available in triage (required acuity minimum: 8)."},
        {"icon": "🟠", "severity": "Medium", "time": "23:54 IST", "title": "General bed shortage", "desc": "5 inpatient beds temporarily offline due to terminal cleaning & maintenance."},
        {"icon": "🟠", "severity": "Medium", "time": "21:30 IST", "title": "Pediatric ward occupancy high", "desc": "Pediatric inpatient census reached 24/30 beds (80% saturation)."},
        {"icon": "🟡", "severity": "Low", "time": "19:15 IST", "title": "Operating Theater turnover backlog", "desc": "PACU step-down delay delaying surgical block start times by 25 mins."},
        {"icon": "🔴", "severity": "High", "time": "18:40 IST", "title": "N95 Respirator low stock trigger", "desc": "Closing stock reached reorder threshold (30 boxes remaining)."}
    ]

    for a in alerts:
        sev_color = "#DC2626" if a["severity"] == "High" else ("#D97706" if a["severity"] == "Medium" else "#2563EB")
        sev_bg = "#FEE2E2" if a["severity"] == "High" else ("#FEF3C7" if a["severity"] == "Medium" else "#EFF6FF")
        st.html(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.65rem 0.85rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; gap: 0.6rem; align-items: flex-start;">
                <span style="font-size: 1rem;">{a['icon']}</span>
                <div>
                    <div style="font-size: 0.84rem; font-weight: 700; color: #0F172A;">{a['title']}</div>
                    <div style="font-size: 0.74rem; color: #64748B;">{a['desc']}</div>
                </div>
            </div>
            <div style="text-align: right; min-width: 90px;">
                <span style="font-size: 0.7rem; font-weight: 700; background: {sev_bg}; color: {sev_color}; padding: 2px 7px; border-radius: 4px;">{a['severity']}</span>
                <div style="font-size: 0.7rem; color: #94A3B8; margin-top: 2px;">{a['time']}</div>
            </div>
        </div>
        """)

    st.html("<hr style='margin: 0.75rem 0;' />")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 Open Resource Management & Capacity", key="dlg_btn_res_mgmt", width="stretch", type="primary"):
            st.session_state["current_page"] = "Resource Management"
            st.rerun()
    with c2:
        if st.button("💬 Search Alerts in Hospital Records (AI)", key="dlg_btn_db_search", width="stretch"):
            st.session_state["current_page"] = "Historical Data & Records"
            st.session_state["last_nlp_query"] = "List all active high severity hospital alerts"
            st.rerun()


@st.dialog("✨ AI Recommendation Clinical & Operational Details", width="large")
def show_recommendation_details_dialog():
    st.html("""
    <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 0.75rem;">
        Algorithmic decision support rationale computed by VitalOptima Linear Programming Optimizer.
    </div>
    """)

    st.html("""
    <div style="background: #F8FAFC; border-left: 4px solid #10B981; padding: 0.85rem 1rem; border-radius: 6px; margin-bottom: 0.75rem;">
        <div style="font-size: 0.92rem; font-weight: 700; color: #0F172A; margin-bottom: 0.2rem;">
            Proposal: Reallocate 4 Registered Nurses from Surgery Float Pool to Emergency Department
        </div>
        <div style="font-size: 0.78rem; color: #475569;">
            Duration: Next 6 hours (covering peak triage influx window 14:00 - 20:00 IST).
        </div>
    </div>
    """)

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Expected Improvement", "+18%", "Throughput gain")
    with k2:
        st.metric("ED Boarding Queue", "-42 Min", "Wait reduction")
    with k3:
        st.metric("Surgery Buffer Impact", "0 Overtime", "Block preserved")

    st.html("""
    <div style="margin-top: 0.75rem;">
        <h5 style="font-size: 0.85rem; font-weight: 700; color: #0F172A; margin-bottom: 0.35rem;">📋 Acuity & Roster Breakdown</h5>
        <ul style="font-size: 0.78rem; color: #334155; line-height: 1.5; padding-left: 1.2rem;">
            <li><b>ED Triage Acuity:</b> Predicted 20% surge (+12 patients/hr) demands 8 nurses; currently only 5 available. Deficit: <b>-3 RNs</b>.</li>
            <li><b>Surgical Suites Census:</b> Elective surgeries concluding early with 4 nurses available in float pool without breaching operating room coverage minimums.</li>
            <li><b>Nurse-to-Patient Ratio:</b> Rebalancing maintains safe clinical ratios (1:4 in ED and 1:2 in ICU/Post-op holding).</li>
        </ul>
    </div>
    """)

    st.html("<hr style='margin: 0.75rem 0;' />")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⚙️ Open Optimization View ➔", key="dlg_btn_goto_opt", width="stretch", type="primary"):
            st.session_state["current_page"] = "Optimization"
            st.rerun()
    with c2:
        if st.button("📋 Open Decision Log Audit Trail ➔", key="dlg_btn_goto_declog", width="stretch"):
            st.session_state["current_page"] = "Decision Log"
            st.rerun()


def render_interactive_active_alerts():
    now = get_ist_now()
    t_icu = (now - timedelta(minutes=17)).strftime("%H:%M")
    t_staff = (now - timedelta(hours=1, minutes=45)).strftime("%H:%M")
    t_bed = (now - timedelta(hours=3, minutes=10)).strftime("%H:%M")

    st.html("""
    <style>
    div[class*="st-key-panel_active_alerts"] > div {
        background: #FFFFFF !important;
        border-radius: 12px !important;
        padding: 0.75rem 0.95rem !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        gap: 0.3rem !important;
    }
    div[class*="st-key-panel_active_alerts"] {
        margin-bottom: 0.55rem !important;
    }
    div[class*="st-key-btn_view_all_alerts_link"] button,
    div[data-testid*="btn_view_all_alerts_link"] button {
        background: transparent !important;
        border: none !important;
        color: #2563EB !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        height: auto !important;
        min-height: auto !important;
        text-align: right !important;
        float: right !important;
        white-space: nowrap !important;
    }
    div[class*="st-key-btn_view_all_alerts_link"] button:hover,
    div[data-testid*="btn_view_all_alerts_link"] button:hover {
        color: #1D4ED8 !important;
        text-decoration: underline !important;
        background: transparent !important;
    }
    </style>
    """)

    with st.container(border=True, key="panel_active_alerts"):
        hdr1, hdr2 = st.columns([2.6, 1.4], gap="small")
        with hdr1:
            st.html('<div class="panel-title" style="font-size: 0.88rem; margin: 0; padding-top: 2px;"><span style="color:#EF4444;">🚨</span> Active Alerts</div>')
        with hdr2:
            if st.button("View all →", key="btn_view_all_alerts_link", type="tertiary"):
                show_all_alerts_dialog()

        st.html(f"""
        <div style="display: flex; flex-direction: column; gap: 0.45rem; margin-top: 0.15rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 0.35rem; border-bottom: 1px solid #F1F5F9;">
                <div style="display: flex; gap: 0.45rem; align-items: flex-start;">
                    <span style="color: #EF4444; font-size: 0.8rem; margin-top: 1px;">🔴</span>
                    <div>
                        <div style="font-size: 0.78rem; font-weight: 700; color: #1E293B;">ICU capacity constraint</div>
                        <div style="font-size: 0.7rem; color: #64748B;">ICU beds at 85% utilization</div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 0.4rem;">
                    <span style="font-size: 0.69rem; color: #94A3B8;">{t_icu}</span>
                    <span style="font-size: 0.67rem; font-weight: 700; background: #FEE2E2; color: #DC2626; padding: 0.1rem 0.35rem; border-radius: 4px;">High</span>
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 0.35rem; border-bottom: 1px solid #F1F5F9;">
                <div style="display: flex; gap: 0.45rem; align-items: flex-start;">
                    <span style="color: #F59E0B; font-size: 0.8rem; margin-top: 1px;">🟠</span>
                    <div>
                        <div style="font-size: 0.78rem; font-weight: 700; color: #1E293B;">ED staff shortage</div>
                        <div style="font-size: 0.7rem; color: #64748B;">Only 5 staff available (required 8)</div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 0.4rem;">
                    <span style="font-size: 0.69rem; color: #94A3B8;">{t_staff}</span>
                    <span style="font-size: 0.67rem; font-weight: 700; background: #FEF3C7; color: #D97706; padding: 0.1rem 0.35rem; border-radius: 4px;">Medium</span>
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="display: flex; gap: 0.45rem; align-items: flex-start;">
                    <span style="color: #F59E0B; font-size: 0.8rem; margin-top: 1px;">🟠</span>
                    <div>
                        <div style="font-size: 0.78rem; font-weight: 700; color: #1E293B;">General bed shortage</div>
                        <div style="font-size: 0.7rem; color: #64748B;">5 beds expected to be unavailable</div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 0.4rem;">
                    <span style="font-size: 0.69rem; color: #94A3B8;">{t_bed}</span>
                    <span style="font-size: 0.67rem; font-weight: 700; background: #FEF3C7; color: #D97706; padding: 0.1rem 0.35rem; border-radius: 4px;">Medium</span>
                </div>
            </div>
        </div>
        """)


def render_interactive_ai_recommendation():
    st.html("""
    <style>
    div[class*="st-key-panel_ai_recommendation"] > div {
        background: #FFFFFF !important;
        border-radius: 12px !important;
        padding: 0.75rem 0.95rem !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        gap: 0.3rem !important;
    }
    div[class*="st-key-panel_ai_recommendation"] {
        margin-bottom: 0.55rem !important;
    }
    div[class*="st-key-btn_view_rec_details_link"] button,
    div[data-testid*="btn_view_rec_details_link"] button {
        background: transparent !important;
        border: none !important;
        color: #2563EB !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        height: auto !important;
        min-height: auto !important;
        text-align: right !important;
        float: right !important;
        white-space: nowrap !important;
    }
    div[class*="st-key-btn_view_rec_details_link"] button:hover,
    div[data-testid*="btn_view_rec_details_link"] button:hover {
        color: #1D4ED8 !important;
        text-decoration: underline !important;
        background: transparent !important;
    }

    div[class*="st-key-btn_rec_act_"] button,
    div[data-testid*="btn_rec_act_"] button {
        padding: 0.2rem 2px !important;
        min-height: 28px !important;
        height: 28px !important;
        border-radius: 6px !important;
        width: 100% !important;
    }
    div[class*="st-key-btn_rec_act_"] button div,
    div[data-testid*="btn_rec_act_"] button div,
    div[class*="st-key-btn_rec_act_"] button p,
    div[data-testid*="btn_rec_act_"] button p {
        font-size: 0.65rem !important;
        font-weight: 600 !important;
        line-height: 1 !important;
        margin: 0 !important;
        letter-spacing: -0.2px !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }
    div[class*="st-key-btn_rec_act_ack"] button,
    div[data-testid*="btn_rec_act_ack"] button {
        border: 1px solid #CBD5E1 !important;
        background: #FFFFFF !important;
    }
    div[class*="st-key-btn_rec_act_ack"] button p,
    div[data-testid*="btn_rec_act_ack"] button p {
        color: #334155 !important;
    }
    div[class*="st-key-btn_rec_act_ack"] button:hover,
    div[data-testid*="btn_rec_act_ack"] button:hover {
        border-color: #94A3B8 !important;
        background: #F1F5F9 !important;
    }
    div[class*="st-key-btn_rec_act_assign"] button,
    div[data-testid*="btn_rec_act_assign"] button {
        border: 1px solid #93C5FD !important;
        background: #EFF6FF !important;
    }
    div[class*="st-key-btn_rec_act_assign"] button p,
    div[data-testid*="btn_rec_act_assign"] button p {
        color: #1D4ED8 !important;
    }
    div[class*="st-key-btn_rec_act_assign"] button:hover,
    div[data-testid*="btn_rec_act_assign"] button:hover {
        border-color: #3B82F6 !important;
        background: #DBEAFE !important;
    }
    div[class*="st-key-btn_rec_act_approve"] button,
    div[data-testid*="btn_rec_act_approve"] button {
        border: none !important;
        background: #10B981 !important;
    }
    div[class*="st-key-btn_rec_act_approve"] button p,
    div[data-testid*="btn_rec_act_approve"] button p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    div[class*="st-key-btn_rec_act_approve"] button:hover,
    div[data-testid*="btn_rec_act_approve"] button:hover {
        background: #059669 !important;
    }
    div[class*="st-key-btn_rec_act_resolve"] button,
    div[data-testid*="btn_rec_act_resolve"] button {
        border: 1px solid #CBD5E1 !important;
        background: #FFFFFF !important;
    }
    div[class*="st-key-btn_rec_act_resolve"] button p,
    div[data-testid*="btn_rec_act_resolve"] button p {
        color: #475569 !important;
    }
    div[class*="st-key-btn_rec_act_resolve"] button:hover,
    div[data-testid*="btn_rec_act_resolve"] button:hover {
        border-color: #94A3B8 !important;
        background: #F1F5F9 !important;
    }
    </style>
    """)

    with st.container(border=True, key="panel_ai_recommendation"):
        hdr1, hdr2 = st.columns([2.6, 1.4], gap="small")
        with hdr1:
            st.html('<div class="panel-title" style="font-size: 0.88rem; margin: 0; padding-top: 2px;"><span style="color:#10B981;">✨</span> AI Recommendation</div>')
        with hdr2:
            if st.button("View details →", key="btn_view_rec_details_link", type="tertiary"):
                show_recommendation_details_dialog()

        rec_status = st.session_state.get("rec_decision_status")
        if rec_status:
            badge_html = f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem;">
                <span style="display: inline-block; background: #DCFCE7; color: #15803D; font-size: 0.68rem; font-weight: 700; padding: 0.12rem 0.5rem; border-radius: 20px; border: 1px solid #BBF7D0;">
                    Expected improvement: 18%
                </span>
                <span style="background: #EFF6FF; color: #1E40AF; font-size: 0.68rem; font-weight: 700; padding: 0.12rem 0.45rem; border-radius: 4px; border: 1px solid #BFDBFE;">
                    {rec_status}
                </span>
            </div>
            """
        else:
            badge_html = """
            <div style="display: inline-block; background: #DCFCE7; color: #15803D; font-size: 0.68rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 20px; border: 1px solid #BBF7D0; margin-bottom: 0.5rem;">
                Expected improvement: 18%
            </div>
            """

        st.html(f"""
        <div style="font-size: 0.82rem; font-weight: 700; color: #0F172A; margin-top: 0.1rem; margin-bottom: 0.2rem;">
            Reallocate 4 nurses from Surgery to ED (next 6 hours)
        </div>
        <div style="font-size: 0.71rem; color: #64748B; margin-bottom: 0.35rem; line-height: 1.35;">
            Based on forecasted 20% increase in ED arrivals and current staff availability.
        </div>
        {badge_html}
        """)

        b1, b2, b3, b4 = st.columns([1.25, 0.85, 0.95, 0.95], gap="small")
        with b1:
            if st.button("Acknowledge", key="btn_rec_act_ack"):
                log_decision(
                    category="Staffing Optimization",
                    recommendation="Reallocate 4 nurses from Surgery to ED (next 6 hours)",
                    decision="Acknowledged",
                    administrator="Admin (AD)",
                    rationale="Reviewed emergency arrival forecast (+20%) and acknowledged reallocation mandate."
                )
                st.session_state["rec_decision_status"] = f"Acknowledged ({get_ist_now().strftime('%H:%M')})"
                st.toast("✅ Recommendation acknowledged and logged to audit trail.")
                st.rerun()

        with b2:
            if st.button("Assign", key="btn_rec_act_assign"):
                log_decision(
                    category="Staffing Optimization",
                    recommendation="Reallocate 4 nurses from Surgery to ED (next 6 hours)",
                    decision="Assigned",
                    modified_details="Assigned 4 Surgery nurses to ED triage coverage",
                    administrator="Admin (AD)",
                    rationale="Shift roster modified to dispatch float nurses to ED."
                )
                st.session_state["rec_decision_status"] = f"Assigned ({get_ist_now().strftime('%H:%M')})"
                st.toast("📋 4 Surgery nurses assigned to ED charge nurse.")
                st.rerun()

        with b3:
            if st.button("Approve", key="btn_rec_act_approve"):
                log_decision(
                    category="Staffing Optimization",
                    recommendation="Reallocate 4 nurses from Surgery to ED (next 6 hours)",
                    decision="Approved",
                    administrator="Admin (AD)",
                    rationale="Approved nurse reallocation to absorb forecasted +20% arrival influx."
                )
                st.session_state["rec_decision_status"] = f"Approved ({get_ist_now().strftime('%H:%M')})"
                st.toast("🚀 Recommendation Approved! Roster committed.")
                st.rerun()

        with b4:
            if st.button("Resolve", key="btn_rec_act_resolve"):
                log_decision(
                    category="Staffing Optimization",
                    recommendation="Reallocate 4 nurses from Surgery to ED (next 6 hours)",
                    decision="Resolved",
                    administrator="Admin (AD)",
                    rationale="Action completed. Shift coverage satisfied."
                )
                st.session_state["rec_decision_status"] = f"Resolved ({get_ist_now().strftime('%H:%M')})"
                st.toast("✅ Action Resolved. Staffing constraint cleared.")
                st.rerun()


def render_interactive_whatif_simulator_card():
    st.html("""
    <style>
    div[class*="st-key-panel_whatif_simulator"] > div {
        background: #FFFFFF !important;
        border-radius: 12px !important;
        padding: 0.75rem 0.95rem !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        gap: 0.35rem !important;
    }
    div[class*="st-key-panel_whatif_simulator"] {
        margin-bottom: 0.55rem !important;
    }
    div[data-testid*="btn_run_sim_trigger_link"] button {
        background: transparent !important;
        border: none !important;
        color: #2563EB !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        height: auto !important;
        min-height: auto !important;
        text-align: right !important;
        float: right !important;
        white-space: nowrap !important;
    }
    div[class*="st-key-btn_run_sim_trigger_link"] button,
    div[data-testid*="btn_run_sim_trigger_link"] button {
        background: transparent !important;
        border: none !important;
        color: #2563EB !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        height: auto !important;
        min-height: auto !important;
        text-align: right !important;
        float: right !important;
        white-space: nowrap !important;
    }
    div[class*="st-key-btn_run_sim_trigger_link"] button:hover,
    div[data-testid*="btn_run_sim_trigger_link"] button:hover {
        color: #1D4ED8 !important;
        text-decoration: underline !important;
        background: transparent !important;
    }

    div[class*="st-key-sim_trigger_card_"] button,
    div[data-testid*="sim_trigger_card_"] button {
        border-radius: 8px !important;
        padding: 0.5rem 0.75rem !important;
        text-align: left !important;
        width: 100% !important;
        white-space: pre-line !important;
        line-height: 1.35 !important;
        margin-bottom: 0.35rem !important;
        box-shadow: none !important;
    }
    div[class*="st-key-sim_trigger_card_ed"] button,
    div[data-testid*="sim_trigger_card_ed"] button {
        background: #FEF2F2 !important;
        border: 1px solid #FEE2E2 !important;
        color: #DC2626 !important;
    }
    div[class*="st-key-sim_trigger_card_ed"] button:hover,
    div[data-testid*="sim_trigger_card_ed"] button:hover {
        border-color: #FCA5A5 !important;
        background: #FEE2E2 !important;
    }
    div[class*="st-key-sim_trigger_card_icu"] button,
    div[data-testid*="sim_trigger_card_icu"] button {
        background: #FFFBEB !important;
        border: 1px solid #FEF3C7 !important;
        color: #D97706 !important;
    }
    div[class*="st-key-sim_trigger_card_icu"] button:hover,
    div[data-testid*="sim_trigger_card_icu"] button:hover {
        border-color: #FCD34D !important;
        background: #FEF3C7 !important;
    }
    div[class*="st-key-sim_trigger_card_staff"] button,
    div[data-testid*="sim_trigger_card_staff"] button {
        background: #F5F3FF !important;
        border: 1px solid #EDE9FE !important;
        color: #7C3AED !important;
    }
    div[class*="st-key-sim_trigger_card_staff"] button:hover,
    div[data-testid*="sim_trigger_card_staff"] button:hover {
        border-color: #C4B5FD !important;
        background: #EDE9FE !important;
    }
    </style>
    """)

    with st.container(border=True, key="panel_whatif_simulator"):
        hdr1, hdr2 = st.columns([2.5, 1.5], gap="small")
        with hdr1:
            st.html('<div class="panel-title" style="font-size: 0.88rem; margin: 0; padding-top: 2px;"><span style="color:#2563EB;">🔬</span> What-if Simulator</div>')
        with hdr2:
            if st.button("Run Simulation →", key="btn_run_sim_trigger_link", type="tertiary"):
                st.session_state["current_page"] = "What-if Simulator"
                st.rerun()

        if st.button("🚨  +20% Emergency Arrivals  ›\nSee impact on resources and shortages", key="sim_trigger_card_ed", help="Simulate +20% surge in emergency patient arrivals"):
            st.session_state["current_page"] = "What-if Simulator"
            st.session_state["sim_active_query"] = "What happens if there is a 20% patient surge from an emergency influx?"
            st.rerun()

        if st.button("⚠️  ICU Capacity Reduction  ›\nSimulate temporary loss of ICU beds", key="sim_trigger_card_icu", help="Simulate temporary loss of ICU beds"):
            st.session_state["current_page"] = "What-if Simulator"
            st.session_state["sim_active_query"] = "What if HVAC contamination shuts down 50% of ICU beds with a 20% patient influx?"
            st.rerun()

        if st.button("👥  Staff Shortage  ›\nModel reduced staff availability", key="sim_trigger_card_staff", help="Simulate 35% clinical staff absenteeism"):
            st.session_state["current_page"] = "What-if Simulator"
            st.session_state["sim_active_query"] = "Simulate a severe respiratory outbreak causing 35% staff absenteeism and 40% surge"
            st.rerun()



def show_dashboard():
    # 1. Top Navigation Bar with live IST timestamp & clinical shift indicator
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)

    # 2. Dynamic Time-of-Day Greeting & Hospital Exterior Header
    greeting_title, greeting_subtitle = get_greeting(ADMIN_USER)
    render_welcome_header(ASSETS_DIR / "hospital_building.jpg", title=greeting_title, subtitle=greeting_subtitle)

    # 3. Top Row - 4 Precision Compact KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.html(render_kpi_card_compact(
            "🛏️", "General Beds",
            GENERAL_BEDS_OCCUPIED, GENERAL_BEDS_TOTAL, "Occupied",
            GENERAL_BEDS_RATE, "#3B82F6",
            GENERAL_BEDS_AVAILABLE, "available", "#10B981"
        ))
    with k2:
        st.html(render_kpi_card_compact(
            "🫀", "ICU Beds",
            ICU_BEDS_OCCUPIED, ICU_BEDS_TOTAL, "Occupied",
            ICU_BEDS_RATE, "#8B5CF6",
            ICU_BEDS_AVAILABLE, "available", "#10B981"
        ))
    with k3:
        st.html(render_kpi_card_compact(
            "👥", "Staff Availability",
            STAFF_AVAILABLE, STAFF_TOTAL, "On Duty",
            STAFF_RATE, "#10B981",
            STAFF_TOTAL - STAFF_AVAILABLE, "off duty", "#3B82F6"
        ))
    with k4:
        st.html(render_kpi_card_compact(
            "🩺", "Operating Rooms",
            OR_OPERATIONAL, OR_TOTAL, "In Use",
            OR_RATE, "#06B6D4",
            OR_AVAILABLE_SLOTS, "available", "#10B981"
        ))

    # 4. Continuous Two-Column Layout (eliminating 400px empty chasm and balancing left vs right)
    col_main_left, col_main_right = st.columns([6.7, 3.3], gap="medium")

    with col_main_left:
        # Chart 1: Predicted vs Actual Arrivals
        with st.container(border=True, key="panel_arrivals_chart"):
            st.html('''
            <div class="panel-header" style="margin-bottom: 0.15rem;">
                <div class="panel-title" style="font-size: 0.90rem;"><span style="color:#2563EB;">📈</span> Predicted vs Actual Patient Arrivals</div>
                <div style="font-size: 0.72rem; color: #64748B;">Hourly emergency arrival volume with 95% forecast confidence interval</div>
            </div>
            ''')
            fig_arr = create_predicted_vs_actual_chart()
            st.plotly_chart(fig_arr, width="stretch", config={"displayModeBar": False})

        # Panel 2: Before vs After Optimization
        with st.container(border=True, key="panel_opt_comparison"):
            st.html('''
            <div class="panel-header" style="margin-bottom: 0.35rem;">
                <div>
                    <div class="panel-title" style="font-size: 0.90rem;"><span style="color:#2563EB;">🔄</span> Before vs After Optimization</div>
                    <div class="panel-subtitle" style="font-size: 0.72rem; color: #64748B;">Comparative allocation efficiency and resource impact</div>
                </div>
            </div>
            ''')
            opt_c1, opt_c2 = st.columns([1.18, 1.0])
            with opt_c1:
                st.html(render_before_after_cards())
            with opt_c2:
                st.html('<div style="font-size:0.76rem; font-weight:700; color:#0F172A; margin-bottom:0.15rem;">Optimization Impact</div>')
                fig_opt = create_optimization_impact_chart()
                st.plotly_chart(fig_opt, width="stretch", config={"displayModeBar": False})

        # Panel 3: Recent Forecasts Table
        st.html(render_recent_forecasts_table())

    with col_main_right:
        # Card 1: Active Alerts
        render_interactive_active_alerts()

        # Card 2: AI Recommendation
        render_interactive_ai_recommendation()

        # Card 3: What-if Simulator Quick Triggers Card
        render_interactive_whatif_simulator_card()

        # Card 4: Quick Actions Card
        with st.container(border=True, key="panel_quick_actions"):
            st.html('''
            <div class="panel-header" style="margin-bottom: 0.35rem;">
                <div class="panel-title" style="font-size: 0.88rem;"><span style="color:#F59E0B;">⚡</span> Quick Actions</div>
            </div>
            ''')
            qa1, qa2 = st.columns(2)
            with qa1:
                if st.button("📈 Run Forecast", width="stretch"):
                    st.session_state["current_page"] = "Demand Forecasting"
                    st.rerun()
                if st.button("🎛️ Simulator", width="stretch"):
                    st.session_state["current_page"] = "What-if Simulator"
                    st.rerun()

            with qa2:
                if st.button("⚙️ Optimize", width="stretch"):
                    st.session_state["current_page"] = "Optimization"
                    st.rerun()
                if st.button("📋 Decision Log", width="stretch"):
                    st.session_state["current_page"] = "Decision Log"
                    st.rerun()

        # Card 5: AI Helper Tip Box
        st.html('''
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.65rem 0.85rem; display: flex; align-items: center; justify-content: space-between; gap: 0.65rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02); margin-bottom: 0.65rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.1rem; color: #3B82F6;">💡</span>
                <span style="font-size: 0.72rem; color: #475569; line-height: 1.35;">Using real-time data and predictive analytics to help you make better decisions.</span>
            </div>
            <div style="width: 24px; height: 24px; border-radius: 50%; background: #EFF6FF; display: flex; align-items: center; justify-content: center; flex-shrink: 0; color: #2563EB; font-size: 0.75rem;">
                💙
            </div>
        </div>
        ''')

    # 5. Footer
    render_footer()
