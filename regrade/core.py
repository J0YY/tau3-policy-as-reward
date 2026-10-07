"""Pinned replay and conservative alternative state specifications.

These are computational sensitivity predicates, not legal compliance labels.
Only named fields are canonicalized after predicates succeed. All other database
fields, records, required read logs, and user state retain exact equality.
"""

import copy, json, math
from functools import lru_cache
from tau2.domains.banking_knowledge.environment import get_environment, get_tasks
from tau2.runner.build import _derive_read_log_allowlist
from tau2.data_model.message import AssistantMessage, UserMessage, ToolCall
from tau2.data_model.tasks import Action
from tau2.evaluator.evaluator_action import ActionEvaluator
from tau2.evaluator.evaluator_env import FullDuplexEnvironmentEvaluator

FILING = "file_debit_card_transaction_dispute_6281"
PRIMARY = {"task_082", "task_084", "task_086"}
SENSITIVITY = PRIMARY | {"task_085", "task_087", "task_088", "task_091"}
LIABILITY = {"task_084": "btxn_c2g7f43h6g89", "task_086": "btxn_5690acdd3de5"}
LOST = "btxn_b17aa1648835"
EXTRA = {
    "task_084": dict(
        transaction_id="btxn_b1f6e32g5f78",
        account_id="chk_e5a31c7d82",
        card_id="dbc_82b5d1a6f3",
        user_id="a7c2f85d91",
        transaction_date="11/11/2025",
        disputed_amount=275.0,
        transaction_type="person_to_person",
    ),
    "task_086": dict(
        transaction_id="btxn_85b8c13c1173",
        account_id="chk_cr47f8d2a1_gff",
        card_id="dbc_cr47f8d2a1_gff",
        user_id="cr47f8d2a1",
        transaction_date="11/10/2025",
        disputed_amount=350.0,
        transaction_type="online_purchase",
    ),
}
for v in EXTRA.values():
    v.update(
        dispute_category="card_not_present_fraud",
        discovery_date="11/14/2025",
        card_in_possession=True,
        pin_compromised="unknown",
        contacted_merchant=False,
        police_report_filed=False,
        written_statement_provided=True,
        provisional_credit_eligible=True,
        card_action="close_and_reissue",
        customer_max_liability_amount=0.0,
    )


@lru_cache(None)
def tasks():
    return {t.id: t for t in get_tasks()}


def fresh(task):
    env = get_environment(
        retrieval_variant="bm25", read_log_allowlist=_derive_read_log_allowlist(task)
    )
    init = task.initial_state
    env.set_state(
        initialization_data=init.initialization_data if init else None,
        initialization_actions=init.initialization_actions if init else None,
        message_history=init.message_history or [] if init else [],
    )
    return env


def replay_actions(task, actions=None):
    env = fresh(task)
    errors = []
    messages = []
    for a in actions if actions is not None else task.evaluation_criteria.actions or []:
        call = ToolCall(
            id=a.action_id, name=a.name, arguments=a.arguments, requestor=a.requestor
        )
        cls = AssistantMessage if a.requestor == "assistant" else UserMessage
        messages.append(cls(role=a.requestor, tool_calls=[call]))
        response = env.get_response(call)
        messages.append(response)
        if response.error or str(response.content).strip().strip(
            '"'
        ).lower().startswith("error"):
            errors.append({"action": a.action_id, "error": response.content})
    return env, errors, messages


def trajectory_messages(sim):
    return (
        FullDuplexEnvironmentEvaluator.ticks_to_message_history(sim.ticks)
        if sim.ticks is not None
        else sim.messages or []
    )


def replay_sim(task, sim):
    env = get_environment(
        retrieval_variant="bm25", read_log_allowlist=_derive_read_log_allowlist(task)
    )
    init = task.initial_state
    messages = trajectory_messages(sim)
    env.set_state(
        initialization_data=init.initialization_data if init else None,
        initialization_actions=init.initialization_actions if init else None,
        message_history=messages,
        strict=False,
    )
    return env, messages


