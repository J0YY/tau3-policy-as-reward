"""Identify retained-state differences in predicate-satisfying public runs."""

import collections, copy, json, pathlib, socket, os
from loguru import logger
from tau2.data_model.simulation import SimulationRun
from regrade.core import *

ROOT = pathlib.Path(__file__).resolve().parents[1]


def diffs(a, b, path=""):
    if type(a) != type(b) and not (
        isinstance(a, (int, float)) and isinstance(b, (int, float))
    ):
        return [path + ":type"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(path + "/" + k + ":missing_pred")
            elif k not in b:
                out.append(path + "/" + k + ":extra_pred")
            else:
                out.extend(diffs(a[k], b[k], path + "/" + k))
        return out
    return [] if a == b else [path + ":value"]


def main():
    logger.remove()
    rows = []
    for f in sorted((ROOT / "results/public").glob("*.json")):
        result = json.loads(f.read_text())
        wanted = {
            r["simulation"]: r
            for r in result["rows"]
            if r["status"] == "ok" and r.get("r2_details", {}).get("predicate_pass")
        }
        if not wanted:
            continue
        path = ROOT / result["provenance"]["source"]
        raw = json.loads(path.read_text())
        sims = raw.get("simulations") or [
            json.loads((path.parent / "simulations" / (i + ".json")).read_text())
            for i in wanted
        ]
        for s in sims:
            if s["id"] not in wanted:
                continue
            t = tasks()[s["task_id"]]
            g, _, _ = replay_actions(t)
            env, _ = replay_sim(
                t, SimulationRun.model_validate(normalize_archive_simulation(s)[0])
            )
            p = env.tools.db.model_dump()
            gd = g.tools.db.model_dump()
            if t.id in LIABILITY:
                record(p, LIABILITY[t.id])[1]["customer_max_liability_amount"] = record(
                    gd, LIABILITY[t.id]
                )[1]["customer_max_liability_amount"]
            if t.id == "task_082":
                for key in ["pin_compromised", "pin_shared_voluntarily"]:
                    record(p, LOST)[1][key] = record(gd, LOST)[1][key]
            if t.id in EXTRA:
                key, _ = record(p, EXTRA[t.id]["transaction_id"])
                del table(p, "debit_card_disputes")[key]
            dd = diffs(p, gd)
            rows.append(
                {
                    "submission": f.stem,
                    "simulation": s["id"],
                    "task": t.id,
                    "differences": dd,
                }
            )
            print(f.stem, t.id, len(dd), flush=True)
    counts = collections.Counter(
        part.split("/")[1] for r in rows for part in set(r["differences"])
    )
    (ROOT / "results/candidate_diagnostics.json").write_text(
        json.dumps(
            {
                "host": socket.gethostname(),
                "slurm_job": os.getenv("SLURM_JOB_ID"),
                "rows": rows,
                "path_counts_by_table": dict(counts),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
