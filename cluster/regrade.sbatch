#!/bin/bash
#SBATCH --job-name=bank-audit-public
#SBATCH --partition=compute
#SBATCH --cpus-per-task=1
#SBATCH --mem=10G
#SBATCH --time=03:00:00
#SBATCH --output=logs/public-%A_%a.log
set -euo pipefail
cd "${AUDIT_ROOT:?Set AUDIT_ROOT to the absolute path of this checkout}"
export PYTHONPATH="$PWD"
export OMP_NUM_THREADS=1
submission=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" "${SUBMISSION_LIST:-cluster/submissions.txt}")
.venv/bin/python -m scripts.regrade_public "$submission"
