import copy, json, math
import pytest
from regrade.core import *


@pytest.fixture(scope="module")
def cases():
    out = {}
    for tid in sorted(SENSITIVITY):
        task = tasks()[tid]
        gold, _, _ = replay_actions(task)
        env, err, _ = replay_actions(
            task,
            edited_actions(task, liability=0, extra=True, pin=True, sensitivity=True),
        )
        assert not err
        out[tid] = (task, gold.tools.db.model_dump(), env.tools.db.model_dump())
    return out


@pytest.mark.parametrize("tid", sorted(SENSITIVITY))
def test_valid_sensitivity(cases, tid):
    t, g, p = cases[tid]
    assert alternative(t, p, g, True)["pass"]


@pytest.mark.parametrize("tid", sorted(PRIMARY))
def test_original_fails_alternative(cases, tid):
    t, g, p = cases[tid]
    assert not alternative(t, g, g)["predicate_pass"]


@pytest.mark.parametrize("tid", sorted(SENSITIVITY))
def test_unrelated_modification_rejected(cases, tid):
    t, g, p = cases[tid]
    p = copy.deepcopy(p)
    key = next(iter(table(p, "users")))
    table(p, "users")[key]["name"] = "UNRELATED MODIFICATION"
    assert not alternative(t, p, g, True)["pass"]


@pytest.mark.parametrize(
    "value", [-1, -50, float("nan"), float("inf"), True, "0", None, 50.01]
)
def test_invalid_liability_rejected(cases, value):
    t, g, p = cases["task_084"]
    p = copy.deepcopy(p)
    record(p, LIABILITY[t.id])[1]["customer_max_liability_amount"] = value
    assert not alternative(t, p, g)["predicate_pass"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("disputed_amount", 1),
        ("user_id", "other"),
        ("account_id", "other"),
        ("card_id", "other"),
        ("status", "CLOSED"),
        ("transaction_date", "01/01/2000"),
        ("dispute_category", "goods_services_not_received"),
        ("customer_max_liability_amount", -1),
        ("pin_shared_voluntarily", True),
        ("provisional_credit_amount", 999),
    ],
)
def test_malformed_extra_rejected(cases, field, value):
    t, g, p = cases["task_084"]
    p = copy.deepcopy(p)
    record(p, EXTRA[t.id]["transaction_id"])[1][field] = value
    assert not alternative(t, p, g)["predicate_pass"]


@pytest.mark.parametrize("tid", sorted(PRIMARY))
def test_missing_record_rejected(cases, tid):
    t, g, p = cases[tid]
    p = copy.deepcopy(p)
    tx = EXTRA[tid]["transaction_id"] if tid in EXTRA else LOST
    k, _ = record(p, tx)
    del table(p, "debit_card_disputes")[k]
    assert not alternative(t, p, g)["pass"]


def test_extra_unrelated_dispute_rejected(cases):
    t, g, p = cases["task_084"]
    p = copy.deepcopy(p)
    table(p, "debit_card_disputes")["invented"] = {"transaction_id": "invented"}
    assert not alternative(t, p, g)["pass"]


def test_action_defect_has_repair_counterexample():
    t = tasks()["task_083"]
    g, e, _ = replay_actions(t)
    assert len(e) == 4
    fixed = copy.deepcopy(t.evaluation_criteria.actions)
    for a in fixed:
        if (
            a.name == "call_discoverable_agent_tool"
            and a.arguments.get("agent_tool_name") == FILING
        ):
            d = json.loads(a.arguments["arguments"])
            d["customer_max_liability_amount"] = 50
            a.arguments["arguments"] = json.dumps(d)
    env, e, msg = replay_actions(t, list(t.evaluation_criteria.actions) + fixed)
    assert len(table(env.tools.db.model_dump(), "debit_card_disputes")) == 4
    assert original_reward(t, env, g, msg)[0] == 1


@pytest.mark.parametrize("reason", ["max_steps", "too_many_errors"])
def test_premature_stop_cannot_pass(reason):
    r = apply_termination(
        {"task": "task_084", "r0": 1.0, "r2": 1.0, "r4": 1.0, "r1": None}, reason
    )
    assert r["r0"] == r["r2"] == r["r4"] == 0 and r["r1"] is None


def test_infrastructure_excluded_not_failed():
    r = apply_termination(
        {"r0": 0.0, "r2": 0.0, "status": "ok"}, "infrastructure_error"
    )
    assert r["r0"] is None and r["status"] == "excluded_infrastructure"


def test_production_gate_accepts_shared_database_alternative():
    t = tasks()["task_084"]
    g, _, _ = replay_actions(t)
    env, errors, msg = replay_actions(t, edited_actions(t, liability=50, extra=True))
    a = alternative(t, env.tools.db.model_dump(), g.tools.db.model_dump())
    assert env.user_tools.db is env.tools.db
    assert env.get_user_db_hash() != g.get_user_db_hash()
    user_equal = (
        env.user_tools.db is env.tools.db
    ) or env.get_user_db_hash() == g.get_user_db_hash()
    assert a["pass"] and user_equal
    assert original_reward(t, env, g, msg)[0] == 0


def test_legacy_adapter_preserves_call_semantics():
    raw = {
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [{"id": "a", "name": "x", "arguments": {"n": 4}}],
            },
            {"role": "tool", "content": "result"},
        ]
    }
    fixed, n = normalize_archive_simulation(raw)
    assert n == 1 and fixed["messages"][1]["id"] == "a"
    assert "id" not in raw["messages"][1]
    assert fixed["messages"][0] == raw["messages"][0]


def test_legacy_adapter_rejects_ambiguous_pairing():
    with pytest.raises(ValueError):
        normalize_archive_simulation(
            {"messages": [{"role": "tool", "content": "orphan"}]}
        )
    with pytest.raises(ValueError):
        normalize_archive_simulation(
            {
                "messages": [
                    {"role": "assistant", "tool_calls": [{"id": "a"}]},
                    {"role": "tool", "id": "b"},
                ]
            }
        )


def test_premature_parse_failure_is_known_zero():
    r = apply_termination(
        {"task": "task_004", "status": "error", "error": "invalid schema"}, "max_steps"
    )
    assert (
        r["r0"] == 0
        and r["status"] == "ok"
        and r["replay_diagnostic"] == "invalid schema"
    )
