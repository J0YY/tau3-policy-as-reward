"""Regrade one submission in a Slurm array; preserve per-run evidence."""

import argparse, collections, json, pathlib, socket, time, os, traceback
from loguru import logger
from tau2.data_model.simulation import SimulationRun
from regrade.core import *

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(sid):
    logger.remove()
    root = ROOT / "data/trajectories" / sid
    path = (
        root / "trajectories.json"
        if (root / "trajectories.json").exists()
        else root / "results.json"
    )
    raw = json.loads(path.read_text())
    embedded = {t["id"]: t for t in raw["tasks"]}
    out = ROOT / "results/public"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    golds = {}
    start = time.time()
    sims = raw.get("simulations") or [
        json.loads(p.read_text()) for p in sorted((root / "simulations").glob("*.json"))
    ]
    for i, s in enumerate(sims):
        tid = s["task_id"]
        row = {
            "submission": sid,
            "simulation": s["id"],
            "task": tid,
            "trial": s.get("trial"),
            "stored_reward": (s.get("reward_info") or {}).get("reward"),
        }
        if s["termination_reason"] not in {"agent_stop", "user_stop"}:
            apply_termination(row, s["termination_reason"])
            rows.append(row)
            continue
        try:
            task = tasks()[tid]
            normalized, repairs = normalize_archive_simulation(s)
            sim = SimulationRun.model_validate(normalized)
            row["legacy_response_ids_restored"] = repairs
            if tid not in golds:
                gold_env = replay_actions(task)[0]
                golds[tid] = (
                    gold_env.get_db_hash(),
                    gold_env.get_user_db_hash(),
                    gold_env.tools.db.model_dump() if tid in SENSITIVITY else None,
                )
                del gold_env
            gold = golds[tid]
            env, msg = replay_sim(task, sim)
            row["r0"], row["r0_provenance"] = original_reward(
                task, env, gold, msg, s.get("reward_info")
            )
            row["r1"] = None if tid in PRIMARY else row["r0"]
            row["r1s"] = None if tid in SENSITIVITY else row["r0"]
            row["r2"] = row["r0"]
            row["r3"] = row["r0"]
            row["r4"] = row["r0"]
            if tid in SENSITIVITY:
                p = env.tools.db.model_dump()
                g = gold[2]
                user_equal = (
                    env.user_tools.db is env.tools.db
                ) or env.get_user_db_hash() == gold[1]
                if tid in PRIMARY:
                    a = alternative(task, p, g)
                    row["r2_details"] = a
                    row["r2"] = float(a["pass"] and user_equal)
                    row["r4"] = (
                        max(row["r0"], row["r2"]) if row["r0"] is not None else None
                    )
                a = alternative(task, p, g, True)
                row["r3_details"] = a
                row["r3"] = float(a["pass"] and user_equal)
                row["disputes"] = list(table(p, "debit_card_disputes").values())
                row["speech_review"] = "unannotated"
            row["status"] = "ok"
        except Exception as e:
            row.update(status="error", error=f"{type(e).__name__}: {e}")
        apply_termination(row, s["termination_reason"])
        rows.append(row)
        if i % 25 == 0:
            print(sid, i, len(sims), row["status"], flush=True)
    provenance = {
        "host": socket.gethostname(),
        "slurm_job": os.getenv("SLURM_JOB_ID"),
        "seconds": time.time() - start,
        "source": str(path.relative_to(ROOT)),
        "embedded_commit": raw.get("info", {}).get("git_commit"),
        "embedded_task_differences": [
            t
            for t, e in embedded.items()
            if t in tasks() and tasks()[t].model_dump(mode="json") != e
        ],
    }
    (out / (sid + ".json")).write_text(
        json.dumps({"provenance": provenance, "rows": rows}, indent=2)
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("submission")
    args = p.parse_args()
    run(args.submission)
