#!/bin/bash
# start_vllm.sh — Starts both vLLM inference servers for UPSC AI Engine V2.0
# Run this BEFORE main.py or data_ingestion.py
# -----------------------------------------------------------------------------
# GPU memory split across 2x 80GB A100:
#   Heavy (Qwen-72B AWQ)  : tensor_parallel across GPU 0+1 → ~2x speed
#   Light (Mistral-7B)    : runs on GPU 1 only, 85% memory utilization
#   NOTE: Both servers share GPU 1. Qwen takes ~40GB total (20GB/GPU in TP=2),
#         leaving ~44GB on GPU 1 for Mistral (85% of 80GB = 68GB, safe).
# -----------------------------------------------------------------------------

set -e

echo "============================================================"
echo " UPSC AI Engine V2.0 — Starting vLLM Inference Servers"
echo "============================================================"

# Load conda environment
export HF_HOME="/home/scai/mtech/aib242291/UPSC_Test_Agent/models"
export HF_HUB_OFFLINE=1
export VLLM_NO_USAGE_STATS=1
# Override CUDA_VISIBLE_DEVICES to be an integer instead of a UUID which crashes vLLM
# Safe single-GPU mode: GPU 0 → Qwen, GPU 1 → Mistral
export CUDA_VISIBLE_DEVICES="0,1"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate upsctest

# ── Heavy endpoint — Qwen-72B-AWQ (Nodes 2, 3, 6) ──────────────────────────
echo "[1/2] Starting Qwen-72B-AWQ on port 8001 (tensor_parallel=2 → GPU 0+1)..."
env CUDA_VISIBLE_DEVICES="0,1" vllm serve /home/scai/mtech/aib242291/UPSC_Test_Agent/models/Qwen2.5-72B-AWQ \
    --port 8001 \
    --quantization awq \
    --tensor-parallel-size 2 \
    --gpu-memory-utilization 0.45 \
    --max-model-len 4096 \
    --dtype float16 \
    --served-model-name "Qwen/Qwen2.5-72B-Instruct-AWQ" \
    --uvicorn-log-level warning \
    > pipeline_data/logs/vllm_heavy.log 2>&1 &

HEAVY_PID=$!
echo "    Heavy server PID: $HEAVY_PID"

# Wait for heavy server to be ready by checking logs
echo "    Waiting for Qwen-72B to load (this takes 2-4 minutes)..."
until grep -q "Starting vLLM server" pipeline_data/logs/vllm_heavy.log 2>/dev/null; do
    sleep 5
    echo "    Still loading..."
done
echo "    ✅ Qwen-72B-AWQ ready on port 8001"

# ── Light endpoint — Mistral-7B (Nodes 1, 4, 5) ─────────────────────────────
echo "[2/2] Starting Mistral-7B-Instruct on port 8002 (GPU 1, 85% mem)..."
env CUDA_VISIBLE_DEVICES="1" vllm serve /home/scai/mtech/aib242291/UPSC_Test_Agent/models/Mistral-7B-v0.3 \
    --port 8002 \
    --gpu-memory-utilization 0.45 \
    --max-model-len 4096 \
    --dtype float16 \
    --served-model-name "mistralai/Mistral-7B-Instruct-v0.3" \
    --uvicorn-log-level warning \
    > pipeline_data/logs/vllm_light.log 2>&1 &

LIGHT_PID=$!
echo "    Light server PID: $LIGHT_PID"

echo "    Waiting for Mistral-7B to load..."
until grep -q "Starting vLLM server" pipeline_data/logs/vllm_light.log 2>/dev/null; do
    sleep 5
    echo "    Still loading..."
done
echo "    ✅ Mistral-7B-Instruct ready on port 8002"

echo ""
echo "============================================================"
echo " Both vLLM servers are running!"
echo "   Heavy: http://localhost:8001  (PID: $HEAVY_PID)"
echo "   Light: http://localhost:8002  (PID: $LIGHT_PID)"
echo ""
echo " Logs:"
echo "   tail -f pipeline_data/logs/vllm_heavy.log"
echo "   tail -f pipeline_data/logs/vllm_light.log"
echo ""
echo " To stop both servers:"
echo "   kill $HEAVY_PID $LIGHT_PID"
echo "============================================================"

# Save PIDs for easy shutdown
echo "$HEAVY_PID" > pipeline_data/logs/vllm_heavy.pid
echo "$LIGHT_PID" > pipeline_data/logs/vllm_light.pid
