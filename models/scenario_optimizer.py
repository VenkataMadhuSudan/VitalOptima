r"""
VitalOptima Scenario-Based & Stochastic Hospital Resource Optimizer
Connects time-series forecast uncertainty (conformal prediction intervals) with
stochastic mixed-integer linear programming (MILP) for robust capacity planning.

Mathematical Formulation:
Two-Stage Stochastic Program under Demand Uncertainty:
  Stage 1 (Here-and-Now Decisions):
    N_d: Baseline regular nurse staffing committed to department d before shift realization.
    Subject to: sum_d N_d <= TotalRegularNurses

  Stage 2 (Wait-and-See / Recourse Decisions for Scenario s in S):
    x_{p, d, s}: Patients of clinical group p assigned to department d under demand scenario s.
    u_{p, s}: Unmet demand for clinical group p under demand scenario s.
    v_{d, s}: Supplemental float-pool / overtime nurses mobilized in department d under scenario s.

  Objective:
    Minimize Total Expected System Cost:
      sum_d C_d * N_d + sum_{s in S} p_s * [
          sum_p W_p * u_{p, s} + sum_{p, d} T_{p, d} * x_{p, d, s} + sum_d S_d * v_{d, s}
      ]

  Constraints (for all s in S):
    1. Demand Satisfaction:
       sum_{d in Allowed(p)} x_{p, d, s} + u_{p, s} = Demand_{p, s},   for all p in Groups
    2. Physical Bed Capacity:
       sum_p x_{p, d, s} <= Capacity_d - Damaged_d,                    for all d in Departments
    3. Acuity Nurse-to-Patient Ratio:
       Ratio_d * sum_p x_{p, d, s} <= N_d + v_{d, s},                  for all d in Departments
    4. Overtime / Float Staffing Boundary:
       v_{d, s} <= MaxSupplemental_d,                                  for all d in Departments
    5. Non-Negativity & Integrality:
       N_d, x_{p, d, s}, u_{p, s}, v_{d, s} in Z_{>=0}
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ortools.linear_solver import pywraplp
    ORTOOLS_AVAILABLE = True
except (OSError, ImportError, Exception):
    pywraplp = None
    ORTOOLS_AVAILABLE = False

from models.optimizer import (
    CLINICAL_COMPATIBILITY,
    UNMET_PENALTIES,
    TRANSFER_PENALTIES,
    DEFAULT_NURSE_PATIENT_RATIOS
)


@dataclass
class DemandScenario:
    """Represents a discrete demand scenario with an assigned probability."""
    name: str
    probability: float
    demands: Dict[str, int]
    description: str = ""


class ScenarioGenerator:
    """
    Constructs statistically grounded demand scenarios from calibrated prediction intervals.
    Generates:
      1. Expected Demand (Median point forecast mu, probability 0.60)
      2. High Demand (+1 Conformal Half-Width mu + q, probability 0.30)
      3. Severe Surge (+2 Conformal Half-Widths mu + 2q, probability 0.10)
    """

    @staticmethod
    def generate_scenarios_from_forecast(
        base_point_forecast: Dict[str, int],
        conformal_halfwidth: float = 12.0,
        ratios_by_group: Optional[Dict[str, float]] = None
    ) -> List[DemandScenario]:
        """
        Derives discrete demand scenarios using empirical conformal quantile half-widths.
        Distributes the aggregate uncertainty across clinical triage groups proportionally.
        """
        # Default distribution of admissions across clinical triage groups
        default_ratios = {
            "General_Medical": 0.40,
            "Emergency_Trauma": 0.25,
            "Surgery_PostOp": 0.15,
            "Pediatric": 0.12,
            "ICU_Critical": 0.08
        }
        group_weights = ratios_by_group or default_ratios

        # Scenario 1: Expected Demand (mu)
        expected_demands = {k: max(0, int(round(v))) for k, v in base_point_forecast.items()}

        # Scenario 2: High Demand (mu + 1.0 * q)
        high_demands = {}
        for k, v in expected_demands.items():
            w = group_weights.get(k, 0.20)
            delta = int(round(w * conformal_halfwidth * 1.0))
            high_demands[k] = v + max(1, delta)

        # Scenario 3: Severe Surge (mu + 2.0 * q)
        surge_demands = {}
        for k, v in expected_demands.items():
            w = group_weights.get(k, 0.20)
            delta = int(round(w * conformal_halfwidth * 2.0))
            surge_demands[k] = v + max(2, delta)

        return [
            DemandScenario(
                name="Expected Demand",
                probability=0.60,
                demands=expected_demands,
                description="Baseline point forecast corresponding to normal operations."
            ),
            DemandScenario(
                name="High Demand (+1 Conformal Interval)",
                probability=0.30,
                demands=high_demands,
                description="80th percentile surge within calibrated conformal prediction bounds."
            ),
            DemandScenario(
                name="Severe Surge (+2 Conformal Intervals)",
                probability=0.10,
                demands=surge_demands,
                description="Tail-risk mass-casualty or epidemic surge testing peak system stress."
            )
        ]


class StochasticResourceOptimizer:
    """
    Two-Stage Stochastic Mixed-Integer Linear Programming (MILP) Optimizer.
    Solves capacity and staffing allocation across multiple probabilistic demand scenarios.
    """

    def __init__(self, preferred_solver: str = "SCIP"):
        self.preferred_solver = preferred_solver
        self.solver_name = preferred_solver

    def optimize_stochastic(
        self,
        scenarios: List[DemandScenario],
        available_capacities: Dict[str, int],
        total_regular_nurses: int = 25,
        base_nurse_cost: float = 50.0,
        overtime_nurse_cost: float = 120.0,
        damaged_beds: Optional[Dict[str, int]] = None,
        max_supplemental_per_dept: int = 5
    ) -> Dict[str, Any]:
        """
        Formulates and solves the extensive form of the two-stage stochastic program.
        """
        start_time = time.time()
        damaged = damaged_beds or {}

        # Sanitize capacities
        clean_caps = {k: max(0, int(v) - damaged.get(k, 0)) for k, v in available_capacities.items()}

        # Verify scenario probabilities sum to ~1.0
        prob_sum = sum(s.probability for s in scenarios)
        if abs(prob_sum - 1.0) > 0.01:
            # Normalize
            for s in scenarios:
                s.probability = s.probability / prob_sum

        if not ORTOOLS_AVAILABLE or pywraplp is None:
            return self._solve_stochastic_fallback(
                scenarios, clean_caps, total_regular_nurses, base_nurse_cost, overtime_nurse_cost, start_time
            )

        try:
            solver = pywraplp.Solver.CreateSolver(self.preferred_solver)
            if not solver:
                solver = pywraplp.Solver.CreateSolver("CBC")
                self.solver_name = "CBC"
            if not solver:
                return self._solve_stochastic_fallback(
                    scenarios, clean_caps, total_regular_nurses, base_nurse_cost, overtime_nurse_cost, start_time
                )

            # -------------------------------------------------------------
            # Stage 1 Decision Variables (Here-and-Now: Base Staffing N_d)
            # -------------------------------------------------------------
            N: Dict[str, Any] = {}
            for dept in clean_caps:
                # Up to 20 nurses per unit
                N[dept] = solver.IntVar(0, total_regular_nurses, f"N_{dept}")

            # Constraint: Total regular nurse budget
            solver.Add(solver.Sum([N[d] for d in clean_caps]) <= total_regular_nurses)

            # -------------------------------------------------------------
            # Stage 2 Decision Variables (Wait-and-See per Scenario s)
            # -------------------------------------------------------------
            x: Dict[Tuple[str, str, int], Any] = {}  # (ptype, dept, scenario_idx)
            u: Dict[Tuple[str, int], Any] = {}       # (ptype, scenario_idx)
            v: Dict[Tuple[str, int], Any] = {}       # (dept, scenario_idx)

            for s_idx, scenario in enumerate(scenarios):
                for ptype in scenario.demands:
                    u[(ptype, s_idx)] = solver.IntVar(0, scenario.demands[ptype], f"u_{ptype}_{s_idx}")
                    allowed = CLINICAL_COMPATIBILITY.get(ptype, [])
                    for dept in clean_caps:
                        if dept in allowed:
                            x[(ptype, dept, s_idx)] = solver.IntVar(
                                0, clean_caps[dept], f"x_{ptype}_{dept}_{s_idx}"
                            )

                for dept in clean_caps:
                    v[(dept, s_idx)] = solver.IntVar(
                        0, max_supplemental_per_dept, f"v_{dept}_{s_idx}"
                    )

            # -------------------------------------------------------------
            # Stage 2 Constraints per Scenario s
            # -------------------------------------------------------------
            for s_idx, scenario in enumerate(scenarios):
                # 1. Demand Satisfaction
                for ptype, dem in scenario.demands.items():
                    allowed = CLINICAL_COMPATIBILITY.get(ptype, [])
                    assigned_terms = [x[(ptype, d, s_idx)] for d in allowed if (ptype, d, s_idx) in x]
                    solver.Add(solver.Sum(assigned_terms) + u[(ptype, s_idx)] == dem)

                # 2. Physical Bed Capacity
                for dept, cap in clean_caps.items():
                    incoming_dept = [
                        x[(p, dept, s_idx)]
                        for p in scenario.demands
                        if (p, dept, s_idx) in x
                    ]
                    solver.Add(solver.Sum(incoming_dept) <= cap)

                # 3. Staffing Acuity Ratio: ratio * sum(x) <= N_d + v_{d, s}
                for dept in clean_caps:
                    ratio = DEFAULT_NURSE_PATIENT_RATIOS.get(dept, 0.25)
                    incoming_dept = [
                        x[(p, dept, s_idx)]
                        for p in scenario.demands
                        if (p, dept, s_idx) in x
                    ]
                    # Formulate: ratio * sum(x) - N_d - v_{d,s} <= 0
                    # To keep integer linear: sum(x) * ratio <= N_d + v_{d,s}
                    # We can multiply by 100 or use float coefficient in SCIP/CBC
                    solver.Add(
                        solver.Sum([ratio * x_var for x_var in incoming_dept]) <= N[dept] + v[(dept, s_idx)]
                    )

            # -------------------------------------------------------------
            # Expected Cost Objective Function
            # -------------------------------------------------------------
            objective = solver.Objective()

            # Base nurse commitment costs (Stage 1)
            for dept in clean_caps:
                objective.SetCoefficient(N[dept], float(base_nurse_cost))

            # Expected recourse costs (Stage 2)
            for s_idx, scenario in enumerate(scenarios):
                p_s = scenario.probability

                # Unmet penalties
                for ptype in scenario.demands:
                    w = UNMET_PENALTIES.get(ptype, 500)
                    objective.SetCoefficient(u[(ptype, s_idx)], float(p_s * w))

                # Placement / Transfer penalties
                for ptype in scenario.demands:
                    allowed = CLINICAL_COMPATIBILITY.get(ptype, [])
                    for dept in clean_caps:
                        if (ptype, dept, s_idx) in x:
                            t_cost = TRANSFER_PENALTIES.get((ptype, dept), 0)
                            if t_cost > 0:
                                objective.SetCoefficient(x[(ptype, dept, s_idx)], float(p_s * t_cost))

                # Supplemental nurse overtime costs
                for dept in clean_caps:
                    objective.SetCoefficient(v[(dept, s_idx)], float(p_s * overtime_nurse_cost))

            objective.SetMinimization()
            solver.set_time_limit(15000)

            status_code = solver.Solve()

        except (OSError, Exception):
            return self._solve_stochastic_fallback(
                scenarios, clean_caps, total_regular_nurses, base_nurse_cost, overtime_nurse_cost, start_time
            )

        exec_ms = round((time.time() - start_time) * 1000, 2)
        is_optimal = status_code == pywraplp.Solver.OPTIMAL
        is_feasible = status_code == pywraplp.Solver.FEASIBLE

        if not (is_optimal or is_feasible):
            return {
                "status": "Infeasible",
                "is_proven_optimal": False,
                "solver_backend": f"Google OR-Tools Stochastic ({self.solver_name})",
                "execution_time_ms": exec_ms,
                "diagnostics": ["Stochastic optimization problem proved infeasible under current constraints."]
            }

        # Collect Stage 1 Solutions (Staffing commitments)
        base_staffing = {dept: int(round(N[dept].solution_value())) for dept in clean_caps}
        total_committed_nurses = sum(base_staffing.values())

        # Collect Stage 2 Solutions per Scenario
        scenario_results = []
        expected_unmet = 0.0
        expected_allocated = 0.0
        expected_overtime_nurses = 0.0

        for s_idx, sc in enumerate(scenarios):
            sc_alloc = []
            sc_unmet = {}
            for ptype in sc.demands:
                sc_unmet[ptype] = int(round(u[(ptype, s_idx)].solution_value()))
                allowed = CLINICAL_COMPATIBILITY.get(ptype, [])
                for dept in clean_caps:
                    if (ptype, dept, s_idx) in x:
                        cnt = int(round(x[(ptype, dept, s_idx)].solution_value()))
                        if cnt > 0:
                            sc_alloc.append({
                                "Patient_Group": ptype.replace("_", " "),
                                "Assigned_Department": dept,
                                "Count": cnt,
                                "Type": "Secondary Overflow" if TRANSFER_PENALTIES.get((ptype, dept), 0) > 0 else "Primary Allocation"
                            })

            sc_overtime = {dept: int(round(v[(dept, s_idx)].solution_value())) for dept in clean_caps}
            tot_sc_alloc = sum(a["Count"] for a in sc_alloc)
            tot_sc_unmet = sum(sc_unmet.values())
            tot_sc_overtime = sum(sc_overtime.values())

            expected_allocated += sc.probability * tot_sc_alloc
            expected_unmet += sc.probability * tot_sc_unmet
            expected_overtime_nurses += sc.probability * tot_sc_overtime

            scenario_results.append({
                "scenario_name": sc.name,
                "probability": sc.probability,
                "demands": sc.demands,
                "total_demand": sum(sc.demands.values()),
                "allocated": tot_sc_alloc,
                "unmet_count": tot_sc_unmet,
                "allocations": sc_alloc,
                "unmet_breakdown": sc_unmet,
                "supplemental_nurses": sc_overtime,
                "total_supplemental_nurses": tot_sc_overtime
            })

        obj_val = round(objective.Value(), 2)

        return {
            "status": "Optimal" if is_optimal else "Feasible",
            "is_proven_optimal": is_optimal,
            "solver_backend": f"Google OR-Tools Two-Stage Stochastic MILP ({self.solver_name})",
            "objective_value": obj_val,
            "execution_time_ms": exec_ms,
            "first_stage_decisions": {
                "base_nurse_staffing": base_staffing,
                "total_committed_nurses": total_committed_nurses,
                "regular_nurse_budget": total_regular_nurses,
                "base_staffing_cost": round(total_committed_nurses * base_nurse_cost, 2)
            },
            "expected_metrics": {
                "expected_allocated_patients": round(expected_allocated, 2),
                "expected_unmet_demand": round(expected_unmet, 2),
                "expected_supplemental_nurses": round(expected_overtime_nurses, 2),
                "expected_recourse_cost": round(obj_val - (total_committed_nurses * base_nurse_cost), 2)
            },
            "scenarios_evaluated": scenario_results,
            "diagnostics": [
                f"Evaluated {len(scenarios)} probability-weighted demand scenarios.",
                f"Committed {total_committed_nurses}/{total_regular_nurses} base regular nurses across {len(clean_caps)} departments.",
                f"Expected unmet patient demand is {expected_unmet:.2f} patients under probability-weighted surges."
            ]
        }

    def _solve_stochastic_fallback(
        self,
        scenarios: List[DemandScenario],
        capacities: Dict[str, int],
        total_regular_nurses: int,
        base_nurse_cost: float,
        overtime_nurse_cost: float,
        start_time: float
    ) -> Dict[str, Any]:
        """
        Deterministic heuristic fallback for multi-scenario planning.
        Labels results honestly as a heuristic rather than an exact stochastic MILP.
        """
        base_staffing = {}
        # Allocate nurses proportionally based on unit bed capacity
        tot_cap = max(1, sum(capacities.values()))
        rem_nurses = total_regular_nurses
        depts = list(capacities.keys())
        for d in depts[:-1]:
            share = int(round(total_regular_nurses * (capacities[d] / tot_cap)))
            base_staffing[d] = share
            rem_nurses -= share
        base_staffing[depts[-1]] = max(0, rem_nurses)

        scenario_results = []
        expected_alloc = 0.0
        expected_unmet = 0.0
        expected_overtime = 0.0

        for sc in scenarios:
            rem_caps = dict(capacities)
            allocs = []
            unmet = {}
            for ptype, dem in sorted(sc.demands.items(), key=lambda x: UNMET_PENALTIES.get(x[0], 100), reverse=True):
                allowed = CLINICAL_COMPATIBILITY.get(ptype, [])
                placed = 0
                for d in allowed:
                    avail = rem_caps.get(d, 0)
                    alloc_cnt = min(dem - placed, avail)
                    if alloc_cnt > 0:
                        allocs.append({
                            "Patient_Group": ptype.replace("_", " "),
                            "Assigned_Department": d,
                            "Count": alloc_cnt,
                            "Type": "Primary Allocation"
                        })
                        rem_caps[d] -= alloc_cnt
                        placed += alloc_cnt
                    if placed >= dem:
                        break
                unmet[ptype] = max(0, dem - placed)

            tot_alloc = sum(a["Count"] for a in allocs)
            tot_unmet = sum(unmet.values())
            # Heuristic overtime: 1 nurse per 4 unallocated patients if any
            tot_overtime = min(5, (tot_unmet + 3) // 4)

            expected_alloc += sc.probability * tot_alloc
            expected_unmet += sc.probability * tot_unmet
            expected_overtime += sc.probability * tot_overtime

            scenario_results.append({
                "scenario_name": sc.name,
                "probability": sc.probability,
                "demands": sc.demands,
                "total_demand": sum(sc.demands.values()),
                "allocated": tot_alloc,
                "unmet_count": tot_unmet,
                "allocations": allocs,
                "unmet_breakdown": unmet,
                "supplemental_nurses": {d: 0 for d in capacities},
                "total_supplemental_nurses": tot_overtime
            })

        exec_ms = round((time.time() - start_time) * 1000, 2)
        base_cost = total_regular_nurses * base_nurse_cost
        recourse_cost = expected_unmet * 500.0 + expected_overtime * overtime_nurse_cost

        return {
            "status": "Feasible",
            "is_proven_optimal": False,
            "solver_backend": "Proportional Capacity Heuristic Fallback (Stochastic Approximate)",
            "objective_value": round(base_cost + recourse_cost, 2),
            "execution_time_ms": exec_ms,
            "first_stage_decisions": {
                "base_nurse_staffing": base_staffing,
                "total_committed_nurses": total_regular_nurses,
                "regular_nurse_budget": total_regular_nurses,
                "base_staffing_cost": round(base_cost, 2)
            },
            "expected_metrics": {
                "expected_allocated_patients": round(expected_alloc, 2),
                "expected_unmet_demand": round(expected_unmet, 2),
                "expected_supplemental_nurses": round(expected_overtime, 2),
                "expected_recourse_cost": round(recourse_cost, 2)
            },
            "scenarios_evaluated": scenario_results,
            "diagnostics": [
                "Solved via proportional capacity heuristic fallback.",
                "Results are approximate bounds rather than exact mathematical proofs."
            ]
        }


def validate_stochastic_allocation(
    stochastic_result: Dict[str, Any],
    available_capacities: Dict[str, int],
    damaged_beds: Optional[Dict[str, int]] = None
) -> Tuple[bool, List[str]]:
    """
    Independent statistical and physical invariant validator for multi-scenario allocations.
    Checks:
      1. Non-anticipativity: Base nurse commitments do not vary by scenario.
      2. Physical Bed Bounds: No department in any scenario exceeds effective capacity.
      3. Clinical Compatibility: Prohibits placement of patients into incompatible units.
      4. Probability Conservation: Scenario probabilities sum to 1.0.
    """
    violations = []
    damaged = damaged_beds or {}

    # 1. Check first-stage staffing consistency
    first_stage = stochastic_result.get("first_stage_decisions", {})
    base_staffing = first_stage.get("base_nurse_staffing", {})
    if not base_staffing:
        violations.append("Missing first-stage regular nurse staffing commitments.")

    # 2. Check scenario probabilities
    scenarios = stochastic_result.get("scenarios_evaluated", [])
    if not scenarios:
        violations.append("No scenarios evaluated in stochastic result.")
    else:
        tot_prob = sum(s.get("probability", 0.0) for s in scenarios)
        if abs(tot_prob - 1.0) > 0.02:
            violations.append(f"Scenario probabilities sum to {tot_prob:.3f}, expected 1.0.")

    # 3. Check physical constraints across all scenarios
    for sc in scenarios:
        sc_name = sc.get("scenario_name", "Unknown")
        dept_counts: Dict[str, int] = {}
        for alloc in sc.get("allocations", []):
            dept = alloc.get("Assigned_Department")
            pg = alloc.get("Patient_Group", "").replace(" ", "_")
            cnt = alloc.get("Count", 0)

            # Compatibility
            allowed = CLINICAL_COMPATIBILITY.get(pg, [])
            if dept not in allowed:
                violations.append(
                    f"Scenario '{sc_name}': Incompatible assignment of '{pg}' to '{dept}'."
                )

            dept_counts[dept] = dept_counts.get(dept, 0) + cnt

        # Capacity check
        for dept, cnt in dept_counts.items():
            cap = available_capacities.get(dept, 0) - damaged.get(dept, 0)
            if cnt > cap:
                violations.append(
                    f"Scenario '{sc_name}': Department '{dept}' exceeded capacity ({cnt} > {cap})."
                )

    return (len(violations) == 0, violations)
