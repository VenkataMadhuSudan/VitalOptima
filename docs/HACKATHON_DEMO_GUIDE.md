# VitalOptima — Technical Hackathon Demonstration & Evaluator Guide

## 1. Executive Summary

VitalOptima is an **AI-Assisted Hospital Operations Intelligence and Mathematical Resource Optimization Platform**. It empowers hospital administrators and clinical operations directors to anticipate patient demand surges, detect departmental bottlenecks, stress-test disaster responses, and solve constrained resource allocation problems.

> **Operational Scope & Medical Guardrail:**  
> VitalOptima is an administrative and resource decision-support system. It **does not** independently diagnose patients, prescribe clinical therapy, or triage individual clinical severity. All clinical recommendations require human-in-the-loop review.

---

## 2. Quickstart & Environment Setup

### 2.1 Prerequisites
* Python 3.11+
* Git
* Modern Web Browser (Chrome, Edge, Firefox, Safari)

### 2.2 Installation
```bash
# Clone the repository
git clone https://github.com/VenkataMadhuSudan/VitalOptima.git
cd VitalOptima

# Install required dependencies
pip install -r requirements.txt

# Initialize local SQLite database & seed default data
python -c "from db.database import init_db; init_db()"
```

### 2.3 Launch Application
```bash
streamlit run app.py
```
The application will open automatically at `http://localhost:8501`.

---

## 3. Demo Accounts & Role-Based Access Control (RBAC)

VitalOptima enforces least-privilege, defense-in-depth role-based access control:

| Account Role | Username | Password | Permitted Operational Scope |
| :--- | :--- | :--- | :--- |
| **Hospital Administrator** | `admin` | `Admin@Vital2026!` | Command Center, ML Forecasting, OR-Tools Optimizer, Crisis Simulator, Inventory, Audit Logs, Settings |
| **Admission Officer** | `admit_officer` | `Admit@Vital2026!` | Patient Admissions, Bed Allocations, Active Admissions, Discharges |

---

## 4. The 7-Step Flagship Operational Workflow

This end-to-end operational workflow demonstrates live calculation, mathematical optimization, and administrative sign-off without hardcoded results.

```
[1. Forecast Demand] ➔ [2. Detect Shortages] ➔ [3. Simulate Emergency] ➔ 
[4. Optimize Allocation] ➔ [5. Explain Recommendation] ➔ [6. Administrator Approval] ➔ [7. Record Decision]
```

### Step 1: Demand Forecasting (ML Engine)
1. Log in as `admin`.
2. Navigate to **Demand Forecasting** via the sidebar.
3. Observe the live 24-hour hourly arrival projections and 7-day inpatient forecasts:
   - **Feature Integrity:** All rolling statistics strictly shift backward ($t-1$) with warmup rows dropped to eliminate lookahead data leakage.
   - **Baseline Comparison Table:** View held-out test evaluation comparing Random Forest against **Persistence ($t-1$)**, **Seasonal-Naive ($t-7$)**, and regularized **Ridge Regression** baselines across a strict 3-way chronological split (70% Train, 15% Calibration, 15% Untouched Test).
   - **Prediction Intervals:** Nominal 90% bounds ($q_{0.05}, q_{0.95}$) calibrated exclusively on the independent calibration split and evaluated on the untouched test split.

### Step 2: Detect Bottlenecks (Hospital Command Center)
1. Navigate to **Hospital Command Center**.
2. Review real-time census metrics:
   - In-Service Bed Utilization (Overall Occupancy vs Safe 85% Threshold).
   - Critical Care (ICU) Headroom.
   - Staffing Ratios (Nurses on duty vs required patient acuity).
   - Medical Consumable Alerts (e.g., N95 respirator reorder breaches).

### Step 3: Simulate an Emergency (What-If Crisis Simulator)
1. Navigate to **Crisis Simulator** and select the **🎛️ Interactive Stress Workbench & Sliders** tab.
2. Select an emergency preset, such as **Mass Casualty Incident (MCI)** or **Winter Respiratory Surge**.
3. Adjust the shock parameters:
   - **Surge Volume (%):** e.g., `+50%` to `+85%` emergency inflow.
   - **ICU Bed Outage (%):** e.g., `10%` to `25%` bed unavailability.
   - **Staff Absenteeism (%):** e.g., `10%` to `35%` nurse shortage.
