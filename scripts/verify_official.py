"""Differential check of our deterministic R0 against upstream top-level evaluator."""

import json, pathlib, random, socket, os
from loguru import logger
from tau2.data_model.simulation import SimulationRun
from tau2.evaluator.evaluator import evaluate_simulation, EvaluationType
from tau2.orchestrator.modes import CommunicationMode
from regrade.core import *
from tau2.runner.build import _derive_read_log_allowlist

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    logger.remove()
    out = []
    for sid in [
        "gemini-3-pro_sierra_2026-03-02",
        "gpt-5-5_sierra_2026-05-05",
        "gemini-3-1-flash-live-preview-thinking-high-banking_google_2026-07-13",
    ]:
        directory = ROOT / "data/trajectories" / sid
        path = (
            directory / "trajectories.json"
            if (directory / "trajectories.json").exists()
            else directory / "results.json"
        )
        raw = json.loads(path.read_text())
        sims = raw.get("simulations") or [
            json.loads(p.read_text())
            for p in sorted((directory / "simulations").glob("*.json"))
        ]
        selected = []
        seen = set()
        for s in sims:
            tid = s["task_id"]
            t = tasks()[tid]
            if tid in seen or any(
                x.value == "NL_ASSERTION" for x in t.evaluation_criteria.reward_basis
            ):
                continue
            if tid in SENSITIVITY | {"task_083"} or len(selected) < 12:
                selected.append(s)
                seen.add(tid)
        cached = {
            r["simulation"]: r
            for r in json.loads(
                (ROOT / "results/public" / (sid + ".json")).read_text()
            )["rows"]
        }
        for s in selected:
            t = tasks()[s["task_id"]]
            sim = SimulationRun.model_validate(normalize_archive_simulation(s)[0])
            official = evaluate_simulation(
                simulation=sim,
                task=t,
                evaluation_type=EvaluationType.ALL,
                solo_mode=False,
                domain="banking_knowledge",
                mode=CommunicationMode.FULL_DUPLEX
                if sim.ticks is not None
                else CommunicationMode.HALF_DUPLEX,
                env_kwargs={
                    "retrieval_variant": "bm25",
                    "read_log_allowlist": _derive_read_log_allowlist(t),
                },
                strict_replay=False,
            ).reward
            ours = cached[s["id"]]["r0"]
            out.append(
                {
                    "submission": sid,
                    "task": t.id,
                    "simulation": s["id"],
                    "official": official,
                    "ours": ours,
                    "equal": official == ours,
                }
            )
            print(sid, t.id, official, ours, flush=True)
    (ROOT / "results/official_differential.json").write_text(
        json.dumps(
            {
                "host": socket.gethostname(),
                "slurm_job": os.getenv("SLURM_JOB_ID"),
                "rows": out,
            },
            indent=2,
        )
    )
    assert all(x["equal"] for x in out)


if __name__ == "__main__":
    main()
