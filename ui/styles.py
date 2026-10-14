"""
VitalOptima UI Styling Engine
Provides responsive CSS tokens, modern typography, glassmorphism, and color palettes.
"""

def get_custom_css(theme: str = "Light Mode") -> str:
    """Return injectible CSS stylesheet for the Streamlit dashboard."""
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0F172A;
        -webkit-font-smoothing: antialiased;
    }

    /* Top navbar wrapper */
    .top-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1.25rem;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
    }

    .hospital-brand-group {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .hospital-logo-icon {
        font-size: 1.75rem;
        background: #EEF2FF;
        color: #1E60F2;
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        border: 1px solid #C7D2FE;
    }

    .hospital-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0;
        line-height: 1.2;
    }

    .hospital-subtitle {
        font-size: 0.8rem;
        font-weight: 500;
        color: #64748B;
        margin: 0;
    }

    .top-meta-group {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 0.35rem 0.75rem;
        background: #ECFDF5;
        color: #059669;
        border: 1px solid #A7F3D0;
        border-radius: 20px;
    }

    .clock-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 0.35rem 0.75rem;
        background: #F1F5F9;
        color: #334155;
        border: 1px solid #CBD5E1;
        border-radius: 20px;
    }

    .admin-chip {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0.8rem;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
    }

    .admin-avatar {
        width: 26px;
        height: 26px;
        background: #1E60F2;
        color: #FFFFFF;
        font-weight: 700;
        font-size: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
    }

    .admin-name {
        font-size: 0.8rem;
        font-weight: 600;
        color: #1E293B;
    }

    /* Custom KPI Metric Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.15rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.06);
    }

    .metric-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #1E60F2, #06B6D4);
    }

    .metric-card.alert-card::before {
        background: linear-gradient(90deg, #EF4444, #F97316);
    }

    .metric-card.warning-card::before {
        background: linear-gradient(90deg, #F59E0B, #EAB308);
    }

    .metric-card.success-card::before {
        background: linear-gradient(90deg, #10B981, #059669);
    }

    .metric-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.4rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .metric-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
        margin-bottom: 0.35rem;
    }

    .metric-subtext {
        font-size: 0.78rem;
        color: #64748B;
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }

    /* Brand sidebar header */
    .sidebar-brand {
        padding: 0.75rem 0.25rem 1.25rem 0.25rem;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }

    .brand-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0F172A;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        letter-spacing: -0.02em;
    }

    .brand-sub {
        font-size: 0.76rem;
        font-weight: 500;
        color: #64748B;
        margin-top: 0.15rem;
    }

    /* Section Cards */
    .section-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.35rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }

    .section-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.25rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .section-card-desc {
        font-size: 0.82rem;
        color: #64748B;
        margin-bottom: 1rem;
    }

    /* Footer */
    .vital-footer {
        margin-top: 3.5rem;
        padding: 1.5rem 0 1rem 0;
        border-top: 1px solid #E2E8F0;
        text-align: center;
        color: #94A3B8;
        font-size: 0.78rem;
    }

    /* Dataframe polish */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        overflow: hidden;
    }

    /* Button modernizing */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.45rem 1rem;
        transition: all 0.15s ease;
    }

    /* Streamlit tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.88rem;
    }
    </style>
    """
