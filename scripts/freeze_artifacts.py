"""Hash the public source and derived-result snapshot."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
patterns = (
    ".gitignore", ".gitattributes", "README.md", "THIRD_PARTY_NOTICES.md", "requirements-analysis.txt", "pyproject.toml", "analysis-plan.md",
    "results/*.json", "results/*.csv", "results/*.txt", "results/public/*.json",
    "regrade/*.py", "scripts/*.py", "scripts/*.sh", "tests/*.py",
    "cluster/*.sbatch", "cluster/*.txt", "coding/*.csv", "coding/*.json",
    "data/*.json", "data/leaderboard/**/submission.json", "disclosure/*.md", "disclosure/*.py",
)
paths = sorted({p for pattern in patterns for p in ROOT.glob(pattern)
                if p.is_file() and p.name not in {"artifact_manifest.json", "citation_audit.json", "citation_audit.txt", "reviewer_revision_review.txt", "build_paper.sh", "package_latex.py"}})
out = {
    "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "artifacts": [{"path": str(p.relative_to(ROOT)),
                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
}
(ROOT / "results/artifact_manifest.json").write_text(json.dumps(out, indent=2) + "\n")
print(f"Hashed {len(paths)} public artifacts")
