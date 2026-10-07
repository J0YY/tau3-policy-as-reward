"""Fetch only declared banking trajectories; record unavailable files explicitly."""

import concurrent.futures as cf
import datetime, hashlib, json, pathlib, urllib.request, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "https://sierra-tau-bench-public.s3.amazonaws.com/submissions/"
DEST = ROOT / "data/trajectories"
DEST.mkdir(parents=True, exist_ok=True)


def get(url, dest):
    if not dest.exists():
        req = urllib.request.Request(
            url, headers={"User-Agent": "banking-benchmark-research/0.1"}
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read()
        json.loads(raw)
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_suffix(".partial")
        temp.write_bytes(raw)
        temp.replace(dest)
    raw = dest.read_bytes()
    return {
        "path": str(dest.relative_to(ROOT)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def fetch(p):
    m = json.loads(p.read_text())
    sid = p.parent.name
    row = {
        "submission": sid,
        "model": m["model_name"],
        "modality": m.get("modality", "text"),
        "published": m["results"]["banking_knowledge"],
        "metadata": str(p.relative_to(ROOT)),
    }
    filename = m.get("trajectory_files", {}).get("banking_knowledge")
    if not filename:
        return row | {"status": "missing_filename"}
    directory = not filename.endswith(".json")
    key = f"{sid}/trajectories/{filename}" + ("/results.json" if directory else "")
    url = BASE + urllib.parse.quote(key, safe="/")
    row["url"] = url
    try:
        out = DEST / sid / ("results.json" if directory else "trajectories.json")
        row.update(get(url, out))
        row["status"] = "downloaded"
        if directory:
            meta = json.loads(out.read_text())
            entries = meta.get("simulation_index", [])

            def one(entry):
                name = entry["id"] + ".json"
                return get(
                    url.rsplit("/", 1)[0] + "/simulations/" + name,
                    out.parent / "simulations" / name,
                )

            with cf.ThreadPoolExecutor(max_workers=4) as pool:
                row["simulation_files"] = list(pool.map(one, entries))
    except Exception as e:
        row.update(status="unavailable", error=f"{type(e).__name__}: {e}")
    print(sid, row["status"], row.get("bytes", 0), flush=True)
    return row


if __name__ == "__main__":
    files = [
        p
        for p in sorted((ROOT / "data/leaderboard").rglob("submission.json"))
        if not p.parent.name.startswith("A_EXAMPLE")
        and json.loads(p.read_text()).get("results", {}).get("banking_knowledge")
    ]
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, files))
    (ROOT / "data/download_manifest.json").write_text(
        json.dumps(
            {
                "retrieved_utc": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "submissions": rows,
            },
            indent=2,
        )
    )
