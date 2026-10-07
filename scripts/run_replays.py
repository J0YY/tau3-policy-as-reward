import argparse, copy, json, pathlib, socket, os, time
from loguru import logger
from regrade.core import *

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    logger.remove()
    rows = []
    start = time.time()
    for tid, task in sorted(tasks().items()):
        gold, errors, msg = replay_actions(task)
        r0, src = original_reward(task, gold, gold, msg)
        rows.append(
            {
                "task": tid,
                "variant": "gold",
                "errors": errors,
                "reward": r0,
                "reward_source": src,
                "disputes": len(
                    table(gold.tools.db.model_dump(), "debit_card_disputes")
                ),
            }
        )
        variants = []
        if tid in LIABILITY:
            variants = [
                ("liability_0", dict(liability=0)),
                ("liability_50", dict(liability=50)),
                ("extra_claim", dict(extra=True)),
                ("combined", dict(liability=50, extra=True)),
            ]
        if tid == "task_082":
            variants = [("pin_unknown", dict(pin=True))]
        if tid in SENSITIVITY:
            variants.append(
                (
                    "sensitivity",
                    dict(liability=0, extra=True, pin=True, sensitivity=True),
                )
            )
        for name, kwargs in variants:
            env, err, msg = replay_actions(task, edited_actions(task, **kwargs))
            alt = alternative(
                task,
                env.tools.db.model_dump(),
                gold.tools.db.model_dump(),
                name == "sensitivity",
            )
            rows.append(
                {
                    "task": tid,
                    "variant": name,
                    "errors": err,
                    "reward": original_reward(task, env, gold, msg)[0],
                    "alternative": alt,
                }
            )
        if tid == "task_083":
            fixed = copy.deepcopy(task.evaluation_criteria.actions)
            for a in fixed:
                if (
                    a.name == "call_discoverable_agent_tool"
                    and a.arguments.get("agent_tool_name") == FILING
                ):
                    d = json.loads(a.arguments["arguments"])
                    d["customer_max_liability_amount"] = 50
                    a.arguments["arguments"] = json.dumps(d)
            for name, aa in [
                ("required_argument_repair", fixed),
                (
                    "broken_then_repaired",
                    list(task.evaluation_criteria.actions) + fixed,
                ),
            ]:
                env, err, msg = replay_actions(task, aa)
                rows.append(
                    {
                        "task": tid,
                        "variant": name,
                        "errors": err,
                        "reward": original_reward(task, env, gold, msg)[0],
                        "disputes": len(
                            table(env.tools.db.model_dump(), "debit_card_disputes")
                        ),
                    }
                )
        print(tid, flush=True)
    out = {
        "host": socket.gethostname(),
        "slurm_job": os.getenv("SLURM_JOB_ID"),
        "seconds": time.time() - start,
        "rows": rows,
    }
    (ROOT / "results/replays.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
