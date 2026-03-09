#!/bin/bash
set -e

echo "=========================================="
echo "  Elastic AgentCore - Environment Setup"
echo "=========================================="

# Install uv package manager
echo ""
echo ">>> Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install all Python dependencies
echo ""
echo ">>> Installing Python dependencies..."
uv sync

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Create your .env file:"
echo "     cp .env.example .env"
echo ""
echo "  2. Edit .env with your Elastic credentials:"
echo "     - KIBANA_URL"
echo "     - ELASTIC_API_KEY"
echo ""
echo "  3. Configure AWS credentials:"
echo "     aws configure"
echo ""
echo "  4. Launch the Streamlit chat UI:"
echo "     uv run streamlit run app.py --server.headless true"
echo ""
