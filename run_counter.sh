#!/bin/bash
set -e

# Configuration
CONTRACT_ADDRESS="${CONTRACT_ADDRESS:-0xa85233C63b9Ee964Add6F2cffe00Fd84eb32338f}"
RPC_URL="${RPC_URL:-http://localhost:8545}"
INSTANCE_ID="${1:-node1}"
PORT="${2:-8080}"

# Host private key - this address will own the NFT and pay for all transactions
HOST_PRIVATE_KEY="${HOST_PRIVATE_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"

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

echo "Getting deployment info from counter..."

# Run counter briefly in preparation mode to get deployment info
python3 counter.py \
    --instance-id "$INSTANCE_ID" \
    --contract "$CONTRACT_ADDRESS" \
    --rpc-url "$RPC_URL" \
    --port "$PORT" \
    --dstack-socket "./simulator/dstack.sock" \
    --host-key "$HOST_PRIVATE_KEY" \
    --prepare-only 2>&1 | tee "counter_${INSTANCE_ID}_prep.log" &

PREP_PID=$!
echo "Preparation PID: $PREP_PID"

# Wait for preparation to complete
sleep 5
kill $PREP_PID 2>/dev/null || true

# Extract host address from preparation log
HOST_ADDRESS=""
for i in {1..10}; do
    if [ -f "counter_${INSTANCE_ID}_prep.log" ]; then
        # Look for host address
        HOST_ADDRESS=$(grep "Host Address:" "counter_${INSTANCE_ID}_prep.log" | head -1 | sed 's/.*Host Address: //' | cut -d' ' -f1)
        if [ -n "$HOST_ADDRESS" ]; then
            break
        fi
    fi
    sleep 1
done

if [ -z "$HOST_ADDRESS" ]; then
    echo "ERROR: Could not extract host address from preparation logs"
    echo "Preparation log contents:"
    cat "counter_${INSTANCE_ID}_prep.log" 2>/dev/null || echo "No preparation log found"
    exit 1
fi

echo "Host address: $HOST_ADDRESS"

# Check if host address already has an NFT
echo "Checking if host address has NFT..."
TOKEN_ID=$(cast call --rpc-url "$RPC_URL" "$CONTRACT_ADDRESS" "walletToTokenId(address)" "$HOST_ADDRESS")
echo "Current token ID: $TOKEN_ID"

# Convert hex to decimal for comparison
TOKEN_ID_DECIMAL=$(echo "$TOKEN_ID" | sed 's/^0x//' | tr '[:lower:]' '[:upper:]' | echo "ibase=16; $(cat)" | bc 2>/dev/null || echo "0")

if [ "$TOKEN_ID_DECIMAL" = "0" ]; then
    echo "Host address needs NFT. Minting node access..."
    
    # Mint NFT for the host address
    cast send \
        --rpc-url "$RPC_URL" \
        --private-key "$HOST_PRIVATE_KEY" \
        "$CONTRACT_ADDRESS" \
        "mintNodeAccess(address,string)" \
        "$HOST_ADDRESS" \
        "$INSTANCE_ID"
    
    echo "NFT minted. Waiting for confirmation..."
    sleep 2
    
    # Verify NFT was minted
    NEW_TOKEN_ID=$(cast call --rpc-url "$RPC_URL" "$CONTRACT_ADDRESS" "walletToTokenId(address)" "$HOST_ADDRESS")
    echo "New token ID: $NEW_TOKEN_ID"
    
    # Convert new token ID to decimal
    NEW_TOKEN_ID_DECIMAL=$(echo "$NEW_TOKEN_ID" | sed 's/^0x//' | tr '[:lower:]' '[:upper:]' | echo "ibase=16; $(cat)" | bc 2>/dev/null || echo "0")
    
    if [ "$NEW_TOKEN_ID_DECIMAL" = "0" ]; then
        echo "ERROR: Failed to mint NFT"
        exit 1
    fi
    
    TOKEN_ID=$NEW_TOKEN_ID
    TOKEN_ID_DECIMAL=$NEW_TOKEN_ID_DECIMAL
else
    echo "Host address already has NFT token ID: $TOKEN_ID_DECIMAL"
fi

# Now register the instance with the contract
echo "Registering instance with contract..."
cast send \
    --rpc-url "$RPC_URL" \
    --private-key "$NFT_OWNER_KEY" \
    "$CONTRACT_ADDRESS" \
    "registerInstance(string)" \
    "$INSTANCE_ID"

echo "Instance registration transaction sent. Waiting for confirmation..."
sleep 2

# Check if instance is already registered
echo "Checking if instance is registered..."
ACTIVE_INSTANCES=$(cast call --rpc-url "$RPC_URL" "$CONTRACT_ADDRESS" "getActiveInstances()")
echo "Active instances: $ACTIVE_INSTANCES"

# Check if our instance ID is in the active instances
if echo "$ACTIVE_INSTANCES" | grep -q "$INSTANCE_ID"; then
    echo "Instance already registered and active"
else
    echo "Instance not registered. Starting counter..."
fi

echo "Starting counter instance in background..."

# Start counter in background and capture its output
python3 counter.py \
    --instance-id "$INSTANCE_ID" \
    --contract "$CONTRACT_ADDRESS" \
    --rpc-url "$RPC_URL" \
    --port "$PORT" \
    --dstack-socket "./simulator/dstack.sock" \
    --host-key "$HOST_PRIVATE_KEY" \
    2>&1 | tee "counter_${INSTANCE_ID}.log" &

COUNTER_PID=$!
echo "Counter PID: $COUNTER_PID"

# Wait for counter to start and register
echo "Waiting for counter to start and register..."
sleep 3

# Wait for counter to start
echo "Waiting for counter to start..."
sleep 5

# Final check - verify instance is registered
ACTIVE_INSTANCES=$(cast call --rpc-url "$RPC_URL" "$CONTRACT_ADDRESS" "getActiveInstances()")
if echo "$ACTIVE_INSTANCES" | grep -q "$INSTANCE_ID"; then
    echo "Instance successfully registered!"
else
    echo "ERROR: Instance failed to register"
    kill $COUNTER_PID 2>/dev/null || true
    exit 1
fi

echo "Counter is running successfully!"

echo ""
echo "=== Counter Instance Started ==="
echo "Instance ID: $INSTANCE_ID"
echo "Host Address: $HOST_ADDRESS"
echo "Token ID: $TOKEN_ID_DECIMAL"
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
echo "Instance is now registered and ready for consensus participation."