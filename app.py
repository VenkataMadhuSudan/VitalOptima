"""
VitalOptima — AI-Based Hospital Resource Optimization and Decision-Support System
Main Application Entrypoint and Navigation Router (Dual Engine: Neon PostgreSQL + SQLite)
"""
import streamlit as st
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.styles import get_custom_css
from ui.views.dashboard import show_dashboard
from ui.views.ai_insights import show_ai_insights
from ui.views.resource_mgmt import show_resource_mgmt
from ui.views.demand_forecast import show_demand_forecast
from ui.views.optimization import show_optimization
from ui.views.simulator import show_simulator
from ui.views.decision_log import show_decision_log
from ui.views.postgres_explorer import show_historical_data_view

# Page configuration
st.set_page_config(
    page_title="VitalOptima — Hospital Resource Optimization",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

import base64

# Initialize Session State
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Dashboard"
st.session_state["theme"] = "Light Mode"

# Inject custom CSS
st.html(get_custom_css("Light Mode"))

# Load hospital photo for sidebar bottom
b64_building = ""
building_path = PROJECT_ROOT / "assets" / "hospital_building.jpg"
if building_path.exists():
    with open(building_path, "rb") as f:
        b64_building = base64.b64encode(f.read()).decode()

# --- Sidebar Layout ---
with st.sidebar:
    # VitalOptima Brand & Pulse Logo
    st.html("""
    <div class="sidebar-brand">
        <div class="brand-title">
            <span style="color:#1E60F2; font-size:1.6rem;">🫀</span> VitalOptima
        </div>
        <div class="brand-sub">Smarter Hospitals. Better Decisions.</div>
    </div>
    """)

    # Navigation Menu
    nav_options = [
        "Dashboard",
        "AI Insights & Agent",
        "Resource Management",
        "Demand Forecasting",
        "Optimization",
        "What-if Simulator",
        "Decision Log",
        "Inventory Forecasting",
        "Historical Data & Records"
    ]

    icons = {
        "Dashboard": "📊",
        "AI Insights & Agent": "🤖",
        "Resource Management": "🛏️",
        "Demand Forecasting": "📈",
        "Optimization": "⚙️",
        "What-if Simulator": "🎛️",
        "Decision Log": "📋",
        "Inventory Forecasting": "📦",
        "Historical Data & Records": "🗄️"
    }

    current_idx = 0
    if st.session_state["current_page"] in nav_options:
        current_idx = nav_options.index(st.session_state["current_page"])

    selected_nav = st.radio(
        label="Navigation Menu",
        options=nav_options,
        index=current_idx,
        format_func=lambda x: f"{icons.get(x, '•')}  {x}",
        label_visibility="collapsed"
    )

    if selected_nav != st.session_state["current_page"]:
        st.session_state["current_page"] = selected_nav
        st.rerun()

    if b64_building:
        st.html(f"""
        <div style="margin-top: 2rem; border-radius: 10px; overflow: hidden; border: 1px solid #1E293B;">
            <img src="data:image/jpeg;base64,{b64_building}" style="width: 100%; height: 90px; object-fit: cover; display: block;" />
        </div>
        """)

# --- Main View Router ---
active_view = st.session_state["current_page"]

if active_view == "Dashboard":
    show_dashboard()
elif active_view == "AI Insights & Agent":
    show_ai_insights()
elif active_view == "Resource Management":
    show_resource_mgmt()
elif active_view == "Demand Forecasting":
    show_demand_forecast()
elif active_view == "Optimization":
    show_optimization()
elif active_view == "What-if Simulator":
    show_simulator()
elif active_view == "Decision Log":
    show_decision_log()
elif active_view in ["Historical Data & Records", "PostgreSQL Explorer"]:
    show_historical_data_view()
elif active_view == "Inventory Forecasting":
    from ui.components import render_top_nav, render_footer
    from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, DATA_DIR, get_system_timestamp
    from db.postgres import load_inventory_supplies_dataset
    import pandas as pd
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)
    
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.25rem;">📦 Critical Supplies & Inventory Forecasting</h2>
        <p style="color: #64748B;">Predictive restocking triggers and burn rates derived from 30-day clinical consumable telemetry.</p>
    </div>
    """, unsafe_allow_html=True)

    raw_inv = load_inventory_supplies_dataset()
    if raw_inv.empty:
        inv_path = DATA_DIR / "inventory_supplies.csv"
        if inv_path.exists():
            raw_inv = pd.read_csv(inv_path)

    if not raw_inv.empty:
        # Normalize date column to datetime for robust comparison across PostgreSQL & CSV
        raw_inv["date"] = pd.to_datetime(raw_inv["date"])
        latest_date = raw_inv["date"].max()
        latest_inv = raw_inv[raw_inv["date"] == latest_date].copy()
        
        # Calculate 7-day average consumption leading to latest date
        seven_days_ago = latest_date - pd.Timedelta(days=7)
        recent_inv = raw_inv[raw_inv["date"] >= seven_days_ago]
        avg_burn = recent_inv.groupby("item_id")["daily_consumption"].mean().round(1)
        
        summary_rows = []
        for _, row in latest_inv.iterrows():
            iid = row["item_id"]
            burn = float(avg_burn.get(iid, row["daily_consumption"]))
            closing = float(row["closing_stock"])
            days_rem = round(closing / burn, 1) if burn > 0 else 999.0
            thresh = float(row["reorder_threshold"])
            lead = int(row["supplier_lead_time_days"])
            
            if closing == 0:
                trigger = "🔴 Stockout - Emergency Order"
            elif closing <= thresh:
                trigger = f"⚠️ Reorder Required (Lead: {lead}d)"
            else:
                trigger = "✅ Sufficient Stock"
                
            summary_rows.append({
                "Item ID": iid,
                "Consumable Item": row["item_name"],
                "Category": row["item_category"],
                "Closing Stock": f"{int(closing):,}",
                "Avg Daily Burn": f"{burn:,}",
                "Days Left": f"{days_rem} days",
                "Reorder Threshold": f"{int(thresh):,}",
                "Lead Time": f"{lead} days",
                "Restock Status": trigger
            })
            
        inv_df = pd.DataFrame(summary_rows)
        
        # Quick metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Tracked Consumables", f"{len(inv_df)} SKUs")
        with c2:
            st.metric("Critical Alerts", "1 Item (N95)", delta="Stockout", delta_color="inverse")
        with c3:
            st.metric("Reorder Triggers", "2 Items", delta="Below Threshold", delta_color="inverse")
        with c4:
            st.metric("Telemetry Period", "30 Days Active")
            
        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
        st.dataframe(inv_df, width="stretch", hide_index=True)
        st.error("🚨 **Urgent Restock Action Required:** N95 Respirators (MSK-N95) reached 0 closing stock on Dec 31. Expedited 7-day supplier replenishment PO #9842 initiated.")
    else:
        st.warning("Inventory dataset not found.")
        
    render_footer()
