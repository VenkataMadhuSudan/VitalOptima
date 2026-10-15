"""
VitalOptima UI Components
High-fidelity visual components matching the hospital command center dashboard:
donut charts, KPI cards, timeline widgets, alert panels, and Plotly charts.
"""
import plotly.graph_objects as go
import streamlit as st
import base64
from datetime import datetime, timedelta
from pathlib import Path
from config import ASSETS_DIR

def render_donut_gauge(value, label, color="#2563EB", bg_color="#E2E8F0", height=100, width=100):
    """
    Renders a sleek circular donut gauge showing a percentage.
    """
    remainder = max(0, 100 - value)
    fig = go.Figure(data=[go.Pie(
        values=[value, remainder],
        hole=0.74,
        marker=dict(colors=[color, bg_color]),
        textinfo='none',
        hoverinfo='none',
        sort=False,
        direction='clockwise'
    )])

    fig.update_layout(
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        height=height,
        width=width,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        annotations=[
            dict(
                text=f"<b>{int(value)}%</b>",
                x=0.5, y=0.58,
                font=dict(size=15, color="#0F172A", family="Plus Jakarta Sans"),
                showarrow=False
            ),
            dict(
                text=f"<span style='font-size:9px; color:#64748B;'>{label}</span>",
                x=0.5, y=0.28,
                font=dict(size=9, color="#64748B", family="Plus Jakarta Sans"),
                showarrow=False
            )
        ]
    )
    return fig

