#!/bin/bash
#SBATCH --job-name=bank-audit-verify
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=logs/verify-%j.log
set -euo pipefail
cd "${AUDIT_ROOT:?Set AUDIT_ROOT to the absolute path of this checkout}"
export PYTHONPATH="$PWD"
.venv/bin/python -m scripts.verify_official
