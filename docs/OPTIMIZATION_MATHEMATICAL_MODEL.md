# VitalOptima — Mathematical Optimization Model & Operations Research Formulation

**Document:** `docs/OPTIMIZATION_MATHEMATICAL_MODEL.md`  
**Author:** Operations Research & Mathematical Optimization Specialist  
**System:** VitalOptima Constrained Resource Optimizer (`models/optimizer.py`)  
**Solver Implementation:** Google OR-Tools (`pywraplp` SCIP / CBC) with Priority Heuristic Fallback  

---

## 1. Problem Formulation & Operational Context

Tertiary hospitals admit patient cohorts possessing heterogeneous clinical acuities under constrained physical bed ceilings and specialized nursing ratios. When arrivals exceed licensed bed counts in a primary unit, administrators must make constrained routing decisions:
1. Transfer eligible patients to clinically compatible secondary overflow beds (e.g., General Medicine overflow to vacant Surgery beds).
2. Prioritize high-acuity life-critical cohorts (ICU, severe trauma) over lower-acuity cohorts.
3. Explicitly report remaining unmet demand as operational deficits requiring emergency surge protocols (e.g., hallway surge beds, regional divert) rather than hiding or forcing invalid admissions.

---

## 2. Mathematical Program Formulation

### Sets and Indices
- $p \in P$: Patient triage groups, where:
  $$P = \{\text{ICU\_Critical}, \text{Emergency\_Trauma}, \text{Surgery\_PostOp}, \text{General\_Medical}, \text{Pediatric}\}$$
- $d \in D$: Clinical inpatient departments, where:
  $$D = \{\text{ICU}, \text{Emergency}, \text{Surgery}, \text{Internal Medicine}, \text{Pediatrics}\}$$
- $\mathcal{C} \subseteq P \times D$: Permissible clinical compatibility pairs defining whether patient group $p$ can be safely cared for in department $d$. Pairs not in $\mathcal{C}$ are strictly prohibited:
  $$\mathcal{C} = \begin{cases}
  (\text{ICU\_Critical}, \text{ICU}), \\
  (\text{Surgery\_PostOp}, \text{Surgery}), \; (\text{Surgery\_PostOp}, \text{Internal Medicine}), \\
  (\text{General\_Medical}, \text{Internal Medicine}), \; (\text{General\_Medical}, \text{Emergency}), \; (\text{General\_Medical}, \text{Surgery}), \\
  (\text{Pediatric}, \text{Pediatrics}), \\
  (\text{Emergency\_Trauma}, \text{Emergency}), \; (\text{Emergency\_Trauma}, \text{ICU})
  \end{cases}$$
- $t \in \{1, \dots, H\}$: Discrete planning horizons (e.g. shifts or forward days).

---

### Parameters
- $D_p \in \mathbb{Z}_{\ge 0}$: Influx demand count for patient triage group $p$.
- $C_d^{\text{gross}} \in \mathbb{Z}_{\ge 0}$: Total licensed staffed beds in department $d$.
- $\Delta_d \in \mathbb{Z}_{\ge 0}$: Damaged, bio-contaminated, or maintenance-offline beds in department $d$.
- $C_d = \max(0, C_d^{\text{gross}} - \Delta_d)$: Net effective available capacity in department $d$.
- $W_p \in \mathbb{R}_{> 0}$: Acuity penalty weight for unallocated patient of group $p$.
- $T_{p, d} \in \mathbb{R}_{\ge 0}$: Secondary transfer friction penalty for placing group $p$ in eligible unit $d$.
- $N_d \in \mathbb{Z}_{\ge 0}$: Available registered nurses on duty in department $d$.
- $r_d \in \mathbb{R}_{> 0}$: Minimum required nurse-to-patient acuity ratio in department $d$.
- $S_d \in \mathbb{R}_{> 0}$: Cost per supplemental float-pool nurse shift mobilized to unit $d$.
- $S_d^{\max} \in \mathbb{Z}_{\ge 0}$: Maximum supplemental float nurses mobilizable to unit $d$.

