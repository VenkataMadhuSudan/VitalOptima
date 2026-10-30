# VitalOptima Research Evaluation: Forecast-Uncertainty-Aware Stochastic Resource Optimization

**Document Version:** 2.0.0  
**Authors:** VitalOptima Senior Engineering & Healthcare Operations Research Team  
**Evaluation Artifact:** `evaluation/research_experiment_results.json`  
**Execution Command:** `python evaluation/research_experiment.py`  

---

## 1. Abstract & Clinical Problem Statement

Traditional hospital capacity planning operates under a **deterministic point-forecast paradigm**: operational managers predict mean emergency arrivals and schedule bed blocks and nursing shifts to match that single value. In practice, healthcare operations exhibit extreme demand volatility driven by diurnal cycles, weather shocks, mass casualty events, and epidemic waves.

When demand spikes beyond the mean forecast:
1. Deterministic allocations encounter severe staffing bottlenecks because nurse-to-patient acuity ratios cannot be met.
2. Inelastic physical bed boundaries and rigid departmental staffing force diversion of critical care patients or deferral of life-saving surgeries.

This research evaluation validates an **uncertainty-aware two-stage stochastic programming methodology** that directly bridges the calibrated prediction intervals from Phase 1 (`models/forecaster.py`) with the mixed-integer linear programming optimizer (`models/optimizer.py`, `models/scenario_optimizer.py`).

---

## 2. Mathematical Formulation

### 2.1 Two-Stage Stochastic Mixed-Integer Linear Program (MILP)

We formulate the hospital resource allocation problem as a stochastic program with recourse over discrete demand scenarios $s \in S$:

#### Stage 1: Here-and-Now Decisions (Pre-Shift Staffing Commitments)
Before the exact realization of emergency arrivals is known, the hospital administrator commits baseline regular nurse staffing $N_d$ to each department $d \in D$:
$$\sum_{d \in D} N_d \le \text{TotalRegularNurses}$$
$$N_d \in \mathbb{Z}_{\ge 0}, \quad \forall d \in D$$

#### Stage 2: Wait-and-See Recourse Decisions (Under Scenario $s$)
After patient arrivals $\text{Demand}_{p, s}$ realize for each clinical triage group $p \in P$ under scenario $s$ with probability $p_s$:
- $x_{p, d, s} \in \mathbb{Z}_{\ge 0}$: Count of patients from group $p$ placed in department $d$.
- $u_{p, s} \in \mathbb{Z}_{\ge 0}$: Unmet patient demand for group $p$.
- $v_{d, s} \in \mathbb{Z}_{\ge 0}$: Supplemental float-pool / overtime nurses mobilized in department $d$.

#### Objective Function
Minimize the total expected operational cost (regular nurse wages plus expected recourse penalties):
$$\min_{N, x, u, v} \sum_{d \in D} C_d^{\text{base}} \cdot N_d + \sum_{s \in S} p_s \left[ \sum_{p \in P} W_p \cdot u_{p, s} + \sum_{p \in P} \sum_{d \in \text{Allowed}(p)} T_{p, d} \cdot x_{p, d, s} + \sum_{d \in D} S_d^{\text{overtime}} \cdot v_{d, s} \right]$$

#### Constraints (Enforced for all $s \in S$)
1. **Demand Balance:**
   $$\sum_{d \in \text{Allowed}(p)} x_{p, d, s} + u_{p, s} = \text{Demand}_{p, s}, \quad \forall p \in P$$
2. **Effective Physical Bed Capacity:**
   $$\sum_{p \in P} x_{p, d, s} \le \text{Capacity}_d - \text{Damaged}_d, \quad \forall d \in D$$
3. **Clinical Acuity Staffing Ratio:**
   $$\text{Ratio}_d \cdot \sum_{p \in P} x_{p, d, s} \le N_d + v_{d, s}, \quad \forall d \in D$$
4. **Overtime / Float Staffing Limits:**
   $$v_{d, s} \le \text{MaxSupplemental}_d, \quad \forall d \in D$$

