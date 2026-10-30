# VitalOptima Scope Disclosures & Known Limitations

**Document Version:** 2.0.0  
**Status:** Official Engineering & Clinical Boundary Disclosure  

---

## 1. Clinical Decision Support Boundary

VitalOptima is engineered specifically as an **administrative operations intelligence and resource allocation tool**. 

> [!WARNING]
> VitalOptima is **NOT** a certified medical device and does **NOT** provide autonomous medical diagnosis, clinical triage, or patient treatment recommendations.
> - Bed allocation recommendations must be reviewed and approved by an authorized hospital triage officer or clinical nurse supervisor.
> - The software is intended to support administrative capacity planning, nurse-to-patient ratio enforcement, and crisis surge simulation.

---

## 2. Data Sources & EHR Integration

- **De-Identified & Synthetic Profiles:** The baseline emergency arrival datasets are derived from historical open-source hospital census records. The 24-hour diurnal curves represent derived hourly weights rather than live continuous streaming sensor feeds.
- **HL7 v2 / FHIR Connectivity:** The current architecture provides REST and database-level ingestion pipelines. It does not include an active HL7 MLLP socket listener or native SMART-on-FHIR client. In production enterprise hospital networks, VitalOptima must be deployed behind an interface engine (e.g., Mirth Connect / NextGen Connect).

---

## 3. Database & Concurrency Scope

- **Authoritative Database Architecture:** VitalOptima employs an authoritative single-writer model (SQLite with WAL mode and partial unique indexes for single-server or air-gapped deployments; PostgreSQL with an outbox journal table for clustered enterprise web workers).
- **No Active-Active Multi-Master:** The platform does **not** implement active-active multi-datacenter bidirectional replication. Concurrency safety is guaranteed within a single authoritative engine via ACID transactions and database-level partial unique indexes.

---

## 4. Mathematical Modeling Assumptions

- **Discrete Time Horizon:** Mixed-Integer Linear Programming models hospital resources in discrete shifts (e.g., 8-hour or 12-hour windows). Turnaround delays between patient discharge and bed sanitization are represented as aggregate capacity reductions rather than real-time spatial pathfinding simulations.
- **Homogeneous Acuity Groups:** Patients are categorized into 5 clinical acuity groups (`General_Medical`, `Emergency_Trauma`, `ICU_Critical`, `Surgery_PostOp`, `Pediatric`). Individual patient sub-specialty requirements within a group (e.g., specialized burn units vs. neuro-ICU) are approximated through departmental compatibility matrices.

---

## 5. Forecasting Limits

- **Autoregressive Extrapolation:** Ridge regression and Random Forest forecasters excel at capturing seasonal, calendar, and autoregressive lag trends ($t-1, t-7, t-14$).
- **Unprecedented Macro Shocks:** An ML forecaster trained on historical data cannot predict unprecedented external shocks (e.g., the emergence of a novel pandemic or catastrophic chemical spill) purely from historical lags. For these outlier events, hospital administrators must utilize the **What-If Scenario Simulator** to manually stress-test capacity.

