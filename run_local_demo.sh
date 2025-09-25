#!/bin/bash

# Local Two-Node Demo with Rye Support

set -e

echo "🚀 Running Local Two-Node DStack P2P Demo"

# Check if required environment variables are set
if [ -z "$PRIVATE_KEY" ]; then
    echo "❌ Error: PRIVATE_KEY environment variable is required"
    echo "Please set it with: export PRIVATE_KEY=your_private_key_here"
    exit 1
fi

# Set default environment variables
export CONTRACT_ADDRESS=${CONTRACT_ADDRESS:-0x9d22D844690ff89ea5e8a6bb4Ca3F7DAc83a40c3}
export RPC_URL=${RPC_URL:-https://base.llamarpc.com}
export NODE1_CONNECTION_URL=${NODE1_CONNECTION_URL:-http://localhost:8081}
export NODE2_CONNECTION_URL=${NODE2_CONNECTION_URL:-http://localhost:8082}

echo "Configuration:"
echo "  Contract Address: $CONTRACT_ADDRESS"
echo "  RPC URL: $RPC_URL"
echo "  Node 1 URL: $NODE1_CONNECTION_URL"
echo "  Node 2 URL: $NODE2_CONNECTION_URL"
echo ""

# Check if rye is available
if command -v rye &> /dev/null; then
    echo "✅ Rye detected - using rye to run the demo"
    echo "Installing/syncing dependencies..."
    rye sync
    echo ""
    echo "🎬 Running demo with rye..."
    rye run python test_local_two_nodes.py
else
    echo "ℹ️  Rye not detected - using system Python"
    echo "Make sure dependencies are installed:"
    echo "  pip install -r requirements.lock"
    echo ""
    echo "🎬 Running demo with system Python..."
    python3 test_local_two_nodes.py
fi

echo "✅ Demo script completed!"
