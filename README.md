# VitalOptima 🏥
### Enterprise AI Hospital Resource Optimization & Clinical Operations Command Center
*Engineered for High-Stakes Healthcare Resource Allocation, Emergency Surge Readiness, and Resilient Clinical Logistics*

---

[![Python 3.11](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Google OR-Tools](https://img.shields.io/badge/Google-OR--Tools%20MILP-EA4335.svg?logo=google&logoColor=white)](https://developers.google.com/optimization)
[![Neon PostgreSQL](https://img.shields.io/badge/Database-Neon%20PostgreSQL%20Cloud-00E599.svg?logo=postgresql&logoColor=white)](https://neon.tech)
[![SQLite Dual-Engine](https://img.shields.io/badge/Fallback-SQLite%20Zero--Downtime-003B57.svg?logo=sqlite&logoColor=white)](#dual-engine-database-architecture)
[![xAI Grok](https://img.shields.io/badge/AI%20Agent-xAI%20Grok--2-000000.svg?logo=x&logoColor=white)](https://x.ai)
[![Security: NIST PBKDF2](https://img.shields.io/badge/Security-NIST%20PBKDF2--HMAC--SHA256-4F46E5.svg)](#security--role-based-access-control-rbac)
[![Test Suite](https://img.shields.io/badge/Unit%20Tests-8%20Suites%20Passing-success.svg)](#-automated-testing--verification-suite)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📑 Table of Contents
- [🎯 Executive Overview & Problem Statement](#-executive-overview--problem-statement)
- [✨ Key Platform Features & Modules](#-key-platform-features--modules)
- [📸 Command Center & Module Walkthrough](#-command-center--module-walkthrough)
- [🏗️ System Architecture & Data Flow](#️-system-architecture--data-flow)
- [🗄️ Dual-Engine Database Architecture](#️-dual-engine-database-architecture)
- [🧮 Mathematical Formulation (OR-Tools MILP)](#-mathematical-formulation-or-tools-milp)
- [📈 Machine Learning Demand Forecaster](#-machine-learning-demand-forecaster)
- [🤖 Grok AI Insights & Autonomous Agent](#-grok-ai-insights--autonomous-agent)
- [🔒 Security & Role-Based Access Control (RBAC)](#-security--role-based-access-control-rbac)
- [🚀 Quick Start & Installation Guide](#-quick-start--installation-guide)
- [🔑 Demo Credentials & Access Profiles](#-demo-credentials--access-profiles)
- [🧪 Automated Testing & Verification Suite](#-automated-testing--verification-suite)
- [🛠️ CLI Pipeline & Predefined Scenarios](#️-cli-pipeline--predefined-scenarios)
- [🛡️ Clinical Governance, Ethics & Safety Disclosures](#️-clinical-governance-ethics--safety-disclosures)
- [👥 Development Team Schedule & Contributions](#-development-team-schedule--contributions)

---

## 🎯 Executive Overview & Problem Statement

Modern tertiary hospitals and trauma centers operate under acute stochastic pressure. Unpredictable emergency arrival waves, sudden mass-casualty incidents, staffing shortages, and supply disruptions frequently cause dangerous clinical bottlenecks:
- **Emergency Department (ED) Crowding & Ambulance Diversion**: Overflowing ED bays cause delayed triage and increased patient mortality.
- **Critical Care (ICU) Saturation**: High occupancy leaves zero margin for post-surgical recovery or acute trauma stabilization.
- **Operating Room (OR) Scheduling Gridlock**: Unplanned emergency procedures disrupt scheduled elective surgeries.
- **Nursing & Clinical Shift Deficits**: Unbalanced staff-to-patient ratios lead to nurse burnout and compromised patient safety.
- **Consumable & Blood Bank Depletion**: Stockouts of critical universal donor blood (O-) or respiratory PPE jeopardize trauma response.

### The VitalOptima Solution
**VitalOptima** is an enterprise-grade Hospital Operations Command Center and Decision-Support System that unifies:
1. **Circadian Machine Learning Demand Forecasting**: Anticipates 24-hour emergency arrival volumes, inpatient admissions, and ICU bed demand with cyclic diurnal features and 95% confidence intervals.
2. **Mathematical Optimization via Google OR-Tools MILP**: Solves complex bed, nursing roster, and surgical suite allocations in sub-second execution times with strict clinical feasibility constraints.
3. **Dedicated Admission Officer Workspace**: Streamlines patient admission, ACID-compliant bed allocation with concurrency mutex locking, real-time census tracking, and safe patient discharge.
4. **Natural Language What-If Crisis Simulator**: Simulates high-stress disaster scenarios (mass-casualty events, respiratory epidemics, ICU contamination, nurse strikes) with automated parameter extraction and HICS protocol recommendations.
5. **Multi-Model AI Intelligence & NL2SQL Assistant**: Features an xAI Grok-powered autonomous agent with read-only hospital tools, a floating AI Executive Summarizer, and a trained domain-specific NL2SQL query engine.
6. **Resilient Dual-Engine Data Layer**: Connects to serverless Neon PostgreSQL Cloud with automated schema migration, while guaranteeing zero-downtime offline fallback to local SQLite and verified CSV telemetry.
7. **NIST-Compliant Security & RBAC**: PBKDF2-HMAC-SHA256 password hashing (100,000 iterations), tamper-resistant audit logging, and strict role segregation between Hospital Administrators and Admission Officers.

> **⚠️ Clinical Safeguard Notice:**
> VitalOptima is strictly an administrative operations, capacity planning, and logistics decision-support platform. It does **not** make autonomous clinical triage, diagnosis, or medical treatment decisions. All patient admission distributions, bed assignments, and operational simulations use authorized, de-identified synthetic hospital census telemetry.

---

## ✨ Key Platform Features & Modules

| Module | Core Functionality | Primary Tech Stack | Target Role |
| :--- | :--- | :--- | :--- |
| **Command Center Dashboard** | Live operational KPIs, donut utilization gauges, departmental occupancy matrix, live alert drawer, and telemetry activity feed. | Streamlit, Plotly, Custom Glassmorphic CSS | Hospital Administrator, CMO |
| **Admission Officer Workspace** | Patient registration, ACID-compliant bed allocation, concurrency mutex lock, live admitted roster, and safe discharge workflow. | SQLite/PostgreSQL, Threading Locks, Streamlit Fragment Polling | Admission Officer, Triage Nurse |
| **Demand Forecasting Engine** | 24-hour forward emergency arrivals and admission trajectories with cyclic sine/cosine circadian encoding and 95% CI bands. | Scikit-learn Random Forest, Ridge, NumPy, Pandas | Operations Director, Forecaster |
| **OR-Tools Resource Optimizer** | Constrained Mixed-Integer Linear Programming (MILP) solving bed, nurse float pool, and OR allocations with penalty weights. | Google OR-Tools, Linear Solver (CBC/SCIP) | Hospital Admin, Operations |
| **What-If Crisis Simulator** | Interactive slider stress testing and domain-trained NLP crisis inquiry parser simulating mass-casualty and epidemic events. | Python NLQ Parser, Monte Carlo Simulation | Disaster Committee, Admin |
| **AI Insights & Grok Agent** | Autonomous multi-turn reasoning, allowlisted read-only analytical tool execution, and deterministic offline fallback. | xAI Grok API, OpenAI SDK, Allowlisted Tools | Chief Medical Officer, Admin |
| **Natural Language Query (NL2SQL)** | Domain-trained English-to-SQL query engine translating natural human questions into parameterized SQL queries with executive explanations. | Custom NL2SQL Engine, SQLAlchemy, Regex | Hospital Analysts, Admin |
| **Blood Bank & Transfusion Reserves** | Real-time tracking of 8 blood groups (A±, B±, AB±, O±), PRBC/platelet/FFP inventory, cross-matched units, and universal donor (O-) deficit alerts. | PostgreSQL/SQLite, CSV Telemetry | Blood Bank Lead, Surgery |
| **Critical Supplies & Consumables** | 30-day consumable telemetry, 7-day rolling burn rates, days of supply remaining, automated reorder triggers, and stockout PO notifications. | Pandas, Predictive Burn Rate Model | Procurement, Supply Chain |
| **PostgreSQL & Records Explorer** | Interactive cloud database explorer with raw SQL query terminal, table inspection, schema viewer, and CSV telemetry exports. | Neon Serverless PostgreSQL, SQLAlchemy 2.0 | Database Administrator, Analyst |
| **Administrative Settings Console** | User provisioning, role assignment, active status toggling, password resets, and tamper-evident security audit logs. | PBKDF2-HMAC-SHA256, Audit Logger | System Administrator |
| **Floating AI Hospital Summarizer** | Pinned slide-over executive digest generating 7-part operational analyses with contextual follow-up Q&A and clipboard export. | LLM (Grok/Gemini/OpenAI) + Rule Fallback | Hospital Administrator |

---

## 📸 Command Center & Module Walkthrough

### 1. Hospital Command Center Dashboard (`ui/views/dashboard.py`)
- **Real-Time Operational KPIs**: General Beds (300 total, 238 occupied, 79% occupancy), ICU Utilization (30 beds, 26 occupied, 87% critical rate), Staff Shift Coverage (142 active on Morning Shift, 82% coverage), OR Availability (18 suites, 15 active, 83% utilization).
- **Interactive Donut Gauges**: High-contrast, color-coded donut meters reflecting real-time capacity thresholds (Green < 80%, Amber 80–89%, Red ≥ 90%).
- **24-Hour Predictive Demand vs. Capacity**: Hourly census forecast tracking emergency arrivals against operational department ceilings, with peak arrival alerts (92 arrivals at 15:00 IST).
- **Live Alert Drawer**: Priority-categorized constraints (ICU capacity warning, OR suite congestion, nurse float pool shortages, fluid supply alerts).
- **Departmental Occupancy Matrix**: Live progress bars tracking Emergency, Internal Medicine, Surgery, Pediatrics, ICU, and Maternity wards.
- **Shift Telemetry & Indian Standard Time (IST) Clock**: Dynamically updates greeting, current clinical shift lead (Dr. Ramesh Patel / Dr. Priya Sharma / Dr. Vikram Sethi), and active shift hours.

### 2. Admission Officer Workspace (`ui/views/admission_workspace.py`)
- **Patient Registration Form**: Captures patient name, age, gender, assigned department, target bed type (General Inpatient vs. ICU), triage acuity level (Level 1 Resuscitation to Level 5 Non-Urgent), and clinical admitting notes.
- **ACID-Compliant Concurrency Control**: Uses an internal re-entrant threading lock (`_ALLOCATION_LOCK`) to guarantee that concurrent admissions across multiple terminals never double-allocate the same physical bed.
- **Dynamic Bed Number Allocation**: Automatically generates human-readable bed identifiers (e.g. `GEN-PED-04`, `ICU-BED-02`) based on real-time availability.
- **Active Inpatient Roster & Live Search**: Filterable table showing admitted patients, admitting officers, admission timestamps, and elapsed length of stay.
- **Safe Patient Discharge**: One-click discharge action that updates patient status, records discharge timestamp, logs the event in the audit trail, and immediately frees the bed for incoming emergency patients.
- **Sub-15s Cross-Session Polling**: Uses Streamlit fragment polling (`@st.fragment(run_every=8)`) to propagate cross-terminal updates without requiring manual page reloads.

### 3. Natural Language What-If Crisis Simulator (`models/simulator_nlp.py`)
- **Dual Interface**: Interactive sliders for quantitative parameter tuning alongside a domain-trained natural language inquiry box.
- **Curated Disaster Scenarios**:
  - *Mass Casualty Trauma Surge*: +85% emergency volume, 10 ICU beds damaged, 5% staff deficit.
  - *Severe Staff Viral Outbreak*: +40% patient wave, 35% clinical staff absenteeism.
  - *Critical ICU Bio-Contamination*: 50% ICU beds locked down for decontamination, +20% surge.
  - *Winter Respiratory Epidemic*: +65% pediatric/medicine surge, 25% ICU bed loss.
- **Domain NLP Entity Extraction**: Evaluates conversational queries (e.g., *"What happens if an 80% patient surge hits during an emergency?"*) to extract numerical stress parameters, identify target wards, and calculate departmental collapse timelines.
- **Actionable Mitigations**: Recommends standardized Hospital Incident Command System (HICS) operational protocols, elective surgery cancellation triggers, and overflow ward activation.

### 4. Blood Bank & Critical Consumables Inventory
- **8 Blood Groups Tracked**: Real-time units available, units cross-matched/reserved for surgeries, net unreserved buffer, minimum safety reserve, daily burn rates, days of supply, and storage temperatures (+2°C to +6°C for PRBC, -18°C for FFP, +20°C to +24°C with agitation for Platelets).
- **Universal Donor (O-) Deficit Warning**: Immediate high-visibility alarm when emergency unreserved O- PRBC drops below the mandatory trauma threshold (10 units).
- **Consumables Stockout Prevention**: Predictive tracking for N95 respirators, IV infusion sets, surgical gloves, normal saline, oxygen cylinders, and antibiotics with automatic reorder status based on supplier lead times.

---

## 🏗️ System Architecture & Data Flow

```mermaid
flowchart TD
    subgraph DataSources["💾 Data & Storage Layer"]
        PG[("Neon Cloud PostgreSQL\n(Serverless / Connection Pool)")]
        SQLITE[("Local SQLite Database\n(db/vitaloptima.db)")]
        CSV["Verified CSV Telemetry\n(365-Day Census, Inventory, Roster)"]
        SYNC["Schema Sync & Migration Engine\n(db/sync_to_postgres.py)"]
        PG <--> SYNC <--> SQLITE
        CSV --> SYNC
    end

    subgraph CoreEngines["⚙️ Analytical & Mathematical Engines"]
        ML["Machine Learning Forecaster\n(Random Forest + Circadian Sine/Cosine)"]
        MILP["Google OR-Tools MILP Solver\n(Bed, Nurse & OR Optimization)"]
        SIM["Crisis Stress Simulator\n(Deterministic Dynamics & Monte Carlo)"]
        NLQ["Domain NL2SQL & NLP Parser\n(Trained Entity Extractor)"]
        GROK["xAI Grok Autonomous Agent\n(Allowlisted Read-Only Tools)"]
    end

    subgraph ServiceLayer["🛡️ Business & Security Services"]
        AUTH["NIST PBKDF2 Auth & RBAC\n(ADMIN vs ADMISSION_OFFICER)"]
        ADMIT["ACID Admission Service\n(Concurrency Mutex Locking)"]
        SUMM["AI Dashboard Summarizer\n(7-Part Analysis & Rule Fallback)"]
        AUDIT["Tamper-Resistant Audit Logger\n(Security & Decision Logs)"]
    end

    subgraph PresentationLayer["💻 Streamlit Command Center UI"]
        DASH["📊 Hospital Operations Dashboard"]
        ADM_UI["🏥 Admission Officer Workspace"]
        FC_UI["📈 Predictive Demand Forecasting"]
        OPT_UI["⚙️ Resource Optimization Workbench"]
        SIM_UI["🎛️ What-If Crisis Simulator"]
        AI_UI["🤖 Grok AI Insights & Improvement Agent"]
        INV_UI["📦 Inventory & Blood Bank Reserves"]
        EXP_UI["🗄️ PostgreSQL Historical Explorer"]
        SET_UI["⚙️ Settings & Accessor Management"]
        FLOAT["✨ Floating Hospital Insights Assistant"]
    end

    DataSources --> CoreEngines
    DataSources --> ServiceLayer
    CoreEngines --> ServiceLayer
    ServiceLayer --> PresentationLayer
```

---

## 🗄️ Dual-Engine Database Architecture

VitalOptima uses a resilient dual-database design ensuring enterprise scalability in cloud deployments and 100% uptime during offline hackathon demonstrations:

```
                                  ┌──────────────────────────────────────────────┐
                                  │           Application Data Gateway           │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                                        ┌────────────────┴────────────────┐
                                        ▼                                 ▼
                         [Primary: Neon Cloud PostgreSQL]   [Fallback: Local SQLite & CSV]
                         • Serverless cloud instance        • Zero configuration required
                         • SQLAlchemy 2.0 connection pool   • Embedded in db/vitaloptima.db
                         • ACID relational schema           • In-memory threading mutex locks
                         • Multi-user concurrent access     • Zero-downtime offline fallback
```

### Relational Schema Tables (`db/schema.py`)
1. **`patient_admissions`**: Patient ID, demographics, department, bed type, bed number, triage priority, admitting officer, timestamps, and discharge status.
2. **`hospital_census_daily`**: 365 days of historical admissions, emergency arrivals, ICU census, discharges, surgeries scheduled, and average length of stay.
3. **`department_resources`**: Real-time total, occupied, unavailable, and available bed capacities across departments.
4. **`staffing_roster`**: Morning, Evening, and Night shift rosters, nurse-to-patient ratios, roles, and mandatory rest hours.
5. **`blood_bank_inventory`**: Real-time units available, cross-matched reservations, critical thresholds, shelf-life days, and status.
6. **`inventory_supplies`**: Consumable SKUs, daily consumption burn rates, closing stock, reorder thresholds, and lead times.
7. **`demand_forecast_hourly`**: 24-hour predictive arrivals, 95% upper/lower confidence bounds, and capacity limits.
8. **`decision_log`**: Administrator approvals, modifications, rejections, rationale, and timestamps.
9. **`users`**: Usernames, PBKDF2 password hashes, cryptographic salts, role assignments, and active flags.
10. **`audit_logs`**: Security events, login attempts, patient admissions, discharges, and role adjustments.
11. **`system_alerts` & `recent_activity`**: High-priority operational alerts and live telemetry logs.

---

## 🧮 Mathematical Formulation (OR-Tools MILP)

VitalOptima formulates clinical bed, nursing float pool, and surgical suite allocations as a constrained Mixed-Integer Linear Program (MILP) solved using Google OR-Tools:

### 1. Sets and Indices
- $P$: Set of patient triage classes ($\text{Emergency Trauma}, \text{ICU Critical}, \text{General Medical}, \text{Elective Surgical}, \text{Pediatric}$).
- $D$: Set of hospital departments ($\text{Emergency}, \text{ICU}, \text{Internal Medicine}, \text{Surgery}, \text{Pediatrics}, \text{Maternity}$).
- $T$: Time periods / shifts ($\text{Morning}, \text{Evening}, \text{Night}$).

### 2. Decision Variables
- $x_{p,d} \in \mathbb{Z}_{\ge 0}$: Number of patients of triage class $p$ allocated to department $d$.
- $\text{Unmet}_p \in \mathbb{Z}_{\ge 0}$: Number of unallocated or deferred patients of class $p$.
- $s_{d} \in \mathbb{Z}_{\ge 0}$: Supplemental float pool nursing staff allocated to department $d$.

### 3. Objective Function
$$\min \sum_{p \in P} w_p \cdot \text{Unmet}_p + \sum_{p \in P} \sum_{d \in D} c_{p,d} \cdot x_{p,d} + \sum_{d \in D} \gamma_d \cdot s_d$$

Where:
- $w_p$: Critical priority penalty for unmet demand ($w_{\text{ICU}} = 1000$, $w_{\text{Trauma}} = 800$, $w_{\text{General}} = 100$, $w_{\text{Elective}} = 10$).
- $c_{p,d}$: Secondary clinical transfer penalty (e.g. allocating medical overflow into surgical beds incurs penalty $c = 25$, while incompatible placements are strictly prohibited with $c = \infty$).
- $\gamma_d$: Cost weight of deploying float pool nursing staff.

### 4. Constraints
1. **Demand Balance**:
   $$\sum_{d \in D} x_{p,d} + \text{Unmet}_p = \text{Demand}_p \quad \forall p \in P$$
2. **Physical Department Bed Capacity**:
   $$\sum_{p \in P} x_{p,d} \le \text{AvailableBeds}_d \quad \forall d \in D$$
3. **Nurse-to-Patient Clinical Safety Ratios**:
   $$\sum_{p \in P} \alpha_{p} \cdot x_{p,d} \le \text{NursesOnDuty}_d + s_d \quad \forall d \in D$$
   *(e.g., ICU requires $\alpha = 0.5$ (1:2 ratio), while General Medical requires $\alpha = 0.2$ (1:5 ratio)).*
4. **Clinical Compatibility Matrix**:
   $$x_{p,d} = 0 \quad \forall (p,d) \notin \text{ClinicallyFeasiblePairs}$$
5. **Float Pool Availability Ceiling**:
   $$\sum_{d \in D} s_d \le \text{MaxFloatPoolStaff}$$

---

## 📈 Machine Learning Demand Forecaster

VitalOptima features a production machine learning pipeline validated on **365 days of hospital census telemetry** (`hospital_census_daily.csv`):

### Model Architecture & Feature Engineering
- **Circadian Cyclic Encoding**: Transforms continuous hour-of-day ($h \in [0, 23]$) into trigonometric harmonic coordinates to model circadian rhythm without boundary discontinuities:
  $$\text{Hour}_{\sin} = \sin\left(\frac{2\pi \cdot h}{24}\right), \quad \text{Hour}_{\cos} = \cos\left(\frac{2\pi \cdot h}{24}\right)$$
- **Temporal Seasonality**: One-hot encoded day of week, weekend flags, and elective surgical scheduling calendar.
- **Autoregressive Moving Averages**: Lag features ($t-1, t-2, t-24$) and 7-day rolling census averages.
- **Ensemble Model**: Scikit-Learn `RandomForestRegressor` with 100 estimators, max depth 12, and min samples split 4.

### Benchmark Evaluation Metrics (`ml_outputs/metrics.csv`)
| Target Horizon | Evaluated Model | MAE | RMSE | WAPE (%) | Performance Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Next-Day Admissions** | **Random Forest (VitalOptima)** | **5.779** | **7.703** | **11.58%** | **45.7% error reduction over baseline** |
| | Ridge Regression | 6.112 | 7.687 | 12.25% | Linear regularized baseline |
| | Seasonal Naive ($t-7$) | 7.903 | 10.876 | 15.83% | Day-of-week recurrence |
| | Persistence ($t-1$) | 10.653 | 13.040 | 21.34% | Previous day carryover |
| **Emergency Arrivals** | **Random Forest (VitalOptima)** | **16.765** | **22.021** | **9.13%** | **Superior peak surge capture** |
| | Ridge Regression | 17.036 | 22.348 | 9.28% | Close linear fit |
| | Seasonal Naive ($t-7$) | 24.000 | 35.186 | 13.07% | High weekend variance |
| | Persistence ($t-1$) | 21.444 | 26.596 | 11.68% | High lag error |
| **ICU Admissions** | **Random Forest (VitalOptima)** | **1.672** | **1.961** | **34.21%** | **Captures rare critical care events** |
| | Ridge Regression | 1.663 | 2.008 | 34.01% | Competitive linear performance |
| | Persistence ($t-1$) | 2.292 | 2.761 | 46.88% | High stochastic miss rate |

---

## 🤖 Grok AI Insights & Autonomous Agent

VitalOptima integrates an autonomous executive intelligence engine powered by xAI Grok (`grok-2-latest`) via the OpenAI-compatible SDK:

### Agent Tool Registry (`src/agent_tools.py`)
To prevent unauthorized database writes or arbitrary execution, the Grok agent operates within a **strictly bounded, allowlisted read-only tool environment**:
1. `get_historical_trends(metric, department)`: Queries 365-day arrival patterns, peak census days, and length-of-stay distributions.
2. `get_forecast_summary(horizon_days)`: Extracts multi-day projected inpatient census, forward peaks, and capacity risk days.
3. `get_forecast_evaluation()`: Retrieves benchmark model performance metrics (MAE, RMSE, WAPE) across model architectures.
4. `check_capacity_risks()`: Identifies departments operating above 80% warning and 90% critical capacity limits.
5. `check_staffing_shortages()`: Analyzes nurse-to-patient ratio deficits across Morning, Evening, and Night shifts.
6. `check_inventory_alerts()`: Scans medical consumables and blood reserves for stockouts or low-buffer states.
7. `run_demand_what_if(surge_pct, icu_loss_beds, staff_reduction_pct)`: Executes deterministic stress simulations on the fly.

### Deterministic Offline Fallback Mode
If no external API key is configured or network timeouts occur, VitalOptima's **Deterministic Analytics Engine** automatically generates structured executive analyses directly from local telemetry, guaranteeing **100% demo availability without internet or paid API dependencies**.

---

## 🔒 Security & Role-Based Access Control (RBAC)

VitalOptima enforces defense-in-depth security matching healthcare compliance standards:

```
                           ┌──────────────────────────────────────────────┐
                           │          Centralized Authentication          │
                           │  • NIST PBKDF2-HMAC-SHA256 (100k Iterations) │
                           │  • Cryptographic 16-Byte Random Salt         │
                           └──────────────────────┬───────────────────────┘
                                                  │
                                 ┌────────────────┴────────────────┐
                                 ▼                                 ▼
                     [Role: HOSPITAL_ADMIN]             [Role: ADMISSION_OFFICER]
                     • Command Center Dashboard         • Admission Officer Workspace
                     • Grok AI Insights & Agent         • Live Patient Registration
                     • Resource Optimization Solver     • Safe Bed Allocation
                     • What-If Crisis Simulator         • Inpatient Roster Tracking
                     • Consumables & Blood Bank         • Patient Discharge Workflow
                     • PostgreSQL Records Explorer      • Restricted from Settings/Admin
                     • User Provisioning & Settings
```

### Password Hashing Specification (`services/auth_service.py`)
- **Algorithm**: PBKDF2-HMAC-SHA256
- **Work Factor**: 100,000 iterations
- **Salt Generation**: `secrets.token_hex(16)` (cryptographically secure per-user salt)
- **Session Verification**: Server-side session authentication with defense-in-depth permission checking (`require_permission`) on all protected views.

---

## 🚀 Quick Start & Installation Guide

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.11)
- **Git**

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone https://github.com/your-team/VitalOptima.git
cd VitalOptima

# Create and activate a Python virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install locked production dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the template configuration file:
```bash
cp .env.example .env
```
Open `.env` and configure your settings:
```ini
# Neon Cloud PostgreSQL Connection String (Optional - falls back to SQLite if omitted)
DATABASE_URL=postgresql://neondb_owner:password@ep-solitary-frost-az28whg1-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require

# Application Settings
APP_ENV=production
APP_PORT=8501
HOSPITAL_NAME="City General Hospital"

# xAI Grok API Key (Optional - falls back to deterministic rule engine if omitted)
XAI_API_KEY=your_xai_api_key_here
```

### 4. Synchronize Database & Generate Telemetry
Initialize the database tables and populate baseline census records:
```bash
# Run automated schema creation and data synchronization
python db/sync_to_postgres.py
```
*(If PostgreSQL credentials are not configured, this script automatically sets up local `db/vitaloptima.db`).*

### 5. Launch the Command Center
```bash
streamlit run app.py
```
Open your browser at **`http://localhost:8501`**.

---

## 🔑 Demo Credentials & Access Profiles

VitalOptima is pre-seeded with two role profiles for immediate evaluator and hackathon testing:

| Role | Username | Password | Permitted Views & Workspaces |
| :--- | :--- | :--- | :--- |
| **Hospital Administrator** | `admin` | `Admin@Vital2026!` | **Full Unrestricted Access**: Dashboard, Grok AI Insights, Resource Management, Demand Forecasting, Optimization Solver, What-If Simulator, Decision Log, Inventory & Blood Bank, PostgreSQL Explorer, Settings. |
| **Admission Officer** | `admit_officer` | `Admit@Vital2026!` | **Dedicated Clinical Workspace**: Patient Registration, Real-Time Bed Allocation, Active Inpatient Roster, Bed Capacity Telemetry, Safe Patient Discharge. |

---

## 🧪 Automated Testing & Verification Suite

VitalOptima includes an enterprise-grade automated test suite spanning **8 comprehensive test files**:

```bash
# Run core optimization and ML tests
python tests/test_core.py

# Run RBAC security and ACID admission workflow tests
python -m unittest tests/test_rbac_and_admissions.py

# Run Grok AI agent and tool registry tests
python -m unittest tests/test_ai_agent_suite.py

# Run blood bank NLQ natural language query tests
python -m unittest tests/test_blood_bank_nlp.py

# Run AI dashboard summarizer verification tests
python -m unittest tests/test_dashboard_summarizer.py

# Run what-if crisis simulator NLP tests
python -m unittest tests/test_simulator_nlp.py

# Run settings and summarizer follow-up QA tests
python -m unittest tests/test_settings_and_summarizer_qa.py

# Run real dataset validation tests
python -m unittest tests/test_real_datasets.py
```

### What the Test Suites Validate:
- `test_core.py`: Mathematical feasibility of Google OR-Tools solver, Random Forest forecaster output, simulator dynamics, and SQLite decision logging.
- `test_rbac_and_admissions.py`: NIST PBKDF2 password hashing, salt uniqueness, permission boundaries, concurrent bed allocation mutex protection, and safe discharge bed release.
- `test_ai_agent_suite.py`: Grok tool registry safety, read-only constraints, missing-key resilience, and deterministic fallback outputs.
- `test_blood_bank_nlp.py`: Natural language entity extraction for all 8 blood groups, universal donor (O-) requests, and stockout queries.
- `test_dashboard_summarizer.py`: Mathematical accuracy of 7-part operational digest, threshold evaluations, and alert classifications.
- `test_simulator_nlp.py`: Natural language stress scenario interpretation, numerical surge extraction, and resilience scoring.

---

## 🛠️ CLI Pipeline & Predefined Scenarios

In addition to the interactive web application, VitalOptima provides standalone CLI scripts for dataset generation, validation, ML model training, and stress scenario generation:

### 1. Dataset Generation & Validation
```bash
# Generate clean de-identified baseline hospital telemetry:
python src/generate_dataset.py

# Run clinical telemetry audit and range integrity validation:
python src/validate_dataset.py
```

### 2. Standalone Model Training & Overlay Forecaster
```bash
# Train Random Forest and Ridge Regression models on chronological 80/20 split:
python src/ml_forecast.py

# Simulate an active 5-day patient surge overlay (+50% arrival multiplier):
python src/ml_forecast.py --surge-multiplier 1.5 --surge-days 5
```
> *Metrics and predictions are computed by the pipeline and written to `ml_outputs/`; they are **never** hardcoded in the raw dataset.*

### 3. Predefined Test Scenarios (`python src/scenarios.py` → `data/scenarios/<name>/`)
Runs offline stress scenario simulations without modifying baseline CSV telemetry:

| Scenario Name | Description & Impact | Associated CLI Command |
|---|---|---|
| `emergency_surge` | Scales `forecast_demand` × 1.5 for ED, × 1.25 for general beds, and × 1.35 for ICU. | `python src/ml_forecast.py --surge-multiplier 1.5 --surge-days 5` |
| `icu_capacity_loss` | Takes 8 ICU beds (5 MICU, 3 SICU) offline due to contamination/repairs; flags 3 displaced patients for relocation. | `python src/scenarios.py` |
| `staff_shortage` | Induces a 25% nurse absenteeism shock across acute shifts; highlights float pool reallocation triggers. | `python src/scenarios.py` |
| `supply_stockout` | Sets critical N95 respirators and surgical consumables to 0 units; triggers emergency procurement protocols. | `python src/scenarios.py` |


---

---

## 📂 Repository File Structure

```
HC_08_VitalOptima/
├── README.md                          # Comprehensive project documentation & architecture guide
├── requirements.txt                   # Locked production Python dependencies
├── app.py                             # Main Streamlit application entrypoint & role router
├── config.py                          # Hospital baselines, shift logic, and IST clock
├── .env                               # Active environment credentials (local/cloud)
├── .env.example                       # Environment configuration template
│
├── assets/
│   └── hospital_building.jpg          # Campus visual header for navigation sidebar
│
├── data/
│   ├── blood_bank_inventory.csv       # Real-time blood group reserves, PRBC, and buffer units
│   ├── demand_forecast.csv            # 24-hour hourly arrival and capacity trajectory
│   ├── department_resources.csv       # Departmental capacities, occupancies, and staffed beds
│   ├── departments.csv                # Core department baseline metadata
│   ├── hospital_census_daily.csv      # 365 days of historical hospital census & arrivals
│   ├── inventory_supplies.csv         # 30-day consumable telemetry, burn rates, and lead times
│   ├── staffing_roster.csv            # Shift schedules, nurse roles, and rest constraints
│   ├── synthetic_generator.py         # De-identified hospital telemetry generator
│   ├── load_census_data.py            # Historical census loader and preprocessor
│   └── save_all_datasets.py           # Dataset persistence and export utilities
│
├── db/
│   ├── database.py                    # SQLite schema, CRUD operations, and default user seeding
│   ├── nlp_query.py                   # Domain-specific Natural Language to SQL (NL2SQL) engine
│   ├── postgres.py                    # Neon PostgreSQL connector with SQLAlchemy connection pooling
│   ├── schema.py                      # SQLAlchemy ORM relational schema definitions
│   ├── sync_to_postgres.py            # Automated schema migration and CSV synchronization
│   └── vitaloptima.db                 # Persistent local SQLite database (resilient fallback)
│
├── ml_outputs/
│   ├── forecast_next_days.csv         # Multi-day forward projected admissions and arrivals
│   ├── metrics.csv                    # Evaluation benchmark comparison (MAE, RMSE, WAPE)
│   └── test_predictions.csv           # Model test set predictions vs ground truth
│
├── models/
│   ├── forecaster.py                  # ML arrival forecasting with RandomForestRegressor
│   ├── optimizer.py                   # Google OR-Tools MILP resource allocation solver
│   ├── simulator.py                   # What-if scenario simulation engine (sliders)
│   └── simulator_nlp.py               # Conversational stress test simulator & NLP engine
│
├── services/
│   ├── __init__.py                    # Services package initializer
│   ├── admission_service.py           # ACID patient registration, bed allocation & safe discharge
│   ├── auth_service.py                # NIST PBKDF2 hashing, session security & RBAC matrix
│   └── dashboard_summarizer.py        # 7-part AI executive dashboard summarizer service
│
├── src/
│   ├── agent_tools.py                 # Allowlisted read-only analytical tools for Grok agent
│   ├── ai_analytics.py                # Hospital census analytics, capacity & staffing checks
│   ├── generate_dataset.py            # Clinical dataset generation pipeline
│   ├── grok_client.py                 # xAI Grok API client with deterministic fallback
│   ├── ml_forecast.py                 # Multi-model training and evaluation harness
│   ├── scenarios.py                   # Disaster scenario definitions and configurations
│   ├── schemas.py                     # Data validation schemas
│   └── validate_dataset.py            # Data validation routines
│
├── ui/
│   ├── styles.py                      # Custom glassmorphic CSS stylesheet
│   ├── components.py                  # Donut gauges, KPI metric cards, and Plotly charts
│   ├── ai_summary_panel.py            # Slide-over floating AI Hospital Insights assistant
│   └── views/
│       ├── dashboard.py               # Hospital Operations Command Center view
│       ├── admission_workspace.py     # Admission Officer patient registration & discharge
│       ├── ai_insights.py             # Grok-Powered AI Insights & Improvement Agent
│       ├── demand_forecast.py         # ML arrival forecasting analysis & feature importance
│       ├── optimization.py            # Google OR-Tools recommendation review workbench
│       ├── simulator.py               # What-if crisis stress simulator (sliders + NLP)
│       ├── resource_mgmt.py           # Ward capacity, nursing roster, and OR block tracking
│       ├── decision_log.py            # Human-in-the-loop audit trail & CSV export
│       ├── postgres_explorer.py       # Cloud PostgreSQL terminal, schema viewer & query tool
│       ├── login_view.py              # Secure authentication gateway & role selector
│       └── settings_view.py           # Administrative accessor management & audit log console
│
└── tests/
    ├── test_core.py                   # Validates OR-Tools solver, ML forecaster, and SQLite DB
    ├── test_rbac_and_admissions.py    # Validates PBKDF2 hashing, RBAC matrix, and admission locks
    ├── test_ai_agent_suite.py         # Validates Grok agent tools and deterministic fallback
    ├── test_blood_bank_nlp.py         # Validates blood group NLP query entity extraction
    ├── test_dashboard_summarizer.py   # Validates 7-part executive summarizer accuracy
    ├── test_real_datasets.py          # Validates 365-day census records and consumable data
    ├── test_settings_and_summarizer_qa.py # Validates user management and QA follow-up queries
    └── test_simulator_nlp.py          # Validates conversational crisis inquiry parsing
```

---

## 🛡️ Clinical Governance, Ethics & Safety Disclosures

1. **Non-Clinical Logistics Boundary**: VitalOptima is strictly engineered for logistical capacity planning, staff scheduling, supply chain monitoring, and administrative resource allocation. It **never** automates clinical triage classifications, medical diagnoses, medication prescribing, or patient treatment decisions.
2. **De-Identified Synthetic Data & Zero-PII**: All patient demographic fields, admission records, and historical census entries utilize fully de-identified, synthetic data conforming to HIPAA Safe Harbor guidelines and clinical data privacy standards. Telemetry sent to LLM intelligence layers consists solely of aggregated departmental census numbers, shift counts, and inventory units. Zero Patient Health Information (PHI) is ever exposed.
3. **Mandatory Human-in-the-Loop Governance**: No AI or mathematical recommendation is deployed automatically. Every bed reallocation, staff float shift, or elective surgery deferral requires explicit approval (Accept, Modify, or Reject) by an authorized clinical administrator, backed by an immutable SQLite/PostgreSQL audit trail.
4. **Algorithmic Safety Constraints**: The Google OR-Tools MILP solver enforces hard clinical compatibility constraints ({p,d} = 0$ for incompatible departments) and sets critical penalties ({\text{ICU}} = 1000$) to prevent hazardous under-allocation of critical care resources.
5. **Deterministic Fail-Safe Fallback**: If an external LLM API key expires or is unavailable, VitalOptima falls back seamlessly to deterministic, verified mathematical heuristics with 100% uptime.
6. **Explainable AI & Transparent Trade-offs**: Feature importances, lag terms, and solver slack variables are visible to clinical leadership to ensure explainable decision support.

---

## 👥 Development Team Schedule & Contributions

*Developed for the 24-Hour National-Level Healthcare AI & Operations Hackathon*

| Team Member | Core Specialization | Project Contributions & Implemented Modules |
| :--- | :--- | :--- |
| **Member 1** | **AI & Mathematical Optimization** | • Google OR-Tools Mixed-Integer Linear Programming (MILP) solver formulation.<br>• Circadian Scikit-Learn Random Forest arrival demand forecasting engine.<br>• xAI Grok autonomous agent tool registry (`agent_tools.py`) and evidence package builder.<br>• Domain-trained Natural Language to SQL (NL2SQL) query engine (`nlp_query.py`). |
| **Member 2** | **Backend & Cloud Architecture** | • Resilient Dual-Engine architecture (Neon Serverless PostgreSQL + local SQLite).<br>• ACID patient admission service with re-entrant concurrency mutex locking (`_ALLOCATION_LOCK`).<br>• NIST PBKDF2-HMAC-SHA256 authentication service and centralized RBAC matrix.<br>• Comprehensive 8-suite automated test framework (`tests/`). |
| **Member 3** | **Frontend & Clinical Product Lead** | • Pixel-perfect Streamlit Command Center dashboard and custom glassmorphic stylesheet.<br>• Dedicated Admission Officer Workspace with sub-15s auto-syncing polling.<br>• Interactive What-If Crisis Simulator with natural language crisis inquiry box.<br>• Floating slide-over AI Hospital Insights assistant and Plotly donut gauges. |

---

<div align="center">
  <b>VitalOptima</b> — <i>Smarter Hospitals. Better Decisions. Resilient Healthcare.</i><br>
  Built with ❤️ for Healthcare Innovation • © 2026 VitalOptima Team
</div>

---

### 📋 Project & Hackathon Metadata
- **Project Name:** VitalOptima (HC_08)
- **Track:** AI-Based Hospital Resource Optimization & Clinical Decision Support
- **Repository:** [https://github.com/VJH-2k26/HC_08_VitalOptima](https://github.com/VJH-2k26/HC_08_VitalOptima)
- **License:** MIT License

