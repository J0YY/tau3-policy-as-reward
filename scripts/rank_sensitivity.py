"""Descriptive ranking changes; validated-score cohort and all-replay sensitivity."""

import itertools, json, pathlib
from scipy.stats import kendalltau, rankdata

ROOT = pathlib.Path(__file__).resolve().parents[1]
s = json.loads((ROOT / "results/summary.json").read_text())["submissions"]
out = {}
for cohort, ss in [
    ("published_reproduced", [x for x in s if x["matches_published"]]),
    ("all_replayed", s),
]:
    base = [x["r0"] for x in ss]
    result = {}
    for regime in ["r1", "r1s", "r2", "r3", "r4"]:
        values = [x[regime + "_pass1"] for x in ss]
        pairs = []
        ties = []
        for i, j in itertools.combinations(range(len(ss)), 2):
            a = base[i] - base[j]
            b = values[i] - values[j]
            if a * b < 0 and abs(a) > 1e-9 and abs(b) > 1e-9:
                pairs.append([ss[i]["submission"], ss[j]["submission"]])
            if (abs(a) < 1e-9) != (abs(b) < 1e-9):
                ties.append([ss[i]["submission"], ss[j]["submission"]])
        result[regime] = {
            "n": len(ss),
            "kendall_tau_b": float(kendalltau(base, values).statistic),
            "strict_order_reversals": pairs,
            "tie_changes": ties,
        }
    out[cohort] = result
(ROOT / "results/rank_sensitivity.json").write_text(json.dumps(out, indent=2))
print(
    {
        c: {
            k: (
                v["kendall_tau_b"],
                len(v["strict_order_reversals"]),
                len(v["tie_changes"]),
            )
            for k, v in d.items()
        }
        for c, d in out.items()
    }
)