def render_top_nav(hospital_name, time_str=None, user_initials="AD", user_name="Admin", timezone_label="IST"):
    """
    Renders the modern top bar with hospital selector, live IST clock, clinical shift pill, search bar, notification badge, and demo data pill.
    """
    if not time_str:
        from config import get_system_timestamp
        time_str = get_system_timestamp()

    from config import get_current_shift
    shift = get_current_shift()

    is_dark = st.session_state.get("theme", "Dark Mode") == "Dark Mode"
    panel_bg = "#0D192E" if is_dark else "#FFFFFF"
    border_col = "#1E2D4A" if is_dark else "#E2E8F0"
    text_pri = "#F8FAFC" if is_dark else "#0F172A"
    text_sec = "#94A3B8" if is_dark else "#64748B"
    badge_bg = "#13233D" if is_dark else "#F1F5F9"

    st.markdown(f"""
    <div class="top-nav-container" style="display: flex; justify-content: space-between; align-items: center; background: {panel_bg}; border: 1px solid {border_col}; border-radius: 12px; padding: 0.55rem 1.15rem; margin-bottom: 0.65rem; width: 100%; box-sizing: border-box;">
        <div style="display: flex; align-items: center; gap: 0.85rem; flex-wrap: wrap;">
            <div style="display: inline-flex; align-items: center; gap: 0.45rem; font-weight: 700; color: {text_pri}; font-size: 0.9rem; background: {badge_bg}; padding: 0.3rem 0.75rem; border-radius: 8px; border: 1px solid {border_col};">
                <span>🏥</span> {hospital_name} <span style="font-size: 0.72rem; color: #94A3B8;">▼</span>
            </div>
            <div style="display: inline-flex; align-items: center; gap: 0.45rem; font-size: 0.82rem; color: {text_sec}; font-weight: 500;">
                <span>🕒</span>
                <b style="color: {text_pri};">{time_str}</b>
                <span style="background: rgba(30, 96, 242, 0.1); color: #1E60F2; font-size: 0.7rem; font-weight: 700; padding: 0.12rem 0.4rem; border-radius: 5px; border: 1px solid rgba(30, 96, 242, 0.25);">
                    {timezone_label}
                </span>
                <span style="font-size: 0.74rem; color: {text_sec}; border-left: 1px solid {border_col}; padding-left: 0.5rem; display: inline-flex; align-items: center; gap: 0.25rem;">
                    <span>{shift['icon']}</span> <b>{shift['name']}</b>
                </span>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div class="top-nav-search" style="background: {badge_bg}; border: 1px solid {border_col}; border-radius: 8px; padding: 0.3rem 0.75rem; color: {text_sec}; font-size: 0.8rem; display: flex; align-items: center; gap: 0.4rem; width: 240px;">
                <span>🔍</span> Search resources, patients...
            </div>
            <div style="position: relative; cursor: pointer; display: flex; align-items: center;">
                <span style="font-size: 1.1rem;">🔔</span>
                <span style="position: absolute; top: -4px; right: -6px; background: #EF4444; color: white; border-radius: 50%; width: 14px; height: 14px; font-size: 9px; display: flex; align-items: center; justify-content: center; font-weight: 700;">1</span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.4rem; font-weight: 600; font-size: 0.82rem; color: {text_pri};">
                <div style="background: #6366F1; color: white; border-radius: 50%; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.74rem;">{user_initials}</div>
                <span>{user_name}</span> <span style="font-size: 0.68rem; color: #94A3B8;">▼</span>
            </div>
            <div style="background: rgba(16, 185, 129, 0.12); color: #10B981; font-size: 0.72rem; font-weight: 700; padding: 0.25rem 0.65rem; border-radius: 20px; border: 1px solid rgba(16, 185, 129, 0.3); display: inline-flex; align-items: center; gap: 0.3rem;">
                <span style="color: #10B981; font-size: 0.7rem;">●</span> LIVE SYSTEM
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_welcome_header(hospital_img_path=None, title="Good afternoon, Admin", subtitle="Here's what's happening at your hospital today."):
    """
    Renders the Command Center title and modern hospital exterior photo banner horizontally.
    """
    is_dark = st.session_state.get("theme", "Dark Mode") == "Dark Mode"
    panel_bg = "#0D192E" if is_dark else "#FFFFFF"
    border_col = "#1E2D4A" if is_dark else "#E2E8F0"
    text_pri = "#F8FAFC" if is_dark else "#0F172A"
    text_sec = "#94A3B8" if is_dark else "#64748B"

    img_tag = ""
    if hospital_img_path and Path(hospital_img_path).exists():
        with open(hospital_img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
            img_tag = f'''<div class="welcome-header-img" style="width: 200px; height: 64px; border-radius: 8px; overflow: hidden; border: 1px solid {border_col}; box-shadow: 0 2px 8px rgba(0,0,0,0.06); flex-shrink: 0;"><img src="data:image/jpeg;base64,{encoded}" style="width: 100%; height: 100%; object-fit: cover; display: block;" alt="City General Hospital Campus" /></div>'''
    else:
        img_tag = f'''<div class="welcome-header-img" style="width: 200px; height: 64px; border-radius: 8px; background: #0B192C; display: flex; align-items: center; justify-content: center; color: #94A3B8; font-size: 0.8rem; border: 1px solid {border_col}; flex-shrink: 0;">🏥 City General Campus</div>'''

    st.markdown(f"""
    <div class="welcome-header-container" style="display: flex; justify-content: space-between; align-items: center; background: {panel_bg}; border: 1px solid {border_col}; border-radius: 12px; padding: 0.75rem 1.25rem; margin-bottom: 0.65rem; width: 100%; box-sizing: border-box;">
        <div>
            <div style="color: #3B82F6; font-size: 0.76rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.15rem;">Hospital Command Center</div>
            <h1 style="font-size: 1.35rem; font-weight: 800; color: {text_pri}; margin: 0 0 0.15rem 0; letter-spacing: -0.02em;">{title}</h1>
            <p style="color: {text_sec}; font-size: 0.82rem; margin: 0;">{subtitle}</p>
        </div>
        {img_tag}
    </div>
    """, unsafe_allow_html=True)

def create_demand_forecast_chart(df_forecast):
    """
    Creates the 24h Patient Demand Forecast line chart with peak annotation.
    """
    fig = go.Figure()

    # Capacity threshold line (100)
    fig.add_trace(go.Scatter(
        x=df_forecast["Hour"],
        y=df_forecast["Emergency_Capacity"],
        mode="lines",
        name="Capacity",
        line=dict(color="#10B981", width=1.5, dash="dash")
    ))

    # Historical demand curve
    fig.add_trace(go.Scatter(
        x=df_forecast["Hour"],
        y=df_forecast["Historical_Demand"],
        mode="lines",
        name="Historical",
        line=dict(color="#94A3B8", width=1.5, dash="dot")
    ))

    # Predicted demand curve
    fig.add_trace(go.Scatter(
        x=df_forecast["Hour"],
        y=df_forecast["Predicted_Demand"],
        mode="lines+markers",
        name="Predicted",
        line=dict(color="#1E60F2", width=2.5),
        marker=dict(size=6, color="#1E60F2"),
        fill='tozeroy',
        fillcolor='rgba(30, 96, 242, 0.05)'
    ))

    # Peak annotation box at 15:00 (value 92)
    fig.add_annotation(
        x="15h" if "15h" in df_forecast["Hour"].values else df_forecast["Hour"].iloc[15],
        y=92,
        text="<b>Peak predicted demand</b><br>92 arrivals at 15:00",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=1.5,
        arrowcolor="#1E60F2",
        ax=0,
        ay=-45,
        bgcolor="#FFFFFF",
        bordercolor="#DBEAFE",
        borderwidth=1,
        borderpad=6,
        font=dict(size=10, color="#1E293B", family="Plus Jakarta Sans")
    )

    fig.update_layout(
        margin=dict(l=30, r=10, t=10, b=20),
        height=235,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9.5, color="#64748B")
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            tickmode="array",
            tickvals=["Now", "3h", "6h", "9h", "12h", "15h", "18h", "21h", "24h"],
            tickfont=dict(size=9.5, color="#64748B"),
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            range=[0, 120],
            tickvals=[0, 30, 60, 90, 120],
            tickfont=dict(size=9.5, color="#64748B"),
            zeroline=False
        ),
        hovermode="x unified"
    )
    return fig

def create_demand_vs_capacity_chart(df_forecast):
    """
    Creates the bar + line combo chart for Predicted Demand vs Available Capacity.
    """
    fig = go.Figure()

    # Predicted Demand (Orange Bars)
    fig.add_trace(go.Bar(
        x=df_forecast["Hour"],
        y=df_forecast["Predicted_Demand"],
        name="Predicted Demand",
        marker_color="#F97316",
        opacity=0.85,
        width=0.45
    ))

    # Available Capacity (Blue Line with markers)
    fig.add_trace(go.Scatter(
        x=df_forecast["Hour"],
        y=df_forecast["Available_Capacity"],
        mode="lines+markers",
        name="Available Capacity",
        line=dict(color="#0284C7", width=2.5),
        marker=dict(size=6, color="#0284C7")
    ))

    # Historical baseline (Grey dash)
    fig.add_trace(go.Scatter(
        x=df_forecast["Hour"],
        y=df_forecast["Historical_Demand"],
        mode="lines",
        name="Historical",
        line=dict(color="#94A3B8", width=1.5, dash="dot")
    ))

    fig.update_layout(
        margin=dict(l=30, r=10, t=10, b=20),
        height=235,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9.5, color="#64748B")
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            tickmode="array",
            tickvals=["Now", "3h", "6h", "9h", "12h", "15h", "18h", "21h", "24h"],
            tickfont=dict(size=9.5, color="#64748B"),
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            range=[0, 200],
            tickvals=[0, 50, 100, 150, 200],
            tickfont=dict(size=9.5, color="#64748B"),
            zeroline=False
        ),
        barmode='group',
        hovermode="x unified"
    )
    return fig

def render_department_table(df_depts):
    """
    Renders the Department Resource Status table with occupancy progress bars.
    """
    rows_html = []
    for _, row in df_depts.iterrows():
        occ = int(row["Occupancy"])
        color = row.get("Color", "#EF4444" if occ >= 85 else "#F59E0B" if occ >= 80 else "#10B981")
        rows_html.append(
            f'<tr>'
            f'<td style="font-weight:700; color:#0F172A; white-space:nowrap; padding:0.35rem 0.25rem;">{row["Department"]}</td>'
            f'<td style="text-align:center; padding:0.35rem 0.2rem;">{row["Total Beds"]}</td>'
            f'<td style="text-align:center; padding:0.35rem 0.2rem;">{row["Occupied"]}</td>'
            f'<td style="text-align:center; padding:0.35rem 0.2rem;"><span style="color:#10B981; font-weight:700;">{row["Available"]}</span></td>'
            f'<td style="text-align:center; color:#64748B; padding:0.35rem 0.2rem;">{row["Unavailable"]}</td>'
            f'<td style="padding:0.35rem 0.25rem;">'
            f'<div class="occ-cell">'
            f'<span style="font-weight:700; color:{color}; min-width:28px;">{occ}%</span>'
            f'<div class="occ-bar-pill" style="background:{color};"></div>'
            f'</div>'
            f'</td>'
            f'</tr>'
        )

    table_rows = "".join(rows_html)
    return (
        f'<table class="dept-table">'
        f'<thead><tr>'
        f'<th style="text-align:left;">Department</th>'
        f'<th style="text-align:center;">Total Beds</th>'
        f'<th style="text-align:center;">Occupied</th>'
        f'<th style="text-align:center;">Available</th>'
        f'<th style="text-align:center;">Unavailable</th>'
        f'<th style="text-align:left;">Occupancy</th>'
        f'</tr></thead>'
        f'<tbody>{table_rows}</tbody>'
        f'</table>'
    )

def render_alerts_panel(active_alerts, shortage_alerts):
    """
    Renders the right-hand Alerts & Notifications panel matching the exact items in the mockup.
    """
    active_items = []
    for a in active_alerts:
        badge_cls = "badge-high" if a["severity"] == "High" else "badge-medium"
        active_items.append(
            f'<div class="alert-item">'
            f'<div class="alert-left">'
            f'<div class="alert-dot" style="background:#EF4444;"></div>'
            f'<div class="alert-content">'
            f'<span class="alert-heading">{a["title"]}</span>'
            f'<span class="alert-desc">{a["desc"]}</span>'
            f'</div>'
            f'</div>'
            f'<div class="alert-right">'
            f'<span class="alert-time">{a["time"]}</span>'
            f'<span class="severity-badge {badge_cls}">{a["severity"]}</span>'
            f'</div>'
            f'</div>'
        )

    shortage_items = []
    for a in shortage_alerts:
        badge_cls = "badge-high" if a["severity"] == "High" else "badge-medium" if a["severity"] == "Medium" else "badge-low"
        dot_color = "#F59E0B" if a["severity"] in ["High", "Medium"] else "#10B981"
        shortage_items.append(
            f'<div class="alert-item">'
            f'<div class="alert-left">'
            f'<div class="alert-dot" style="background:{dot_color};"></div>'
            f'<div class="alert-content">'
            f'<span class="alert-heading">{a["title"]}</span>'
            f'<span class="alert-desc">{a["desc"]}</span>'
            f'</div>'
            f'</div>'
            f'<div class="alert-right">'
            f'<span class="alert-time">{a["time"]}</span>'
            f'<span class="severity-badge {badge_cls}">{a["severity"]}</span>'
            f'</div>'
            f'</div>'
        )

    act_str = "".join(active_items)
    sht_str = "".join(shortage_items)

    return (
        f'<div class="dashboard-panel" style="margin-bottom:0.75rem;">'
        f'<div class="panel-header" style="margin-bottom:0.4rem;">'
        f'<div class="panel-title"><span>🚨</span> Alerts & Notifications</div>'
        f'<a href="#" style="font-size:0.78rem; color:#2563EB; font-weight:600; text-decoration:none;">View all →</a>'
        f'</div>'
        f'<div class="alert-section-title" style="margin-top:0.2rem;"><span style="color:#EF4444;">⚡</span> Active Alerts ({len(active_alerts)})</div>'
        f'<div class="alert-section-sub" style="margin-bottom:0.35rem;">Immediate attention required</div>'
        f'<div style="margin-bottom: 0.65rem;">{act_str}</div>'
        f'<div class="alert-section-title"><span style="color:#F59E0B;">⚠️</span> Shortage Alerts ({len(shortage_alerts)})</div>'
        f'<div class="alert-section-sub" style="margin-bottom:0.35rem;">Potential capacity issues</div>'
        f'<div>{sht_str}</div>'
        f'</div>'
    )

def render_recent_activity(activities):
    """
    Renders the Recent Activity timeline.
    """
    items_html = []
    for act in activities:
        t_str = act["time_str"] if isinstance(act, dict) or hasattr(act, "__getitem__") else act[1]
        title = act["title"] if isinstance(act, dict) or hasattr(act, "__getitem__") else act[2]
        details = act["details"] if isinstance(act, dict) or hasattr(act, "__getitem__") else act[3]
        color = act["color"] if isinstance(act, dict) or hasattr(act, "__getitem__") else act[4]

        items_html.append(
            f'<div class="timeline-item">'
            f'<div class="timeline-time">{t_str}</div>'
            f'<div class="timeline-bullet" style="background:{color};"></div>'
            f'<div class="timeline-body">'
            f'<span class="timeline-title">{title}</span>'
            f'<span class="timeline-detail">{details}</span>'
            f'</div>'
            f'</div>'
        )

    items_str = "".join(items_html)
    return f'<div class="timeline-container">{items_str}</div>'

def render_before_after_cards():
    """
    Renders the Before vs After (Optimized) comparison cards matching the target mockup.
    """
    return '''
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 0.65rem;">
        <div class="before-card">
            <div>
                <div class="opt-tag-before">Before</div>
                <div class="opt-subtext" style="margin-top:0.35rem;">Unmet Demand</div>
                <div class="opt-num-large">18</div>
                <div class="opt-subtext">(patients)</div>
            </div>
            <div style="margin-top:0.6rem;">
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; font-weight:700;">
                    <span style="color:#64748B;">Resource Utilization</span>
                    <span style="color:#0F172A;">72%</span>
                </div>
                <div class="opt-progress-track">
                    <div class="opt-progress-fill-blue"></div>
                </div>
            </div>
        </div>

        <div class="after-card">
            <div>
                <div class="opt-tag-after">After (Optimized)</div>
                <div class="opt-subtext" style="margin-top:0.35rem;">Unmet Demand</div>
                <div class="opt-num-large" style="color:#059669 !important;">5</div>
                <div class="opt-subtext">(patients)</div>
            </div>
            <div style="margin-top:0.6rem;">
                <div style="display:flex; justify-content:space-between; font-size:0.75rem; font-weight:700;">
                    <span style="color:#64748B;">Resource Utilization</span>
                    <span style="color:#10B981;">86%</span>
                </div>
                <div class="opt-progress-track">
                    <div class="opt-progress-fill-green"></div>
                </div>
            </div>
        </div>
    </div>
    '''

def create_optimization_impact_chart():
    """
    Renders the Optimization Impact bar chart comparing Before vs After for Beds, Staff, and ORs.
    """
    fig = go.Figure()
    categories = ["Beds", "Staff", "ORs"]
    before_vals = [52, 54, 53]
    after_vals = [65, 68, 67]

    fig.add_trace(go.Bar(
        x=categories,
        y=before_vals,
        name="Before",
        marker_color="#BFDBFE",
        width=0.28
    ))
    fig.add_trace(go.Bar(
        x=categories,
        y=after_vals,
        name="After",
        marker_color="#10B981",
        width=0.28
    ))

    fig.update_layout(
        margin=dict(l=25, r=10, t=10, b=15),
        height=145,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9.5, color="#64748B")
        ),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=10, color="#64748B"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            range=[0, 100],
            tickvals=[0, 50, 100],
            tickfont=dict(size=9.5, color="#64748B"),
            zeroline=False
        ),
        barmode='group',
        bargap=0.35,
        hovermode="x unified"
    )
    return fig

def render_ai_recommendation_card():
    """
    Renders the AI Recommendation card with actionable buttons.
    """
    return """
    <div class="dashboard-panel" style="margin-bottom:0.75rem;">
        <div class="panel-header" style="margin-bottom:0.4rem;">
            <div class="panel-title"><span style="color:#10B981;">✨</span> AI Recommendation</div>
            <a href="#" style="font-size:0.78rem; color:#2563EB; font-weight:600; text-decoration:none;">View details →</a>
        </div>
        <div style="font-size:0.86rem; font-weight:700; color:#0F172A; margin-bottom:0.25rem;">
            Reallocate 4 nurses from Surgery to ED (next 6 hours)
        </div>
        <div style="font-size:0.76rem; color:#64748B; margin-bottom:0.6rem; line-height:1.4;">
            Based on forecasted 20% increase in ED arrivals and current staff availability.
        </div>
        <div style="display:inline-block; background:#DCFCE7; color:#15803D; font-size:0.72rem; font-weight:700; padding:0.2rem 0.6rem; border-radius:20px; border:1px solid #BBF7D0; margin-bottom:0.65rem;">
            Expected improvement: 18%
        </div>
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:0.35rem;">
            <button style="border:1px solid #CBD5E1; background:#F8FAFC; color:#475569; font-size:0.7rem; font-weight:600; padding:0.35rem 0.2rem; border-radius:6px; cursor:pointer;">Acknowledge</button>
            <button style="border:1px solid #93C5FD; background:#EFF6FF; color:#1E40AF; font-size:0.7rem; font-weight:600; padding:0.35rem 0.2rem; border-radius:6px; cursor:pointer;">Assign</button>
            <button style="border:none; background:#10B981; color:#FFFFFF; font-size:0.7rem; font-weight:700; padding:0.35rem 0.2rem; border-radius:6px; cursor:pointer;">Approve</button>
            <button style="border:1px solid #E2E8F0; background:#FFFFFF; color:#64748B; font-size:0.7rem; font-weight:600; padding:0.35rem 0.2rem; border-radius:6px; cursor:pointer;">Resolve</button>
        </div>
    </div>
    """

def render_whatif_simulator_card():
    """
    Renders the What-if Simulator quick trigger card.
    """
    return """
    <div class="dashboard-panel" style="margin-bottom:0.75rem;">
        <div class="panel-header" style="margin-bottom:0.4rem;">
            <div class="panel-title"><span style="color:#2563EB;">🔬</span> What-if Simulator</div>
            <a href="#" style="font-size:0.78rem; color:#2563EB; font-weight:600; text-decoration:none;">Run Simulation →</a>
        </div>
        <div style="display:flex; flex-direction:column; gap:0.45rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; background:#FEF2F2; border:1px solid #FEE2E2; border-radius:8px; padding:0.5rem 0.75rem; cursor:pointer;">
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span style="font-size:0.95rem;">🚨</span>
                    <div>
                        <div style="font-size:0.8rem; font-weight:700; color:#DC2626;">+20% Emergency Arrivals</div>
                        <div style="font-size:0.7rem; color:#64748B;">See impact on resources and shortages</div>
                    </div>
                </div>
                <span style="color:#94A3B8; font-size:0.8rem;">›</span>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; background:#FFFBEB; border:1px solid #FEF3C7; border-radius:8px; padding:0.5rem 0.75rem; cursor:pointer;">
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span style="font-size:0.95rem;">⚠️</span>
                    <div>
                        <div style="font-size:0.8rem; font-weight:700; color:#D97706;">ICU Capacity Reduction</div>
                        <div style="font-size:0.7rem; color:#64748B;">Simulate temporary loss of ICU beds</div>
                    </div>
                </div>
                <span style="color:#94A3B8; font-size:0.8rem;">›</span>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; background:#F5F3FF; border:1px solid #EDE9FE; border-radius:8px; padding:0.5rem 0.75rem; cursor:pointer;">
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span style="font-size:0.95rem;">👥</span>
                    <div>
                        <div style="font-size:0.8rem; font-weight:700; color:#7C3AED;">Staff Shortage</div>
                        <div style="font-size:0.7rem; color:#64748B;">Model reduced staff availability</div>
                    </div>
                </div>
                <span style="color:#94A3B8; font-size:0.8rem;">›</span>
            </div>
        </div>
    </div>
    """

def render_recent_forecasts_table():
    """
    Renders the Recent Forecasts table with dynamic IST telemetry timestamps.
    """
    from config import get_ist_now
    now = get_ist_now()
    telemetry_time = (now - timedelta(minutes=now.minute % 15)).strftime("%b %d, %H:%M")

    return f"""
    <div class="dashboard-panel" style="margin-top:0;">
        <div class="panel-header" style="margin-bottom:0.4rem;">
            <div class="panel-title"><span style="color:#2563EB;">📈</span> Recent Forecasts</div>
            <span style="font-size:0.7rem; color:#64748B;">Telemetry sync: <b style="color:#0F172A;">{telemetry_time} IST</b></span>
        </div>
        <table style="width:100%; border-collapse:collapse; font-size:0.78rem;">
            <thead>
                <tr style="border-bottom:1px solid #E2E8F0; color:#64748B; text-align:left;">
                    <th style="padding:0.4rem 0.5rem; font-weight:600;">Target</th>
                    <th style="padding:0.4rem 0.5rem; font-weight:600;">Model</th>
                    <th style="padding:0.4rem 0.5rem; font-weight:600;">Next 24h (±)</th>
                    <th style="padding:0.4rem 0.5rem; font-weight:600;">Confidence</th>
                    <th style="padding:0.4rem 0.5rem; font-weight:600;">Last Telemetry</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom:1px solid #F1F5F9;">
                    <td style="padding:0.45rem 0.5rem; font-weight:700; color:#0F172A;">Emergency Arrivals</td>
                    <td style="padding:0.45rem 0.5rem; color:#64748B;">Random Forest (365d)</td>
                    <td style="padding:0.45rem 0.5rem; font-weight:700; color:#0F172A;">187 (±12)</td>
                    <td style="padding:0.45rem 0.5rem;"><span style="background:#DCFCE7; color:#15803D; font-weight:700; padding:0.15rem 0.5rem; border-radius:12px; font-size:0.72rem;">89%</span></td>
                    <td style="padding:0.45rem 0.5rem; color:#64748B;">{telemetry_time}</td>
                </tr>
                <tr style="border-bottom:1px solid #F1F5F9;">
                    <td style="padding:0.45rem 0.5rem; font-weight:700; color:#0F172A;">Inpatient Admissions</td>
                    <td style="padding:0.45rem 0.5rem; color:#64748B;">Random Forest</td>
                    <td style="padding:0.45rem 0.5rem; font-weight:700; color:#0F172A;">48 (±4)</td>
                    <td style="padding:0.45rem 0.5rem;"><span style="background:#DCFCE7; color:#15803D; font-weight:700; padding:0.15rem 0.5rem; border-radius:12px; font-size:0.72rem;">86%</span></td>
                    <td style="padding:0.45rem 0.5rem; color:#64748B;">{telemetry_time}</td>
                </tr>
                <tr style="border-bottom:1px solid #F1F5F9;">
                    <td style="padding:0.45rem 0.5rem; font-weight:700; color:#0F172A;">ICU Admissions</td>
                    <td style="padding:0.45rem 0.5rem; color:#64748B;">Gradient Boost</td>
                    <td style="padding:0.45rem 0.5rem; font-weight:700; color:#0F172A;">4 (±1)</td>
                    <td style="padding:0.45rem 0.5rem;"><span style="background:#DCFCE7; color:#15803D; font-weight:700; padding:0.15rem 0.5rem; border-radius:12px; font-size:0.72rem;">91%</span></td>
                    <td style="padding:0.45rem 0.5rem; color:#64748B;">{telemetry_time}</td>
                </tr>
                <tr>
                    <td style="padding:0.45rem 0.5rem; font-weight:700; color:#0F172A;">Scheduled Surgeries</td>
                    <td style="padding:0.45rem 0.5rem; color:#64748B;">Multi-Regression</td>
                    <td style="padding:0.45rem 0.5rem; font-weight:700; color:#0F172A;">12 (±2)</td>
                    <td style="padding:0.45rem 0.5rem;"><span style="background:#DCFCE7; color:#15803D; font-weight:700; padding:0.15rem 0.5rem; border-radius:12px; font-size:0.72rem;">94%</span></td>
                    <td style="padding:0.45rem 0.5rem; color:#64748B;">{telemetry_time}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

def render_kpi_card_compact(icon, title, occupied_val, total_val, unit_label, pct, fill_color, avail_count, avail_label, dot_color="#10B981"):
    """
    Renders the compact mockup KPI card with horizontal progress bar and available count.
    """
    return f"""
    <div class="kpi-card-mockup">
        <div class="kpi-mockup-top">
            <div class="kpi-mockup-icon" style="background: {fill_color}18; color: {fill_color};">
                {icon}
            </div>
            <div class="kpi-mockup-title">{title}</div>
        </div>
        <div>
            <div class="kpi-mockup-num">
                {occupied_val} <span class="kpi-mockup-denom">/ {total_val}</span>
            </div>
            <div class="kpi-mockup-label">{unit_label}</div>
        </div>
        <div>
            <div class="kpi-mockup-progress-row">
                <div class="kpi-mockup-track">
                    <div class="kpi-mockup-fill" style="width: {pct}%; background: {fill_color};"></div>
                </div>
                <div class="kpi-mockup-pct">{pct}%</div>
            </div>
            <div class="kpi-mockup-footer">
                <span class="kpi-mockup-dot" style="background: {dot_color};"></span>
                <span>{avail_count} {avail_label}</span>
            </div>
        </div>
    </div>
    """

def create_predicted_vs_actual_chart(df_forecast=None):
    """
    Renders the Predicted vs Actual Patient Arrivals line chart with shaded confidence interval
    matching the exact mockup aesthetics.
    """
    fig = go.Figure()

    hours = ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]
    actual_vals = [26, 38, 36, 48, 62, 70, 72, 68]
    forecast_vals = [24, 34, 38, 52, 65, 78, 62, 54]
    upper_band = [v + 12 for v in forecast_vals]
    lower_band = [max(0, v - 12) for v in forecast_vals]

    # Upper bound of confidence band
    fig.add_trace(go.Scatter(
        x=hours,
        y=upper_band,
        mode='lines',
        line=dict(width=0),
        hoverinfo='none',
        showlegend=False
    ))

    # Lower bound of confidence band with light purple fill
    fig.add_trace(go.Scatter(
        x=hours,
        y=lower_band,
        mode='lines',
        line=dict(width=0),
        fill='tonexty',
        fillcolor='rgba(139, 92, 246, 0.12)',
        hoverinfo='none',
        showlegend=False
    ))

    # Forecast dashed purple curve
    fig.add_trace(go.Scatter(
        x=hours,
        y=forecast_vals,
        mode='lines',
        name='-- Forecast',
        line=dict(color='#8B5CF6', width=2.5, dash='dash')
    ))

    # Actual solid blue curve with markers
    fig.add_trace(go.Scatter(
        x=hours,
        y=actual_vals,
        mode='lines+markers',
        name='Actual',
        line=dict(color='#2563EB', width=3),
        marker=dict(size=6, color='#2563EB')
    ))

    # Peak annotation
    fig.add_annotation(
        x="15:00",
        y=78,
        text="<b>Peak Demand Surge</b>: 78 arrivals/hr (±12)",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowcolor="#8B5CF6",
        ax=0,
        ay=-36,
        bgcolor="#FFFFFF",
        bordercolor="#DDD6FE",
        borderwidth=1,
        borderpad=5,
        font=dict(size=9.5, color="#5B21B6", family="Plus Jakarta Sans, sans-serif")
    )

    fig.update_layout(
        margin=dict(l=30, r=15, t=10, b=20),
        height=295,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color="#64748B")
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#F8FAFC",
            tickmode="array",
            tickvals=hours,
            tickfont=dict(size=10, color="#64748B")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            range=[0, 110],
            tickvals=[0, 25, 50, 75, 100],
            tickfont=dict(size=10, color="#64748B"),
            zeroline=False
        ),
        hovermode="x unified"
    )
    return fig

