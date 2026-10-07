Thanks for documenting this. Your report already establishes both the internal specification problem—the task-086 gold liability cannot be derived from its supplied facts—and the zero-pass result across 110 graded public trials. It also identifies the related tasks 082, 084, 085, 087, and 088. The following extends that finding with a source comparison and controlled replay; it does not claim priority for the original inconsistency or zero-pass result.

I audited banking release v1.0.1 at `fc0055dc4e0a316c3f83133267fbd6faaa770992`, freezing submission metadata at `4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`. The new checks concern dispute caps, PIN coding, grader mechanics, and alternative specifications.

### Additional reference-state findings

| Task | Reference behavior | Controlled change | Original DB reward |
|---|---|---|---|
| 084 | Three new disputes; the $275 EveryonePay claim (`btxn_b1f6e32g5f78`) is left unfiled under the tier cap | File the additional claim after the reference actions | 1 → 0; four disputes successfully filed |
| 086 | Five new disputes; the $350 claim (`btxn_85b8c13c1173`) is left unfiled under the tier cap | File the additional claim after the reference actions | 1 → 0; six disputes successfully filed |
| 084 | TechWorld (`btxn_c2g7f43h6g89`) maximum liability $412.88 | Change that filing argument to $0 or $50 | 1 → 0 |
| 086 | TechWorld (`btxn_5690acdd3de5`) maximum liability $500 | Change that filing argument to $0 or $50 | 1 → 0 |
| 082 | Lost wallet containing a written PIN (`btxn_b17aa1648835`) coded `yes_shared` | Change `pin_compromised` to `unknown` | 1 → 0 |

The tools accept these altered filings. The DB scorer rejects the changed state. That follows from exact-state comparison; the substantive concern is which state the reference requires, rather than hash comparison itself.

The source comparison is conditional on Regulation E coverage and the relevant notice facts:

- **Dispute cap:** [§1005.11(b)–(c)](https://www.consumerfinance.gov/rules-policy/regulations/1005/11/) requires investigation after qualifying notice of a covered error. The number of other open disputes is not a condition. A filing is the simulation's intake representation; a missing database record alone does not establish failure to investigate at a real bank. An accepted escalation path could matter, but the reference does not represent one for the omitted claims.
- **Liability:** Under [§1005.6(b)(1)–(3)](https://www.consumerfinance.gov/rules-policy/regulations/1005/6/), the relevant clocks concern knowledge of access-device loss/theft and statement delivery, rather than simply the transaction date. The $50 sensitivity assumes relevant loss/theft was first learned of on reporting. The zero sensitivity uses the reading that no access device was lost or stolen, subject to the statement-notice rule. Physical possession of the card alone cannot resolve this: [§1005.2(a)](https://www.consumerfinance.gov/rules-policy/regulations/1005/2/) also includes codes in the access-device definition. Task 086 has conflicting January/November discovery dates; the tested alternative uses its fixed November task date and reporting-on-discovery reading. Its Green Fee-Free and Evergreen accounts are listed as personal products in document 012, although primary purpose remains unresolved given the restaurant-use narrative.
- **PIN:** Official comment 6(b)-2 says negligence does not increase liability; comment 2(m)-2 distinguishes granting another person authority. A lost wallet containing a written PIN does not itself show voluntary sharing. The task-082 transaction also predates the stated wallet loss, so the script does not establish how compromise happened.

### Related policy clauses

Documents 031, 032, and 036 also warrant review against [§1005.11](https://www.consumerfinance.gov/rules-policy/regulations/1005/11/) and the [CFPB EFT FAQs](https://www.consumerfinance.gov/compliance/compliance-resources/deposit-accounts-resources/electronic-fund-transfers/electronic-fund-transfers-faqs/):

1. A 60-day transaction-date filing cutoff, instead of the statement-based notice window.
2. Prior merchant contact as a condition of provisional-credit entitlement for non-fraud disputes. For covered errors, credit depends on the investigation period and statutory conditions; merchant contact is not an independent exception.
3. “A police report may be required.” This needs clarification if it can delay investigation; Error Resolution FAQ 4 rejects such a prerequisite.
4. Categorical provisional-credit exclusions for incorrect amounts and ATM deposits not credited, despite these categories potentially falling within §1005.11(a). This does not mean immediate credit is required in every case.

### Public replay: unchanged scores, different records

The separately frozen collection contains 10,880 simulations from 32 accessible submissions (one advertised archive returned 404). Excluding 161 infrastructure failures, replay reproduces 26 published scores. Of the six discrepancies, two reconcile numerically when infrastructure failures count as zero; four remain unresolved. Premature stops remain scored zeros.

There are **111 scored trials per task** for 082, 084, and 086, and **zero complete passes under either original or primary alternative grading**. The alternatives change the targeted records while retaining other required state and tool logs. Original-or-alternative grading therefore changes no score or ranking. This independently extends the issue's zero-pass observation; it does not establish that the two archive collections are strictly nested.

The final records nevertheless vary:

| Recorded outcome | Count / 111 |
|---|---:|
| Task 084: $275 claim present | 34 |
| Task 086: $350 claim present | 23 |
| Task 082: PIN `yes_shared` / `yes_observed` / `unknown` / record missing | 54 / 32 / 5 / 20 |
| Task 084: TechWorld liability $412.88 / $500 / $50 / $0 / $47.50 / −1 / missing | 21 / 28 / 32 / 1 / 1 / 2 / 26 |
| Task 086: TechWorld liability $500 / $50 / $0 / −1 / missing | 50 / 16 / 6 / 11 / 28 |

Here −1 is the tool's unlimited-liability sentinel. “Claim present” checks the transaction ID; it does not certify all fields. Fifty runs meet the complete targeted predicates (37 on 082, eight on 084, five on 086), but all still differ on other retained requirements. There is no observed complete public trajectory that newly passes the primary alternative.

The implication is a **latent, conditional scoring penalty**: the tested change costs reward when the remaining workflow matches the reference, even though no present public score moves. This is not a prediction about when agents will reach that point.

### Separate action-grader defect in 083

The four expected dispute calls omit the required liability argument and fail. Reproducing them earns action-match credit. Repairing the calls alone files four disputes but fails action matching. Crucially, issuing the expected broken calls **and then the repairs** both files the disputes and passes. Correct filing is therefore compatible with passing; the defect is that passing requires reproducing invalid expected calls. This counterexample prevents an overstatement of the problem.

### Minimal offline reproduction

The script below reproduces the five liability/PIN hash mismatches above. It makes no model API calls. Save it as `replay_reference_patch.py` and run it in an environment with the pinned benchmark and knowledge dependencies installed (Python 3.12/3.13):

```bash
git clone https://github.com/sierra-research/tau2-bench.git
cd tau2-bench
git checkout fc0055dc4e0a316c3f83133267fbd6faaa770992
python -m pip install -e '.[knowledge]'
python /path/to/replay_reference_patch.py
```

Each printed `matches original DB` value is `False`; the script asserts that the original and modified tool sequences have no errors. The original reference state is the DB target for these tasks. This minimal script covers the liability/PIN changes; the additional-claim and action-grader experiments are reported separately above.

<details>
<summary>Reproduction script</summary>

```python
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
```
</details>

These are computational checks and source-grounded, model-assisted interpretations, not external legal endorsement. Useful maintainer clarifications would be the intended treatment of the tier cap after qualifying notice, the facts supporting each liability tier, the lost-wallet PIN category, and accepted escalation or alternative-state paths. The earlier task-074 correction in #374 is a helpful precedent for resolving a concrete reference mismatch.
