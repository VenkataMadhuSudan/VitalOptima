"""
VitalOptima UI Shared Components
Reusable presentation widgets, top navigation header, footer, and metric cards.
"""
import streamlit as st

def render_top_nav(hospital_name: str, timestamp: str, initials: str, user: str):
    """Renders the persistent executive top navbar across all views."""
    st.html(f"""
    <div class="top-navbar">
        <div class="hospital-brand-group">
            <div class="hospital-logo-icon">🏥</div>
            <div>
                <div class="hospital-title">{hospital_name}</div>
                <div class="hospital-subtitle">AI Resource Optimization & Clinical Operations Command</div>
            </div>
        </div>
        <div class="top-meta-group">
            <div class="status-pill">
                <span style="font-size:0.65rem;">🟢</span> Live Clinical Telemetry
            </div>
            <div class="clock-pill">
                <span>🕒</span> {timestamp}
            </div>
            <div class="admin-chip">
                <div class="admin-avatar">{initials}</div>
                <div class="admin-name">{user}</div>
            </div>
        </div>
    </div>
    """)

def render_footer():
    """Renders the standard enterprise footer and clinical disclaimer."""
    st.html("""
    <div class="vital-footer">
        <div><strong>VitalOptima™ Enterprise Clinical Resource Optimizer</strong> • Version 2.4.0 (Dual Engine: Neon Cloud + SQLite)</div>
        <div style="margin-top: 0.35rem; font-size: 0.72rem; color: #94A3B8;">
            Synthetic Hospital Operations Demonstration. Algorithmic recommendations require qualified clinical administrator authorization.
        </div>
    </div>
    """)

def render_metric_card(title: str, value: str, subtext: str, card_type: str = "default", icon: str = ""):
    """Renders a custom HTML KPI metric card with clean gradient accents."""
    type_class = ""
    if card_type == "alert":
        type_class = "alert-card"
    elif card_type == "warning":
        type_class = "warning-card"
    elif card_type == "success":
        type_class = "success-card"

    st.html(f"""
    <div class="metric-card {type_class}">
        <div class="metric-title">
            <span>{title}</span>
            <span>{icon}</span>
        </div>
        <div class="metric-value">{value}</div>
        <div class="metric-subtext">{subtext}</div>
    </div>
    """)
