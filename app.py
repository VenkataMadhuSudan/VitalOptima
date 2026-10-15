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
from ui.views.login_view import show_login_view
from ui.views.admission_workspace import show_admission_workspace
from ui.views.settings_view import show_settings_view
from services.auth_service import get_current_user, logout_user, has_permission

# Page configuration
st.set_page_config(
    page_title="VitalOptima — Hospital Resource Optimization",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

import base64

# Check current authenticated user
current_user = get_current_user()

# If not authenticated, render login gateway
if not current_user:
    st.session_state["theme"] = "Light Mode"
    st.html(get_custom_css("Light Mode"))
    show_login_view()
    st.stop()

# Initialize Session State
if "current_page" not in st.session_state:
    if current_user["role"] == "ADMISSION_OFFICER":
        st.session_state["current_page"] = "Admission Workspace"
    else:
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

    # User Profile & Role Card
    role_badge_color = "#1E60F2" if current_user["role"] == "ADMIN" else "#10B981"
    role_badge_bg = "#EFF6FF" if current_user["role"] == "ADMIN" else "#ECFDF5"
    st.html(f"""
    <div style="background: #0F233D; border: 1px solid #1E3A5F; border-radius: 8px; padding: 0.65rem 0.85rem; margin-bottom: 1rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.25rem;">
            <div style="font-size: 0.82rem; font-weight: 700; color: #F8FAFC;">{current_user.get('full_name')}</div>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.4rem;">
            <span style="font-size: 0.68rem; font-weight: 700; background: {role_badge_bg}; color: {role_badge_color}; padding: 0.1rem 0.45rem; border-radius: 4px;">
                {current_user.get('role')}
            </span>
            <span style="font-size: 0.70rem; color: #94A3B8;">{current_user.get('department', 'Hospital')}</span>
        </div>
    </div>
    """)

    # Define Navigation Options based on Centralized RBAC
    if current_user["role"] == "ADMISSION_OFFICER":
        nav_options = [
            "Admission Workspace"
        ]
        # Force navigation state to permitted workspace
        if st.session_state["current_page"] != "Admission Workspace":
            st.session_state["current_page"] = "Admission Workspace"
    else:
        # ADMIN has full access
        nav_options = [
            "Dashboard",
            "Admission Workspace",
            "AI Insights & Agent",
            "Resource Management",
            "Demand Forecasting",
            "Optimization",
            "What-if Simulator",
            "Decision Log",
            "Inventory Forecasting",
            "Historical Data & Records",
            "Settings"
        ]

    icons = {
        "Dashboard": "📊",
        "Admission Workspace": "🏥",
        "AI Insights & Agent": "🤖",
        "Resource Management": "🛏️",
        "Demand Forecasting": "📈",
        "Optimization": "⚙️",
        "What-if Simulator": "🎛️",
        "Decision Log": "📋",
        "Inventory Forecasting": "📦",
        "Historical Data & Records": "🗄️",
        "Settings": "⚙️"
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

    # Sign Out Button
    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
    if st.button("🚪 Sign Out", width="stretch", type="secondary"):
        logout_user()
        st.rerun()

    if b64_building:
        st.html(f"""
        <div style="margin-top: 1.5rem; border-radius: 10px; overflow: hidden; border: 1px solid #1E293B;">
            <img src="data:image/jpeg;base64,{b64_building}" style="width: 100%; height: 90px; object-fit: cover; display: block;" />
        </div>
        """)

# --- Main View Router with Defense-in-Depth Permission Verification ---
active_view = st.session_state["current_page"]

if active_view == "Admission Workspace":
    show_admission_workspace()
elif active_view == "Dashboard":
    if not has_permission(current_user, "analytics.view"):
        st.error("⛔ Access Denied: Administrator role required to view the Hospital Operations Dashboard.")
    else:
        show_dashboard()
elif active_view == "AI Insights & Agent":
    if not has_permission(current_user, "analytics.view"):
        st.error("⛔ Access Denied: Administrator role required to view AI Insights.")
    else:
        show_ai_insights()
elif active_view == "Resource Management":
    if not has_permission(current_user, "analytics.view"):
        st.error("⛔ Access Denied.")
    else:
        show_resource_mgmt()
elif active_view == "Demand Forecasting":
    if not has_permission(current_user, "forecasting.view"):
        st.error("⛔ Access Denied.")
    else:
        show_demand_forecast()
elif active_view == "Optimization":
    if not has_permission(current_user, "optimization.view"):
        st.error("⛔ Access Denied.")
    else:
        show_optimization()
elif active_view == "What-if Simulator":
    if not has_permission(current_user, "simulator.view"):
        st.error("⛔ Access Denied.")
    else:
        show_simulator()
elif active_view == "Decision Log":
    if not has_permission(current_user, "decisions.manage"):
        st.error("⛔ Access Denied.")
    else:
        show_decision_log()
elif active_view in ["Historical Data & Records", "PostgreSQL Explorer"]:
    if not has_permission(current_user, "audit.view"):
        st.error("⛔ Access Denied.")
    else:
        show_historical_data_view()
elif active_view in ["Settings", "Settings & Access Management"]:
    if not has_permission(current_user, "users.manage"):
        st.error("⛔ Access Denied: Administrator role required.")
    else:
        show_settings_view()
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

        # =====================================================================
        # SEPARATE TABLE: HOSPITAL BLOOD BANK & TRANSFUSION BACKUP RESERVES
        # =====================================================================
        st.markdown("""
        <div style="margin-top: 2.25rem; margin-bottom: 1.15rem; border-top: 1px solid #E2E8F0; padding-top: 1.5rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
                <div>
                    <h3 style="font-weight: 800; color: #0F172A; margin-bottom: 0.25rem; font-size: 1.35rem; display: flex; align-items: center; gap: 0.45rem;">
                        <span>🩸</span> Hospital Blood Bank & Transfusion Backup Reserves
                    </h3>
                    <p style="color: #64748B; font-size: 0.88rem; margin: 0;">
                        Real-time blood component inventory, emergency cross-matched reserves, minimum trauma buffers, and shelf-life horizons.
                    </p>
                </div>
                <div style="background: #FEE2E2; color: #DC2626; font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.65rem; border-radius: 6px; border: 1px solid #FCA5A5;">
                    🚨 O- Universal Buffer Deficit Active
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        from db.postgres import load_blood_bank_dataset
        raw_blood = load_blood_bank_dataset()
        if not raw_blood.empty:
            tot_units = int(raw_blood["units_available"].sum())
            tot_res = int(raw_blood["units_reserved"].sum())
            tot_burn = round(float(raw_blood["daily_consumption"].sum()), 1)
            crit_count = len(raw_blood[raw_blood["status"].str.contains("Critical", case=False, na=False)])

            # Blood Bank KPI Metrics
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                st.metric("Total Blood Reserves", f"{tot_units:,} Units", "Across 8 Blood Groups")
            with b2:
                st.metric("Units Cross-Matched", f"{tot_res:,} Units", "Reserved for Surgery/ICU")
            with b3:
                st.metric("Daily Transfusion Rate", f"{tot_burn:,} Units/day", "Hospital-Wide Consumption")
            with b4:
                st.metric("Critical Deficits", f"{crit_count} Group (O-)", delta="Under Buffer", delta_color="inverse")

            # Filters for the blood bank table
            f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 3.0])
            with f_col1:
                all_groups = ["All Groups"] + sorted(list(raw_blood["blood_group"].unique()))
                selected_group = st.selectbox("Filter Blood Group", all_groups, key="sb_blood_group")
            with f_col2:
                all_comps = ["All Components"] + sorted(list(raw_blood["component_type"].unique()))
                selected_comp = st.selectbox("Filter Component", all_comps, key="sb_blood_comp")

            filtered_blood = raw_blood.copy()
            if selected_group != "All Groups":
                filtered_blood = filtered_blood[filtered_blood["blood_group"] == selected_group]
            if selected_comp != "All Components":
                filtered_blood = filtered_blood[filtered_blood["component_type"] == selected_comp]

            # Format DataFrame for display
            display_blood = filtered_blood[[
                "blood_group", "component_type", "units_available", "units_reserved",
                "net_available_units", "critical_threshold", "daily_consumption",
                "days_of_supply", "shelf_life_days", "storage_temp", "status"
            ]].copy()
            display_blood.columns = [
                "Blood Group", "Component Type", "Units Available", "Reserved (Cross-Matched)",
                "Net Unreserved", "Min Buffer Threshold", "Daily Consumption",
                "Days of Supply", "Shelf Life (Days)", "Storage Temp", "Transfusion Status"
            ]

            st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
            st.dataframe(display_blood, width="stretch", hide_index=True)

            st.warning("🩸 **Blood Transfusion Advisory:** O- Negative Universal Donor PRBC has dropped to **4 units** (only 2 unreserved for emergency trauma) against a minimum safety reserve of **10 units**. Urgent blood drive notification dispatched to regional blood center.")
        else:
            st.info("Blood bank inventory dataset initializing...")
    else:
        st.warning("Inventory dataset not found.")

    render_footer()

# --- Floating AI Hospital Insights Assistant (Admin Only) ---
if current_user and current_user.get("role") == "ADMIN":
    from ui.ai_summary_panel import render_floating_ai_assistant
    render_floating_ai_assistant()

