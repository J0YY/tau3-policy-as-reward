"""Attach official termination gates to initial replay outputs and preserve audit."""

import json, pathlib
from regrade.core import apply_termination

ROOT = pathlib.Path(__file__).resolve().parents[1]
for p in sorted((ROOT / "results/public").glob("*.json")):
    d = json.loads(p.read_text())
    src = ROOT / d["provenance"]["source"]
    raw = json.loads(src.read_text())
    sims = raw.get("simulations") or [
        json.loads(f.read_text())
        for f in sorted((src.parent / "simulations").glob("*.json"))
    ]
    reasons = {s["id"]: s["termination_reason"] for s in sims}
    for row in d["rows"]:
        apply_termination(row, reasons[row["simulation"]])
    d["provenance"]["termination_gate_verified"] = True
    p.write_text(json.dumps(d, indent=2))
    print(p.stem, flush=True)
