#!/usr/bin/env bash
# run_generate.sh — Convenience wrapper for generate_questions_final.py
# Uses the upsctest conda environment that has all dependencies.
#
# USAGE EXAMPLES:
#   ./run_generate.sh --status
#   ./run_generate.sh --count 5
#   ./run_generate.sh --batch pipeline_data/topic_queue.json
#   ./run_generate.sh --topic "Indian Polity" --subtopic "Article 21" --paper GS2
#   ./run_generate.sh --ingest-only          # Re-ingest all data
#   ./run_generate.sh --ingest --count 10    # Ingest then generate 10 Qs
#
# For HPC SLURM submission, see run_slurm.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/scai/mtech/aib242291/.conda/envs/upsctest/bin/python"

cd "$SCRIPT_DIR"
exec "$PYTHON" generate_questions_final.py "$@"