4. Observe the unmitigated impact: Resilience Health Index drops sharply, and acute bed and nursing deficits are identified.

### Step 4: Mathematical Optimization (Google OR-Tools MILP)
1. Scroll down to the **⚖️ Google OR-Tools Mathematical Resource Optimization** section.
2. The Mixed-Integer Linear Programming (MILP) solver executes automatically on the post-shock state:
   - **Hard Physical Bounds:** Unit capacities are strictly respected; no bed is allocated beyond availability.
   - **Clinical Specialty Compatibility:** Strict specialty matrix prevents invalid patient-unit transfers.
   - **Independent Verification:** The returned allocation is verified independently against all hard constraints (`✓ Clinically Verified`).

### Step 5: Explain the Recommendation
1. Review the calculated **Before vs. After** metrics:
   - **Unmitigated Deficit (Before)** vs **Optimal Allocation (After)**.
   - **Remaining Unmet Demand:** Explicitly reported (never hidden or fabricated).
2. Review the synthesized action pillars:
   - **Bed Management:** Specific unit reallocation orders.
   - **Staffing Float Pool:** Nurse redeployment to high-acuity zones.
   - **Surgical Standby:** Elective deferral recommendations to protect trauma suites.
3. Read the mathematically grounded explanation detailing the exact solver trade-offs.

### Step 6: Administrator Approval & Sign-Off
1. Scroll to the **✍️ Administrator Review & Decision Protocol** section.
2. Select your review determination: **Accepted**, **Modified**, or **Rejected**.
3. Enter your administrative and clinical justification in the rationale field.
4. Click **🔐 Sign & Commit Decision to Tamper-Evident Audit Trail**.

### Step 7: Cryptographic Decision & Audit Log Verification
1. Navigate to **Decision Log** to view your committed operational action.
2. Navigate to **Settings & Admin** ➔ **Audit Trail**.
3. Observe your decision logged with an append-only **SHA-256 cryptographic hash chain** (`record_hash` linked to `prev_hash`).
4. To test cryptographic verification:
   ```bash
   python -c "from services.auth_service import verify_audit_log_chain; print(verify_audit_log_chain())"
   ```

---

## 5. Automated Verification & Reproducible Benchmarks

Run the complete test suite locally:
```bash
# Discover and execute all automated tests
python -m unittest discover tests

# Run specific domain test suites
python -m unittest tests/test_core.py
python -m unittest tests/test_rbac_and_admissions.py
python -m unittest tests/test_ai_agent_suite.py
python -m unittest tests/test_audit_hash_chain.py
```

### Verify Optimization Solver Directly:
```bash
python -c "
from models.optimizer import ResourceOptimizer
opt = ResourceOptimizer()
res = opt.optimize_bed_allocation({'General_Medical': 25, 'Emergency_Trauma': 10}, {'General_Ward': 20, 'Emergency_Unit': 15})
print('Status:', res['status'], '| Allocated:', res['total_allocated'], '| Unmet:', res['total_unmet'], '| Verified:', res['is_verified'])
"
```

---

## 6. Known Limitations & Scope Boundaries

1. **Synthetic Telemetry:** Demonstration datasets (`data/*.csv`) are synthetically modeled for hospital architecture evaluation and do not represent real PHI/HIPAA protected patient records.
2. **Clinical Decision Making:** The system does not triage or diagnose clinical conditions; it allocates capacity based on department classifications.
3. **Dual Database Architecture:** Dual-mode supports PostgreSQL (cloud primary) and SQLite (offline local). Cross-database active-active failover is not claimed; local SQLite ensures 100% offline hackathon demonstrability.
4. **Offline AI Provider:** When no `XAI_API_KEY` is provided, the platform automatically utilizes its built-in deterministic analytics provider with zero degradation of core optimization or forecasting functionality.
