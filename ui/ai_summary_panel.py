"""
VitalOptima — AI Dashboard Summarizer Floating Assistant & Summary Panel
Implements the fixed bottom-right floating trigger button, compact slide-over
hospital insights drawer, structured operational sections (A-G),
deterministic data freshness indicator, refresh control, copy summary,
and interactive parameter-safe contextual follow-up query engine.
"""

import time
import streamlit as st
from typing import Dict, Any, Optional
from services.dashboard_summarizer import DashboardSummarizerService, handle_dashboard_qa_request
from config import ADMIN_USER, get_ist_now


def _get_auth_context() -> Dict[str, Any]:
    """Retrieves current authenticated administrator context from session state."""
    auth_user = st.session_state.get("authenticated_user")
    if isinstance(auth_user, dict):
        return {
            "user_id": str(auth_user.get("id", "admin_01")),
            "username": auth_user.get("username", ADMIN_USER),
            "role": auth_user.get("role", "ADMIN"),
            "department": auth_user.get("department", "Hospital Administration")
        }
    return {
        "user_id": str(st.session_state.get("user_id", "admin_01")),
        "username": str(st.session_state.get("username", ADMIN_USER)),
        "role": str(st.session_state.get("user_role", "ADMIN")),
        "department": "Hospital Administration"
    }