def render_forecast_confidence_panel():
    """
    Renders the Forecast Confidence and Key Factors side-panel matching the mockup.
    """
    return """
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.75rem 0.85rem; height: 100%; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;">
        <div>
            <div style="font-size: 0.78rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 0.35rem; margin-bottom: 0.45rem;">
                <span style="color:#2563EB;">📈</span> Forecast Confidence
            </div>
            <div style="display: flex; align-items: center; gap: 0.65rem; margin-bottom: 0.65rem;">
                <div style="width: 44px; height: 44px; border-radius: 50%; border: 3px solid #10B981; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.78rem; color: #0F172A; flex-shrink: 0; background: #FFFFFF;">
                    78%
                </div>
                <div>
                    <div style="font-size: 0.78rem; font-weight: 700; color: #0F172A;">Moderate confidence</div>
                    <div style="font-size: 0.69rem; color: #64748B;">(±12 arrivals)</div>
                </div>
            </div>
        </div>
        <div>
            <div style="font-size: 0.74rem; font-weight: 700; color: #0F172A; margin-bottom: 0.3rem; display: flex; align-items: center; gap: 0.3rem;">
                <span style="color:#2563EB;">🗝️</span> Key Factors
            </div>
            <ul style="margin: 0; padding-left: 1rem; font-size: 0.71rem; color: #64748B; line-height: 1.45;">
                <li>Historical seasonal trend</li>
                <li>Day of week pattern</li>
                <li>Recent increase in arrivals</li>
            </ul>
        </div>
    </div>
    """

