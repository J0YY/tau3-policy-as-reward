"""Descriptive recorded-state outcomes and capability associations.

No speech or legal labels. Unconditional denominators include scored early stops.
Family grouping uses model-lineage names; correlation is descriptive, not causal.
"""

import collections
import json
import os
from pathlib import Path
import socket
import numpy as np
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = {"task_082", "task_084", "task_086"}
EXCLUDED = PRIMARY | {"task_083", "task_085", "task_087", "task_088", "task_091"}
TX = {
    "extra084": "btxn_b1f6e32g5f78",
    "extra086": "btxn_85b8c13c1173",
    "tech084": "btxn_c2g7f43h6g89",
    "tech086": "btxn_5690acdd3de5",
    "pin082": "btxn_b17aa1648835",
}
METRICS = {
    "extra084": "task_084",
    "extra086": "task_086",
    "low084": "task_084",
    "low086": "task_086",
    "nonshared082": "task_082",
}


def family(sid):
    for prefix, label in [
        ("claude", "Claude"),
        ("gpt", "GPT"),
        ("gemini", "Gemini"),
        ("grok", "Grok"),
        ("xai", "Grok"),
        ("qwen", "Qwen"),
        ("glm", "GLM"),
        ("kimi", "Kimi"),
        ("muse", "Muse"),
        ("inkling", "Inkling"),
    ]:
        if sid.startswith(prefix):
            return label
    raise ValueError(sid)


def matching(disputes, tx):
    return [r for r in disputes if r.get("transaction_id") == tx]


def value_category(records, field):
    if not records:
        return "missing record"
    if len(records) > 1:
        return "multiple records"
    v = records[0].get(field)
    if v is None:
        return "missing field"
    if type(v) in (int, float) and np.isfinite(v):
        return f"{v:g}"
    return str(v)


def numeric(records):
    if len(records) != 1:
        return None
    x = records[0].get("customer_max_liability_amount")
    return float(x) if type(x) in (int, float) and np.isfinite(x) else None


def outcomes(disputes, tid):
    out = {}
    if tid in ("task_084", "task_086"):
        suffix = tid[-3:]
        extra = matching(disputes, TX["extra" + suffix])
        tech = matching(disputes, TX["tech" + suffix])
        x = numeric(tech)
        out.update(
            {
                f"extra{suffix}": bool(extra),
                f"low{suffix}": x is not None and 0 <= x <= 50,
                "extra_record_count": len(extra),
                "liability": x,
                "liability_category": value_category(
                    tech, "customer_max_liability_amount"
                ),
            }
        )
    if tid == "task_082":
        pin = matching(disputes, TX["pin082"])
        v = pin[0].get("pin_compromised") if len(pin) == 1 else None
        out.update(
            nonshared082=v in ("unknown", "no", "yes_observed"),
            pin_category=value_category(pin, "pin_compromised"),
            pin_shared_voluntarily=pin[0].get("pin_shared_voluntarily")
            if len(pin) == 1
            else None,
        )
    return out


