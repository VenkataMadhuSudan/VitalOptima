# VitalOptima 🏥
### AI-Powered Hospital Command Center, Mathematical Resource Optimizer & Decision-Support System
*Built for the 24-Hour National-Level Healthcare Hackathon*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Streamlit 1.40+](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg)](https://streamlit.io)
[![OR-Tools](https://img.shields.io/badge/Google-OR--Tools-orange.svg)](https://developers.google.com/optimization)
[![xAI Grok](https://img.shields.io/badge/xAI-Grok%20Intelligence-black.svg)](https://x.ai)
[![PostgreSQL](https://img.shields.io/badge/Neon-PostgreSQL%20Cloud-336791.svg)](https://neon.tech)
[![SQLite](https://img.shields.io/badge/SQLite-Local%20Resilience-003B57.svg)](https://sqlite.org)
[![Security: PBKDF2 RBAC](https://img.shields.io/badge/Security-PBKDF2%20RBAC-success.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 Executive Overview & Problem Statement

Modern healthcare facilities operate under extreme stochastic volatility. Changing patient arrival volumes, sudden mass casualty surges, acute clinical staffing deficits, and medical supply chain disruptions frequently cause severe operational bottlenecks across:

- **General Inpatient Beds & Overflow Medical Wards**
- **Intensive Care Units (ICU) & High-Dependency Beds**
- **Surgical Operating Theaters (OR Blocks)**
- **Nursing & Resident Clinical Shift Rosters**
- **Blood Bank Reserves & Critical Transfusion Components**
- **Medical Consumables & PPE Inventory**

**VitalOptima** is an enterprise-grade Hospital Operations Command Center and Intelligent Decision-Support System that unifies:
1. **Multi-Target Machine Learning Forecasting**: Projects 7-day forward daily patient admissions, emergency arrivals, discharges, and ICU admissions using Random Forest and Ridge Regression models.
2. **Mathematical Resource Optimization**: Formulates bed, nurse, and operating room reallocations as Mixed-Integer Linear Programs (MILP) solved via Google OR-Tools.
3. **Conversational What-If Stress Simulation**: Features both parameter shock sliders and a zero-shot Natural Language Processing (NLP) search engine evaluating hospital stress across 8 specialized clinical lenses.
4. **xAI Grok Intelligence Layer**: Delivers generative operational reasoning, out-of-sample holdout model diagnostics, unit bottleneck matrices, and tool-calling execution backed by deterministic zero-hallucination fail-safes.
5. **Real-Time Patient Admission & Bed Allocation Workspace**: Provides role-based intake triage, live bed assignment across wards, dynamic capacity decrementing, and discharge tracking.
6. **Hospital Blood Bank & Transfusion Backup Reserves**: Tracks real-time units across 8 blood groups (O-, O+, A-, A+, B-, B+, AB-, AB+) and components (PRBC, FFP, Platelets, Cryoprecipitate, Whole Blood).
7. **Natural Language Database Records Engine**: Allows administrators and clinicians to ask plain-English questions translated into verified SQL across historical census, staffing, and inventory records.
8. **Human-in-the-Loop Clinical Governance**: Enforces mandatory administrator review (Accept, Modify, Reject) with an immutable audit trail.

> **⚠️ Clinical Safeguard Notice:**  
> VitalOptima is strictly an administrative logistics, bed management, and operational resource planning platform. It does **not** perform autonomous clinical triage, patient diagnosis, or medical treatment dispensing. All patient admission profiles and stress-testing simulations utilize de-identified, synthetic clinical records conforming to healthcare privacy standards.

---

## 🔐 Role-Based Access Control (RBAC) & Default Credentials

VitalOptima implements defense-in-depth Role-Based Access Control secured by NIST-compliant salted **PBKDF2-HMAC-SHA256** password hashing (100,000 iterations).

| Role | Username | Default Password | Accessible Workspaces & Permissions |
| :--- | :--- | :--- | :--- |
| **Hospital Administrator** (`ADMIN`) | `admin` | `Admin@Vital2026!` | **Full System Access**: Executive Command Dashboard, AI Insights & Agent, OR-Tools Optimizer, Demand Forecasting, What-if Simulator, Resource Management, Blood Bank & SQL Explorer, Decision Audit Trail, and User Management. |
| **Admission Officer** (`ADMISSION_OFFICER`) | `admit_officer` | `Admit@Vital2026!` | **Focused Clinical Workspace**: Patient Triage Intake, Bed Allocation (`MED-B*`, `SUR-B*`, `MICU-B*`, `OBS-B*`, `PED-B*`), Active Inpatient Census, Patient Discharge, and Clinical Notes. *(Administrative optimization & system configuration restricted)* |

---

## 🖥️ Command Center Modules & Architecture

The VitalOptima platform comprises 11 tightly integrated functional modules accessible via the navigation sidebar:

### 1. 📊 Executive Command Dashboard (`ui/views/dashboard.py`)
- Real-time KPI summary donuts (General Beds 79%, ICU Utilization 77%, Staff Roster 97%, Operating Rooms 67%).
- 24-hour emergency arrival demand trajectory with peak census boundaries.
- Live active alert drawer tracking departmental saturation, staff deficits, and supply stockout warnings.
- Interactive AI Recommendation and What-If Simulator cards with one-click decision logging.

### 2. 🛏️ Admission & Bed Allocation Workspace (`ui/views/admission_workspace.py`)
- Dedicated role-tailored workflow for hospital admission officers.
- Real-time patient intake (`ADM-YYYYMMDD-XXX`) with gender, age, admission type (Emergency, Elective, Urgent), and clinical notes.
- Departmental bed assignment across Medicine, Surgery, Medical ICU, Obstetrics, and Pediatrics.
- Concurrency-safe bed allocation lock preventing double-booking race conditions.
- Real-time patient discharge workflow returning beds immediately to available capacity.

### 3. 🤖 AI Insights & Operational Intelligence (`ui/views/ai_insights.py`, `src/`)
- Powered by **xAI Grok** (`grok-2-latest`, `grok-beta`) with automatic fallback to **Zero-Hallucination Deterministic Analytics**.
- **6 Integrated Diagnostic Tabs**:
  - **Executive Briefing**: High-level key takeaways presented in soft visual stat cards with evidence-grounded risk indicators.
  - **Historical Trends**: 365-day time series analysis with interactive rolling 7-day trendlines and day-of-week inflow patterns.
  - **ML Forecast Evaluation**: Out-of-sample holdout metrics (MAE, RMSE, WAPE) benchmarking Random Forest vs. Ridge Regression vs. Seasonal-Naive baselines.
  - **Unit Risk Breakdown**: Department-specific capacity bottlenecks and acuity constraints.
  - **Action Plan & Directives**: Structured operational directives with assigned timelines and clinical leads.
  - **Interactive Agent & Simulator**: Natural language decision assistant executing allowlisted read-only Python analytics tools.

### 4. 🏥 Resource Management & Capacity (`ui/views/resource_mgmt.py`)
- Granular bed tracking across General Wards, Step-Down Units, and ICUs.
- Shift staffing roster tracking available vs. scheduled nurses, physician coverage, and overtime allocation.
- Operating Theater (OR) block schedule tracking active surgical suites, turnovers, and emergency trauma buffers.

### 5. 🔮 Demand Forecasting Engine (`ui/views/demand_forecast.py`, `src/ml_forecast.py`)
- Recursive multi-target regression models predicting **Admissions**, **Emergency Arrivals**, **Discharges**, and **ICU Admissions**.
- Chronological 80/20 train-test split preventing data leakage.
- Cyclic circadian features (day-of-week, lag terms $t-1$, $t-7$, $t-14$, and rolling 7-day averages).
- Projected bed occupancy curve highlighting 90% capacity risk barriers.

### 6. ⚙️ Mathematical Resource Optimization (`ui/views/optimization.py`, `models/optimizer.py`)
- Solves patient-to-bed and nurse-to-department assignments using **Google OR-Tools Mixed-Integer Linear Programming (MILP)**.
- Formulates multi-objective cost functions minimizing unmet emergency demand and cross-department transfer penalties.
- Interactive administrator review interface allowing one-click **Approval**, **Modification**, or **Rejection**.

### 7. 🔬 What-If Scenario Stress Simulator (`ui/views/simulator.py`, `models/simulator_nlp.py`)
- Dual-mode stress evaluation:
  - **Parameter Sliders & Presets**: Mass casualty surges (+20% to +100%), ICU outages (-10% to -50%), and staffing viral outbreaks (-10% to -40%).
  - **Conversational NLP Search Engine**: Zero-shot intent parser extracting parameters from plain-English queries across **8 clinical lenses** (Bed Deficit, ICU Stress, Staffing Acuity, Consumables, HICS Disaster Mitigations, Failure Order Vulnerability, Triage Saturation, Overall Resilience).

### 8. 📋 Decision Log & Audit Trail (`ui/views/decision_log.py`, `db/database.py`)
- Comprehensive audit ledger recording every administrative action with timestamp, category, decision, rationale, and actor ID.
- Instant CSV export for hospital compliance audits and shift handovers.

### 9. 🩸 Hospital Blood Bank & Transfusion Reserves (`data/blood_bank_inventory.csv`, `db/nlp_query.py`)
- Live inventory tracking for all blood groups (O-, O+, A-, A+, B-, B+, AB-, AB+) across PRBC, Fresh Frozen Plasma (FFP), Platelets, and Cryoprecipitate.
- Automated safety buffer calculation (days of supply, critical thresholds, daily burn rates, and cold chain storage temperatures).

### 10. 💬 Historical Data & Records Explorer (`ui/views/postgres_explorer.py`, `db/nlp_query.py`)
- Natural Language to SQL query interface supporting dual-engine queries across Neon PostgreSQL and SQLite.
- Pre-configured executive prompt chips for instantaneous queries covering patient arrival spikes, low consumables, bed occupancy, and blood bank reserves.

### 11. ⚙️ System Administration & Settings (`ui/views/settings_view.py`)
- Centralized user provisioning and access revocation.
- Real-time database connection diagnostics (PostgreSQL Cloud status, latency, and SQLite sync health).
- AI engine configuration (xAI Grok API key, model selection, and fallback controls).

---

## 🏗️ System Architecture & Directory Structure

```
HC_08_VitalOptima/
├── README.md                      # Comprehensive project documentation & setup guide
├── requirements.txt               # Locked production dependencies
├── app.py                         # Streamlit application entry point & RBAC router
├── config.py                      # Hospital constants, IST timezone, baselines, color system
├── .env.example                   # Environment configuration template
│
├── assets/
│   └── hospital_building.jpg      # Hospital campus visualization asset
│
├── data/                          # Authoritative hospital datasets (CSV telemetry)
│   ├── blood_bank_inventory.csv   # Blood groups, component units, thresholds & burn rates
│   ├── hospital_daily_data.csv    # 365-day historical census, arrivals, and discharges
│   ├── hospital_resources.csv     # Department bed allocations, staffed capacity & baselines
│   ├── department_resources.csv   # Granular departmental operational capacities
│   ├── staffing_roster.csv        # Nurse & doctor shift availability and rosters
│   ├── inventory_supplies.csv     # Medical consumables, PPE stock, lead times & reorders
│   ├── synthetic_generator.py     # De-identified synthetic hospital census generator
│   └── demand_forecast.csv        # 24-hour cyclical emergency arrival stream
│
├── src/                           # Core AI, Analytics & Machine Learning Pipeline
│   ├── agent_tools.py             # Allowlisted Python analytical tools for AI agent
│   ├── ai_analytics.py            # Evidence synthesis & deterministic what-if computation
│   ├── grok_client.py             # xAI Grok API client & deterministic fallback engine
│   ├── ml_forecast.py             # Multi-target Random Forest & Ridge Regression models
│   ├── schemas.py                 # Telemetry validation data schemas
│   ├── validate_dataset.py        # Data hygiene, range, and consistency validation
│   └── scenarios.py               # Deterministic scenario definitions & stress models
│
├── models/                        # Mathematical Optimization & Simulation Engines
│   ├── optimizer.py               # Google OR-Tools MILP resource allocation solver
│   ├── simulator.py               # Parameterized disaster surge simulation engine
│   ├── simulator_nlp.py           # Zero-shot NLP query parser & 8-lens simulation evaluator
│   └── forecaster.py              # Scikit-learn arrival & occupancy forecaster
│
├── db/                            # Dual-Engine Database Architecture (Postgres + SQLite)
│   ├── database.py                # SQLite schema, tables (users, admissions, audit, blood bank)
│   ├── postgres.py                # Neon PostgreSQL connection pooling & execution
│   ├── nlp_query.py               # Natural language to SQL translator & intent extractor
│   ├── schema.py                  # DDL statements for PostgreSQL cloud tables
│   ├── sync_to_postgres.py        # Automated schema migration & CSV sync utility
│   └── vitaloptima.db             # Local SQLite database (zero-downtime offline persistence)
│
├── services/                      # Enterprise Business Logic & Security Services
│   ├── auth_service.py            # NIST PBKDF2-HMAC-SHA256 hashing, RBAC & audit logger
│   ├── admission_service.py       # Patient admission lifecycle, bed locking & concurrency checks
│   └── dashboard_summarizer.py    # Floating AI Executive Digest & contextual Q&A assistant
│
├── ui/                            # User Interface Components & Views
│   ├── styles.py                  # Centralized stylesheet (custom CSS glassmorphism & cards)
│   ├── components.py              # Reusable Plotly charts, top navbar, metric cards & footers
│   └── views/
│       ├── dashboard.py           # Hospital Command Center view
│       ├── admission_workspace.py # Patient Admission & Bed Allocation workspace
│       ├── ai_insights.py         # Grok AI Insights & Operational Intelligence view
│       ├── resource_mgmt.py       # Departmental bed, staff, and OR management
│       ├── demand_forecast.py     # ML Forecast analysis, test set holdouts & metrics
│       ├── optimization.py        # OR-Tools MILP recommendation review & approval workbench
│       ├── simulator.py           # Conversational NLP & Slider What-If Simulator
│       ├── decision_log.py        # Administrator audit history and CSV export
│       ├── postgres_explorer.py   # Natural Language SQL Database Explorer
│       ├── login_view.py          # Secure PBKDF2 login gateway
│       └── settings_view.py       # Administrative settings, users & database status
│
├── ml_outputs/                    # Persisted Machine Learning Outputs
│   ├── metrics.csv                # Out-of-sample holdout evaluation metrics (MAE, RMSE, WAPE)
│   ├── forecast_next_days.csv     # Recursive 7-day multi-target predictions
│   └── test_predictions.csv       # Actual vs. predicted test set comparisons
│
└── tests/                         # Automated Unit & Integration Test Suites
    ├── test_rbac_and_admissions.py# Comprehensive RBAC, security & admission service tests
    ├── test_ai_agent_suite.py     # AI analytics, tool calling, and fallback engine tests
    ├── test_blood_bank_nlp.py     # Blood bank inventory and NLP query tests
    ├── test_simulator_nlp.py      # What-If Simulator conversational NLP tests
    ├── test_dashboard_summarizer.py# Floating dashboard summarizer unit tests
    ├── test_settings_and_summarizer_qa.py # Settings, user management & QA assistant tests
    ├── test_real_datasets.py      # CSV dataset schema and telemetry validation tests
    └── test_core.py               # Optimization solver and database unit tests
```

---

## 🧮 Mathematical Formulation (Google OR-Tools MILP)

VitalOptima formulates hospital resource reallocation as a Mixed-Integer Linear Program (MILP):

$$\min \sum_{p \in P} w_p \cdot \text{Unmet}_p + \sum_{p \in P} \sum_{d \in D} c_{p,d} \cdot x_{p,d} + \sum_{d \in D} \lambda_d \cdot \text{Overtime}_d$$

### Constraints:
1. **Demand Balance**:
   $$\sum_{d \in D} x_{p,d} + \text{Unmet}_p = \text{Demand}_p \quad \forall p \in P$$
2. **Department Staffed Bed Capacity**:
   $$\sum_{p \in P} x_{p,d} \le \text{Capacity}_d \quad \forall d \in D$$
3. **Clinical Feasibility**:
   $$x_{p,d} = 0 \quad \text{if department } d \text{ cannot clinically support patient acuity class } p$$
4. **Nurse-to-Patient Safe Acuity Ratio**:
   $$\text{StaffAvailable}_d + \text{Overtime}_d \ge \alpha_d \sum_{p \in P} x_{p,d} \quad \forall d \in D$$

Where:
- $w_p$ is a critical penalty weight ($w_{\text{ICU}} = 1000$, $w_{\text{ED}} = 500$) preventing critical patient boarding.
- $c_{p,d}$ represents inter-department transfer costs (routing overflow to secondary surgical holding).
- $\alpha_d$ represents mandatory clinical nurse-to-patient ratios (e.g., $1:2$ for ICU, $1:4$ for ED).

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python**: 3.10 or 3.11 recommended
- **Git**

### 2. Clone & Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/VJH-2k26/HC_08_VitalOptima.git
cd HC_08_VitalOptima

# Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install locked dependencies
pip install -r requirements.txt
```

### 3. Database Initialization (Dual-Engine: Neon Postgres + SQLite)
VitalOptima operates out-of-the-box using local SQLite (`db/vitaloptima.db`). To connect cloud PostgreSQL:
```bash
# Copy environment template
cp .env.example .env

# Configure your connection string in .env:
# DATABASE_URL=postgresql://username:password@ep-sample-project.c-3.aws.neon.tech/neondb?sslmode=require

# (Optional) Run automated schema migration & CSV sync to PostgreSQL:
python db/sync_to_postgres.py
```
> **Resiliency Guarantee:** If PostgreSQL is offline or credentials are not supplied, VitalOptima automatically initializes local SQLite (`db/vitaloptima.db`) and CSV telemetry with zero downtime.

### 4. Launch the Command Center
```bash
streamlit run app.py
```
Open your browser at **`http://localhost:8501`**.

Log in using either default account:
- **Admin**: `admin` / `Admin@Vital2026!`
- **Admission Officer**: `admit_officer` / `Admit@Vital2026!`

### 5. Running Automated Test Suites
Run the complete automated test suite covering all 8 test modules:
```bash
python -m unittest discover tests
```

---

## 🧪 Out-of-Sample Model Benchmarks

Telemetry below reflects out-of-sample holdout test evaluations (80/20 chronological split, 292 training days, 73 holdout test days):

| Forecasting Target | Selected Model Architecture | MAE | RMSE | WAPE (%) | Baseline Winner |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Inpatient Admissions** | Random Forest Regressor | **5.12** | **6.45** | **8.4%** | RF outperforms Ridge by 14.2% |
| **Emergency Arrivals** | Random Forest Regressor | **14.80** | **18.22** | **7.6%** | RF captures non-linear peak days |
| **Patient Discharges** | Ridge Regression | **6.21** | **7.89** | **10.1%** | Ridge regularizes discharge variance |
| **ICU Admissions** | Ridge Regression | **1.84** | **2.35** | **13.5%** | Ridge prevents extreme outlier swings |

*Model outputs and metrics are persisted in `ml_outputs/metrics.csv`.*

---

## 🛡️ Model Governance, Privacy & Ethical AI

1. **Human-in-the-Loop Safeguard**: VitalOptima never autonomously dispatches resources or changes patient records without explicit human review and cryptographic audit logging.
2. **Zero-PII Transmission**: Telemetry sent to LLM intelligence layers consists solely of aggregated departmental census numbers, shift counts, and inventory units. Zero Patient Health Information (PHI) is ever exposed.
3. **Deterministic Fail-Safe Fallback**: If an external LLM API key expires or is unavailable, VitalOptima falls back seamlessly to deterministic, verified mathematical heuristics with 100% uptime.
4. **Transparent Trade-offs**: Feature importances, lag terms, and solver slack variables are visible to clinical leadership to ensure explainable decision support.

---

## 👥 Hackathon Team & Project Metadata

- **Project Name:** VitalOptima (HC_08)
- **Track:** AI-Based Hospital Resource Optimization & Clinical Decision Support
- **Repository:** [https://github.com/VJH-2k26/HC_08_VitalOptima](https://github.com/VJH-2k26/HC_08_VitalOptima)
- **License:** MIT License