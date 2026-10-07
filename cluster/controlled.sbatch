#!/bin/bash
#SBATCH --job-name=bank-audit-controls
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=logs/controls-%j.log
set -euo pipefail
cd "${AUDIT_ROOT:?Set AUDIT_ROOT to the absolute path of this checkout}"
export PYTHONPATH="$PWD"
.venv/bin/python -m pytest -q
.venv/bin/python -m scripts.run_replays
.venv/bin/python -m scripts.controlled_sweep