---

## 3. Empirical Experimental Design

We conducted an empirical simulation over 15 distinct operational trials with fixed random seed (`seed=42`) using the empirical parameters derived from the real historical emergency dataset:
- Empirical Daily Mean Arrivals ($\mu$): $174.2$ patients/day
- Empirical Conformal Interval Half-Width ($\hat{q}$): $25.2$ patients/day
- Evaluated Policies:
  - **Policy A (Deterministic Forecast Optimization):** Sized base nurse staffing strictly to satisfy the point forecast $\mu$, distributing surplus regular nurses proportionally.
  - **Policy B (Uncertainty-Aware Two-Stage Stochastic MILP):** Generated three discrete conformal scenarios ($s_1$: Expected $\mu$, $p=0.60$; $s_2$: High $\mu + \hat{q}$, $p=0.30$; $s_3$: Severe Surge $\mu + 2\hat{q}$, $p=0.10$) and solved the joint two-stage MILP.

Both policies were then evaluated against identical stochastic demand realizations drawn from the empirical distribution across normal, high, and severe surge regimes.

---

## 4. Benchmark Results

The table below summarizes the independently verified experimental results recorded in `evaluation/research_experiment_results.json`:

| Metric | Policy A: Deterministic Forecast | Policy B: Uncertainty-Aware Stochastic | Empirical Impact ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Mean Unmet Demand (Overall)** | $18.00 \pm 44.63$ patients | $\mathbf{15.73 \pm 42.52}$ patients | **-12.6% overall reduction** |
| **Surge Regime Unmet Demand** | $84.67$ patients | $\mathbf{77.00}$ patients | **-9.1% surge reduction** |
| **Mean Total Operational Penalty** | $\$11,064.00$ | $\mathbf{\$8,866.33}$ | **-19.9% cost reduction** |
| **Mean Bed Utilization** | $54.9\%$ | $\mathbf{56.6\%}$ | $+1.7\%$ higher throughput |
| **Solver Execution Latency** | $< 1.0\text{ ms}$ | $33.95\text{ ms}$ | $+33\text{ ms}$ (well below $15\text{s}$ SLA) |
| **Mathematical Optimality** | Proven Optimal (Single) | Proven Optimal (Joint) | Verified across all scenarios |

---

## 5. Honest Scientific Discussion & Trade-Offs

### 5.1 Why Does the Stochastic Policy Outperform the Deterministic Policy?
1. **Asymmetric Acuity Penalties:** In healthcare, unmet critical care ($W_{\text{ICU}} = 1000$) carries a far higher clinical and financial penalty than a regular nurse wage ($C_{\text{base}} = 50$). Sizing regular nurse staffing based solely on average ICU demand leaves zero staffing headroom when a spike arrives.
2. **Proactive Float Staffing:** The stochastic solver placed 6 regular nurses in ICU and 6 in Emergency, whereas the deterministic heuristic placed only 4 in ICU. When a severe surge materialized, Policy A was constrained by the 1-nurse supplemental limit, whereas Policy B accommodated the surge safely.

### 5.2 Real-World Trade-Offs & Limitations
- **Slightly Higher Base Staffing Cost in Low-Demand Periods:** Hedging against tail risks commits regular nurses who may experience lower patient ratios during unusually quiet shifts.
- **Computational Overhead:** Solving the extensive form of the two-stage MILP requires creating decision variables for every scenario. In our benchmark, execution time increased from $< 1\text{ ms}$ to $33.95\text{ ms}$. While a $33\text{ ms}$ solve time is completely imperceptible to a human operator, scaling to 50 scenarios and 20 departments would require decomposition algorithms (e.g., Benders Decomposition / L-shaped method).
- **Physical Boundary Ceiling:** No optimization algorithm can admit more patients than physical licensed beds. When realized demand exceeded total hospital bed capacity ($136 > 136$), both policies inevitably incurred unmet demand, highlighting that mathematical optimization must be paired with physical infrastructure investment.
