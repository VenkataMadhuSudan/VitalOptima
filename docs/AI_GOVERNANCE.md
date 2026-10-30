# VitalOptima — AI Governance, Guardrails & Bounded Tool Architecture

**Document:** `docs/AI_GOVERNANCE.md`  
**Author:** AI Governance Specialist & Senior Software Architect  
**Scope:** LLM Integration, Bounded Tool Execution, Prompt Injection Defenses, Deterministic Fallbacks  
**Verification Suite:** `tests/test_ai_agent_suite.py` & `tests/test_cybersecurity_and_governance.py`  

---

## 1. Architectural Philosophy: Calculations Outside the Model

A foundational failure mode in AI-assisted enterprise healthcare is delegating mathematical optimization, statistical inference, or clinical triage to probabilistic language models. LLMs suffer from non-deterministic variance, hallucinations, and inability to prove combinatorial constraint satisfaction.

```
+-----------------------------------------------------------------------------------+
|                        DETERMINISTIC COMPUTATIONAL CORE                           |
|  - Google OR-Tools MILP Solver: Mathematical allocations & capacity bounds        |
|  - Scikit-Learn Forecaster: Non-leaky empirical arrival forecasts & intervals    |
|  - Relational Database Engine: ACID transactions, unique indexes, audit chain     |
+-----------------------------------------+-----------------------------------------+
                                          |
                        Structured JSON Evidence Package
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            AI INTERPRETATION LAYER                                |
|  - Language Models: Grok / OpenAI / Offline Deterministic Engine                  |
|  - Responsibilities: Natural language synthesis, executive briefing summaries   |
|  - Strict Boundaries: CANNOT mutate databases, change beds, or alter allocations |
+-----------------------------------------------------------------------------------+
```

### Absolute Governance Guardrails
1. **No Autonomous Clinical Actions:** The language model **cannot** admit patients, discharge patients, alter bed numbers, or prescribe medical interventions.
2. **No Arbitrary SQL Execution:** The AI client has zero access to raw SQL execution endpoints.
3. **Strict Human Authorization Required:** Every optimization recommendation requires explicit administrator review, rationale entry, and cryptographic sign-off before being committed.

---

## 2. Bounded, Read-Only Tool Registry

When an external LLM agent is active (e.g. xAI Grok), it is restricted to an allowlist of 7 bounded read-only analytical tools in `src/agent_tools.py`:

| Tool Name | Permitted Functionality | Mutation Rights | Output Constraints |
| :--- | :--- | :---: | :--- |
| `get_historical_trends` | Aggregates 365-day census trends | **READ ONLY** | Max 10 summary metrics |
| `get_forecast_summary` | Returns forward 7-day predicted census | **READ ONLY** | Bounded to horizon $\le 7$ days |
| `get_forecast_evaluation` | Inspects hold-out MAE/RMSE/WAPE metrics | **READ ONLY** | Summarized error tables |
| `check_capacity_risks` | Inspects current bed saturation by ward | **READ ONLY** | Department capacity numbers |
| `check_staffing_shortages` | Audits 7-day shift nurse deficits | **READ ONLY** | Filterable by department string |
| `check_inventory_alerts` | Audits stockouts & reorder thresholds | **READ ONLY** | Top consumables status |
| `run_demand_what_if` | Executes deterministic forward shock test | **READ ONLY** | Simulated metrics (no db writes) |

### 2.1 Defensive Argument Schema Filtering
To prevent unexpected argument exceptions (`TypeError: unexpected keyword argument`) caused by LLM hallucinations:
```python
def execute_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if name not in TOOL_REGISTRY:
        return {"error": f"Tool '{name}' is not in the allowlist of safe analytical tools."}
    
    fn = TOOL_REGISTRY[name]
    sig = inspect.signature(fn)
    # Strictly filter arguments to permitted parameter names
    valid_args = {k: v for k, v in (arguments or {}).items() if k in sig.parameters}
    return fn(**valid_args)
```

---

## 3. SQL Injection Resistance & Parameterized Queries

The natural language query engine (`db/nlp_query.py`) translates user inquiries into SQL:
1. **Template-Driven Parsing:** Intent classification maps queries to pre-compiled SQL query templates.
2. **Strict Parameter Binding:** User filter tokens (e.g., blood types `'O-'`, department names `'ICU'`) are bound exclusively via parameterized SQL tuples:
   ```python
   cursor.execute("SELECT * FROM blood_bank_inventory WHERE blood_group = ?", (clean_group,))
   ```
   Direct string interpolation (`f"SELECT ... WHERE dept = '{user_input}'"`) is strictly forbidden.
3. **Test Verification:** Verified in `tests/test_cybersecurity_and_governance.py` with SQL injection payloads (`' OR 1=1 --`).

---

## 4. Deterministic Offline Fallback Guarantee

VitalOptima operates with **zero cloud dependencies**:
- If `XAI_API_KEY` is missing, invalid, or encountering network timeouts, the platform automatically activates `generate_deterministic_insights()`.
- Produces a structured 9-field operational executive briefing computed directly from real census, department resources, and staffing rosters with **zero hallucination risk**.
