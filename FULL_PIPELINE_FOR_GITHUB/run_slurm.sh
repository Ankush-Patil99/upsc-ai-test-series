#!/usr/bin/env bash
# run_slurm.sh — Submit UPSC MCQ generation to SLURM cluster
# Requires at least 1 GPU for vLLM inference (Qwen-72B + Mistral-7B)
#
# USAGE:
#   sbatch run_slurm.sh                         # Default: 5 questions from topic bank
#   sbatch run_slurm.sh --count 50              # Generate 50 questions
#   sbatch run_slurm.sh --batch pipeline_data/topic_queue.json --output pipeline_data/output/batch1.json

#SBATCH --job-name=upsc_generate
#SBATCH --output=pipeline_data/logs/slurm_generate_%j.log
#SBATCH --error=pipeline_data/logs/slurm_generate_%j.err
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:4
#SBATCH --mem=80G
#SBATCH --cpus-per-task=16

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/scai/mtech/aib242291/.conda/envs/upsctest/bin/python"

echo "=== UPSC MCQ Generator ==="
echo "Job ID   : $SLURM_JOB_ID"
echo "Node     : $SLURM_NODELIST"
echo "GPUs     : $SLURM_GPUS_ON_NODE"
echo "Started  : $(date)"
echo ""

cd "$SCRIPT_DIR"
mkdir -p logs output

# ── Start vLLM servers ─────────────────────────────────────────────────────
echo "Starting vLLM servers..."
bash start_vllm.sh &
VLLM_PID=$!

# Wait for vLLM to be ready (adjust sleep based on model load time)
echo "Waiting 120s for vLLM to initialize..."
sleep 120

# ── Run question generation ────────────────────────────────────────────────
echo "Starting question generation..."
"$PYTHON" generate_questions_final.py "$@"

# ── Cleanup ────────────────────────────────────────────────────────────────
kill $VLLM_PID 2>/dev/null || true

echo ""
echo "=== Done: $(date) ==="
