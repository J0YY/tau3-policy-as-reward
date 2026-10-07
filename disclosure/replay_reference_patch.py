"""Minimal offline reproduction on tau2-bench v1.0.1.

Install the benchmark's knowledge extras, then run this script. It compares
original DB hashes after changing only one expected filing argument. No API key.
"""

import copy
import json
from tau2.domains.banking_knowledge.environment import get_environment, get_tasks
from tau2.runner.build import _derive_read_log_allowlist
from tau2.data_model.message import ToolCall


def replay(task, transaction=None, field=None, value=None):
    env = get_environment(
        retrieval_variant="bm25", read_log_allowlist=_derive_read_log_allowlist(task)
    )
    init = task.initial_state
    env.set_state(
        initialization_data=init.initialization_data,
        initialization_actions=init.initialization_actions,
        message_history=init.message_history or [],
    )
    errors = []
    changed = 0
    for a in task.evaluation_criteria.actions:
        args = copy.deepcopy(a.arguments)
        if (
            a.name == "call_discoverable_agent_tool"
            and args.get("agent_tool_name")
            == "file_debit_card_transaction_dispute_6281"
        ):
            inner = json.loads(args["arguments"])
            if transaction and inner["transaction_id"] == transaction:
                inner[field] = value
                args["arguments"] = json.dumps(inner)
                changed += 1
        response = env.get_response(
            ToolCall(id=a.action_id, name=a.name, arguments=args, requestor=a.requestor)
        )
        if response.error or str(response.content).strip().strip(
            '"'
        ).lower().startswith("error"):
            errors.append(str(response.content))
    if transaction:
        assert changed == 1
    assert not errors, errors
    return env.get_db_hash()


def main():
    tasks = {t.id: t for t in get_tasks()}
    for tid, tx, field, values in [
        ("task_084", "btxn_c2g7f43h6g89", "customer_max_liability_amount", [0, 50]),
        ("task_086", "btxn_5690acdd3de5", "customer_max_liability_amount", [0, 50]),
        ("task_082", "btxn_b17aa1648835", "pin_compromised", ["unknown"]),
    ]:
        task = tasks[tid]
        original = replay(task)
        for value in values:
            print(
                tid,
                field,
                value,
                "matches original DB:",
                replay(task, tx, field, value) == original,
            )


if __name__ == "__main__":
    main()
