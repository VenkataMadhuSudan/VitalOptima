"""
VitalOptima PostgreSQL Explorer & Natural Language Query View
Domain-specific Natural Language to SQL Assistant, dual-engine status, and raw table browser.
"""
import streamlit as st
import pandas as pd

from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp, DATA_DIR
from ui.components import render_top_nav, render_footer, render_metric_card
from db.nlp_query import process_natural_language_query, SAMPLE_PROMPT_CHIPS
from db.postgres import test_connection, get_table_summary, fetch_table_df

def show_historical_data_view():
    """Historical records, Natural Language Query, and database table explorer."""
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)

    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.2rem; letter-spacing: -0.02em;">
            🗄️ Historical Clinical Records & NLQ Assistant
        </h2>
        <p style="color: #64748B; font-size: 0.92rem; margin: 0;">
            Query clinical data in plain English via the domain-specific NL2SQL engine, or inspect raw records across the dual database architecture.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Connection Health Bar
    conn_info = test_connection()
    is_connected = conn_info.get("connected", False)

    h1, h2, h3, h4 = st.columns(4)
    with h1:
        render_metric_card("Primary Database", "Neon PostgreSQL", "Cloud Enterprise Instance", card_type="default", icon="☁️")
    with h2:
        render_metric_card("PostgreSQL Status", "ONLINE" if is_connected else "DISCONNECTED", "Live query pool" if is_connected else "Using SQLite fallback", card_type="success" if is_connected else "warning", icon="🔌")
    with h3:
        render_metric_card("Local Durability", "Active (SQLite)", "Automatic local sync", card_type="default", icon="💾")
    with h4:
        render_metric_card("NLQ Query Engine", "Ready", "Trained on 12 schema routes", card_type="success", icon="🧠")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    tab_nlq, tab_tables = st.tabs(["💬 Ask VitalOptima (Natural Language SQL)", "📊 Raw Clinical Table Explorer"])

    # --- TAB 1: NATURAL LANGUAGE QUERY ---
    with tab_nlq:
        st.markdown("#### 💬 Ask Hospital Operations Questions in Plain English")
        st.write("The NL2SQL engine extracts hospital entities, departments, and shifts to execute analytical queries with clinical insights.")

        # Quick Prompt Chips
        st.markdown("**Sample Inquiries (Click to pre-fill):**")
        chip_cols = st.columns(3)
        for i, chip in enumerate(SAMPLE_PROMPT_CHIPS[:6]):
            with chip_cols[i % 3]:
                if st.button(chip, key=f"chip_{i}"):
                    st.session_state["nlq_prompt"] = chip

        # Input form
        default_val = st.session_state.get("nlq_prompt", "")
        with st.form("nlq_search_form"):
            user_input = st.text_input(
                "Enter your question",
                value=default_val,
                placeholder="e.g. How many patients arrived on Mondays? or Which medical supplies are running low?"
            )
            submit_nlq = st.form_submit_button("🔍 Execute Question", type="primary")

        if submit_nlq and user_input.strip():
            with st.spinner("Analyzing clinical question and querying database..."):
                res = process_natural_language_query(user_input.strip())

            if res.get("success"):
                st.success(f"**Insight:** {res.get('answer_summary')}")
                
                # Show SQL generated
                with st.expander("🛠️ Generated SQL Query", expanded=False):
                    st.code(res.get("sql_query"), language="sql")

                # Show returned data
                df_res = res.get("df")
                if df_res is not None and not df_res.empty:
                    st.markdown("##### 📋 Resulting Dataset")
                    st.dataframe(df_res, width="stretch", hide_index=True)

                # Show insights
                insights = res.get("insights", [])
                if insights:
                    st.markdown("##### 💡 Executive Clinical Takeaways")
                    for ins in insights:
                        st.markdown(f"- {ins}")
            else:
                # If error occurred, provide helpful feedback
                st.warning(f"**Query Response:** {res.get('answer_summary', 'Could not parse query.')}")
                if res.get("sql_query"):
                    with st.expander("Attempted SQL"):
                        st.code(res.get("sql_query"), language="sql")

    # --- TAB 2: RAW TABLE BROWSER ---
    with tab_tables:
        st.markdown("#### 📊 Raw Hospital Database Table Browser")
        
        tables = [
            "hospital_census_daily",
            "department_resources",
            "staffing_roster",
            "inventory_supplies",
            "decision_log",
            "recent_activity",
            "scenarios"
        ]

        t_sel = st.selectbox("Select Database Table to Inspect", tables)
        limit = st.slider("Max Rows to Fetch", 10, 500, 50, 10)

        df_table = fetch_table_df(t_sel, limit=limit)
        
        # Fallback to CSV if table is empty in PostgreSQL
        if df_table.empty:
            name_map = {
                "hospital_census_daily": "hospital_daily_data.csv",
                "department_resources": "hospital_resources.csv",
                "staffing_roster": "staff_availability.csv",
                "inventory_supplies": "medical_inventory.csv"
            }
            if t_sel in name_map:
                csv_file = DATA_DIR / name_map[t_sel]
                if csv_file.exists():
                    df_table = pd.read_csv(csv_file).head(limit)

        if not df_table.empty:
            st.markdown(f"**Showing {len(df_table)} rows from `{t_sel}`:**")
            st.dataframe(df_table, width="stretch", hide_index=True)
            
            csv_down = df_table.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download {t_sel} (CSV)",
                data=csv_down,
                file_name=f"{t_sel}_export.csv",
                mime="text/csv"
            )
        else:
            st.info(f"No records available in table `{t_sel}`.")

    render_footer()
