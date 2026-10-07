"""Identify denominator explanations without forcing the published baseline."""

import collections, json, pathlib, statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / "results/summary.json").read_text())
ledger = []
cohorts = {}
for s in summary["submissions"]:
    rows = json.loads(
        (ROOT / "results/public" / (s["submission"] + ".json")).read_text()
    )["rows"]
    groups = collections.defaultdict(list)
    for r in rows:
        if r["status"] in {"ok", "excluded_infrastructure"}:
            groups[r["task"]].append(r.get("r0") or 0.0)
    incl = statistics.mean(statistics.mean(v) for v in groups.values()) * 100
    if not s["matches_published"]:
        ledger.append(
            {
                "submission": s["submission"],
                "model": s["model"],
                "published": s["published"],
                "official_exclude_infra": s["r0"],
                "infra_as_failure_sensitivity": incl,
                "infra_count": s["infrastructure_exclusions"],
                "denominator_alone_explains": abs(incl - s["published"]) <= 0.005001,
                "remaining_status": "denominator convention explains to rounding"
                if abs(incl - s["published"]) <= 0.005001
                else "unresolved archive/metadata discrepancy; not assigned a cause",
            }
        )
for name, ss in [
    (
        "published_reproduced",
        [s for s in summary["submissions"] if s["matches_published"]],
    ),
    ("all_replayed", summary["submissions"]),
]:
    rows = [
        r
        for s in ss
        for r in json.loads(
            (ROOT / "results/public" / (s["submission"] + ".json")).read_text()
        )["rows"]
    ]
    d = {}
    for t in ["task_082", "task_083", "task_084", "task_086"]:
        rr = [r for r in rows if r["task"] == t and r["status"] == "ok"]
        d[t] = {
            "scored": len(rr),
            "termination_gated": sum(r.get("termination_gated", False) for r in rr),
            "normal_completion": sum(
                r.get("termination_reason") in {"agent_stop", "user_stop"} for r in rr
            ),
            "r0": sum(r["r0"] or 0 for r in rr),
            "predicates": sum(
                r.get("r2_details", {}).get("predicate_pass", False) for r in rr
            ),
            "r2": sum(r["r2"] or 0 for r in rr),
        }
    cohorts[name] = {
        "submissions": len(ss),
        "archive_simulations": len(rows),
        "tasks": d,
    }
(ROOT / "results/baseline_reconciliation.json").write_text(
    json.dumps({"ledger": ledger, "cohorts": cohorts}, indent=2)
)
print(json.dumps({"ledger": ledger, "cohorts": cohorts}, indent=2))