def render_compact_active_alerts():
    """
    Renders the exact 3 Active Alerts from the mockup with dynamic IST timestamps.
    """
    from config import get_ist_now
    now = get_ist_now()
    t_icu = (now - timedelta(minutes=17)).strftime("%H:%M")
    t_staff = (now - timedelta(hours=1, minutes=45)).strftime("%H:%M")
    t_bed = (now - timedelta(hours=3, minutes=10)).strftime("%H:%M")

    return f"""
    <div class="dashboard-panel" style="margin-bottom: 0.55rem; padding: 0.75rem 0.95rem;">
        <div class="panel-header" style="margin-bottom: 0.35rem;">
            <div class="panel-title" style="font-size: 0.88rem;"><span style="color:#EF4444;">🚨</span> Active Alerts</div>
            <a href="#" style="font-size: 0.74rem; color: #2563EB; font-weight: 600; text-decoration: none;">View all →</a>
        </div>
        <div style="display: flex; flex-direction: column; gap: 0.4rem;">
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
    </div>
    """

def render_compact_ai_recommendation():
    """
    Renders the AI Recommendation card with tight dimensions matching the mockup.
    """
    return """
    <div class="dashboard-panel" style="margin-bottom: 0; padding: 0.75rem 0.95rem;">
        <div class="panel-header" style="margin-bottom: 0.3rem;">
            <div class="panel-title" style="font-size: 0.88rem;"><span style="color:#10B981;">✨</span> AI Recommendation</div>
            <a href="#" style="font-size: 0.74rem; color: #2563EB; font-weight: 600; text-decoration: none;">View details →</a>
        </div>
        <div style="font-size: 0.82rem; font-weight: 700; color: #0F172A; margin-bottom: 0.2rem;">
            Reallocate 4 nurses from Surgery to ED (next 6 hours)
        </div>
        <div style="font-size: 0.71rem; color: #64748B; margin-bottom: 0.45rem; line-height: 1.35;">
            Based on forecasted 20% increase in ED arrivals and current staff availability.
        </div>
        <div style="display: inline-block; background: #DCFCE7; color: #15803D; font-size: 0.68rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 20px; border: 1px solid #BBF7D0; margin-bottom: 0.55rem;">
            Expected improvement: 18%
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.3rem;">
            <button style="border: 1px solid #CBD5E1; background: #F8FAFC; color: #475569; font-size: 0.68rem; font-weight: 600; padding: 0.3rem 0.15rem; border-radius: 6px; cursor: pointer;">Acknowledge</button>
            <button style="border: 1px solid #93C5FD; background: #EFF6FF; color: #1E40AF; font-size: 0.68rem; font-weight: 600; padding: 0.3rem 0.15rem; border-radius: 6px; cursor: pointer;">Assign</button>
            <button style="border: none; background: #10B981; color: #FFFFFF; font-size: 0.68rem; font-weight: 700; padding: 0.3rem 0.15rem; border-radius: 6px; cursor: pointer;">Approve</button>
            <button style="border: 1px solid #E2E8F0; background: #FFFFFF; color: #64748B; font-size: 0.68rem; font-weight: 600; padding: 0.3rem 0.15rem; border-radius: 6px; cursor: pointer;">Resolve</button>
        </div>
    </div>
    """

