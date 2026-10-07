"""Enumerate the entire corpus; flags are machine triage, never legal verdicts."""

import collections, csv, hashlib, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS = ROOT / "vendor/tau2-bench/data/tau2/domains/banking_knowledge"
KEYWORDS = re.compile(
    r"regulation|reg e\b|reg z\b|disput|liabilit|provisional|refund|fee|waiver|police|affidavit|business days",
    re.I,
)


def dumpcsv(path, rows):
    with path.open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    manifest = []
    tasks = []
    actions = []
    docs = []
    basis = collections.Counter()
    stale = {x["id"]: x for x in json.loads((CORPUS / "tasks.json").read_text())}
    for p in sorted(CORPUS.rglob("*")):
        if p.is_file():
            manifest.append(
                {
                    "path": str(p.relative_to(CORPUS)),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "bytes": p.stat().st_size,
                }
            )
    for p in sorted((CORPUS / "tasks").glob("task_*.json")):
        t = json.loads(p.read_text())
        ev = t.get("evaluation_criteria") or {}
        rb = ",".join(ev.get("reward_basis", []))
        basis[rb] += 1
        acts = ev.get("actions", [])
        tools = []
        for a in acts:
            args = a["arguments"]
            name = args.get("agent_tool_name", a["name"])
            tools.append(name)
            inner = args.get("arguments", args)
            if isinstance(inner, str):
                try:
                    inner = json.loads(inner)
                except json.JSONDecodeError:
                    pass
            actions.append(
                {
                    "unit_id": t["id"] + ":" + a["action_id"],
                    "task": t["id"],
                    "action_id": a["action_id"],
                    "tool": name,
                    "wrapper": a["name"],
                    "arguments": json.dumps(inner, sort_keys=True),
                    "machine_candidate": bool(KEYWORDS.search(name)),
                    "human_verdict": "",
                    "expert_review": "",
                }
            )
        text = json.dumps(t)
        tags = []
        for tag, pat in {
            "Reg E": "debit_card_transaction_dispute|Regulation E",
            "Reg Z": "credit_card.*dispute",
            "credit_decision": "credit_limit|credit_card_application",
            "fees": "fee|interest",
            "closure": "close.*account",
            "escalation": "transfer_to_human",
        }.items():
            if re.search(pat, text, re.I):
                tags.append(tag)
        tasks.append(
            {
                "task": t["id"],
                "reward_basis": rb,
                "actions": len(acts),
                "regime_triage": ";".join(tags),
                "tools": ";".join(sorted(set(tools))),
                "differs_from_stale": stale.get(t["id"]) != t,
                "human_screen": "",
            }
        )
    for p in sorted((CORPUS / "documents").glob("*.json")):
        d = json.loads(p.read_text())
        txt = json.dumps(d)
        docs.append(
            {
                "document": p.name,
                "title": d.get("title", ""),
                "hits": ";".join(sorted(set(x.lower() for x in KEYWORDS.findall(txt)))),
                "human_screen": "",
            }
        )
    for name, rows in [
        ("task_screen.csv", tasks),
        ("action_units.csv", actions),
        ("document_screen.csv", docs),
    ]:
        dumpcsv(ROOT / "coding" / name, rows)
    (ROOT / "data/corpus_manifest.json").write_text(json.dumps(manifest, indent=2))
    summary = {
        "tasks": len(tasks),
        "documents": len(docs),
        "gold_actions": len(actions),
        "reward_basis": dict(basis),
        "stale_task_differences": [r["task"] for r in tasks if r["differs_from_stale"]],
        "document_keyword_hits": sum(bool(r["hits"]) for r in docs),
        "debit_filings": sum(
            "file_debit_card_transaction_dispute" in r["tool"]
            and r["wrapper"] == "call_discoverable_agent_tool"
            for r in actions
        ),
    }
    (ROOT / "results/inventory.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
