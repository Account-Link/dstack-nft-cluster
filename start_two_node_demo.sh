#!/bin/bash

# Two-Node DStack P2P Demo Startup Script

set -e

echo "🚀 Starting Two-Node DStack P2P Demo"

# Check if required environment variables are set
if [ -z "$PRIVATE_KEY" ]; then
    echo "❌ Error: PRIVATE_KEY environment variable is required"
    echo "Please set it with: export PRIVATE_KEY=your_private_key_here"
    exit 1
fi

# Default environment variables
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

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up containers..."
    docker-compose -f docker-compose-node1.yml down --remove-orphans 2>/dev/null || true
    docker-compose -f docker-compose-node2.yml down --remove-orphans 2>/dev/null || true
}

# Set trap to cleanup on script exit
trap cleanup EXIT

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
cleanup

# Build the Docker image
echo "🔨 Building Docker image..."
docker-compose -f docker-compose-node1.yml build

# Start Node 1
echo "🚀 Starting Node 1..."
docker-compose -f docker-compose-node1.yml up -d

# Start Node 2  
echo "🚀 Starting Node 2..."
docker-compose -f docker-compose-node2.yml up -d

# Wait for containers to be ready
echo "⏳ Waiting for containers to start..."
sleep 5

# Check container status
echo "📊 Container status:"
docker ps --filter "name=dstack-node" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Wait for DStack agents to be ready
echo "⏳ Waiting for DStack agents to initialize..."
sleep 10

# Run the demo
echo "🎬 Running two-node demo..."
python3 demo_two_nodes.py

echo "✅ Demo completed! Check the logs above for results."
echo ""
echo "To view container logs:"
echo "  Node 1: docker-compose -f docker-compose-node1.yml logs -f"
echo "  Node 2: docker-compose -f docker-compose-node2.yml logs -f"
echo ""
echo "To stop the demo:"
echo "  ./stop_two_node_demo.sh"
