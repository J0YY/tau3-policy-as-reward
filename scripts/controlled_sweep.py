"""Paired counterfactuals, neutral controls, and field-boundary sensitivity."""

import copy, json, pathlib, socket, os, time
from loguru import logger
from regrade.core import *

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    logger.remove()
    rows = []
    start = time.time()
    for tid in ["task_082", "task_084", "task_086"]:
        task = tasks()[tid]
        gold, _, _ = replay_actions(task)
        variants = [("original", task.evaluation_criteria.actions)]
        if tid in LIABILITY:
            for value in [-1, 0, 1, 25, 49.99, 50, 50.01, 100, 412.88, 500]:
                for extra in [False, True]:
                    variants.append(
                        (
                            f"liability_{value}_extra_{extra}",
                            edited_actions(task, liability=value, extra=extra),
                        )
                    )
        else:
            for pin in ["yes_shared", "yes_observed", "no", "unknown"]:
                aa = copy.deepcopy(task.evaluation_criteria.actions)
                for a in aa:
                    if (
                        a.name == "call_discoverable_agent_tool"
                        and a.arguments.get("agent_tool_name") == FILING
                    ):
                        d = json.loads(a.arguments["arguments"])
                        if d["transaction_id"] == LOST:
                            d["pin_compromised"] = pin
                            a.arguments["arguments"] = json.dumps(d)
                variants.append(("pin_" + pin, aa))
        # A neutral JSON numeric spelling change should survive normalization.
        numeric = copy.deepcopy(task.evaluation_criteria.actions)
        for a in numeric:
            if (
                a.name == "call_discoverable_agent_tool"
                and a.arguments.get("agent_tool_name") == FILING
            ):
                d = json.loads(a.arguments["arguments"])
                d["disputed_amount"] = float(d["disputed_amount"])
                a.arguments["arguments"] = json.dumps(d)
        variants.append(("neutral_numeric_format", numeric))
        # Semantically unrelated discretionary flag also changes the exact reference.
        unrelated = copy.deepcopy(task.evaluation_criteria.actions)
        for a in unrelated:
            if (
                a.name == "call_discoverable_agent_tool"
                and a.arguments.get("agent_tool_name") == FILING
            ):
                d = json.loads(a.arguments["arguments"])
                d["police_report_filed"] = not d["police_report_filed"]
                a.arguments["arguments"] = json.dumps(d)
                break
        variants.append(("unrelated_police_flag", unrelated))
        for name, aa in variants:
            env, err, msg = replay_actions(task, aa)
            r0, _ = original_reward(task, env, gold, msg)
            rows.append(
                {
                    "task": tid,
                    "variant": name,
                    "r0": r0,
                    "r2": alternative(
                        task, env.tools.db.model_dump(), gold.tools.db.model_dump()
                    ),
                    "error_count": len(err),
                }
            )
    out = {
        "host": socket.gethostname(),
        "slurm_job": os.getenv("SLURM_JOB_ID"),
        "seconds": time.time() - start,
        "rows": rows,
    }
    (ROOT / "results/controlled_sweep.json").write_text(json.dumps(out, indent=2))
    print(len(rows))


if __name__ == "__main__":
    main()
