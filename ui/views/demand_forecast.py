"""
VitalOptima Demand Forecasting View
Pixel-accurate recreation of Predictive Demand & Bed Occupancy Forecasting view in Light Mode.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ui.components import render_top_nav, render_footer
from config import HOSPITAL_NAME, ADMIN_INITIALS, ADMIN_USER, get_system_timestamp

def show_demand_forecast():
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), ADMIN_INITIALS, ADMIN_USER)
    # Title & Subtitle matching Light Mode
    st.markdown("""
    <div style="margin-bottom: 0.85rem; margin-top: -0.25rem;">
        <h2 style="font-weight: 800; font-size: 1.55rem; color: #0F172A; margin-bottom: 0.25rem;">
            <span style="display:inline-block; vertical-align:middle; margin-right: 0.4rem;">📈</span>Predictive Demand & Bed Occupancy Forecasting
        </h2>
        <p style="color: #64748B; font-size: 0.92rem; margin: 0; line-height: 1.4;">Machine learning regression models projecting departmental occupancy with 90% confidence uncertainty envelopes.</p>
    </div>
    """, unsafe_allow_html=True)

    # Controls Row: Select Department vs Forecast Horizon
    ctrl_col1, ctrl_col2 = st.columns([3, 1.2])

    with ctrl_col1:
        department_options = [
            "Emergency Department",
            "General Ward",
            "ICU",
            "Operating Room"
        ]
        selected_dept = st.selectbox(
            "Select Hospital Department:",
            options=department_options,
            index=0,
            key="df_dept_select"
        )

    with ctrl_col2:
        st.markdown('<div style="font-size:0.85rem; font-weight:600; color:#0F172A; margin-bottom:0.25rem;">Forecast Horizon (Hours):</div>', unsafe_allow_html=True)
        horizon = st.radio(
            "Forecast Horizon (Hours):",
            options=["24", "48", "72"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            key="df_horizon_radio"
        )

    # Department parameters dictionary
    dept_configs = {
        "Emergency Department": {
            "mae": "2.11 beds",
            "rmse": "2.93 beds",
            "peak_text": "47 / 45 beds",
            "peak_val": 47,
            "capacity": 45,
            "unit": "Beds",
            "peak_influx": "+8 hours",
            "y_range": [15, 55],
            "y_ticks": [20, 25, 30, 35, 40, 45, 50],
            # 65 hourly points from Oct 12 00:00 to Oct 14 16:00
            "hist_curve": [
                28, 25, 20, 18, 22, 25, 27, 25, 23, 19, 21, 23,
                38, 45, 43, 40, 37, 35, 36, 41, 44, 43, 41, 38,
                35, 40, 43, 45, 44, 42, 40, 43, 45, 44, 42, 41,
                43, 45, 44, 42, 38, 36, 40, 43, 45, 44, 42, 44,
                45, 44, 42, 40, 38, 38, 41, 43, 45, 44, 42, 44,
                45, 44, 44, 45, 45
            ]
        },
        "General Ward": {
            "mae": "5.84 beds",
            "rmse": "7.12 beds",
            "peak_text": "289 / 300 beds",
            "peak_val": 289,
            "capacity": 300,
            "unit": "Beds",
            "peak_influx": "+14 hours",
            "y_range": [180, 320],
            "y_ticks": [200, 225, 250, 275, 300],
            "hist_curve": [
                210, 212, 215, 218, 220, 222, 225, 228, 230, 232, 235, 238,
                240, 242, 245, 248, 250, 252, 255, 258, 260, 259, 255, 250,
                248, 246, 250, 255, 260, 265, 268, 269, 270, 268, 265, 262,
                260, 258, 262, 265, 270, 272, 275, 274, 272, 270, 268, 270,
                272, 275, 278, 280, 281, 282, 283, 284, 285, 284, 283, 282,
                283, 284, 284, 285, 285
            ]
        },
        "ICU": {
            "mae": "0.92 beds",
            "rmse": "1.34 beds",
            "peak_text": "28 / 30 beds",
            "peak_val": 28,
            "capacity": 30,
            "unit": "Beds",
            "peak_influx": "+10 hours",
            "y_range": [10, 35],
            "y_ticks": [15, 20, 25, 30],
            "hist_curve": [
                16, 17, 18, 19, 18, 19, 20, 21, 22, 23, 24, 23,
                22, 21, 22, 23, 24, 25, 24, 23, 22, 23, 24, 25,
                24, 23, 22, 21, 22, 23, 24, 25, 25, 24, 23, 24,
                25, 26, 25, 24, 23, 24, 25, 25, 26, 26, 25, 25,
                24, 23, 22, 21, 22, 23, 24, 25, 25, 24, 23, 24,
                25, 25, 26, 26, 26
            ]
        },
        "Operating Room": {
            "mae": "0.65 suites",
            "rmse": "0.89 suites",
            "peak_text": "10 / 12 suites",
            "peak_val": 10,
            "capacity": 12,
            "unit": "Suites",
            "peak_influx": "+6 hours",
            "y_range": [0, 14],
            "y_ticks": [2, 4, 6, 8, 10, 12],
            "hist_curve": [
                4, 3, 2, 2, 3, 5, 7, 8, 9, 8, 7, 6,
                5, 4, 3, 2, 2, 4, 6, 8, 9, 9, 8, 7,
                6, 5, 4, 3, 2, 4, 6, 8, 9, 8, 7, 6,
                5, 4, 3, 2, 3, 5, 7, 8, 9, 8, 8, 8,
                4, 3, 2, 2, 3, 5, 7, 8, 9, 8, 7, 6,
                7, 8, 8, 8, 8
            ]
        }
    }

    cfg = dept_configs[selected_dept]

    # 4 Metric Cards in a row - High Contrast Light Mode
    st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; min-height: 92px; padding: 0.75rem 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size: 0.78rem; font-weight: 600; color: #64748B;">Model Backtest MAE</div>
            <div style="font-size: 1.85rem; font-weight: 800; color: #0F172A; margin: 0.15rem 0;">
                {cfg['mae']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; min-height: 92px; padding: 0.75rem 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size: 0.78rem; font-weight: 600; color: #64748B;">Model RMSE</div>
            <div style="font-size: 1.85rem; font-weight: 800; color: #0F172A; margin: 0.15rem 0;">
                {cfg['rmse']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        exceeds = cfg['peak_val'] > cfg['capacity']
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; min-height: 92px; padding: 0.75rem 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size: 0.78rem; font-weight: 600; color: #64748B;">Peak Predicted Occupancy</div>
            <div style="font-size: 1.85rem; font-weight: 800; color: {'#DC2626' if exceeds else '#0F172A'}; margin: 0.15rem 0;">
                {cfg['peak_text']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; min-height: 92px; padding: 0.75rem 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size: 0.78rem; font-weight: 600; color: #64748B;">Peak Influx In</div>
            <div style="font-size: 1.85rem; font-weight: 800; color: #0F172A; margin: 0.15rem 0;">
                {cfg['peak_influx']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Timeline Chart Generation
    h_hours = int(horizon)
    hist_start = pd.Timestamp("2026-10-12 00:00")
    now_ts = pd.Timestamp("2026-10-14 16:00")
    
    hist_timeline = pd.date_range(start=hist_start, end=now_ts, freq="1h")
    future_timeline = pd.date_range(start=now_ts, periods=h_hours + 1, freq="1h")
    full_timeline = pd.date_range(start=hist_start, periods=len(hist_timeline) + h_hours, freq="1h")

    # Future forecast curve
    last_hist_val = cfg["hist_curve"][-1]
    peak_val = cfg["peak_val"]
    
    t_steps = len(future_timeline)
    peak_step = min(8, t_steps - 1)
    
    future_vals = []
    for step in range(t_steps):
        if step <= peak_step:
            val = last_hist_val + (peak_val - last_hist_val) * (step / max(1, peak_step))
        else:
            val = peak_val - (peak_val - last_hist_val * 0.95) * ((step - peak_step) / max(1, (t_steps - peak_step))) * 0.35
        future_vals.append(round(val, 1))

    # Confidence interval (90% prediction envelope)
    uncertainty_margin = 3.8 if "Emergency" in selected_dept else 8.0 if "General" in selected_dept else 1.8
    upper_envelope = [v + uncertainty_margin * (1.0 + 0.35 * (i / t_steps)) for i, v in enumerate(future_vals)]
    lower_envelope = [max(0, v - uncertainty_margin * (1.0 + 0.35 * (i / t_steps))) for i, v in enumerate(future_vals)]

    # Format timestamps for X-axis display
    hist_str = [ts.strftime("%Y-%m-%d %H:%M") for ts in hist_timeline]
    future_str = [ts.strftime("%Y-%m-%d %H:%M") for ts in future_timeline]
    full_str = [ts.strftime("%Y-%m-%d %H:%M") for ts in full_timeline]

    fig = go.Figure()

    # 1. Shaded 90% Prediction Interval
    fig.add_trace(go.Scatter(
        x=future_str,
        y=upper_envelope,
        mode="lines",
        line=dict(width=0),
        hoverinfo="none",
        showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=future_str,
        y=lower_envelope,
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(37, 99, 235, 0.18)",
        name="90% Prediction Interval",
        hoverinfo="none"
    ))

    # 2. Observed History (Grey solid line)
    fig.add_trace(go.Scatter(
        x=hist_str,
        y=cfg["hist_curve"][:len(hist_str)],
        mode="lines",
        name="Observed History",
        line=dict(color="#64748B", width=2),
        hoverinfo="x+y"
    ))

    # 3. Forecasted Occupancy (Bright blue solid line)
    fig.add_trace(go.Scatter(
        x=future_str,
        y=future_vals,
        mode="lines",
        name="Forecasted Occupancy",
        line=dict(color="#1E60F2", width=2.5),
        hoverinfo="x+y"
    ))

    # 4. Total Capacity Horizontal Red Dashed Line
    cap_line = [cfg["capacity"]] * len(full_str)
    fig.add_trace(go.Scatter(
        x=full_str,
        y=cap_line,
        mode="lines",
        name=f"Total Capacity ({cfg['capacity']} {cfg['unit']})",
        line=dict(color="#EF4444", width=2, dash="dash"),
        showlegend=False,
        hoverinfo="skip"
    ))

    # Label annotation on capacity line
    ann_idx = min(len(future_str) - 2, 8)
    fig.add_annotation(
        x=future_str[ann_idx],
        y=cfg["capacity"],
        text=f"Total Capacity ({cfg['capacity']} {cfg['unit']})",
        showarrow=False,
        yshift=12,
        font=dict(size=9.5, color="#DC2626", family="Plus Jakarta Sans, sans-serif"),
        bgcolor="#FFFFFF",
        bordercolor="#FECACA",
        borderwidth=1,
        borderpad=3
    )

    # Ticks matching Image 3: 00:00 / Oct 12, 2026, 12:00, 00:00 / Oct 13, 2026, etc.
    tick_indices = [
        0, 12, 24, 36, 48, 60, min(len(full_str) - 1, 72), min(len(full_str) - 1, 84)
    ]
    tick_indices = sorted(list(set([i for i in tick_indices if i < len(full_str)])))
    tick_vals = [full_str[i] for i in tick_indices]
    tick_text = []
    for i in tick_indices:
        ts = full_timeline[i]
        if ts.hour == 0:
            tick_text.append(f"00:00<br>{ts.strftime('%b %d, %Y')}")
        else:
            tick_text.append("12:00")

    fig.update_layout(
        margin=dict(l=40, r=20, t=15, b=35),
        height=330,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="right",
            x=0.98,
            font=dict(size=10, color="#334155")
        ),
        xaxis=dict(
            title=dict(text="Timeline", font=dict(size=11, color="#334155")),
            showgrid=True,
            gridcolor="#F1F5F9",
            tickmode="array",
            tickvals=tick_vals,
            ticktext=tick_text,
            tickfont=dict(size=9.5, color="#475569"),
            zeroline=False
        ),
        yaxis=dict(
            title=dict(text="Occupied Beds", font=dict(size=11, color="#334155")),
            showgrid=True,
            gridcolor="#F1F5F9",
            range=cfg["y_range"],
            tickvals=cfg["y_ticks"],
            tickfont=dict(size=10, color="#475569"),
            zeroline=False
        ),
        hovermode="x unified"
    )

    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    render_footer()
