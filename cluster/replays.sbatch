#!/bin/bash
#SBATCH --job-name=bank-audit-replay
#SBATCH --partition=compute
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=logs/replays-%j.log
set -euo pipefail
cd "${AUDIT_ROOT:?Set AUDIT_ROOT to the absolute path of this checkout}"
export PYTHONPATH="$PWD"
.venv/bin/python -m scripts.run_replays
