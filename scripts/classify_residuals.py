"""Transparent structural taxonomy, not adjudication of remaining legal errors."""

import collections, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
raw = json.loads((ROOT / "results/candidate_diagnostics.json").read_text())
counts = collections.Counter()
rows = []
for row in raw["rows"]:
    cats = set()
    details = collections.defaultdict(list)
    for path in row["differences"]:
        parts = path.split("/")
        table = parts[1]
        field = parts[-1].split(":")[0] if len(parts) > 4 else None
        if table == "debit_card_disputes" and field in {
            "customer_max_liability_amount",
            "provisional_credit_amount",
            "provisional_credit_eligible",
            "provisional_credit_issued",
        }:
            cat = "retained_liability_or_credit_choice"
        elif table == "debit_card_disputes" and field is not None:
            cat = "retained_dispute_facts_or_classification"
        elif table == "debit_card_disputes":
            cat = "dispute_record_presence_or_identity"
        elif table == "agent_discoverable_tools":
            cat = "required_tool_log_difference"
        elif table == "verification_history":
            cat = "verification_record_or_timestamp"
        elif table in {"debit_cards", "debit_card_orders"}:
            cat = "card_servicing_state_or_order_identity"
        elif table == "human_transfer_requests":
            cat = "escalation_record"
        else:
            cat = "other_financial_state"
        cats.add(cat)
        details[cat].append(path)
    counts.update(cats)
    rows.append(
        {k: row[k] for k in ["submission", "simulation", "task"]}
        | {"categories": sorted(cats), "paths_by_category": dict(details)}
    )
out = {
    "method": "Deterministic classification by table and field name; categories overlap. Does not infer which residual is legally or operationally erroneous.",
    "run_counts": dict(counts),
    "rows": rows,
}
(ROOT / "results/residual_taxonomy.json").write_text(json.dumps(out, indent=2))
print(dict(counts))
