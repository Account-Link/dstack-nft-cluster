#!/bin/bash
set -e

# Configuration
CONTRACT_ADDRESS="${CONTRACT_ADDRESS:-0xa85233C63b9Ee964Add6F2cffe00Fd84eb32338f}"
RPC_URL="${RPC_URL:-http://localhost:8545}"
NUM_INSTANCES="${1:-3}"

echo "=== Testing P2P Cluster with $NUM_INSTANCES instances ==="
echo "Contract: $CONTRACT_ADDRESS"
echo "RPC URL: $RPC_URL"

# Check prerequisites
if [ ! -S "./simulator/dstack.sock" ]; then
    echo "ERROR: DStack simulator not found at ./simulator/dstack.sock"
    echo "Please start the simulator first"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "ERROR: uv not found. Please install uv first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Clean up any existing instances
echo "Cleaning up existing hello P2P instances..."
pkill -f "hello_p2p.py" || true
sleep 2

# Start instances
PIDS=()
BASE_PORT=8080

for i in $(seq 1 $NUM_INSTANCES); do
    INSTANCE_ID="hello$i"
    PORT=$((BASE_PORT + i - 1))
    
    echo "Starting instance $i: $INSTANCE_ID on port $PORT"
    
    # Start instance in background
    ./run_hello_p2p.sh "$INSTANCE_ID" "$PORT" > "hello_${INSTANCE_ID}.log" 2>&1 &
    PID=$!
    PIDS+=($PID)
    
    echo "Started $INSTANCE_ID (PID: $PID) on port $PORT"
    
    # Brief pause between starts
    sleep 3
done

echo ""
echo "=== All instances started ==="
for i in $(seq 1 $NUM_INSTANCES); do
    INSTANCE_ID="hello$i"
    PORT=$((BASE_PORT + i - 1))
    echo "  $INSTANCE_ID: http://localhost:$PORT (log: hello_${INSTANCE_ID}.log)"
done

echo ""
echo "=== Monitoring cluster formation ==="
echo "Waiting 15 seconds for cluster to form..."
sleep 15

# Check peer discovery
echo ""
echo "=== Checking peer discovery ==="
ALL_CONNECTED=true

for i in $(seq 1 $NUM_INSTANCES); do
    PORT=$((BASE_PORT + i - 1))
    INSTANCE_ID="hello$i"
    
    echo -n "Checking $INSTANCE_ID peers: "
    
    if PEERS=$(curl -s "http://localhost:$PORT/peers" 2>/dev/null); then
        PEER_COUNT=$(echo "$PEERS" | jq -r '.peers | length' 2>/dev/null || echo "0")
        EXPECTED_PEERS=$((NUM_INSTANCES - 1))  # All except self
        
        if [ "$PEER_COUNT" -eq "$EXPECTED_PEERS" ]; then
            echo "✅ Found $PEER_COUNT peers (expected $EXPECTED_PEERS)"
        else
            echo "❌ Found $PEER_COUNT peers (expected $EXPECTED_PEERS)"
            ALL_CONNECTED=false
        fi
    else
        echo "❌ Instance not responding"
        ALL_CONNECTED=false
    fi
done

echo ""
if [ "$ALL_CONNECTED" = true ]; then
    echo "🎉 SUCCESS: All instances discovered each other!"
else
    echo "⚠️  Some instances haven't fully connected yet"
fi

echo ""
echo "=== Testing peer communication ==="
for i in $(seq 1 $NUM_INSTANCES); do
    PORT=$((BASE_PORT + i - 1))
    INSTANCE_ID="hello$i"
    
    echo -n "Testing $INSTANCE_ID hello endpoint: "
    if RESPONSE=$(curl -s "http://localhost:$PORT/hello?from=test" 2>/dev/null); then
        MESSAGE=$(echo "$RESPONSE" | jq -r '.message' 2>/dev/null || echo "Invalid response")
        echo "✅ $MESSAGE"
    else
        echo "❌ No response"
    fi
done

echo ""
echo "=== Cluster Status ==="
echo "Running instances:"
for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
        echo "  PID $pid: ✅ Running"
    else
        echo "  PID $pid: ❌ Stopped"
    fi
done

echo ""
echo "=== Instructions ==="
echo "View logs:"
for i in $(seq 1 $NUM_INSTANCES); do
    echo "  tail -f hello_hello$i.log"
done
echo ""
echo "Stop all instances:"
echo "  pkill -f \"hello_p2p.py\""
echo ""
echo "Individual instance URLs:"
for i in $(seq 1 $NUM_INSTANCES); do
    PORT=$((BASE_PORT + i - 1))
    echo "  hello$i: http://localhost:$PORT"
    echo "    /info   - Instance info"
    echo "    /peers  - Peer list"
    echo "    /hello  - Hello endpoint"
done

echo ""
echo "✨ P2P cluster test completed!"