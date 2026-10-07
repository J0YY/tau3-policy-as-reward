"""Task-weighted pass^k, paired task bootstrap, explicit replay/coverage ledger."""

import collections, csv, json, math, pathlib
import numpy as np
from scipy.stats import kendalltau, spearmanr

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGIMES = ["r0", "r1", "r1s", "r2", "r3", "r4"]


def task_scores(rows, regime, k=1):
    groups = collections.defaultdict(list)
    for r in rows:
        if r.get("status") == "ok" and r.get(regime) is not None:
            groups[r["task"]].append(r[regime])
    if not groups or k > min(map(len, groups.values())):
        return {}
    return {
        t: math.comb(int(sum(v)), k) / math.comb(len(v), k)
        for t, v in groups.items()
        if len(v) >= k
    }


def ci_delta(rows, regime):
    a = task_scores(rows, "r0")
    b = task_scores(rows, regime)
    # R1 changes denominator; paired bootstrap uses same draw then excludes tasks.
    keys = sorted(a)
    av = np.array([a[t] for t in keys])
    bv = np.array([b.get(t, np.nan) for t in keys])
    rng = np.random.default_rng(20261007)
    idx = rng.integers(0, len(keys), (10000, len(keys)))
    delta = (np.nanmean(bv[idx], axis=1) - av[idx].mean(axis=1)) * 100
    return np.quantile(delta, [0.025, 0.975]).tolist()


def main():
    summary = []
    allrows = []
    coverage = []
    for p in sorted((ROOT / "results/public").glob("*.json")):
        d = json.loads(p.read_text())
        rows = d["rows"]
        sid = p.stem
        allrows.extend(rows)
        meta = json.loads(
            (
                ROOT
                / "data/leaderboard/web/leaderboard/public/submissions"
                / sid
                / "submission.json"
            ).read_text()
        )
        pub = meta["results"]["banking_knowledge"]
        r0 = task_scores(rows, "r0")
        score = np.mean(list(r0.values())) * 100
        row = {
            "submission": sid,
            "model": meta["model_name"],
            "retrieval": pub.get("retrieval_config"),
            "modality": meta.get("modality", "text"),
            "simulations": len(rows),
            "replay_errors": sum(r["status"] == "error" for r in rows),
            "infrastructure_exclusions": sum(
                r["status"] == "excluded_infrastructure" for r in rows
            ),
            "r0_tasks": len(r0),
            "r0": score,
            "published": pub["pass_1"],
            "matches_published": bool(abs(score - pub["pass_1"]) <= 0.005001),
        }
        for regime in REGIMES:
            for k in range(1, 5):
                scores = task_scores(rows, regime, k)
                row[f"{regime}_tasks_k{k}"] = len(scores)
                row[f"{regime}_trials_k{k}"] = sum(
                    r.get("status") == "ok"
                    and r.get(regime) is not None
                    and r["task"] in scores
                    for r in rows
                )
                row[f"{regime}_pass{k}"] = (
                    np.mean(list(scores.values())) * 100 if scores else None
                )
            row[regime + "_delta_ci"] = ci_delta(rows, regime)
        summary.append(row)
        coverage.append(
            {
                "submission": sid,
                "n": len(rows),
                "errors": [r for r in rows if r["status"] == "error"],
                "provenance": d["provenance"],
            }
        )
    if not summary:
        return
    counts = {}
    for tid in ["task_082", "task_083", "task_084", "task_086"]:
        rr = [r for r in allrows if r["task"] == tid and r["status"] == "ok"]
        counts[tid] = {
            "n": len(rr),
            "r0_pass": sum(r["r0"] or 0 for r in rr),
            "predicate_pass": sum(
                r.get("r2_details", {}).get("predicate_pass", False) for r in rr
            ),
            "r2_pass": sum(r["r2"] or 0 for r in rr),
            "r4_gains": sum((r["r4"] or 0) > (r["r0"] or 0) for r in rr),
        }
    payload = {
        "submissions": summary,
        "decision_counts": counts,
        "coverage": coverage,
        "total_simulations": len(allrows),
    }
    (ROOT / "results/summary.json").write_text(json.dumps(payload, indent=2))
    print(
        json.dumps(
            {
                "n": len(summary),
                "simulations": len(allrows),
                "counts": counts,
                "r0_matches": sum(x["matches_published"] for x in summary),
            },
            indent=2,
        )
    )
    with (ROOT / "results/score_table.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)


if __name__ == "__main__":
    main()
