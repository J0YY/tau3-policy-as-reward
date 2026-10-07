import concurrent.futures as cf, datetime, hashlib, json, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "legal/sources"
OUT.mkdir(exist_ok=True)
URLS = {
    "rege2": "https://www.consumerfinance.gov/rules-policy/regulations/1005/2/",
    "rege6": "https://www.consumerfinance.gov/rules-policy/regulations/1005/6/",
    "rege11": "https://www.consumerfinance.gov/rules-policy/regulations/1005/11/",
    "rege_interp2": "https://www.consumerfinance.gov/rules-policy/regulations/1005/interp-2/",
    "regz13": "https://www.consumerfinance.gov/rules-policy/regulations/1026/13/",
    "regb2": "https://www.consumerfinance.gov/rules-policy/regulations/1002/2/",
    "eft_faq": "https://www.consumerfinance.gov/compliance/compliance-resources/deposit-accounts-resources/electronic-fund-transfers/electronic-fund-transfers-faqs/",
    "ecfr_20251114": "https://www.ecfr.gov/api/versioner/v1/full/2025-11-14/title-12.xml?part=1005",
    "tauknowledge": "https://arxiv.org/abs/2603.04370",
    "loopholes": "https://arxiv.org/abs/2609.14400",
    "procedure": "https://arxiv.org/abs/2603.03116",
    "euagent": "https://arxiv.org/abs/2510.21524",
}


def one(pair):
    k, u = pair
    r = {
        "id": k,
        "url": u,
        "retrieved_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    try:
        with urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=45
        ) as f:
            raw = f.read()
        p = OUT / (k + (".xml" if "ecfr" in k else ".html"))
        p.write_bytes(raw)
        r.update(
            path=str(p.relative_to(ROOT)),
            sha256=hashlib.sha256(raw).hexdigest(),
            bytes=len(raw),
            status="ok",
        )
    except Exception as e:
        r.update(status="error", error=str(e))
    return r


with cf.ThreadPoolExecutor(max_workers=4) as pool:
    rows = list(pool.map(one, URLS.items()))
(OUT / "manifest.json").write_text(json.dumps(rows, indent=2))
print([(r["id"], r["status"]) for r in rows])
