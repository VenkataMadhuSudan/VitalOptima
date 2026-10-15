"""
VitalOptima Historical Data & Natural Language Query Assistant
Allows hospital administrators, clinical directors, and operations staff to query, search,
and inspect hospital records using plain English language without writing any SQL.
"""
import os
import time
import json
from datetime import datetime
import streamlit as st
import pandas as pd
from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp
from ui.components import render_top_nav, render_footer
from db.postgres import (
    test_connection, get_table_summary, fetch_table_df,
    run_custom_query, sync_csvs_to_postgres
)
from db.nlp_query import process_natural_language_query, SAMPLE_PROMPT_CHIPS

def show_postgres_explorer():
    """Alias for backwards compatibility."""
    show_historical_data_view()

def show_historical_data_view():
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)

    # Initialize chat history in session state
    if "nlp_chat_history" not in st.session_state:
        st.session_state["nlp_chat_history"] = []

    # Header with executive subtitle
    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
            <div>
                <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.25rem; font-size: 1.6rem;">
                    🗄️ Historical Data & Natural Language Search Assistant
                </h2>
                <p style="color: #64748B; margin-bottom: 0; font-size: 0.95rem;">
                    Search hospital operations, 365-day census records, clinical shifts, and supply telemetry in <b>plain English</b> — no technical database knowledge required.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Connection and Telemetry Status Bar
    is_connected, conn_info = test_connection()
    table_summary = get_table_summary() if is_connected else {}
    total_tables = len(table_summary)
    total_records = sum(t["row_count"] for t in table_summary.values()) if table_summary else 0

    # System Status Pill
    if is_connected:
        st.markdown(f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.75rem 1.25rem; margin-bottom: 1.25rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
            <div style="display: flex; align-items: center; gap: 0.6rem;">
                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #10B981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);"></span>
                <span style="font-weight: 700; color: #0F172A; font-size: 0.88rem;">Cloud Hospital Archive Connected</span>
                <span style="background: #E2E8F0; color: #475569; font-size: 0.75rem; padding: 2px 8px; border-radius: 6px; font-weight: 600;">{total_tables} Operational Tables</span>
                <span style="background: #EFF6FF; color: #1E60F2; font-size: 0.75rem; padding: 2px 8px; border-radius: 6px; font-weight: 600;">{total_records:,} Indexed Records</span>
            </div>
            <div style="font-size: 0.8rem; color: #64748B;">
                Database Engine: <b>PostgreSQL 18.6 (Cloud AWS)</b> &nbsp;|&nbsp; Latency: <b>{conn_info.get('latency_ms', 0)} ms</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Main Navigation Tabs: 1. Natural Language Search | 2. Table Catalog
    tab_nlp, tab_catalog = st.tabs([
        "💬 Ask in English (AI Search Assistant)",
        "📋 Historical Data Catalog & Tables"
    ])

    # =========================================================================
    # TAB 1: NATURAL LANGUAGE QUERY ASSISTANT (FOR ADMINISTRATORS)
    # =========================================================================
    with tab_nlp:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.5rem; margin-top: 0.5rem; margin-bottom: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <h4 style="color: #0F172A; font-weight: 800; margin-bottom: 0.25rem;">
                🤖 Ask Any Question About Hospital Records
            </h4>
            <p style="color: #64748B; font-size: 0.88rem; margin-bottom: 1rem;">
                Type your inquiry in plain English below, or click any recommended question chip. The assistant will parse your question, query the hospital database, and summarize the records.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # AI Engine Settings Expander (xAI Grok / Google Gemini / Local Engine)
        active_llm_key = st.session_state.get("gemini_api_key") or os.environ.get("XAI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
        has_llm = bool(active_llm_key and str(active_llm_key).strip())
        is_grok = bool(os.environ.get("XAI_API_KEY") or (has_llm and str(active_llm_key).startswith("xai-")))

        if is_grok:
            status_badge_html = '<span style="color: #10B981; font-weight: 700;">🟢 xAI Grok-2 Active (Cloud LLM)</span>'
        elif has_llm:
            status_badge_html = '<span style="color: #10B981; font-weight: 700;">🟢 Google Gemini AI Active</span>'
        else:
            status_badge_html = '<span style="color: #64748B; font-weight: 700;">⚪ Local High-Precision NL2SQL Engine (Zero-Key Mode)</span>'

        with st.expander("⚙️ AI Assistant Settings & Cloud LLM Config", expanded=False):
            st.markdown(f"""
            <div style="font-size: 0.88rem; color: #334155; margin-bottom: 0.6rem;">
                <b>Current NL2SQL Engine:</b> {status_badge_html}
            </div>
            """, unsafe_allow_html=True)

            k_col1, k_col2 = st.columns([4, 1.2])
            with k_col1:
                entered_key = st.text_input(
                    "xAI Grok or Gemini API Key:",
                    value=active_llm_key if has_llm else "",
                    type="password",
                    placeholder="xai-... or AIzaSy...",
                    key="pe_gemini_key_input",
                    help="Supports xAI Grok (XAI_API_KEY) and Google Gemini (GEMINI_API_KEY). Keys entered here are shared across the system."
                )
            with k_col2:
                if st.button("💾 Save Key", width="stretch", key="pe_save_gemini_key_btn"):
                    st.session_state["gemini_api_key"] = entered_key.strip()
                    st.success("API Key saved!")
                    st.rerun()
            st.markdown("<div style='font-size: 0.78rem; color: #64748B; margin-top: 0.25rem;'>Add <code>XAI_API_KEY</code> to <code>.env</code> to activate xAI Grok. Zero-key mode uses our local database NL2SQL engine.</div>", unsafe_allow_html=True)

        # Quick Question Chips (Clickable)
        st.markdown("<p style='font-size: 0.82rem; font-weight: 700; color: #475569; margin-bottom: 0.4rem;'>💡 Quick Example Questions:</p>", unsafe_allow_html=True)
        
        chip_cols = st.columns(4)
        clicked_query = None

        chips = [
            ("📈 Monday Patient Volume", "How many patients arrived on Mondays?"),
            ("🚨 Consumable Stockouts", "Which medical supplies are running low or out of stock?"),
            ("🛏️ Department Occupancies", "Which hospital departments currently have highest occupancy?"),
            ("👥 Night Shift Deficits", "Show staff shortages and nurse deficits for night shifts"),
            ("📅 Length of Stay by Day", "What is the average length of stay by day of week?"),
            ("🩺 Total Surgeries Done", "What is the total number of surgeries scheduled?"),
            ("📦 Lead Time > 5 Days", "Which consumables have a supplier lead time over 5 days?"),
            ("🏥 Pediatrics Capacity", "Show general bed and ICU bed capacity for Pediatrics"),
            ("⚠️ Active System Alerts", "List all active high severity hospital alerts"),
            ("⚖️ Decisions Audit Trail", "What administrative decisions were recently accepted or modified?"),
            ("🎛️ Saved Simulations", "Show saved what-if disaster simulation scenarios"),
            ("🔥 Surge Days (>250)", "Which days had over 250 arrivals?")
        ]

        for i, (label, text) in enumerate(chips):
            col = chip_cols[i % 4]
            with col:
                if st.button(label, key=f"chip_btn_{i}", width="stretch"):
                    clicked_query = text

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

        # Chat Input Bar
        if "last_nlp_query" not in st.session_state:
            st.session_state["last_nlp_query"] = ""

        input_col, submit_col = st.columns([5, 1])
        with input_col:
            user_question = st.text_input(
                "Enter your question in natural English:",
                value="",
                placeholder="e.g., Which departments have over 80% occupancy? or Show days with highest emergency arrivals",
                label_visibility="collapsed",
                key="nlp_user_input_box"
            )
        with submit_col:
            search_clicked = st.button("🔍 Search Records", width="stretch", type="primary")

        # Determine effective query to execute
        query_to_run = None
        if clicked_query:
            query_to_run = clicked_query
        elif search_clicked and user_question.strip():
            query_to_run = user_question.strip()
        elif user_question.strip() and user_question.strip() != st.session_state["last_nlp_query"]:
            query_to_run = user_question.strip()

        if query_to_run:
            st.session_state["last_nlp_query"] = query_to_run
            engine_name = "Google Gemini AI" if has_gemini else "Hospital NL2SQL Engine"
            with st.spinner(f"Analyzing question with {engine_name} and querying hospital records..."):
                start_time = time.time()
                result = process_natural_language_query(query_to_run, api_key=active_gemini_key)
                exec_ms = round((time.time() - start_time) * 1000, 1)

                # Append to session history (keep last 5)
                st.session_state["nlp_chat_history"].insert(0, {
                    "question": query_to_run,
                    "result": result,
                    "time": time.strftime("%H:%M:%S"),
                    "exec_ms": exec_ms
                })
                if len(st.session_state["nlp_chat_history"]) > 6:
                    st.session_state["nlp_chat_history"].pop()

        # Display Chat History / Latest Result
        if st.session_state["nlp_chat_history"]:
            for idx, entry in enumerate(st.session_state["nlp_chat_history"]):
                q = entry["question"]
                res = entry["result"]
                q_time = entry["time"]
                exec_ms = entry["exec_ms"]

                engine_badge = res.get("engine", "VitalOptima NL2SQL Engine")

                # Question Bubble
                st.markdown(f"""
                <div style="background: #EFF6FF; border-left: 4px solid #1E60F2; padding: 0.85rem 1.15rem; border-radius: 8px; margin-top: 1rem; margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 0.6rem;">
                            <span style="font-weight: 700; color: #1E40AF; font-size: 0.95rem;">👤 Administrator Question:</span>
                            <span style="background: #E0E7FF; color: #3730A3; font-size: 0.72rem; font-weight: 700; padding: 2px 7px; border-radius: 4px;">{engine_badge}</span>
                        </div>
                        <span style="font-size: 0.75rem; color: #64748B;">{q_time} ({exec_ms} ms)</span>
                    </div>
                    <div style="font-size: 1.05rem; font-weight: 600; color: #0F172A; margin-top: 0.25rem;">
                        "{q}"
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if res["success"]:
                    # Answer Card
                    st.markdown(f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1.1rem 1.25rem; margin-bottom: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <span style="font-size: 1.1rem;">🤖</span>
                            <span style="font-weight: 700; color: #0F172A; font-size: 0.98rem;">VitalOptima Assistant Answer:</span>
                        </div>
                        <div style="color: #334155; font-size: 0.92rem; line-height: 1.5;">
                            {res['answer_summary']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Insights if available
                    if res.get("insights"):
                        for ins in res["insights"]:
                            st.info(f"💡 **Key Insight:** {ins}")

                    # Result Dataframe
                    df_out = res["df"]
                    if not df_out.empty:
                        st.dataframe(df_out, width="stretch", hide_index=True)
                        
                        # Download CSV
                        csv_data = df_out.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 Download Search Results (CSV)",
                            data=csv_data,
                            file_name=f"vitaloptima_search_{idx}.csv",
                            mime="text/csv",
                            key=f"dl_csv_{idx}"
                        )

                    # Collapsible Technical SQL Details
                    with st.expander("🔍 Show Generated SQL Query (For Technical Auditing)", expanded=False):
                        st.code(res["sql_query"], language="sql")
                        st.caption(f"Executed against PostgreSQL table: `public.{res['table_name']}`")

                else:
                    st.error(f"⚠️ {res.get('error', 'Could not process query.')}")

                st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px dashed #CBD5E1;' />", unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: HISTORICAL DATA CATALOG (TABLE BROWSER & CSV SYNC)
    # =========================================================================
    with tab_catalog:
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

        table_options = [
            ("department_resources", "🏥 Department Capacity & Wards (department_resources)"),
            ("hospital_census_daily", "📅 365 Days Daily Hospital Census (hospital_census_daily)"),
            ("staffing_roster", "👥 Clinical Staffing Rosters & Shifts (staffing_roster)"),
            ("inventory_supplies", "📦 Consumables & Stock Telemetry (inventory_supplies)"),
            ("demand_forecast_hourly", "📈 24-Hour Patient Demand Forecast (demand_forecast_hourly)"),
            ("decision_log", "⚖️ Administrative Decisions Audit Log (decision_log)"),
            ("system_alerts", "🚨 Active Safety Alerts & Alarms (system_alerts)"),
            ("scenarios", "🎛️ Saved Disaster Stress Simulations (scenarios)"),
            ("recent_activity", "⏱️ Real-time Hospital Event Log (recent_activity)")
        ]

        t_col1, t_col2, t_col3 = st.columns([2.5, 1, 1.2])
        with t_col1:
            selected_table_tuple = st.selectbox(
                "Select Historical Table to Inspect:",
                options=table_options,
                format_func=lambda x: x[1]
            )
            selected_table = selected_table_tuple[0]

        with t_col2:
            row_limit = st.selectbox("Max Rows:", [50, 100, 250, 500, 1000], index=1)

        with t_col3:
            st.markdown("<div style='height: 1.8rem;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Sync CSVs to Cloud DB", width="stretch"):
                with st.spinner("Re-syncing all records to PostgreSQL..."):
                    try:
                        res = sync_csvs_to_postgres()
                        st.success(f"Synced {sum(res.values())} records across {len(res)} tables!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sync error: {e}")

        # Fetch and show selected table
        with st.spinner(f"Loading '{selected_table}' records..."):
            df = fetch_table_df(selected_table, limit=row_limit)

        if not df.empty:
            total_in_tbl = table_summary.get(selected_table, {}).get("row_count", len(df))
            st.markdown(f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 0.75rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: #475569;">
                <div>
                    <b>Table:</b> <code>{selected_table}</code> &nbsp;|&nbsp;
                    <b>Columns:</b> {len(df.columns)} &nbsp;|&nbsp;
                    <b>Loaded:</b> {len(df)} of {total_in_tbl} records
                </div>
                <div>
                    <span style="color: #10B981; font-weight: 600;">● Live Cloud Records</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Table search
            table_filter = st.text_input(f"Filter records in {selected_table}:", "", key=f"filter_{selected_table}")
            if table_filter:
                mask = df.astype(str).apply(lambda row: row.str.contains(table_filter, case=False).any(), axis=1)
                display_df = df[mask]
            else:
                display_df = df

            st.dataframe(display_df, width="stretch", hide_index=True, height=380)

            # Export button
            csv_table = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"📥 Download {selected_table}.csv",
                data=csv_table,
                file_name=f"{selected_table}_export.csv",
                mime="text/csv",
                key=f"dl_tbl_{selected_table}"
            )
        else:
            st.warning(f"No records found in table '{selected_table}'. Click 'Sync CSVs to Cloud DB' above to ingest records.")

    render_footer()
