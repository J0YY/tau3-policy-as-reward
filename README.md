# τ³-Banking: policy as reward

Replication materials for **When a Banking Benchmark Penalizes Filing a Fraud Claim**.

[Read the paper](paper/main.pdf) · [Editable LaTeX](paper/main.tex) · [Maintainer disclosure](https://github.com/sierra-research/tau2-bench/issues/592#issuecomment-6042790694)

The audit compares selected banking policies with Regulation E, tests controlled changes to reference trajectories, and replays 10,880 public simulations from 32 submissions. It reproduces 26 published scores. Tasks 082, 084, and 086 have no passing runs under either original or primary alternative grading, so current rankings are unchanged. Controlled replays show a conditional scoring penalty when the rest of the reference workflow succeeds. Recorded outcomes vary beneath those shared zeros.

Legal interpretation is source-grounded and model-assisted, with explicit coverage and timing assumptions. State outcomes are descriptive; the capability comparisons are exploratory associations. No human coding agreement, external legal endorsement, or consumer-harm finding is claimed.

## Repository contents

| Location | Contents |
| --- | --- |
| `paper/` | Manuscript, references, generated tables, and figures |
| `regrade/` | Replay adapters, original grading, alternative predicates, and metrics |
| `scripts/` | Acquisition, inventory, controls, public replay, diagnostics, aggregation, and plotting |
| `tests/` | 67 tests for replay/scoring, recorded states, and tool-call chronology |
| `analysis-plan.md` | Original local computational plan and subsequent scope amendment |
| `results/public/` | Per-run replay results for all 32 accessible submissions |
| `results/` | Aggregates, controls, state outcomes, rank sensitivities, discrepancies, and environment snapshots |
| `data/` | Frozen submission metadata, input manifests, and issue provenance |
| `coding/` | Automated task, document, and action inventories; blank human-verdict columns are unused |
| `cluster/` | Slurm templates for CPU replay |
| `disclosure/` | Posted issue report and standalone minimal reproduction |

The raw trajectory archives (about 7.5 GB) and full upstream benchmark are acquired separately. Download manifests preserve source URLs, sizes, hashes, and failed downloads. This repository includes compact derived outputs sufficient to inspect the reported counts and rebuild the manuscript figures.

## Setup

Use Python 3.12 or 3.13. Replay uses offline BM25 retrieval and requires no model API key. A TeX installation with `pdflatex` and `bibtex` is needed only to rebuild the PDF.

```bash
git clone https://github.com/J0YY/tau3-policy-as-reward.git
cd tau3-policy-as-reward
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-analysis.txt
mkdir -p vendor logs paper/rendered

git clone https://github.com/sierra-research/tau2-bench.git vendor/tau2-bench
git -C vendor/tau2-bench checkout fc0055dc4e0a316c3f83133267fbd6faaa770992
.venv/bin/pip install -e 'vendor/tau2-bench[knowledge]'
```

The benchmark release is v1.0.1. Leaderboard metadata is frozen independently at `4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`. Its banking data, tools, and environment evaluator match the pinned release. Use individual task files: the aggregate `tasks.json` differs on 13 tasks.

`results/environment*.txt` records the original installed package versions for reference. The setup commands install the pinned benchmark and compatible dependencies; the snapshots document the original runs rather than serving as portable lockfiles.

## Inspect results and rebuild the paper

The saved result ledgers are included. Rebuild their aggregate tables and figures with:

```bash
bash scripts/build_paper.sh
pdftoppm -scale-to 1400 -png paper/main.pdf paper/rendered/page
```

`build_paper.sh` recomputes the aggregate score summary, generates tables and figures, then runs LaTeX and BibTeX. It does not download trajectories or rerun agent inference. `results/state_outcomes.json` contains the saved per-run outcomes and capability analysis; recompute it with:

```bash
.venv/bin/python -m scripts.state_outcomes
.venv/bin/python -m scripts.restricted_correlations
```

This uses the saved dispute states plus `results/extra_state_replays.json`, which contains the nine early-stop states recovered from the original archives. If that cache is removed, regenerating it requires the downloaded trajectories and pinned benchmark.

Verify the included artifact hashes before regenerating outputs:

```bash
python3 - <<'PY'
import hashlib, json
from pathlib import Path
for row in json.loads(Path('results/artifact_manifest.json').read_text())['artifacts']:
    assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
print('Artifact hashes verified')
PY
```

## Prepare a standalone LaTeX ZIP

After building the paper, package its editable sources and figures with:

```bash
python3 scripts/package_latex.py
```

The archive appears at `dist/tau3-policy-as-reward-latex.zip`. It includes the manuscript, bibliography, generated TeX inputs, figures, and build instructions. It compiles independently of the analysis environment. Upload it to Overleaf with `main.tex` as the main document, or extract it and run `bash build.sh` with a TeX installation.

## Reproduce the full replay

This writes fresh outputs at the paths used by the saved evidence. Preserve a copy or use a separate checkout to compare them with the published snapshot.

```bash
.venv/bin/python scripts/inventory.py
.venv/bin/python scripts/fetch_public.py
.venv/bin/python -m pytest -q
.venv/bin/python -m scripts.run_replays
.venv/bin/python -m scripts.controlled_sweep
```

The frozen metadata lists 33 banking submissions. At collection time 32 archives were accessible; the Distyl archive returned HTTP 404. Acquisition records failures explicitly. For one downloaded submission:

```bash
.venv/bin/python -m scripts.regrade_public claude-opus-4-5_sierra_2026-02-26
```

To replay every downloaded submission sequentially:

```bash
.venv/bin/python - <<'PY'
import json, subprocess, sys
from pathlib import Path
manifest = json.loads(Path('data/download_manifest.json').read_text())
for row in manifest['submissions']:
    if row['status'] == 'downloaded':
        subprocess.run([sys.executable, '-m', 'scripts.regrade_public', row['submission']], check=True)
PY
```

Then generate diagnostics and rebuild:

```bash
.venv/bin/python -m scripts.summarize
.venv/bin/python -m scripts.verify_official
.venv/bin/python -m scripts.diagnose_candidates
.venv/bin/python -m scripts.classify_residuals
.venv/bin/python -m scripts.reconcile_scores
.venv/bin/python -m scripts.rank_sensitivity
.venv/bin/python -m scripts.state_outcomes
.venv/bin/python -m scripts.restricted_correlations
.venv/bin/python -m scripts.trajectory_checks
bash scripts/build_paper.sh
```

The historical `finalize_replays.py` and `fix_shared_gate.py` scripts document corrections to initial run outputs. Fresh `regrade_public.py` runs already implement those rules; do not apply the historical repairs as an extra reproduction step.

For the minimal five liability/PIN comparisons posted on issue 592:

```bash
.venv/bin/python disclosure/replay_reference_patch.py
```

## Scoring and denominators

Machine-readable files retain these identifiers:

| Identifier | Meaning |
| --- | --- |
| `r0` | Pinned original grader, retaining the archived language judgment on the single mixed-basis task |
| `r1`, `r1s` | Remove three or seven selected tasks |
| `r2` / `R2-state` | Primary alternative record requirements with remaining state and logs retained |
| `r3` / `R3-state` | Stronger zero-liability sensitivity on seven tasks |
| `r4` / `R4-state` | Accept either original or primary alternative success |

Original, primary alternative, and accept-either scores coincide for every submission in the saved corpus. Premature stops receive zero; infrastructure failures are excluded. All retained runs have resolved original rewards. Higher-order pass estimates are emitted only when every retained task has enough trials.

The main state cohort has 111 scored trials on each of tasks 082, 084, and 086. The reproduced-score subset has 88. Capability analysis uses 81 common unaffected tasks, unconditional state-outcome rates, equal submission weighting, and explicitly described model-family sensitivities. Family-bootstrap intervals concern composition sensitivity, not a causal effect. `results/restricted_correlations.json` repeats the analysis on 27 submissions with at least three trials. The five excluded submissions all use voice with all tools exposed, so this restriction changes cohort composition as well as trial precision. `results/trajectory_checks.json` records completed dispute-history reads, their timing relative to filing, final open-dispute counts, and the task-086 date/liability cross-tabulation; regenerating it requires the downloaded archives.

Six baseline discrepancies are preserved in `results/baseline_reconciliation.json`: two reconcile numerically under an infrastructure-denominator sensitivity, and four remain unresolved. The main alternative adds no complete-task passes. Fifty runs meet the targeted component predicates but differ elsewhere; the residual ledger identifies those fields without assuming every difference is an independent error.

## Cluster execution

The original runs used the Athena CPU cluster; scheduler accounting is retained in `results/slurm_accounting.txt`. The templates now take an explicit checkout path:

```bash
export AUDIT_ROOT="$PWD"
mkdir -p logs
sbatch --array=0-31%4 cluster/regrade.sbatch
```

The array reads `cluster/submissions.txt`; check that its entries downloaded successfully. Set `SUBMISSION_LIST` to use another list. Partition, memory, and time requests reflect the original cluster and may need adjustment elsewhere. No GPU or new model inference is required.

## Provenance and updates

Issue [592](https://github.com/sierra-research/tau2-bench/issues/592) predates this audit and established the task-086 specification inconsistency and its 110-trial zero-pass result. The paper credits those findings and the related flagged tasks. Our follow-up provides external-law comparisons, omitted-claim/PIN analysis, controlled grader checks, and re-grading.

`results/artifact_manifest.json` hashes the published source and results. Regenerate it with `python3 scripts/freeze_artifacts.py` after changing outputs. Third-party source attribution is in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
