"""
VitalOptima Custom CSS Stylesheet
Recreates the hospital operations command center aesthetics:
dark navy sidebar, glassmorphic metric cards, responsive grid, and custom widgets.
"""

def get_custom_css(theme="Light Mode"):
    is_dark = (theme == "Dark Mode")
    body_bg = "#070F1E" if is_dark else "#F8FAFC"
    panel_bg = "#0D192E" if is_dark else "#FFFFFF"
    border_color = "#1E2D4A" if is_dark else "#E2E8F0"
    text_primary = "#F8FAFC" if is_dark else "#0F172A"
    text_secondary = "#94A3B8" if is_dark else "#64748B"
    card_sub_bg = "#13233D" if is_dark else "#F1F5F9"
    
    css = """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Global resets & typography */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: VAR_BODY_BG !important;
        color: VAR_TEXT_PRIMARY !important;
    }

    /* Global container text */
    [data-testid="stMainBlockContainer"] p,
    [data-testid="stMainBlockContainer"] span,
    [data-testid="stMainBlockContainer"] label,
    [data-testid="stMainBlockContainer"] div,
    [data-testid="stMainBlockContainer"] h1,
    [data-testid="stMainBlockContainer"] h2,
    [data-testid="stMainBlockContainer"] h3,
    [data-testid="stMainBlockContainer"] h4,
    [data-testid="stMainBlockContainer"] h5,
    [data-testid="stMainBlockContainer"] h6,
    [data-testid="stMainBlockContainer"] td,
    [data-testid="stMainBlockContainer"] th,
    [data-testid="stMainBlockContainer"] li {
        color: VAR_TEXT_PRIMARY;
    }
    /* Form controls, inputs, text areas, number inputs, selects */
    input, textarea, select,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] div,
    [data-baseweb="select"] div,
    div[role="listbox"],
    div[role="listbox"] div,
    div[role="option"] {
        color: VAR_TEXT_PRIMARY !important;
        -webkit-text-fill-color: VAR_TEXT_PRIMARY !important;
        background-color: VAR_PANEL_BG !important;
        border-color: VAR_BORDER_COLOR !important;
    }

    input::placeholder, textarea::placeholder {
        color: VAR_TEXT_SECONDARY !important;
        -webkit-text-fill-color: VAR_TEXT_SECONDARY !important;
    }

    /* Tables & Dataframes */
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    .stTable,
    table {
        color: #0F172A !important;
        background-color: #FFFFFF !important;
    }
    table th {
        color: #334155 !important;
        background-color: #F8FAFC !important;
        font-weight: 700 !important;
    }
    table td {
        color: #0F172A !important;
    }

    .kpi-card-mockup {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
    }

    /* Sliders - Vibrant Cyan Accent */
    [data-testid="stSlider"] div,
    [data-baseweb="slider"] div {
        color: VAR_TEXT_PRIMARY !important;
    }
    div[data-testid="stSlider"] div[role="slider"] {
        background-color: #00D2B4 !important;
        border-color: #00D2B4 !important;
        box-shadow: 0 0 10px rgba(0, 210, 180, 0.8) !important;
    }
    div[data-testid="stSlider"] div[class*="StyledTrack"] > div {
        background-color: #00D2B4 !important;
    }
    div[data-testid="stSlider"] div[class*="StyledTrack"] {
        background-color: #1E2D4A !important;
    }

    /* Captions */
    [data-testid="stCaptionContainer"] p,
    .stCaption {
        color: VAR_TEXT_SECONDARY !important;
    }

    /* Metrics */
    [data-testid="stMetricValue"] div {
        color: VAR_TEXT_PRIMARY !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] p {
        color: VAR_TEXT_SECONDARY !important;
        font-weight: 600 !important;
    }

    /* Main background */
    .stApp {
        background-color: VAR_BODY_BG !important;
    }

    /* Transparent Streamlit Header */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Proper compact padding matching command center screenshots */
    .block-container {
        padding-top: 1.0rem !important;
        padding-bottom: 1.25rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }

    /* Streamlit Sidebar custom styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #071426 0%, #0A192F 100%) !important;
        border-right: 1px solid #1E293B;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
    [data-testid="stSidebar"] label span {
        color: #94A3B8 !important;
    }

    [data-testid="stSidebar"] .brand-title,
    [data-testid="stSidebar"] .brand-title * {
        color: #FFFFFF !important;
    }

    /* Sidebar Radio Navigation Pill styling */
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {
        gap: 0.35rem !important;
        display: flex !important;
        flex-direction: column !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: transparent !important;
        padding: 0.65rem 1rem !important;
        border-radius: 10px !important;
        margin: 0 !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        border: 1px solid transparent !important;
        display: flex !important;
        align-items: center !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(30, 41, 59, 0.6) !important;
    }

    /* Hide radio group header */
    [data-testid="stSidebar"] [data-testid="stRadio"] > label {
        display: none !important;
    }

    /* Hide the radio circle button and marks completely */
    [data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child,
    [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child,
    [data-testid="stSidebar"] [data-testid="stRadio"] label div[class*="ex0avrt0"],
    [data-testid="stSidebar"] [data-testid="stRadio"] label div[class*="ex0avrt1"],
    [data-testid="stSidebar"] [data-testid="stRadio"] label div[class*="ex0avrt2"] {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 0 !important;
        visibility: hidden !important;
    }

    /* Inactive Radio text styling */
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {
        color: #94A3B8 !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        margin: 0 !important;
    }

    /* Active selected radio item - vibrant blue pill */
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked),
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[aria-checked="true"]) {
        background: #1E60F2 !important;
        box-shadow: 0 4px 14px rgba(30, 96, 242, 0.45) !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p,
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input[aria-checked="true"]) p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Before vs After Optimization styling */
    .before-card {
        background: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        padding: 0.85rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .after-card {
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        border-radius: 10px;
        padding: 0.85rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    /* Mockup-Accurate Compact KPI Cards */
    .kpi-card-mockup {
        background: VAR_PANEL_BG !important;
        border-radius: 12px !important;
        padding: 0.95rem 1.1rem !important;
        border: 1px solid VAR_BORDER_COLOR !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        height: 100% !important;
        box-sizing: border-box !important;
    }

    .kpi-mockup-top {
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }

    .kpi-mockup-icon {
        width: 30px;
        height: 30px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.05rem;
    }

    .kpi-mockup-title {
        font-weight: 700;
        font-size: 0.88rem;
        color: #0F172A;
    }

    .kpi-mockup-num {
        font-size: 1.55rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
        margin-top: 0.4rem;
    }

    .kpi-mockup-denom {
        font-size: 0.95rem;
        font-weight: 600;
        color: #64748B;
    }

    .kpi-mockup-label {
        font-size: 0.72rem;
        color: #64748B;
        font-weight: 500;
        margin-top: 0.1rem;
    }

    .kpi-mockup-progress-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-top: 0.5rem;
    }

    .kpi-mockup-track {
        flex: 1;
        height: 6px;
        background: #F1F5F9;
        border-radius: 3px;
        overflow: hidden;
    }

    .kpi-mockup-fill {
        height: 100%;
        border-radius: 3px;
    }

    .kpi-mockup-pct {
        font-size: 0.74rem;
        font-weight: 700;
        color: #475569;
        min-width: 28px;
        text-align: right;
    }

    .kpi-mockup-footer {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.74rem;
        color: #64748B;
        margin-top: 0.4rem;
        font-weight: 500;
    }

    .kpi-mockup-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
    }

    /* Clean Compact Welcome Header */
    .header-mockup {
        margin-bottom: 1.15rem;
    }

    .header-mockup h1 {
        font-size: 1.7rem;
        font-weight: 800;
        color: #0F172A;
        margin: 0 0 0.2rem 0;
        letter-spacing: -0.02em;
    }

    .header-mockup p {
        color: #64748B;
        font-size: 0.88rem;
        margin: 0;
    }

    .opt-tag-before {
        font-size: 0.75rem;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .opt-tag-after {
        font-size: 0.75rem;
        font-weight: 700;
        color: #10B981;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .opt-num-large {
        font-size: 1.65rem;
        font-weight: 800;
        color: #0F172A !important;
        margin: 0.2rem 0;
    }

    .opt-subtext {
        font-size: 0.75rem;
        color: #64748B !important;
    }

    .opt-progress-track {
        width: 100%;
        height: 7px;
        background: #E2E8F0;
        border-radius: 4px;
        overflow: hidden;
        margin-top: 0.35rem;
    }

    .opt-progress-fill-blue {
        height: 100%;
        width: 72%;
        background: #3B82F6;
        border-radius: 4px;
    }

    .opt-progress-fill-green {
        height: 100%;
        width: 86%;
        background: #10B981;
        border-radius: 4px;
    }

    /* Custom Top Navigation Bar */
    .top-nav-bar {
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: center !important;
        background: VAR_PANEL_BG !important;
        padding: 0.75rem 1.25rem !important;
        border-radius: 12px !important;
        border: 1px solid VAR_BORDER_COLOR !important;
        margin-bottom: 1.25rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
        width: 100% !important;
    }
    
    .nav-left-group {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 1.25rem !important;
    }

    .hospital-badge {
        display: inline-flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
        font-weight: 700 !important;
        color: VAR_TEXT_PRIMARY !important;
        font-size: 0.95rem !important;
        background: VAR_CARD_SUB_BG !important;
        padding: 0.4rem 0.85rem !important;
        border-radius: 8px !important;
        border: 1px solid VAR_BORDER_COLOR !important;
    }

    .nav-time-display {
        font-size: 0.85rem !important;
        color: VAR_TEXT_SECONDARY !important;
        font-weight: 500 !important;
    }

    .nav-right-group {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 1rem !important;
    }

    .search-mock {
        background: VAR_CARD_SUB_BG !important;
        border: 1px solid VAR_BORDER_COLOR !important;
        border-radius: 8px !important;
        padding: 0.4rem 1rem !important;
        color: VAR_TEXT_SECONDARY !important;
        font-size: 0.85rem !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
        width: 320px !important;
    }

    .demo-pill, .live-pill {
        background: rgba(16, 185, 129, 0.12) !important;
        color: #10B981 !important;
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        padding: 0.3rem 0.75rem !important;
        border-radius: 20px !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 0.35rem !important;
    }

    .user-pill {
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        color: VAR_TEXT_PRIMARY !important;
    }

    .user-avatar {
        background: #6366F1 !important;
        color: white !important;
        border-radius: 50% !important;
        width: 30px !important;
        height: 30px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-weight: 700 !important;
        font-size: 0.8rem !important;
    }

    /* Welcome Header Banner with Hospital Image on Right */
    .welcome-banner {
        background: VAR_PANEL_BG !important;
        border-radius: 14px !important;
        padding: 1.25rem 1.75rem !important;
        border: 1px solid VAR_BORDER_COLOR !important;
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin-bottom: 1.25rem !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03) !important;
        position: relative !important;
        overflow: hidden !important;
        width: 100% !important;
    }

    .welcome-content h4 {
        color: #3B82F6 !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin: 0 0 0.25rem 0 !important;
    }

    .welcome-content h1 {
        font-size: 1.85rem !important;
        font-weight: 800 !important;
        color: VAR_TEXT_PRIMARY !important;
        margin: 0 0 0.25rem 0 !important;
        letter-spacing: -0.02em !important;
    }

    .welcome-content p {
        color: VAR_TEXT_SECONDARY !important;
        font-size: 0.92rem !important;
        margin: 0 !important;
    }

    .hospital-image-container {
        width: 340px !important;
        height: 110px !important;
        border-radius: 10px !important;
        overflow: hidden !important;
        border: 1px solid VAR_BORDER_COLOR !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        flex-shrink: 0 !important;
    }

    .hospital-image-container img {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important;
        display: block !important;
    }

    /* KPI Metric Cards Grid */
    .kpi-card {
        background: #FFFFFF;
        border-radius: 14px;
        padding: 1.25rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.04);
    }

    .kpi-header {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        margin-bottom: 0.5rem;
    }

    .kpi-icon-box {
        width: 38px;
        height: 38px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
    }

    .kpi-title {
        font-weight: 700;
        color: #0F172A;
        font-size: 0.95rem;
    }

    .kpi-subtitle {
        font-size: 0.75rem;
        color: #64748B;
    }

    .kpi-total {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0F172A;
    }

    .kpi-body {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
    }

    .kpi-stat-col {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .kpi-stat-item {
        font-size: 0.8rem;
        color: #64748B;
    }

    .stat-val-red {
        font-weight: 800;
        color: #EF4444;
        font-size: 1.25rem;
    }

    .stat-val-green {
        font-weight: 800;
        color: #10B981;
        font-size: 1.25rem;
    }

    .stat-val-dark {
        font-weight: 700;
        color: #1E293B;
        font-size: 0.95rem;
    }

    .kpi-footer-trend {
        font-size: 0.75rem;
        color: #64748B;
        display: flex;
        align-items: center;
        gap: 0.25rem;
        border-top: 1px solid #F1F5F9;
        padding-top: 0.5rem;
        margin-top: auto;
    }

    /* Content Cards (Charts, Tables, Lists) */
    .dashboard-panel {
        background: VAR_PANEL_BG !important;
        border-radius: 12px !important;
        padding: 0.85rem 1rem !important;
        border: 1px solid VAR_BORDER_COLOR !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        margin-bottom: 0.65rem !important;
        box-sizing: border-box !important;
    }

    .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.5rem;
    }

    .panel-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0F172A;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    .panel-subtitle {
        font-size: 0.74rem;
        color: #64748B;
        margin-top: 0.1rem;
    }

    .panel-badge {
        background: #EFF6FF;
        color: #1D4ED8;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        border: 1px solid #DBEAFE;
    }

    /* Department Status Table */
    .dept-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.78rem;
    }

    .dept-table th {
        text-align: left;
        padding: 0.35rem 0.25rem;
        color: #64748B;
        font-weight: 700;
        font-size: 0.72rem;
        border-bottom: 1px solid #E2E8F0;
        white-space: nowrap;
    }

    .dept-table td {
        padding: 0.4rem 0.25rem;
        border-bottom: 1px solid #F1F5F9;
        color: #1E293B;
        font-weight: 500;
        font-size: 0.78rem;
        white-space: nowrap;
    }

    .occ-cell {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
    }

    .occ-bar-pill {
        width: 32px;
        height: 7px;
        border-radius: 4px;
        display: inline-block;
        flex-shrink: 0;
    }

    /* Alerts Drawer */
    .alert-section-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #0F172A;
        display: flex;
        align-items: center;
        gap: 0.4rem;
        margin-top: 0.5rem;
        margin-bottom: 0.25rem;
    }

    .alert-section-sub {
        font-size: 0.75rem;
        color: #64748B;
        margin-bottom: 0.75rem;
    }

    .alert-item {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 0.6rem 0.25rem;
        border-bottom: 1px solid #F8FAFC;
    }

    .alert-left {
        display: flex;
        gap: 0.65rem;
        align-items: flex-start;
    }

    .alert-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-top: 5px;
        flex-shrink: 0;
    }

    .alert-content {
        display: flex;
        flex-direction: column;
    }

    .alert-heading {
        font-size: 0.82rem;
        font-weight: 700;
        color: #1E293B;
    }

    .alert-desc {
        font-size: 0.75rem;
        color: #64748B;
    }

    .alert-right {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .alert-time {
        font-size: 0.75rem;
        color: #94A3B8;
    }

    .severity-badge {
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
    }

    .badge-high {
        background: #FEE2E2;
        color: #DC2626;
        border: 1px solid #FECACA;
    }

    .badge-medium {
        background: #FEF3C7;
        color: #D97706;
        border: 1px solid #FDE68A;
    }

    .badge-low {
        background: #F0FDF4;
        color: #16A34A;
        border: 1px solid #DCFCE7;
    }

    /* Timeline Widget */
    .timeline-container {
        display: flex;
        flex-direction: column;
        gap: 0.9rem;
        position: relative;
        padding-left: 0.5rem;
    }

    .timeline-item {
        display: flex;
        align-items: flex-start;
        gap: 0.85rem;
        position: relative;
    }

    .timeline-time {
        font-size: 0.8rem;
        font-weight: 700;
        color: #475569;
        min-width: 45px;
    }

    .timeline-bullet {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-top: 4px;
        flex-shrink: 0;
    }

    .timeline-body {
        display: flex;
        flex-direction: column;
    }

    .timeline-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #0F172A;
    }

    .timeline-detail {
        font-size: 0.78rem;
        color: #64748B;
    }

    /* Quick Action Buttons Grid */
    .quick-actions-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.85rem;
    }

    .action-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1rem 0.75rem;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.4rem;
        cursor: pointer;
        transition: all 0.15s ease;
    }

    .action-card:hover {
        border-color: #2563EB;
        background: #EFF6FF;
        transform: translateY(-2px);
    }

    .action-icon {
        font-size: 1.5rem;
    }

    .action-label {
        font-size: 0.85rem;
        font-weight: 700;
        color: #1E293B;
    }

    /* Sidebar Logo & Badge */
    .sidebar-brand {
        padding: 0.75rem 0.5rem 1.5rem 0.5rem;
    }

    .brand-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        letter-spacing: -0.02em;
    }

    .brand-sub {
        font-size: 0.72rem;
        color: #94A3B8;
        margin-top: 0.2rem;
    }

    .sidebar-demo-card, .sidebar-live-card {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 0.85rem;
        margin-top: 1.5rem;
    }

    .sidebar-demo-title, .sidebar-live-title {
        font-size: 0.75rem;
        font-weight: 700;
        color: #34D399;
        display: flex;
        align-items: center;
        gap: 0.35rem;
        margin-bottom: 0.25rem;
    }

    .sidebar-demo-text, .sidebar-live-text {
        font-size: 0.72rem;
        color: #94A3B8;
        line-height: 1.4;
    }

    /* Footer styling */
    .dashboard-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.25rem 0.5rem 0.5rem 0.5rem;
        border-top: 1px solid #E2E8F0;
        margin-top: 1.5rem;
        font-size: 0.8rem;
        color: #64748B;
    }

    .footer-brand {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 600;
    }

    .footer-dot {
        width: 8px;
        height: 8px;
        background: #10B981;
        border-radius: 50%;
        display: inline-block;
    }

    /* Streamlit Button Overrides */
    div.stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    /* Unified Container Panels matching Dashboard Grid */
    div[class*="st-key-panel_"] > div {
        background: VAR_PANEL_BG !important;
        border-radius: 12px !important;
        padding: 0.75rem 0.95rem !important;
        border: 1px solid VAR_BORDER_COLOR !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        box-sizing: border-box !important;
    }
    div[class*="st-key-panel_"] {
        margin-bottom: 0.65rem !important;
    }

    /* Responsive Design System across Desktop, Laptop, Tablet, Mobile */
    @media (max-width: 1280px) {
        .block-container {
            padding-left: 1.0rem !important;
            padding-right: 1.0rem !important;
        }
        .kpi-card-mockup {
            padding: 0.75rem 0.85rem !important;
        }
        .kpi-mockup-num {
            font-size: 1.35rem !important;
        }
    }

    @media (max-width: 1024px) {
        .welcome-header-img {
            width: 160px !important;
            height: 58px !important;
        }
        .top-nav-search {
            width: 180px !important;
            font-size: 0.75rem !important;
        }
    }

    @media (max-width: 860px) {
        .welcome-header-img {
            display: none !important;
        }
        .top-nav-search {
            display: none !important;
        }
    }

    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.65rem !important;
            padding-left: 0.65rem !important;
            padding-right: 0.65rem !important;
        }
        .top-nav-container {
            flex-direction: column !important;
            gap: 0.5rem !important;
            align-items: flex-start !important;
            padding: 0.65rem 0.85rem !important;
        }
        .welcome-header-container {
            flex-direction: column !important;
            padding: 0.75rem 0.95rem !important;
        }
        .kpi-card-mockup {
            margin-bottom: 0.5rem !important;
            min-height: auto !important;
        }
        .dashboard-footer {
            flex-direction: column !important;
            gap: 0.5rem !important;
            text-align: center !important;
        }
    }

    /* =========================================================================
       Dashboard Component Panels & Interactive Action Cards
       ========================================================================= */
    div[class*="st-key-panel_active_alerts"] > div,
    div[class*="st-key-panel_ai_recommendation"] > div,
    div[class*="st-key-panel_whatif_simulator"] > div {
        background: #FFFFFF !important;
        border-radius: 12px !important;
        padding: 0.75rem 0.95rem !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        gap: 0.3rem !important;
    }

    div[class*="st-key-panel_active_alerts"],
    div[class*="st-key-panel_ai_recommendation"],
    div[class*="st-key-panel_whatif_simulator"] {
        margin-bottom: 0.55rem !important;
    }

    div[class*="st-key-btn_view_all_alerts_link"] button,
    div[data-testid*="btn_view_all_alerts_link"] button,
    div[class*="st-key-btn_view_rec_details_link"] button,
    div[data-testid*="btn_view_rec_details_link"] button,
    div[class*="st-key-btn_run_sim_trigger_link"] button,
    div[data-testid*="btn_run_sim_trigger_link"] button {
        background: transparent !important;
        border: none !important;
        color: #2563EB !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
        height: auto !important;
        min-height: auto !important;
        text-align: right !important;
        float: right !important;
        white-space: nowrap !important;
    }

    div[class*="st-key-btn_view_all_alerts_link"] button:hover,
    div[data-testid*="btn_view_all_alerts_link"] button:hover,
    div[class*="st-key-btn_view_rec_details_link"] button:hover,
    div[data-testid*="btn_view_rec_details_link"] button:hover,
    div[class*="st-key-btn_run_sim_trigger_link"] button:hover,
    div[data-testid*="btn_run_sim_trigger_link"] button:hover {
        color: #1D4ED8 !important;
        text-decoration: underline !important;
        background: transparent !important;
    }

    div[class*="st-key-btn_rec_act_"] button,
    div[data-testid*="btn_rec_act_"] button {
        padding: 0.2rem 2px !important;
        min-height: 28px !important;
        height: 28px !important;
        border-radius: 6px !important;
        width: 100% !important;
    }

    div[class*="st-key-btn_rec_act_"] button div,
    div[data-testid*="btn_rec_act_"] button div,
    div[class*="st-key-btn_rec_act_"] button p,
    div[data-testid*="btn_rec_act_"] button p {
        font-size: 0.65rem !important;
        font-weight: 600 !important;
        line-height: 1 !important;
        margin: 0 !important;
        letter-spacing: -0.2px !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }

    div[class*="st-key-btn_rec_act_ack"] button,
    div[data-testid*="btn_rec_act_ack"] button {
        border: 1px solid #CBD5E1 !important;
        background: #FFFFFF !important;
    }
    div[class*="st-key-btn_rec_act_ack"] button p,
    div[data-testid*="btn_rec_act_ack"] button p {
        color: #334155 !important;
    }
    div[class*="st-key-btn_rec_act_ack"] button:hover,
    div[data-testid*="btn_rec_act_ack"] button:hover {
        border-color: #94A3B8 !important;
        background: #F1F5F9 !important;
    }

    div[class*="st-key-btn_rec_act_assign"] button,
    div[data-testid*="btn_rec_act_assign"] button {
        border: 1px solid #93C5FD !important;
        background: #EFF6FF !important;
    }
    div[class*="st-key-btn_rec_act_assign"] button p,
    div[data-testid*="btn_rec_act_assign"] button p {
        color: #1D4ED8 !important;
    }
    div[class*="st-key-btn_rec_act_assign"] button:hover,
    div[data-testid*="btn_rec_act_assign"] button:hover {
        border-color: #3B82F6 !important;
        background: #DBEAFE !important;
    }

    div[class*="st-key-btn_rec_act_approve"] button,
    div[data-testid*="btn_rec_act_approve"] button {
        border: none !important;
        background: #10B981 !important;
    }
    div[class*="st-key-btn_rec_act_approve"] button p,
    div[data-testid*="btn_rec_act_approve"] button p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    div[class*="st-key-btn_rec_act_approve"] button:hover,
    div[data-testid*="btn_rec_act_approve"] button:hover {
        background: #059669 !important;
    }

    div[class*="st-key-btn_rec_act_resolve"] button,
    div[data-testid*="btn_rec_act_resolve"] button {
        border: 1px solid #CBD5E1 !important;
        background: #FFFFFF !important;
    }
    div[class*="st-key-btn_rec_act_resolve"] button p,
    div[data-testid*="btn_rec_act_resolve"] button p {
        color: #475569 !important;
    }
    div[class*="st-key-btn_rec_act_resolve"] button:hover,
    div[data-testid*="btn_rec_act_resolve"] button:hover {
        border-color: #94A3B8 !important;
        background: #F1F5F9 !important;
    }

    div[class*="st-key-sim_trigger_card_"] button,
    div[data-testid*="sim_trigger_card_"] button {
        border-radius: 8px !important;
        padding: 0.5rem 0.75rem !important;
        text-align: left !important;
        width: 100% !important;
        white-space: pre-line !important;
        line-height: 1.35 !important;
        margin-bottom: 0.35rem !important;
        box-shadow: none !important;
    }
    div[class*="st-key-sim_trigger_card_ed"] button,
    div[data-testid*="sim_trigger_card_ed"] button {
        background: #FEF2F2 !important;
        border: 1px solid #FEE2E2 !important;
        color: #DC2626 !important;
    }
    div[class*="st-key-sim_trigger_card_ed"] button:hover,
    div[data-testid*="sim_trigger_card_ed"] button:hover {
        border-color: #FCA5A5 !important;
        background: #FEE2E2 !important;
    }
    div[class*="st-key-sim_trigger_card_icu"] button,
    div[data-testid*="sim_trigger_card_icu"] button {
        background: #FFFBEB !important;
        border: 1px solid #FEF3C7 !important;
        color: #D97706 !important;
    }
    div[class*="st-key-sim_trigger_card_icu"] button:hover,
    div[data-testid*="sim_trigger_card_icu"] button:hover {
        border-color: #FCD34D !important;
        background: #FEF3C7 !important;
    }
    div[class*="st-key-sim_trigger_card_staff"] button,
    div[data-testid*="sim_trigger_card_staff"] button {
        background: #F5F3FF !important;
        border: 1px solid #EDE9FE !important;
        color: #7C3AED !important;
    }
    div[class*="st-key-sim_trigger_card_staff"] button:hover,
    div[data-testid*="sim_trigger_card_staff"] button:hover {
        border-color: #C4B5FD !important;
        background: #EDE9FE !important;
    }
    </style>
    """
    css = css.replace("VAR_BODY_BG", body_bg)
    css = css.replace("VAR_PANEL_BG", panel_bg)
    css = css.replace("VAR_BORDER_COLOR", border_color)
    css = css.replace("VAR_TEXT_PRIMARY", text_primary)
    css = css.replace("VAR_TEXT_SECONDARY", text_secondary)
    css = css.replace("VAR_CARD_SUB_BG", card_sub_bg)
    return css