def original_reward(task, env, gold, messages, stored=None):
    basis = {str(x.value) for x in task.evaluation_criteria.reward_basis}
    value = 1.0
    provenance = []
    if "DB" in basis:
        gh, gu = (
            (gold[0], gold[1])
            if isinstance(gold, tuple)
            else (gold.get_db_hash(), gold.get_user_db_hash())
        )
        value *= float(env.get_db_hash() == gh and env.get_user_db_hash() == gu)
        provenance.append("pinned_DB")
    if "ACTION" in basis:
        value *= ActionEvaluator.calculate_reward(task, messages).reward
        provenance.append("pinned_ACTION")
    if "NL_ASSERTION" in basis:
        # Do not silently replace a paid stochastic language judge with a heuristic.
        breakdown = (stored or {}).get("reward_breakdown", {})
        nl = breakdown.get("NL_ASSERTION")
        if nl is None:
            return None, provenance + ["missing_NL_component"]
        value *= nl
        provenance.append("archived_NL_component")
    return value, provenance


def table(db, name):
    return db.get(name, {}).get("data", {})


def record(db, tx):
    hits = [
        (k, v)
        for k, v in table(db, "debit_card_disputes").items()
        if v.get("transaction_id") == tx
    ]
    return hits[0] if len(hits) == 1 else (None, None)


def bounded(x, upper):
    return type(x) in (int, float) and math.isfinite(x) and 0 <= x <= upper


def alternative(task, pred_db, gold_db, sensitivity=False):
    """Return component predicates and equality after narrowly allowed changes."""
    tid = task.id
    p = copy.deepcopy(pred_db)
    g = copy.deepcopy(gold_db)
    checks = {}

    def change(tx, fields, conditions):
        pk, pv = record(p, tx)
        gk, gv = record(g, tx)
        checks[tx + ":exists"] = pv is not None
        if pv is None or gv is None:
            return
        original = record(pred_db, tx)[1]
        for label, ok in conditions(original).items():
            checks[tx + ":" + label] = bool(ok)
        for f in fields:
            pv[f] = gv.get(f)

    if tid in LIABILITY:
        change(
            LIABILITY[tid],
            ["customer_max_liability_amount"],
            lambda v: {
                "liability_0_50": bounded(v.get("customer_max_liability_amount"), 50)
            },
        )
    if tid == "task_082":
        change(
            LOST,
            ["pin_compromised", "pin_shared_voluntarily"],
            lambda v: {
                "not_voluntary_sharing": v.get("pin_compromised")
                in {"no", "unknown", "yes_observed"}
                and v.get("pin_shared_voluntarily") is False
            },
        )
    if tid in EXTRA:
        expected = EXTRA[tid]
        pk, pv = record(p, expected["transaction_id"])
        checks["extra:exists"] = pv is not None
        if pv:
            fixed = [
                "transaction_id",
                "account_id",
                "card_id",
                "user_id",
                "transaction_date",
                "discovery_date",
                "disputed_amount",
                "card_in_possession",
                "status",
            ]
            checks["extra:identity_amount_dates"] = all(
                pv.get(f) == (expected | {"status": "OPEN"}).get(f) for f in fixed
            )
            checks["extra:fraud"] = (
                pv.get("dispute_category")
                in {"card_not_present_fraud", "unauthorized_transaction"}
                and pv.get("is_fraud_category") is True
            )
            checks["extra:type"] = pv.get("transaction_type") in {
                expected["transaction_type"],
                "online_purchase",
            }
            checks["extra:liability"] = bounded(
                pv.get("customer_max_liability_amount"), 50
            )
            checks["extra:pin"] = (
                pv.get("pin_compromised") in {"no", "unknown"}
                and pv.get("pin_shared_voluntarily") is False
            )
            checks["extra:credit_consistent"] = (
                type(pv.get("provisional_credit_eligible")) is bool
                and pv.get("provisional_credit_issued")
                == pv["provisional_credit_eligible"]
                and pv.get("provisional_credit_amount")
                == (
                    pv["disputed_amount"] if pv["provisional_credit_eligible"] else None
                )
            )
            checks["extra:boolean_fields"] = all(
                type(pv.get(f)) is bool
                for f in [
                    "contacted_merchant",
                    "police_report_filed",
                    "written_statement_provided",
                ]
            )
            checks["extra:card_action"] = pv.get("card_action") in {
                "keep_active",
                "freeze_pending_investigation",
                "close_and_reissue",
            }
            # Remove exactly the additional record; the existing filing log is retained.
            del table(p, "debit_card_disputes")[pk]
    if sensitivity:
        for gv in table(g, "debit_card_disputes").values():
            tx = gv.get("transaction_id")
            cat = gv.get("dispute_category")
            if gv.get("customer_max_liability_amount") is None:
                continue
            nonfraud = cat in {
                "duplicate_charge",
                "incorrect_amount",
                "atm_cash_discrepancy",
                "atm_deposit_not_credited",
            }
            heldfraud = (
                cat in {"card_present_fraud", "card_not_present_fraud"}
                and gv.get("card_in_possession") is True
            )
            if nonfraud or heldfraud:
                change(
                    tx,
                    ["customer_max_liability_amount"],
                    lambda v: {
                        "sensitivity_liability_zero": bounded(
                            v.get("customer_max_liability_amount"), 0
                        )
                    },
                )
    checks["unaffected_state_equal"] = p == g
    return {
        "predicate_pass": all(
            v for k, v in checks.items() if k != "unaffected_state_equal"
        ),
        "retained_state_pass": p == g,
        "pass": all(checks.values()),
        "checks": checks,
    }