def render_footer():
    """
    Renders the official footer with disclaimer and live IST timestamp.
    """
    from config import get_system_timestamp
    ist_time = get_system_timestamp()

    st.html(f"""
    <div class="dashboard-footer">
        <div class="footer-brand">
            <span style="color:#10B981; font-size:1.1rem;">🌱</span>
            <b>VitalOptima</b> <span style="color:#94A3B8;">| AI-powered hospital resource optimization and decision support</span>
        </div>
        <div>
            <span class="footer-dot"></span> Last updated: {ist_time} (IST)
        </div>
    </div>
    """)


from ui.ai_summary_panel import render_floating_ai_assistant


def render_metric_card(title: str, value: str, subtext: str, card_type: str = "default", icon: str = "") -> None:
    """
    Renders an executive metric card with custom styling and accent badges.
    """
    border_color = "#E2E8F0"
    badge_bg = "#F8FAFC"
    badge_fg = "#475569"
    if card_type == "alert":
        border_color = "#FECACA"
        badge_bg = "#FEF2F2"
        badge_fg = "#EF4444"
    elif card_type == "warning":
        border_color = "#FED7AA"
        badge_bg = "#FFF7ED"
        badge_fg = "#F97316"
    elif card_type == "success":
        border_color = "#A7F3D0"
        badge_bg = "#ECFDF5"
        badge_fg = "#10B981"

    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid {border_color}; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
            <span style="font-size: 0.78rem; font-weight: 600; color: #64748B;">{title}</span>
            <span style="font-size: 1.1rem;">{icon}</span>
        </div>
        <div style="font-size: 1.35rem; font-weight: 800; color: #0F172A; margin-bottom: 0.25rem;">{value}</div>
        <div style="font-size: 0.75rem; color: #64748B;">{subtext}</div>
    </div>
    """, unsafe_allow_html=True)

