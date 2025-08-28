#!/bin/bash
set -e

# Configuration
CONTRACT_ADDRESS="${CONTRACT_ADDRESS:-0xa85233C63b9Ee964Add6F2cffe00Fd84eb32338f}"
RPC_URL="${RPC_URL:-http://localhost:8545}"
INSTANCE_ID="${1:-node1}"
PORT="${2:-8080}"
FUNDING_AMOUNT="${FUNDING_AMOUNT:-0.1}"

# NFT owner private key (should have NFT)
NFT_OWNER_KEY="${NFT_OWNER_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"

echo "=== Running Counter Instance: $INSTANCE_ID on port $PORT ==="
echo "Contract: $CONTRACT_ADDRESS"
echo "RPC URL: $RPC_URL"

# Activate virtual environment
echo "Activating virtual environment..."
source venv310/bin/activate

# Check if simulator is running
if [ ! -S "./simulator/dstack.sock" ]; then
    echo "ERROR: DStack simulator not found at ./simulator/dstack.sock"
    echo "Please start the simulator first"
    exit 1
fi

echo "Starting counter instance in background..."

# Start counter in background and capture its output
python3 counter.py \
    --instance-id "$INSTANCE_ID" \
    --contract "$CONTRACT_ADDRESS" \
    --rpc-url "$RPC_URL" \
    --port "$PORT" \
    --dstack-socket "./simulator/dstack.sock" \
    2>&1 | tee "counter_${INSTANCE_ID}.log" &

COUNTER_PID=$!
echo "Counter PID: $COUNTER_PID"

# Wait for counter to start and output registration info
echo "Waiting for counter to initialize..."
sleep 3

# Extract instance address from log
INSTANCE_ADDRESS=""
for i in {1..10}; do
    if [ -f "counter_${INSTANCE_ID}.log" ]; then
        INSTANCE_ADDRESS=$(grep "Instance Address:" "counter_${INSTANCE_ID}.log" | head -1 | sed 's/.*Instance Address: //' | cut -d' ' -f1)
        if [ -n "$INSTANCE_ADDRESS" ]; then
            break
        fi
    fi
    sleep 1
done

if [ -z "$INSTANCE_ADDRESS" ]; then
    echo "ERROR: Could not extract instance address from counter logs"
    kill $COUNTER_PID 2>/dev/null || true
    exit 1
fi

echo "Instance address: $INSTANCE_ADDRESS"

# Check current balance
echo "Checking instance balance..."
BALANCE=$(cast balance --rpc-url "$RPC_URL" "$INSTANCE_ADDRESS")
echo "Current balance: $BALANCE wei"

# Fund the instance if needed
if [ "$BALANCE" = "0" ]; then
    echo "Funding instance with $FUNDING_AMOUNT ETH..."
    cast send \
        --rpc-url "$RPC_URL" \
        --private-key "$NFT_OWNER_KEY" \
        --value "${FUNDING_AMOUNT}ether" \
        "$INSTANCE_ADDRESS" \
        ""
    
    echo "Funding transaction sent. Waiting for confirmation..."
    sleep 2
    
    NEW_BALANCE=$(cast balance --rpc-url "$RPC_URL" "$INSTANCE_ADDRESS")
    echo "New balance: $NEW_BALANCE wei"
else
    echo "Instance already has balance, skipping funding"
fi

echo ""
echo "=== Counter Instance Started ==="
echo "Instance ID: $INSTANCE_ID"
echo "Instance Address: $INSTANCE_ADDRESS"
echo "Port: $PORT"
echo "PID: $COUNTER_PID"
echo "Log file: counter_${INSTANCE_ID}.log"
echo ""
echo "To interact with the counter:"
echo "  curl http://localhost:$PORT/status"
echo "  curl http://localhost:$PORT/counter"
echo "  curl -X POST http://localhost:$PORT/increment"
echo ""
echo "To stop the counter:"
echo "  kill $COUNTER_PID"
echo ""
echo "Registration details are in the log file."
echo "NFT owner should use those details to call registerInstanceWithProof()"