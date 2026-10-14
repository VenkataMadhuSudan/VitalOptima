"""
VitalOptima Dashboard View
Executive Command Center: High-level KPI metrics, real-time census trends, unit health, and alerts.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp, DATA_DIR, ML_OUTPUTS_DIR
from ui.components import render_top_nav, render_footer, render_metric_card
from db.database import get_recent_activities, get_decision_logs
from db.postgres import load_census_dataset, load_department_resources_dataset

def show_dashboard():
    """Main executive command center view."""
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)

    # Header title
    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <h2 style="font-weight: 800; color: #0F172A; margin-bottom: 0.2rem; letter-spacing: -0.02em;">
            🏥 Clinical Operations Command Center
        </h2>
        <p style="color: #64748B; font-size: 0.92rem; margin: 0;">
            Real-time hospital census monitoring, departmental capacity utilization, and AI predictive alert telemetry.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Load Data
    daily_df = load_census_dataset()
    res_df = load_department_resources_dataset()

    # Fallback to local files if empty
    if daily_df.empty and (DATA_DIR / "hospital_daily_data.csv").exists():
        daily_df = pd.read_csv(DATA_DIR / "hospital_daily_data.csv")
    if res_df.empty and (DATA_DIR / "hospital_resources.csv").exists():
        res_df = pd.read_csv(DATA_DIR / "hospital_resources.csv")

    fc_df = pd.DataFrame()
    fc_path = ML_OUTPUTS_DIR / "forecast_next_days.csv"
    if fc_path.exists():
        try:
            fc_df = pd.read_csv(fc_path)
        except Exception:
            pass

    # 2. Key Metrics Computation
    total_beds = 330
    current_occ = 261
    gen_occ = 238
    icu_occ = 23
    today_arrivals = 178
    avg_arrivals = 175

    if not daily_df.empty:
        last_row = daily_df.iloc[-1]
        gen_occ = int(last_row.get("general_beds_occupied", 238))
        icu_occ = int(last_row.get("icu_beds_occupied", 23))
        total_gen = int(last_row.get("general_beds_total", 300))
        total_icu = int(last_row.get("icu_beds_total", 30))
        total_beds = total_gen + total_icu
        current_occ = gen_occ + icu_occ
        today_arrivals = int(last_row.get("emergency_arrivals", 178))
        if len(daily_df) >= 7:
            avg_arrivals = int(daily_df["emergency_arrivals"].tail(7).mean())

    occ_pct = round(100.0 * current_occ / total_beds, 1) if total_beds > 0 else 0.0
    icu_pct = round(100.0 * icu_occ / 30, 1)

    # 3. Top KPI Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card_type = "alert" if occ_pct >= 90 else ("warning" if occ_pct >= 80 else "default")
        render_metric_card(
            title="Total Bed Occupancy",
            value=f"{current_occ} / {total_beds}",
            subtext=f"<strong>{occ_pct}%</strong> capacity in service • Normal < 85%",
            card_type=card_type,
            icon="🛏️"
        )
    with c2:
        card_type = "warning" if icu_pct >= 85 else "default"
        render_metric_card(
            title="ICU / Critical Care",
            value=f"{icu_occ} / 30",
            subtext=f"<strong>{icu_pct}%</strong> occupied • 7 beds available",
            card_type=card_type,
            icon="🩺"
        )
    with c3:
        arr_delta = today_arrivals - avg_arrivals
        delta_str = f"+{arr_delta} vs 7d avg" if arr_delta >= 0 else f"{arr_delta} vs 7d avg"
        render_metric_card(
            title="Emergency Arrivals",
            value=f"{today_arrivals} pts",
            subtext=f"<strong>{delta_str}</strong> (avg: {avg_arrivals}/day)",
            card_type="default",
            icon="🚑"
        )
    with c4:
        render_metric_card(
            title="Active System Alerts",
            value="3 Active",
            subtext="1 Staff Shortage • 2 Demand Deficits",
            card_type="alert",
            icon="🚨"
        )

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # 4. Critical Warning Banners
    with st.expander("🚨 **Active Hospital Operational Alerts (Action Required)**", expanded=True):
        a1, a2, a3 = st.columns(3)
        with a1:
            st.error("""
            **🚨 Staffing Shortage (GB-MED)**
            * General Medicine is treating **95 patients** with only **91 staffed beds**.
            * Deficit: **4 patients** over nurse ratio limit.
            * *Recommendation:* Deploy float nurse team immediately.
            """)
        with a2:
            st.warning("""
            **⚠️ Capacity Bottleneck (ICU-SICU)**
            * Surgical ICU forecasted demand is **13 beds** vs **11 usable**.
            * Deficit: **2 critical beds**.
            * *Recommendation:* Step down stable post-op cases to surgical floor.
            """)
        with a3:
            st.info("""
            **📦 Inventory Stockout Alert (MSK-N95)**
            * N95 Respirators hit **0 closing stock** on Dec 31.
            * Reorder threshold: 37 units (Lead: 7 days).
            * *Recommendation:* Expedite supplier shipment PO #9842.
            """)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # 5. Charts Row: Trend Trajectory & Department Breakdown
    col_chart1, col_chart2 = st.columns([1.6, 1.4])

    with col_chart1:
        st.markdown("""
        <div class="section-card-title">📈 30-Day Census Trend & 7-Day Forecast Trajectory</div>
        <div class="section-card-desc">Historical daily bed occupancy with recursive forward projection & 90% risk barrier.</div>
        """, unsafe_allow_html=True)

        if not daily_df.empty:
            tail_df = daily_df.tail(30).copy()
            tail_df["date"] = pd.to_datetime(tail_df["date"])
            tail_df["total_occ"] = tail_df["general_beds_occupied"] + tail_df["icu_beds_occupied"]

            fig = go.Figure()
            # Historical line
            fig.add_trace(go.Scatter(
                x=tail_df["date"],
                y=tail_df["total_occ"],
                mode="lines+markers",
                name="Observed Inpatients",
                line=dict(color="#1E60F2", width=3),
                marker=dict(size=4)
            ))

            # Forward forecast projection
            if not fc_df.empty and "projected_total_occupied" in fc_df.columns:
                fc_df["date_dt"] = pd.to_datetime(fc_df["date"])
                # Connect last point of historical to first point of forecast
                connect_dates = [tail_df["date"].iloc[-1], fc_df["date_dt"].iloc[0]]
                connect_values = [tail_df["total_occ"].iloc[-1], fc_df["projected_total_occupied"].iloc[0]]
                fig.add_trace(go.Scatter(
                    x=connect_dates, y=connect_values,
                    mode="lines",
                    showlegend=False,
                    line=dict(color="#06B6D4", width=2, dash="dot")
                ))

                fig.add_trace(go.Scatter(
                    x=fc_df["date_dt"],
                    y=fc_df["projected_total_occupied"],
                    mode="lines+markers",
                    name="AI 7-Day Projection",
                    line=dict(color="#06B6D4", width=3, dash="dash"),
                    marker=dict(size=6, symbol="diamond")
                ))

            # 90% capacity threshold
            risk_line = 0.90 * total_beds
            fig.add_hline(
                y=risk_line,
                line_dash="dot",
                line_color="#EF4444",
                annotation_text=f"90% Risk Threshold ({int(risk_line)} Beds)",
                annotation_position="top left",
                annotation_font=dict(color="#EF4444", size=10)
            )

            fig.update_layout(
                height=340,
                margin=dict(l=20, r=20, t=25, b=25),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Total Inpatients")
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Loading census time-series data...")

    with col_chart2:
        st.markdown("""
        <div class="section-card-title">🛏️ Departmental Bed & Capacity Breakdown</div>
        <div class="section-card-desc">Current in-service beds, staffed thresholds, and patient census by department.</div>
        """, unsafe_allow_html=True)

        if not res_df.empty:
            beds_only = res_df[res_df["resource_type"].isin(["General Bed", "ICU Bed"])].copy()
            beds_only["usable"] = beds_only["total_capacity"] - beds_only["unavailable_capacity"]

            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                y=beds_only["department"],
                x=beds_only["occupied_capacity"],
                name="Occupied Beds",
                orientation='h',
                marker=dict(color='#1E60F2')
            ))
            fig_bar.add_trace(go.Bar(
                y=beds_only["department"],
                x=beds_only["available_capacity"],
                name="Available Beds",
                orientation='h',
                marker=dict(color='#A5B4FC')
            ))
            fig_bar.add_trace(go.Scatter(
                y=beds_only["department"],
                x=beds_only["staffed_capacity"],
                mode='markers',
                name='Staffed Capacity Limit',
                marker=dict(color='#EF4444', size=11, symbol='line-ns', line=dict(width=3, color='#EF4444'))
            ))

            fig_bar.update_layout(
                barmode='stack',
                height=340,
                margin=dict(l=10, r=10, t=25, b=25),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                xaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Beds"),
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig_bar, width="stretch")
        else:
            st.info("Department resources data not available.")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # 6. Bottom Row: Recent Activities & Quick Administrative Decisions
    col_act, col_dec = st.columns([1, 1])

    with col_act:
        st.markdown("""
        <div class="section-card-title">📋 Live Clinical Activity Stream</div>
        <div class="section-card-desc">Automated event auditing and algorithmic execution logs.</div>
        """, unsafe_allow_html=True)

        activities = get_recent_activities()
        if activities:
            for act in activities[:5]:
                color = act.get("color", "#3B82F6")
                st.markdown(f"""
                <div style="display: flex; gap: 0.75rem; align-items: flex-start; padding: 0.5rem 0; border-bottom: 1px solid #F1F5F9;">
                    <span style="font-weight: 700; font-size: 0.8rem; color: #64748B; width: 45px;">{act.get('time_str', '')}</span>
                    <div style="flex-grow: 1;">
                        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: {color}; margin-right: 4px;"></span>
                        <strong style="color: #0F172A; font-size: 0.85rem;">{act.get('title', '')}</strong>
                        <div style="color: #64748B; font-size: 0.78rem;">{act.get('details', '')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("No recent activities logged.")

    with col_dec:
        st.markdown("""
        <div class="section-card-title">⚖️ Recent Governance & Clinical Decisions</div>
        <div class="section-card-desc">Approved administrative actions and physician authorizations.</div>
        """, unsafe_allow_html=True)

        decisions = get_decision_logs()
        if decisions:
            for d in decisions[:3]:
                badge_bg = "#ECFDF5" if d.get("decision") == "Accepted" else "#FEF3C7"
                badge_col = "#059669" if d.get("decision") == "Accepted" else "#D97706"
                st.markdown(f"""
                <div style="padding: 0.65rem; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; margin-bottom: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;">
                        <span style="font-weight: 700; color: #1E293B; font-size: 0.82rem;">{d.get('category')}</span>
                        <span style="background: {badge_bg}; color: {badge_col}; font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 12px;">{d.get('decision')}</span>
                    </div>
                    <div style="color: #475569; font-size: 0.78rem;">{d.get('recommendation')}</div>
                    <div style="font-size: 0.7rem; color: #94A3B8; margin-top: 0.2rem;">{d.get('timestamp')} • Authorized by {d.get('administrator')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("No decisions recorded yet.")

    render_footer()
