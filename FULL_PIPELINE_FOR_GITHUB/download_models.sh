#!/bin/bash
# Description: Download models for 80GB A100.

# --- AUTHENTICATION ---
export HF_TOKEN="your_huggingface_token_here"  # Paste your token between the quotes

# --- CONFIGURATION ---
export HF_HOME="/home/scai/mtech/aib242291/UPSC_Test_Agent/models"
mkdir -p $HF_HOME

echo "Downloading main models for 80GB A100..."

# 1. LIGHTWEIGHT MODEL
hf download mistralai/Mistral-7B-Instruct-v0.3 --local-dir $HF_HOME/Mistral-7B-v0.3

# 2. PREMIUM HEAVY MODEL 
hf download Qwen/Qwen2.5-72B-Instruct-AWQ --local-dir $HF_HOME/Qwen2.5-72B-AWQ

# 3. EMBEDDING MODELS
hf download BAAI/bge-large-en-v1.5 --local-dir $HF_HOME/bge-large
hf download BAAI/bge-small-en --local-dir $HF_HOME/bge-small

echo "All models successfully downloaded."