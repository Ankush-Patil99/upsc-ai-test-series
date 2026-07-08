#!/bin/bash
# ============================================================================
# UPSC AI Test Series — AWS EC2 Deployment Script
# ============================================================================
# This script sets up a fresh AWS EC2 Ubuntu instance (t2.micro free tier)
# with Docker, pulls the production stack, and starts the application.
#
# Prerequisites:
#   1. An AWS EC2 instance (Ubuntu 22.04, t2.micro) with ports 8000, 80 open.
#   2. SSH access to the instance.
#   3. Docker Hub credentials (set as GitHub Secrets for CI/CD).
#
# Usage:
#   ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP> 'bash -s' < deploy.sh
# ============================================================================

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  UPSC AI Test Series — Production Deployment"
echo "═══════════════════════════════════════════════════════════"

# ── 1. Install Docker & Docker Compose ────────────────────────────────────────
echo "[1/5] Installing Docker..."
sudo apt-get update -qq
sudo apt-get install -y -qq docker.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# ── 2. Clone the repository ──────────────────────────────────────────────────
echo "[2/5] Cloning repository..."
REPO_DIR="$HOME/upsc-test-series"
if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR" && git pull origin main
else
    git clone https://github.com/Ankush-Patil99/upsc-ai-test-series.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# ── 3. Create production environment file ─────────────────────────────────────
echo "[3/5] Creating .env file..."
cat > .env << 'EOF'
# ── LLM API Keys (Free tier fallback for cloud deployment) ────────────────────
GROQ_API_KEY=your_groq_api_key_here

# ── Auth ──────────────────────────────────────────────────────────────────────
SECRET_KEY=$(openssl rand -hex 32)

# ── LangSmith Tracing (Optional but recommended for demos) ────────────────────
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=upsc-test-series-prod
EOF

echo "⚠️  IMPORTANT: Edit .env with your real API keys before proceeding!"
echo "   nano .env"

# ── 4. Build and start production stack ───────────────────────────────────────
echo "[4/5] Building and starting Docker containers..."
sudo docker compose -f docker-compose.prod.yml up -d --build

# ── 5. Enable pgvector extension ─────────────────────────────────────────────
echo "[5/5] Enabling pgvector extension..."
sleep 10  # Wait for PostgreSQL to be fully ready
sudo docker exec upsc_db_prod psql -U upsc_user -d upsc_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Deployment Complete!"
echo ""
echo "  API:      http://$(curl -s ifconfig.me):8000"
echo "  Frontend: http://$(curl -s ifconfig.me):8000/ui"
echo "  Swagger:  http://$(curl -s ifconfig.me):8000/docs"
echo "═══════════════════════════════════════════════════════════"
