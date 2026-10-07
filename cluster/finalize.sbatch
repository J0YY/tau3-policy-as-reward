#!/bin/bash
#SBATCH --job-name=bank-audit-finalize
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=10G
#SBATCH --time=01:00:00
#SBATCH --output=logs/finalize-%j.log
set -euo pipefail
cd "${AUDIT_ROOT:?Set AUDIT_ROOT to the absolute path of this checkout}"
export PYTHONPATH="$PWD"
.venv/bin/python -m scripts.summarize
.venv/bin/python -m scripts.state_outcomes
.venv/bin/python -m pytest -q
.venv/bin/python -m pip freeze > results/environment.txt
