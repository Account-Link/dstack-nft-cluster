#!/bin/bash
set -e

# Configuration
CONTRACT_ADDRESS="${CONTRACT_ADDRESS:-0xa85233C63b9Ee964Add6F2cffe00Fd84eb32338f}"
RPC_URL="${RPC_URL:-http://localhost:8545}"
INSTANCE_ID="${1:-hello1}"
PORT="${2:-8080}"

# Host private key - this address will own the NFT and pay for all transactions
HOST_PRIVATE_KEY="${HOST_PRIVATE_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"

echo "=== Running Hello P2P Instance: $INSTANCE_ID on port $PORT ==="
echo "Contract: $CONTRACT_ADDRESS"
echo "RPC URL: $RPC_URL"

# Using uv for dependency management
echo "Using uv for Python environment..."

# Check if simulator is running
if [ ! -S "./simulator/dstack.sock" ]; then
    echo "ERROR: DStack simulator not found at ./simulator/dstack.sock"
    echo "Please start the simulator first"
    exit 1
fi

echo "Getting deployment info and instance address..."

# Get instance address from TEE environment
uv run python -c "
from dstack_sdk import DstackClient

client = DstackClient('./simulator/dstack.sock')
info = client.info()

# Extract instance address using signature derivation
import hashlib
instance_address = '0x' + hashlib.sha256(info.instance_id.encode()).hexdigest()[:40]

print('INSTANCE_ID=' + info.instance_id)
print('INSTANCE_ADDRESS=' + instance_address)
" > temp_instance_info.sh

# Source the instance address
source temp_instance_info.sh
rm temp_instance_info.sh

if [ -z "$INSTANCE_ADDRESS" ]; then
    echo "ERROR: Could not get instance address from DStack"
    exit 1
fi

echo "Instance address: $INSTANCE_ADDRESS"

# Connection URL for this instance (dev mode - can use any format)
CONNECTION_URL="http://localhost:$PORT"

echo "Connection URL: $CONNECTION_URL"

# Check if this instance already has an NFT
echo "Checking if instance has NFT..."
TOKEN_ID=$(cast call --rpc-url "$RPC_URL" "$CONTRACT_ADDRESS" \
    "walletToTokenId(address)" "$INSTANCE_ADDRESS" 2>/dev/null || echo "0")

if [ "$TOKEN_ID" = "0" ]; then
    echo "Minting NFT for instance..."
    
    # Mint NFT for this instance
    cast send --private-key "$HOST_PRIVATE_KEY" --rpc-url "$RPC_URL" "$CONTRACT_ADDRESS" \
        "mintNodeAccess(address,string)" "$INSTANCE_ADDRESS" "$INSTANCE_ID"
    
    # Verify NFT was minted
    TOKEN_ID=$(cast call --rpc-url "$RPC_URL" "$CONTRACT_ADDRESS" \
        "walletToTokenId(address)" "$INSTANCE_ADDRESS")
    
    echo "NFT minted with token ID: $TOKEN_ID"
else
    echo "Instance already has NFT with token ID: $TOKEN_ID"
fi

echo ""
echo "Starting Hello P2P application..."
echo "View logs: tail -f hello_${INSTANCE_ID}.log"
echo "Stop with: pkill -f \"hello_p2p.py.*$INSTANCE_ID\""
echo ""

# Run the Hello P2P application (ultra-simple interface!)
uv run python hello_p2p.py "$CONTRACT_ADDRESS" \
    --port "$PORT" \
    --verbose 2>&1 | tee "hello_${INSTANCE_ID}.log"