def render_floating_ai_assistant():
    """
    Renders the fixed bottom-right AI Assistant button and the expandable
    Hospital Insights summary panel. Accessible across administrator dashboard views.
    """
    # Initialize session state keys
    if "show_ai_summary_panel" not in st.session_state:
        st.session_state["show_ai_summary_panel"] = False
    if "ai_summary_data" not in st.session_state:
        st.session_state["ai_summary_data"] = None
    if "ai_qa_history" not in st.session_state:
        st.session_state["ai_qa_history"] = []
    if "ai_show_copy_modal" not in st.session_state:
        st.session_state["ai_show_copy_modal"] = False

    auth_context = _get_auth_context()
    service = DashboardSummarizerService()

    # Inject dedicated styling for the floating trigger and panel
    st.html("""
    <style>
    /* =========================================================================
       FLOATING TRIGGER BUTTON (Fixed Bottom-Right)
       ========================================================================= */
    div[class*="st-key-btn_floating_ai_trigger"] button,
    div[data-testid*="btn_floating_ai_trigger"] button {
        position: fixed !important;
        bottom: 24px !important;
        right: 24px !important;
        width: 58px !important;
        height: 58px !important;
        min-height: 58px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #1E60F2 0%, #1040B0 100%) !important;
        color: #FFFFFF !important;
        border: 2px solid rgba(255, 255, 255, 0.4) !important;
        box-shadow: 0 10px 25px -4px rgba(30, 96, 242, 0.5), 0 6px 12px -2px rgba(15, 23, 42, 0.25) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.45rem !important;
        cursor: pointer !important;
        z-index: 9990 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    div[class*="st-key-btn_floating_ai_trigger"] button:hover,
    div[data-testid*="btn_floating_ai_trigger"] button:hover {
        transform: scale(1.1) translateY(-3px) !important;
        box-shadow: 0 16px 32px -4px rgba(30, 96, 242, 0.65), 0 8px 16px -2px rgba(15, 23, 42, 0.35) !important;
        border-color: #FFFFFF !important;
    }
    div[class*="st-key-btn_floating_ai_trigger"] button:focus-visible {
        outline: 3px solid #60A5FA !important;
        outline-offset: 3px !important;
    }

    /* Pulsing status ring behind button */
    .ai-beacon-ping {
        position: fixed;
        bottom: 24px;
        right: 24px;
        width: 58px;
        height: 58px;
        border-radius: 50%;
        background: rgba(30, 96, 242, 0.35);
        animation: ai-pulse 2.5s infinite;
        z-index: 9989;
        pointer-events: none;
    }
    @keyframes ai-pulse {
        0% { transform: scale(0.95); opacity: 0.8; }
        70% { transform: scale(1.45); opacity: 0; }
        100% { transform: scale(1.45); opacity: 0; }
    }

    /* =========================================================================
       AI SUMMARY PANEL CONTAINER
       ========================================================================= */
    div[class*="st-key-panel_ai_summary_drawer"] {
        position: fixed !important;
        bottom: 92px !important;
        right: 24px !important;
        width: 430px !important;
        max-width: calc(100vw - 36px) !important;
        max-height: 78vh !important;
        background: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 16px !important;
        box-shadow: 0 24px 48px -12px rgba(15, 23, 42, 0.28), 0 12px 24px -8px rgba(15, 23, 42, 0.16) !important;
        z-index: 9991 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        padding: 0.95rem 1rem !important;
        display: flex !important;
        flex-direction: column !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Custom thin scrollbar */
    div[class*="st-key-panel_ai_summary_drawer"]::-webkit-scrollbar {
        width: 6px;
    }
    div[class*="st-key-panel_ai_summary_drawer"]::-webkit-scrollbar-track {
        background: #F1F5F9;
        border-radius: 8px;
    }
    div[class*="st-key-panel_ai_summary_drawer"]::-webkit-scrollbar-thumb {
        background: #94A3B8;
        border-radius: 8px;
    }
    div[class*="st-key-panel_ai_summary_drawer"]::-webkit-scrollbar-thumb:hover {
        background: #64748B;
    }

    /* Compact header buttons */
    div[class*="st-key-btn_ai_drawer_"] button {
        padding: 0.2rem 0.5rem !important;
        min-height: 28px !important;
        height: 28px !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }

    /* Suggestion pill buttons */
    div[class*="st-key-btn_qa_chip_"] button {
        padding: 0.2rem 0.45rem !important;
        min-height: 24px !important;
        height: 24px !important;
        font-size: 0.67rem !important;
        line-height: 1.1 !important;
        border-radius: 12px !important;
        background: #F1F5F9 !important;
        border: 1px solid #CBD5E1 !important;
        color: #334155 !important;
        white-space: nowrap !important;
    }
    div[class*="st-key-btn_qa_chip_"] button:hover {
        background: #E2E8F0 !important;
        border-color: #94A3B8 !important;
        color: #0F172A !important;
    }
    </style>
    """)

    # Render beacon animation
    if not st.session_state["show_ai_summary_panel"]:
        st.html('<div class="ai-beacon-ping"></div>')

    # Floating Action Button
    button_icon = "✕" if st.session_state["show_ai_summary_panel"] else "✨"
    button_help = "Close Hospital Insights" if st.session_state["show_ai_summary_panel"] else "AI Dashboard Summary — Click to analyze hospital resources"

    if st.button(button_icon, key="btn_floating_ai_trigger", help=button_help):
        st.session_state["show_ai_summary_panel"] = not st.session_state["show_ai_summary_panel"]
        st.rerun()

    # If drawer is closed, return immediately
    if not st.session_state["show_ai_summary_panel"]:
        return

    # =========================================================================
    # OPEN AI SUMMARY PANEL (Fixed bottom-right drawer)
    # =========================================================================
    with st.container(key="panel_ai_summary_drawer"):
        # Load or retrieve cached summary
        summary = st.session_state.get("ai_summary_data")
        if not summary:
            with st.spinner("Analyzing your hospital dashboard..."):
                summary = service.generate_summary(auth_context=auth_context, force_refresh=False)
                st.session_state["ai_summary_data"] = summary

        # ---------------------------------------------------------------------
        # HEADER BAR
        # ---------------------------------------------------------------------
        h_col1, h_col2 = st.columns([2.7, 1.3], gap="small")
        with h_col1:
            st.html("""
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="width: 28px; height: 28px; border-radius: 8px; background: linear-gradient(135deg, #1E60F2, #0B4AD4); display: flex; align-items: center; justify-content: center; color: white; font-size: 0.95rem; box-shadow: 0 2px 6px rgba(30,96,242,0.35);">
                    ✨
                </div>
                <div>
                    <div style="font-size: 0.92rem; font-weight: 800; color: #0F172A; line-height: 1.15;">Hospital Insights</div>
                    <div style="font-size: 0.69rem; color: #64748B;">Your hospital dashboard, explained.</div>
                </div>
            </div>
            """)

        with h_col2:
            st.html("<div style='display:flex; justify-content:flex-end; gap:0.25rem;'>")
            hdr_b1, hdr_b2 = st.columns(2)
            with hdr_b1:
                if st.button("🔄", key="btn_ai_drawer_refresh", help="Refresh dashboard summary with live data"):
                    with st.spinner("Refreshing metrics..."):
                        fresh_summary = service.generate_summary(auth_context=auth_context, force_refresh=True)
                        st.session_state["ai_summary_data"] = fresh_summary
                        st.rerun()
            with hdr_b2:
                if st.button("✕", key="btn_ai_drawer_close", help="Close summary panel"):
                    st.session_state["show_ai_summary_panel"] = False
                    st.rerun()
            st.html("</div>")

        # Sub-header: Freshness indicator & Provider mode pill
        data_as_of = summary.get("dataAsOf", "Just now")
        provider_name = summary.get("provider", "rule_based")
        is_fallback = summary.get("isFallback", True)

        badge_label = "📋 Rule-based summary" if is_fallback else f"✨ AI-Powered ({provider_name.title()})"
        badge_color = "#3B82F6" if is_fallback else "#10B981"
        badge_bg = "#EFF6FF" if is_fallback else "#ECFDF5"

        st.html(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.35rem 0.55rem; margin: 0.55rem 0 0.65rem 0;">
            <div style="font-size: 0.68rem; color: #64748B; display: flex; align-items: center; gap: 0.25rem;">
                <span>🕒</span> <span>Data as of: <b>{data_as_of}</b></span>
            </div>
            <div style="font-size: 0.66rem; font-weight: 700; color: {badge_color}; background: {badge_bg}; padding: 0.12rem 0.45rem; border-radius: 6px; border: 1px solid {badge_color}30;">
                {badge_label}
            </div>
        </div>
        """)

        # ---------------------------------------------------------------------
        # SECTION A: OVERALL STATUS
        # ---------------------------------------------------------------------
        overall = summary.get("overallStatus", {})
        lvl = overall.get("level", "attention")
        border_col = "#EF4444" if lvl == "critical" else ("#F59E0B" if lvl == "attention" else "#10B981")
        bg_col = "#FEF2F2" if lvl == "critical" else ("#FFFBEB" if lvl == "attention" else "#F0FDF4")
        lvl_icon = "🚨" if lvl == "critical" else ("⚠️" if lvl == "attention" else "✅")

        st.html(f"""
        <div style="background: {bg_col}; border-left: 4px solid {border_col}; border-radius: 8px; padding: 0.6rem 0.75rem; margin-bottom: 0.75rem;">
            <div style="font-size: 0.8rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 0.35rem; margin-bottom: 0.25rem;">
                <span>{lvl_icon}</span> <span>{overall.get('title', 'Overall Status')}</span>
            </div>
            <div style="font-size: 0.73rem; color: #334155; line-height: 1.42;">
                {overall.get('summary', '')}
            </div>
        </div>
        """)

        # ---------------------------------------------------------------------
        # SECTION B: KEY INSIGHTS (3-5 Bullet Points)
        # ---------------------------------------------------------------------
        st.html("""
        <div style="font-size: 0.78rem; font-weight: 800; color: #0F172A; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.35rem;">
            <span>📊</span> Key Insights
        </div>
        """)

        insights = summary.get("keyInsights", [])
        for item in insights:
            sev = item.get("severity", "low")
            sev_col = "#DC2626" if sev in ["critical", "high"] else ("#D97706" if sev == "medium" else "#2563EB")
            sev_bg = "#FEE2E2" if sev in ["critical", "high"] else ("#FEF3C7" if sev == "medium" else "#EFF6FF")

            st.html(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.55rem 0.7rem; margin-bottom: 0.45rem; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                    <span style="font-size: 0.76rem; font-weight: 700; color: #0F172A;">{item.get('title')}</span>
                    <span style="font-size: 0.74rem; font-weight: 800; color: {sev_col}; background: {sev_bg}; padding: 1px 6px; border-radius: 5px;">{item.get('value')}</span>
                </div>
                <div style="font-size: 0.71rem; color: #475569; line-height: 1.35; margin-bottom: 0.25rem;">
                    {item.get('explanation')}
                </div>
                <div style="font-size: 0.65rem; color: #94A3B8; display: flex; justify-content: space-between;">
                    <span><b>Metric:</b> {item.get('metric', '')}</span>
                    <span style="color: #64748B;">{item.get('trend', '')}</span>
                </div>
            </div>
            """)

        # ---------------------------------------------------------------------
        # SECTION C: ATTENTION REQUIRED
        # ---------------------------------------------------------------------
        st.html("""
        <div style="font-size: 0.78rem; font-weight: 800; color: #0F172A; text-transform: uppercase; letter-spacing: 0.5px; margin: 0.75rem 0 0.4rem 0; display: flex; align-items: center; gap: 0.35rem;">
            <span>⚠️</span> Attention Required
        </div>
        """)

        attention = summary.get("attentionItems", [])
        for att in attention:
            sev_str = att.get("severity", "Medium")
            s_color = "#DC2626" if sev_str in ["Critical", "High"] else ("#D97706" if sev_str == "Medium" else "#2563EB")
            s_bg = "#FEE2E2" if sev_str in ["Critical", "High"] else ("#FEF3C7" if sev_str == "Medium" else "#EFF6FF")
            s_icon = "🔴" if sev_str in ["Critical", "High"] else ("🟠" if sev_str == "Medium" else "🟡")

            st.html(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid {s_color}; border-radius: 8px; padding: 0.55rem 0.7rem; margin-bottom: 0.45rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;">
                    <div style="font-size: 0.76rem; font-weight: 700; color: #0F172A;">
                        <span>{s_icon}</span> {att.get('problem')}
                    </div>
                    <span style="font-size: 0.65rem; font-weight: 800; color: {s_color}; background: {s_bg}; padding: 1px 5px; border-radius: 4px;">{sev_str}</span>
                </div>
                <div style="font-size: 0.69rem; color: #64748B; margin-bottom: 0.25rem;">
                    <b>Unit:</b> {att.get('department')} • <b>Telemetry:</b> {att.get('metric')}
                </div>
                <div style="font-size: 0.71rem; color: #334155; line-height: 1.35; margin-bottom: 0.3rem;">
                    <b>Impact:</b> {att.get('impact')}
                </div>
                <div style="font-size: 0.70rem; color: #1D4ED8; background: #EFF6FF; border-radius: 5px; padding: 0.25rem 0.45rem; border: 1px solid #DBEAFE;">
                    <b>Action:</b> {att.get('suggestedAction')}
                </div>
            </div>
            """)

        # ---------------------------------------------------------------------
        # SECTION D: RECOMMENDED ACTIONS
        # ---------------------------------------------------------------------
        st.html("""
        <div style="font-size: 0.78rem; font-weight: 800; color: #0F172A; text-transform: uppercase; letter-spacing: 0.5px; margin: 0.75rem 0 0.4rem 0; display: flex; align-items: center; gap: 0.35rem;">
            <span>🛡️</span> Recommended Administrative Actions
        </div>
        """)

        actions = summary.get("recommendedActions", [])
        for act in actions:
            pri = act.get("priority", "High")
            p_badge = "#10B981" if pri == "High" else "#3B82F6"
            st.html(f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.55rem 0.7rem; margin-bottom: 0.45rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;">
                    <div style="font-size: 0.75rem; font-weight: 700; color: #0F172A;">{act.get('title')}</div>
                    <span style="font-size: 0.64rem; font-weight: 700; color: #FFFFFF; background: {p_badge}; padding: 1px 5px; border-radius: 4px;">{pri} Priority</span>
                </div>
                <div style="font-size: 0.70rem; color: #475569; margin-bottom: 0.2rem;">
                    <b>Evidence:</b> {act.get('evidence')}
                </div>
                <div style="font-size: 0.70rem; color: #047857; background: #ECFDF5; padding: 0.2rem 0.45rem; border-radius: 4px; border: 1px solid #D1FAE5;">
                    <b>Expected Benefit:</b> {act.get('operationalBenefit')}
                </div>
            </div>
            """)

        # ---------------------------------------------------------------------
        # SECTION E: TRENDS & FORECASTS
        # ---------------------------------------------------------------------
        trends = summary.get("trendsAndForecasts", {})
        st.html(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.55rem 0.7rem; margin: 0.65rem 0;">
            <div style="font-size: 0.75rem; font-weight: 800; color: #0F172A; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.3rem;">
                <span>📈</span> Trends & Demand Horizon
            </div>
            <div style="font-size: 0.71rem; color: #334155; line-height: 1.35; margin-bottom: 0.3rem;">
                {trends.get('demandTrend', '')}
            </div>
            <div style="font-size: 0.67rem; color: #64748B;">
                <b>Peak Window:</b> {trends.get('peakWindow', '')}<br/>
                <b>Capacity vs Demand:</b> {trends.get('capacityVsDemand', '')}<br/>
                <b>Telemetry Model:</b> {trends.get('forecastModel', '')}
            </div>
        </div>
        """)

        # ---------------------------------------------------------------------
        # SECTION F: POSITIVE OBSERVATIONS
        # ---------------------------------------------------------------------
        positives = summary.get("positiveObservations", [])
        if positives:
            pos_items_html = "".join([f"<li style='margin-bottom: 0.25rem;'>{p}</li>" for p in positives])
            st.html(f"""
            <div style="background: #F0FDF4; border: 1px solid #DCFCE7; border-radius: 8px; padding: 0.55rem 0.75rem; margin-bottom: 0.65rem;">
                <div style="font-size: 0.75rem; font-weight: 800; color: #166534; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.3rem;">
                    <span>✅</span> Positive Operational Indicators
                </div>
                <ul style="font-size: 0.70rem; color: #15803D; margin: 0; padding-left: 1.1rem; line-height: 1.35;">
                    {pos_items_html}
                </ul>
            </div>
            """)

        # ---------------------------------------------------------------------
        # SECTION G: DATA QUALITY & FRESHNESS
        # ---------------------------------------------------------------------
        dq = summary.get("dataFreshness", {})
        st.html(f"""
        <div style="font-size: 0.66rem; color: #94A3B8; background: #F8FAFC; border-radius: 6px; padding: 0.35rem 0.55rem; margin-bottom: 0.75rem; border: 1px solid #E2E8F0;">
            <b>Data Provenance:</b> {dq.get('censusTelemetry', '')} • {dq.get('inventoryTelemetry', '')}<br/>
            <i>No clinical diagnosis or autonomous patient-care actions performed.</i>
        </div>
        """)

        # ---------------------------------------------------------------------
        # COPY SUMMARY ACTION
        # ---------------------------------------------------------------------
        raw_text_summary = _build_plain_text_summary(summary)
        c_col1, c_col2 = st.columns([1.8, 1.2])
        with c_col1:
            if st.button("📋 Copy Clean Text Summary", key="btn_copy_ai_summary", width="stretch"):
                st.session_state["ai_show_copy_modal"] = not st.session_state.get("ai_show_copy_modal", False)
                st.rerun()

        if st.session_state.get("ai_show_copy_modal"):
            st.code(raw_text_summary, language="markdown")

        st.html("<hr style='margin: 0.65rem 0;'/>")

        # ---------------------------------------------------------------------
        # SECTION 10: CONTEXTUAL FOLLOW-UP Q&A (MULTI-QUERY & HISTORY CLEAR)
        # ---------------------------------------------------------------------
        qa_head_col, qa_clear_col = st.columns([2.8, 1.2])
        with qa_head_col:
            st.html("""
            <div style="font-size: 0.78rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 0.35rem; margin-top: 0.15rem;">
                <span>💬</span> Ask About Hospital Resources
            </div>
            """)
        with qa_clear_col:
            if st.session_state.get("ai_qa_history"):
                if st.button("🧹 Clear", key="btn_clear_ai_qa_top", width="stretch", help="Clear all query history"):
                    st.session_state["ai_qa_history"] = []
                    st.rerun()

        # Quick Suggestion Chips (immediate execution on click)
        clicked_chip_query = None
        chip1, chip2 = st.columns(2)
        with chip1:
            if st.button("🔥 Most Urgent?", key="btn_qa_chip_1", width="stretch"):
                clicked_chip_query = "Which department needs the most attention?"
            if st.button("🫀 ICU Utilization?", key="btn_qa_chip_2", width="stretch"):
                clicked_chip_query = "Why is ICU utilization high?"
            if st.button("🩸 Blood Backup?", key="btn_qa_chip_5", width="stretch"):
                clicked_chip_query = "What is the status of the blood bank and available blood reserves?"
        with chip2:
            if st.button("📈 Demand vs Capacity?", key="btn_qa_chip_3", width="stretch"):
                clicked_chip_query = "How does predicted demand compare with capacity?"
            if st.button("📦 Low Supplies?", key="btn_qa_chip_4", width="stretch"):
                clicked_chip_query = "Which resources or supplies are below required levels?"
            if st.button("👥 Staffing Status?", key="btn_qa_chip_6", width="stretch"):
                clicked_chip_query = "What is the current nurse and doctor availability?"

        # Continuous Multi-Query Input with Clear-on-Submit form
        with st.form("form_ai_summary_qa", clear_on_submit=True):
            user_q = st.text_input(
                "Follow-up Question",
                placeholder="Ask about hospital resources (Press Enter or Send)...",
                label_visibility="collapsed",
                key="ai_qa_text_input_box"
            )
            q_btn_col1, q_btn_col2 = st.columns([3.2, 1.0])
            with q_btn_col1:
                submit_qa = st.form_submit_button("Send Query ➔", width="stretch", type="primary")
            with q_btn_col2:
                reset_submit = st.form_submit_button("Clear", width="stretch")

        if reset_submit:
            st.session_state["ai_qa_history"] = []
            st.rerun()

        # Execute query if chip clicked OR form submitted
        target_query = None
        if clicked_chip_query:
            target_query = clicked_chip_query
        elif submit_qa and user_q and user_q.strip():
            target_query = user_q.strip()

        if target_query:
            with st.spinner("Analyzing verified metrics..."):
                qa_res = handle_dashboard_qa_request(
                    auth_context=auth_context,
                    query=target_query,
                    current_summary=summary
                )
                ts_str = get_ist_now().strftime("%I:%M %p")
                if "ai_qa_history" not in st.session_state:
                    st.session_state["ai_qa_history"] = []
                st.session_state["ai_qa_history"].insert(0, {
                    "id": f"qa_{int(time.time() * 1000)}",
                    "question": target_query,
                    "answer": qa_res.get("answer", "No answer found."),
                    "timestamp": ts_str
                })
                # Retain conversation history up to 25 items
                if len(st.session_state["ai_qa_history"]) > 25:
                    st.session_state["ai_qa_history"].pop()
                st.rerun()

        # Render Full Interactive Q&A History with Individual Deletion
        qa_history = st.session_state.get("ai_qa_history", [])
        if qa_history:
            st.html(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.65rem 0 0.35rem 0; border-top: 1px solid #E2E8F0; padding-top: 0.45rem;">
                <span style="font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">Query History ({len(qa_history)})</span>
                <span style="font-size: 0.65rem; color: #94A3B8;">Click 🗑️ to remove an individual query</span>
            </div>
            """)

            delete_target_index = None
            for idx, item in enumerate(qa_history):
                # Question header pill
                st.html(f"""
                <div style="background: #F1F5F9; border-left: 3px solid #3B82F6; border-radius: 6px; padding: 0.4rem 0.55rem; margin-top: 0.35rem; margin-bottom: 0.25rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.74rem; font-weight: 700; color: #0F172A;">Q: {item.get('question')}</span>
                        <span style="font-size: 0.64rem; color: #64748B;">{item.get('timestamp', '')}</span>
                    </div>
                </div>
                """)

                q_body_col, q_del_col = st.columns([8.8, 1.2])
                with q_body_col:
                    st.markdown(item.get("answer", ""))
                with q_del_col:
                    if st.button("🗑️", key=f"btn_del_qa_{item.get('id', idx)}", help="Delete this query from history"):
                        delete_target_index = idx

                st.html("<hr style='margin: 0.3rem 0 0.45rem 0; border: none; border-top: 1px dashed #E2E8F0;'/>")

            if delete_target_index is not None:
                st.session_state["ai_qa_history"].pop(delete_target_index)
                st.rerun()