def edited_actions(task, liability=None, extra=False, pin=False, sensitivity=False):
    acts = copy.deepcopy(task.evaluation_criteria.actions)
    for a in acts:
        if (
            a.name != "call_discoverable_agent_tool"
            or a.arguments.get("agent_tool_name") != FILING
        ):
            continue
        d = json.loads(a.arguments["arguments"])
        tx = d["transaction_id"]
        if liability is not None and tx == LIABILITY.get(task.id):
            d["customer_max_liability_amount"] = liability
        if pin and tx == LOST:
            d["pin_compromised"] = "unknown"
        if sensitivity and (
            d["dispute_category"]
            in {
                "duplicate_charge",
                "incorrect_amount",
                "atm_cash_discrepancy",
                "atm_deposit_not_credited",
            }
            or (
                d["dispute_category"]
                in {"card_present_fraud", "card_not_present_fraud"}
                and d["card_in_possession"]
            )
        ):
            d["customer_max_liability_amount"] = 0
        a.arguments["arguments"] = json.dumps(d)
    if extra and task.id in EXTRA:
        acts.append(
            Action(
                action_id=task.id + "_extra",
                name="call_discoverable_agent_tool",
                requestor="assistant",
                arguments={
                    "agent_tool_name": FILING,
                    "arguments": json.dumps(EXTRA[task.id]),
                },
            )
        )
    return acts


def apply_termination(row, reason):
    """Match official premature-stop gate and metrics infrastructure exclusion."""
    row["termination_reason"] = reason
    if reason == "infrastructure_error":
        row["status"] = "excluded_infrastructure"
        for key in ["r0", "r1", "r1s", "r2", "r3", "r4"]:
            row[key] = None
    elif reason not in {"agent_stop", "user_stop"}:
        if row.get("status") == "error":
            row["replay_diagnostic"] = row.pop("error", "")
        row["status"] = "ok"
        row["termination_gated"] = True
        for key in ["r0", "r1", "r1s", "r2", "r3", "r4"]:
            row[key] = 0.0
        if row.get("task") in PRIMARY:
            row["r1"] = None
        if row.get("task") in SENSITIVITY:
            row["r1s"] = None
        row.setdefault("r0_provenance", []).append("official_premature_stop_gate")
    return row


def normalize_archive_simulation(raw):
    """Recover omitted legacy ToolMessage IDs only from adjacent ordered calls.

    No call, argument, content, or reward is changed. Ambiguous or mismatching
    sequences raise; raw archives remain untouched. Returns copy and audit count.
    """
    raw = copy.deepcopy(raw)
    pending = []
    repairs = 0
    for m in raw.get("messages") or []:
        if m.get("role") in {"assistant", "user"} and m.get("tool_calls"):
            if pending:
                raise ValueError("Unanswered tool calls before next call group")
            pending = list(m["tool_calls"])
        elif m.get("role") == "tool":
            if not pending:
                raise ValueError("Orphan tool response in legacy adapter")
            call = pending.pop(0)
            if m.get("id") is not None and m["id"] != call["id"]:
                raise ValueError("Response ID contradicts ordered caller")
            if "id" not in m:
                m["id"] = call["id"]
                repairs += 1
            if "requestor" not in m:
                m["requestor"] = call.get("requestor", "assistant")
        elif pending:
            raise ValueError("Non-tool message interrupts pending responses")
    # Interrupted unfinished calls remain invalid in the original replay too.
    if pending:
        raise ValueError("Missing tool responses at end of archive")
    return raw, repairs