#### Penalty Weight Rationale
| Patient Group $p$ | Unmet Penalty $W_p$ | Clinical Justification |
| :--- | :---: | :--- |
| `ICU_Critical` | **1000** | Imminent life-threat; invasive mechanical ventilation or continuous inotrope titration required. |
| `Emergency_Trauma` | **800** | Acute hemorrhagic or neuro-trauma risk within golden resuscitation hour. |
| `Surgery_PostOp` | **300** | Post-anesthesia PACU step-down delay; potential surgical airway or wound compromise. |
| `Pediatric` | **250** | Vulnerable pediatric physiology; requires dedicated pediatric nursing competencies. |
| `General_Medical` | **100** | Sub-acute medical stabilization; lower immediate decompensation risk. |

Transfer penalties ($T_{p, d} \in [10, 25]$) are **orders of magnitude smaller** than unmet penalties ($W_p \in [100, 1000]$). This guarantees a strict lexicographic preference:
$$\text{Primary Placement} \succ \text{Secondary Placement} \succ \text{Unmet Demand}$$
An unallocated patient is never accepted if a clinically compatible bed exists, but primary beds are always exhausted before secondary overflow is utilized.

---

### Decision Variables
- $x_{p, d} \in \mathbb{Z}_{\ge 0}$: Number of patients of group $p$ allocated to department $d$.
- $u_p \in \mathbb{Z}_{\ge 0}$: Slack variable representing unallocated patient demand for group $p$.
- $s_d \in \mathbb{Z}_{\ge 0}$: Integer count of supplemental float nurses assigned to department $d$.

---

### Objective Function
$$\min_{x, u, s} \quad \mathcal{Z} = \sum_{p \in P} W_p u_p + \sum_{(p, d) \in \mathcal{C}} T_{p, d} x_{p, d} + \sum_{d \in D} S_d s_d$$

---

### Hard Constraints

1. **Demand Conservation:** Every incoming patient is either allocated to an approved unit or accounted for as explicit unmet demand:
   $$\sum_{d: (p, d) \in \mathcal{C}} x_{p, d} + u_p = D_p, \quad \forall p \in P$$

2. **Physical Department Capacity Ceiling:** No department can be allocated beyond its net effective available capacity:
   $$\sum_{p: (p, d) \in \mathcal{C}} x_{p, d} \le C_d, \quad \forall d \in D$$

3. **Clinical Specialty Compatibility:** Prohibited patient-department pairings are excluded by construction:
   $$x_{p, d} = 0, \quad \forall (p, d) \notin \mathcal{C}$$

4. **Nurse-to-Patient Acuity Staffing Bounds:** When staffing constraints are active, allocated patient volume must not breach licensed acuity ratios:
   $$r_d \cdot \sum_{p: (p, d) \in \mathcal{C}} x_{p, d} \le N_d + s_d, \quad \forall d \in D$$

5. **Float-Pool Mobilization Bounds:**
   $$0 \le s_d \le S_d^{\max}, \quad \forall d \in D$$

6. **Integrality & Non-Negativity:**
   $$x_{p, d} \in \mathbb{Z}_{\ge 0}, \quad u_p \in \mathbb{Z}_{\ge 0}, \quad s_d \in \mathbb{Z}_{\ge 0}$$

---

## 3. Solver Status & Diagnostic Guarantees

The optimizer handles solver termination codes strictly:
- **`OPTIMAL`:** Proven minimum-cost allocation satisfying all hard bounds with optimality gap $0.0\%$.
- **`FEASIBLE`:** Solution found satisfying all hard bounds within time limit, but branch-and-bound tree not exhausted.
- **`INFEASIBLE`:** Mathematically impossible to satisfy hard constraints (not possible in standard formulation due to slack variables $u_p$).
- **`UNKNOWN` / `TIME_LIMIT`:** Handled gracefully with fallback activation.