def _build_plain_text_summary(summary: Dict[str, Any]) -> str:
    """Formats the summary as clean Markdown text suitable for clipboard copy or email."""
    ov = summary.get("overallStatus", {})
    insights = summary.get("keyInsights", [])
    attention = summary.get("attentionItems", [])
    actions = summary.get("recommendedActions", [])

    lines = [
        f"# VitalOptima Hospital Dashboard Summary",
        f"**Data As Of:** {summary.get('dataAsOf', 'N/A')} | **Mode:** {summary.get('provider', 'rule_based').title()}",
        "",
        f"## Overall Status: {ov.get('title', '')}",
        f"{ov.get('summary', '')}",
        "",
        "## Key Insights:",
    ]
    for i in insights:
        lines.append(f"- **{i.get('title')}:** {i.get('value')} — {i.get('explanation')}")

    lines.append("")
    lines.append("## Attention Required:")
    for a in attention:
        lines.append(f"- [{a.get('severity', 'Medium')}] **{a.get('problem')}** ({a.get('department')}): {a.get('impact')} -> *Action:* {a.get('suggestedAction')}")

    lines.append("")
    lines.append("## Recommended Actions:")
    for r in actions:
        lines.append(f"1. **{r.get('title')}** ({r.get('priority', 'High')} Priority): {r.get('evidence')} — Expected gain: {r.get('operationalBenefit')}")

    return "\n".join(lines)
