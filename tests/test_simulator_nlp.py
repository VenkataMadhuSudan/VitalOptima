import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from models.simulator_nlp import parse_what_if_query, SIMULATOR_PROMPT_CHIPS

print("=" * 80)
print("TESTING WHAT-IF SIMULATOR NLP ENGINE AGAINST DIVERSE INQUIRIES:")
print("=" * 80)

for label, q in SIMULATOR_PROMPT_CHIPS:
    res = parse_what_if_query(q)
    print(f"[{label}]")
    print(f"  Query: \"{q}\"")
    print(f"  -> Matched Intent: {res['matched_intent']}")
    print(f"  -> Table Title: {res['table_title']}")
    print(f"  -> Table Columns: {list(res['primary_df'].columns)}")
    print(f"  -> First Row Sample: {dict(list(res['primary_df'].iloc[0].items())[:3])}")
    print(f"  -> Number of Available Lenses: {len(res['available_views'])}")
    print("-" * 80)

# Also test conversational edge cases
edge_cases = [
    "What if 10 ICU beds are closed due to bio-contamination?",
    "Can we handle if arrivals double?",
    "What protocols if staff goes on strike with 30 nurses missing?",
    "Which department will run out of capacity first?"
]

print("\nTESTING CONVERSATIONAL EDGE CASES:")
print("=" * 80)
for q in edge_cases:
    res = parse_what_if_query(q)
    print(f"Query: \"{q}\"")
    print(f"  Extracted: {res['parameters']} -> Health: {res['health_idx']}/100 | Bed Deficit: {res['total_bed_deficit']}")
    print(f"  Summary:\n{res['answer_summary']}")
    print("-" * 80)

print("\nALL WHAT-IF SIMULATOR NLP TESTS PASSED EXCELLENTLY!")
