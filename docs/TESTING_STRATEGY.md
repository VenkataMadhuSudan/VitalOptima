# VitalOptima Quality Assurance & Testing Strategy

**Document Version:** 2.0.0  
**Status:** Approved & Verified in CI/CD  
**Scope:** Automated Verification, Statistical Testing, Optimization Benchmarking, Concurrency, and Cybersecurity  

---

## 1. Executive Summary & Testing Philosophy

Hospital operations decision-support systems demand rigorous verification. A bug in bed capacity calculations, an unhandled race condition during admission, or an uncalibrated forecasting spike could lead to unsafe patient transfers, nurse burnout, or emergency department gridlock.

VitalOptima enforces a **multi-tiered testing architecture** governed by strict engineering rules:
1. **Never claim without verification:** Every bugfix, optimization guarantee, and security mitigation must be backed by an automated regression test.
2. **Zero statistical fabrication:** Machine learning baselines and prediction intervals must be evaluated against identical timestamps without data leakage.
3. **Mathematical exactness:** Mixed-Integer Linear Programs (MILP) must be validated against brute-force combinatorial solutions and independent constraint checkers.
4. **Hardware-level concurrency testing:** Race conditions must be tested using real multi-connection concurrent threads against SQLite and PostgreSQL engines.

---

## 2. Test Architecture Pyramid

```
                ▲
               / \
              /   \
             / E2E \       Smoke Tests & UI Imports
            / Smoke \      (`test_smoke.py`, Streamlit context validation)
           /---------\
          / Concurrency\   Database Contention & Outbox Replay
         / & Security   \  (`test_database_reliability.py`, `test_cybersecurity_and_governance.py`)
        /-----------------\
       / Domain Rigor      \ Time-Series Integrity & MILP Optimality
      / (ML & Operations)   \ (`test_forecast_integrity.py`, `test_optimizer_rigor.py`)
     /-----------------------\
    /  Core Unit Test Suites  \ RBAC, Data Parsers, Simulator, NLP, Core Logic
   /  (Deterministic Suites)   \ (`test_core.py`, `test_rbac_and_admissions.py`, `test_real_datasets.py`)
  /-----------------------------\
 / Static Analysis & Security AST\ Ruff Linter, Bandit Security Scanner, pyproject.toml
/---------------------------------\
```

---

## 3. Dedicated Verification Suites

| Test Suite | File | What It Genuinely Verifies | Assertions / Cases |
| :--- | :--- | :--- | :--- |
| **Smoke & System Readiness** | `tests/test_smoke.py` | Config loading, shift boundaries, schema init, forecaster/optimizer instantation, UI imports. | 6 tests |
| **MILP Optimization Rigor** | `tests/test_optimizer_rigor.py` | Hard capacity boundaries, clinical incompatibility, 1,260-state brute force proof, float staffing, offline beds, time-indexed scheduling. | 9 tests |
| **Time-Series ML Integrity** | `tests/test_forecast_integrity.py` | Feature pipeline temporal leakage, negative lag prevention, conformal interval coverage, baseline comparisons, rolling origin backtest. | 10 tests |
| **Database & Concurrency** | `tests/test_database_reliability.py` | 8-thread simultaneous bed contention, duplicate admission rejection via partial unique index, double discharge, outbox journal replay, online backup/restore. | 5 tests |
| **Admission Concurrency** | `tests/test_admission_concurrency.py` | Multi-user simulated bed assignment contention under active SQLite locks. | 2 tests |
| **Cybersecurity & Governance** | `tests/test_cybersecurity_and_governance.py` | Login brute-force rate limiting (5 failed attempts -> 15 min lockout), RBAC enforcement, session age expiration, audit chain checkpoint truncation detection, tool argument filtering. | 5 tests |
| **Audit Hash Chain** | `tests/test_audit_hash_chain.py` | SHA-256 genesis linking, tampering detection across modified rows. | 5 tests |
| **RBAC & Admission Workflows** | `tests/test_rbac_and_admissions.py` | Role permissions, discharge tracking, audit entry creation, census reconciliation. | 25+ tests |
| **Real Datasets Validation** | `tests/test_real_datasets.py` | Schema conformation, missing values, clinical date range validity of CSV datasets. | 4 tests |
| **Core Functionality** | `tests/test_core.py` | Forecaster baseline generation, optimizer feasibility, scenario simulator stress test. | 5 tests |

---

## 4. Execution Commands

### 4.1 Running Specific Test Suites
```bash
# Run MILP mathematical proofs and constraint verification
python -m unittest tests/test_optimizer_rigor.py

# Run ML time-series zero-leakage and conformal coverage verification
python -m unittest tests/test_forecast_integrity.py

# Run multi-threaded database concurrency and partial index tests
python -m unittest tests/test_database_reliability.py tests/test_admission_concurrency.py

# Run cybersecurity, brute-force lockout, and audit checkpoint tests
python -m unittest tests/test_cybersecurity_and_governance.py

# Run smoke tests for immediate environment validation
python -m unittest tests/test_smoke.py
```

### 4.2 Comprehensive Test Discovery
```bash
python -m unittest discover tests
```

### 4.3 Static Code Analysis & Security AST Scan
```bash
# Static analysis with Ruff
ruff check .

# Automated AST security audit with Bandit
bandit -r models services db src -c pyproject.toml
```

---

## 5. CI / CD Quality Gates

All automated pushes and pull requests trigger the GitHub Actions workflow (`.github/workflows/ci.yml`). A pull request cannot be merged unless:
1. **Ruff** detects zero syntax errors or unhandled exceptions.
2. **Bandit** passes with zero high-severity or medium-severity security issues.
3. Database schema initializes cleanly in a fresh testing container.
4. Smoke test passes.
5. All domain-specific rigor suites (MILP, ML forecasting, Concurrency, Cybersecurity) pass with 100% success rate.
6. The full discovery suite (`python -m unittest discover tests`) completes with 0 errors and 0 failures.

---

## 6. Regression & Flakiness Prevention Policies

- **Thread Sleep & Timing Windows:** Concurrent contention tests avoid flaky arbitrary `sleep()` calls. Instead, worker threads use `threading.Barrier` or synchronization primitives to release threads simultaneously at the exact nanosecond.
- **Database Isolation:** Unit tests run either with `:memory:` SQLite connections or isolated temporary test database files (`test_concurrency.db`) that are cleaned up in `tearDown()`.
- **Deterministic Random Seeds:** All stochastic components and backtesting evaluations utilize fixed seeds (`seed=42`) to guarantee reproducibility.
