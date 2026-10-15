# VitalOptima 🏥
### AI-Based Hospital Resource Optimization and Decision-Support System
*Built for the 24-Hour National-Level Healthcare Hackathon*

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg)](https://streamlit.io)
[![OR-Tools](https://img.shields.io/badge/Google-OR--Tools-orange.svg)](https://developers.google.com/optimization)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: Functional Prototype](https://img.shields.io/badge/Status-Demonstrable%20Prototype-success.svg)](#)

---

## 🎯 Executive Overview & Problem Statement
Modern healthcare facilities operate under extreme stochastic strain. Changing patient arrival volumes, sudden mass casualty incidents, and acute staffing shortages lead to severe bottlenecks in:
- **General Inpatient Beds & Overflow Wards**
- **Critical Intensive Care Units (ICU)**
- **Surgical Operating Rooms (ORs)**
- **Specialized Nursing & Clinical Staff Shifts**

**VitalOptima** is an intelligent Hospital Command Center and Decision-Support System.that:
1. **Forecasts 24-hour emergency arrival demand** using machine learning with cyclic circadian features.
2. **Recommends mathematically optimal bed, staff, and OR allocations** using Google OR-Tools Mixed-Integer Linear Programming (MILP).
3. **Simulates high-stress disaster scenarios** (mass casualty surges, ICU outages, and staffing deficits).
4. **Enforces human-in-the-loop governance**, allowing administrators to Accept, Modify, or Reject recommendations with a persistent SQLite audit trail.

> **⚠️ Clinical Safeguard Notice:**
> VitalOptima is strictly an administrative operations and logistics optimization system. It does **not** make autonomous clinical triage or medical treatment decisions. All patient admission distributions and operational simulations use authorized, de-identified synthetic data.

---

## 📸 Hospital Command Center Dashboard
The VitalOptima command center interface provides real-time situational awareness:
- **Real-Time Operational KPIs**: General Beds (320), ICU Utilization (85%), Staff Coverage (80%), OR Availability (83%) with donut charts and DoD trends.
- **24-Hour Demand Forecast**: Emergency arrival projection with peak load detection (92 arrivals at 15:00) and capacity threshold boundaries.
- **Predicted Demand vs. Available Capacity**: Hourly census tracking against operational ceilings.
- **Live Alert Drawer**: Priority-categorized immediate constraints (ICU limits, OR bottlenecks) and projected shortages (staff shifts, fluid supply).
- **Departmental Status Matrix**: Live occupancy bars across Emergency, Internal Medicine, Surgery, Pediatrics, ICU, and Maternity.
- **Recent Telemetry Activity**: Timeline of model executions, shift changes, and surge alarms.

---

## 🏗️ System Architecture

```
HC_08_VitalOptima/
├── README.md                      # Documentation, setup guide, hackathon pitch
├── requirements.txt               # Locked production dependencies
├── app.py                         # Streamlit application entry point & page router
├── config.py                      # System constants, colors, and operational baselines
├── assets/
│   └── hospital_building.jpg      # Architectural hospital campus visualization
├── data/
│   ├── synthetic_generator.py     # De-identified synthetic hospital census generator
│   ├── departments.csv            # Departmental capacities and baseline status
│   └── demand_forecast.csv        # 24-hour arrival and capacity stream
├── models/
│   ├── forecaster.py              # ML arrival forecasting with RandomForestRegressor
│   ├── optimizer.py               # Google OR-Tools MILP resource allocation solver
│   └── simulator.py               # What-if scenario stress-test simulation engine
├── db/
│   └── database.py                # SQLite schema and CRUD for decision logs & audit trails
├── ui/
│   ├── styles.py                  # Custom command center CSS stylesheet
│   ├── components.py              # Plotly charts, donut gauges, KPI cards, timeline widgets
│   └── views/
│       ├── dashboard.py           # Pixel-perfect Hospital Command Center view
│       ├── resource_mgmt.py       # Detailed ward, staff roster, and OR block tracking
│       ├── demand_forecast.py     # ML forecast analysis, retrain triggers, feature importance
│       ├── optimization.py        # OR-Tools recommendation review & approval workbench
│       ├── simulator.py           # Stress-test simulation with interactive sliders & presets
│       └── decision_log.py        # Administrator audit history and CSV export
└── tests/
    └── test_core.py               # Automated unit tests for solver, ML, and DB layers
```

---

## 🧮 Mathematical Formulation (OR-Tools MILP)

VitalOptima formulates bed and staff allocation as a constrained Mixed-Integer Linear Program:

$$\min \sum_{p \in P} w_p \cdot \text{Unmet}_p + \sum_{p \in P} \sum_{d \in D} c_{p,d} \cdot x_{p,d}$$

**Subject to:**
1. **Demand Balance**: $\sum_{d \in D} x_{p,d} + \text{Unmet}_p = \text{Demand}_p \quad \forall p \in P$
2. **Department Capacity**: $\sum_{p \in P} x_{p,d} \le \text{Capacity}_d \quad \forall d \in D$
3. **Clinical Feasibility**: $x_{p,d} = 0 \quad \text{if department } d \text{ cannot accommodate patient class } p$

Where $w_p$ is a critical penalty weight ($w_{\text{ICU}} = 1000$) preventing critical patient delays, and $c_{p,d}$ represents secondary transfer penalties.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-team/VitalOptima.git
cd VitalOptima

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup (Neon PostgreSQL Cloud / Local)
```bash
# Copy the environment template
cp .env.example .env

# Configure your PostgreSQL connection string in .env:
# DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Run the automated schema migration & CSV dataset sync script:
python db/sync_to_postgres.py
```
> **Note on Resiliency & Demo Fallback:**
> VitalOptima features a dual-engine architecture. If PostgreSQL is offline or credentials are missing during an offline demo, the application automatically falls back to local SQLite (`db/vitaloptima.db`) and CSV telemetry with zero downtime or crashes.

### 4. Launch the Command Center
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501` to view the command dashboard.

---

## 👥 24-Hour Development Team Schedule

| Member | Specialization | Core Responsibilities |
| :--- | :--- | :--- |
| **Member 1** | **AI & Mathematical Optimization** | Scikit-learn demand forecaster, Google OR-Tools MILP solver formulation, constraint tuning, and unit testing. |
| **Member 2** | **Backend & Simulation Architecture** | Synthetic telemetry generator, SQLite audit logging, what-if stress engine, scenario persistence, and data models. |
| **Member 3** | **Frontend & Product Lead** | Streamlit command dashboard, Plotly data visualizations, custom CSS glassmorphism, and human-in-the-loop review UI. |

---

## 🛡️ Model Governance & Ethics
1. **Human-in-the-Loop**: No resource deployment is automated without administrative approval.
2. **Transparent Trade-offs**: Feature importances (diurnal cycles, lag terms) and solver slack variables are exposed.
3. **Safety Fallbacks**: Infeasibility fallbacks guarantee safe overflow ward routing during catastrophic surges.

---

## ✨ AI Dashboard Summarizer ("Hospital Insights")

VitalOptima includes an enterprise-grade **AI Dashboard Summarizer** accessible via a floating assistant button (`✨`) pinned to the bottom-right corner of the administrator interface.

### Key Capabilities:
- **Instant Operational Digest**: Explains live dashboard metrics in plain English without requiring manual interpretation of charts or tables.
- **7-Part Structured Analysis**:
  - **Overall Status**: Concise evaluation of current hospital resilience and acute bottlenecks.
  - **Key Insights**: 3–5 bullet points detailing bed utilization, critical care margins, shift staffing coverage, OR schedules, and peak arrival forecasts.
  - **Attention Required**: Prioritized operational risk items tagged with clear severity badges (`Critical`, `High`, `Medium`, `Low`) based on configured thresholds.
  - **Recommended Actions**: 2–4 practical administrative actions grounded in mathematical optimization and telemetry evidence (e.g. nurse float pool reallocation, discharge audits).
  - **Trends & Forecasts**: Directional arrival trajectory, peak arrival window (15:00 IST), and 95% confidence intervals from the Random Forest model.
  - **Positive Observations**: Highlights stable wards and well-resourced departments.
  - **Data Provenance & Freshness**: Discloses 365-day census records, 30-day consumable telemetry, and real-time IST clock.
- **Dual AI & Deterministic Architecture**:
  - **LLM-Powered Mode**: Supports Google Gemini, Anthropic Claude, or OpenAI GPT-4o with zero patient PII transmitted.
  - **Rule-Based Offline Fallback**: Fully deterministic, mathematical rule-based summarizer that operates instantly with 100% reliability even if no external API key is configured or if network timeouts occur.
- **Contextual Follow-Up Q&A**: Parameter-safe natural language queries (e.g., *"Which department needs the most attention?"*, *"Why is ICU utilization high?"*).
- **Executive Actions**: Live metric refresh, instant clean text clipboard copy, and responsive slide-over drawer UI.