def corr(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if (
        len(a) < 2
        or len(a) != len(b)
        or not np.isfinite(a).all()
        or not np.isfinite(b).all()
    ):
        return None
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def rank_correlation(x, y, groups=None):
    a = rankdata(x)
    b = rankdata(y)
    if groups is not None:
        g = np.asarray(groups)
        for name in set(groups):
            ids = g == name
            a[ids] -= np.mean(a[ids])
            b[ids] -= np.mean(b[ids])
    return corr(a, b)


def associations(subs, seed=20261007, n_boot=10000):
    rng = np.random.default_rng(seed)
    groups = sorted({s["family"] for s in subs})
    result = {}
    for metric in METRICS:
        valid = [s for s in subs if s["rates"][metric] is not None]
        x = np.array([s["unaffected_score"] for s in valid])
        y = np.array([s["rates"][metric] for s in valid])
        g = np.array([s["family"] for s in valid])
        boots = []
        for _ in range(n_boot):
            selected = rng.choice(groups, len(groups), replace=True)
            ids = np.concatenate([np.flatnonzero(g == f) for f in selected])
            v = rank_correlation(x[ids], y[ids])
            if v is not None:
                boots.append(v)
        loo = []
        for group in groups:
            keep = g != group
            v = rank_correlation(x[keep], y[keep])
            if v is not None:
                loo.append(v)
        result[metric] = {
            "n_submissions": len(valid),
            "spearman": rank_correlation(x, y),
            "family_centered_rank_correlation": rank_correlation(x, y, g),
            "raw_spearman_family_bootstrap_95_percentile": np.quantile(
                boots, [0.025, 0.975]
            ).tolist()
            if boots
            else None,
            "bootstrap_defined": len(boots),
            "raw_spearman_leave_one_family_out_range": [min(loo), max(loo)]
            if loo
            else None,
        }
    return result


def main():
    allrows = []
    submissions = []
    missing = []
    summary = {
        s["submission"]: s
        for s in json.loads((ROOT / "results/summary.json").read_text())["submissions"]
    }
    for f in sorted((ROOT / "results/public").glob("*.json")):
        d = json.loads(f.read_text())
        sid = f.stem
        for r in d["rows"]:
            if r["task"] in PRIMARY and r["status"] == "ok" and "disputes" not in r:
                missing.append((sid, d, r))
    # Only nine early-stop runs lack an already saved state; replay these once.
    cachepath = ROOT / "results/extra_state_replays.json"
    cache = json.loads(cachepath.read_text()) if cachepath.exists() else {}
    if any(r["simulation"] not in cache for _, _, r in missing):
        from loguru import logger

        logger.remove()
        from tau2.data_model.simulation import SimulationRun
        from regrade.core import tasks, replay_sim, normalize_archive_simulation, table

        sources = {}
        for sid, d, r in missing:
            key = r["simulation"]
            if key in cache:
                continue
            if sid not in sources:
                path = ROOT / d["provenance"]["source"]
                raw = json.loads(path.read_text())
                sources[sid] = {s["id"]: s for s in raw.get("simulations", [])}
            raw = sources[sid][key]
            sim = SimulationRun.model_validate(normalize_archive_simulation(raw)[0])
            env, _ = replay_sim(tasks()[r["task"]], sim)
            cache[key] = {
                "disputes": list(
                    table(env.tools.db.model_dump(), "debit_card_disputes").values()
                ),
                "source": d["provenance"]["source"],
                "termination_reason": r["termination_reason"],
            }
            print("Recovered state", sid, r["task"], key, flush=True)
        cachepath.write_text(json.dumps(cache, indent=2) + "\n")
    for f in sorted((ROOT / "results/public").glob("*.json")):
        d = json.loads(f.read_text())
        sid = f.stem
        per_task = collections.defaultdict(list)
        chosen = []
        for r in d["rows"]:
            if r["status"] != "ok":
                continue
            if r["task"] not in EXCLUDED and r.get("r0") is not None:
                per_task[r["task"]].append(r["r0"])
            if r["task"] not in PRIMARY:
                continue
            disputes = r.get("disputes", cache.get(r["simulation"], {}).get("disputes"))
            if disputes is None:
                raise ValueError("State missing " + r["simulation"])
            row = {
                "submission": sid,
                "simulation": r["simulation"],
                "task": r["task"],
                "termination_reason": r["termination_reason"],
                **outcomes(disputes, r["task"]),
            }
            chosen.append(row)
            allrows.append(row)
        sub = {
            "submission": sid,
            "model": summary[sid]["model"],
            "family": family(sid),
            "matches_published": summary[sid]["matches_published"],
            "unaffected_score": 100 * np.mean([np.mean(v) for v in per_task.values()]),
            "unaffected_n_tasks": len(per_task),
            "unaffected_task_scores": {
                k: float(np.mean(v)) for k, v in per_task.items()
            },
            "rates": {},
            "denominators": {},
        }
        for metric, tid in METRICS.items():
            rows = [r for r in chosen if r["task"] == tid]
            sub["denominators"][metric] = len(rows)
            sub["rates"][metric] = (
                np.mean([r[metric] for r in rows]).item() if rows else None
            )
        submissions.append(sub)
    common_tasks = sorted(
        set.intersection(*(set(s["unaffected_task_scores"]) for s in submissions))
    )
    for sub in submissions:
        sub["available_task_score"] = sub["unaffected_score"]
        sub["unaffected_score"] = (
            float(np.mean([sub["unaffected_task_scores"][t] for t in common_tasks]))
            * 100
        )
    counts = {}
    for tid in sorted(PRIMARY):
        rows = [r for r in allrows if r["task"] == tid]
        counts[tid] = {
            "n": len(rows),
            "early_stop_n": sum(
                r["termination_reason"] not in ("agent_stop", "user_stop") for r in rows
            ),
        }
        for metric, t in METRICS.items():
            if t == tid:
                counts[tid][metric] = sum(r[metric] for r in rows)
        field = "pin_category" if tid == "task_082" else "liability_category"
        counts[tid][field] = dict(collections.Counter(r[field] for r in rows))
    result = {
        "host": socket.gethostname(),
        "slurm_job": os.getenv("SLURM_JOB_ID"),
        "cohort": "All 32 accessible submissions; all 111 scored trials per primary task; infrastructure excluded, early stops included",
        "unaffected_excluded_tasks": sorted(EXCLUDED),
        "common_unaffected_tasks": common_tasks,
        "common_unaffected_task_count": len(common_tasks),
        "family_definition": "Model-name lineage, including Grok and xai-realtime in one family; singleton lineages retained",
        "bootstrap_seed": 20261007,
        "bootstrap_resamples": 10000,
        "counts": counts,
        "submissions": submissions,
        "rows": allrows,
        "associations": associations(submissions),
        "available_task_score_sensitivity": associations(
            [{**s, "unaffected_score": s["available_task_score"]} for s in submissions]
        ),
        "reproduced_cohort_sensitivity": associations(
            [s for s in submissions if s["matches_published"]]
        ),
    }
    (ROOT / "results/state_outcomes.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        json.dumps({"counts": counts, "associations": result["associations"]}, indent=2)
    )


if __name__ == "__main__":
    main()
