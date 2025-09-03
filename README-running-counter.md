# DStack NFT Counter Cluster - Running Guide

This document explains how to run the distributed counter system with NFT-based membership and DStack integration.

## Overview

The system consists of:
- **Smart Contract**: NFT membership contract for node authorization
- **DStack Simulator**: Provides TEE attestation and key derivation
- **Counter Nodes**: Python services that derive instance-specific keys and participate in consensus
- **Shell Script**: Automates the process of funding and starting counter instances

## Prerequisites

1. **Foundry/Anvil**: Local blockchain running on `http://localhost:8545`
2. **DStack Simulator**: Running in `./simulator/` directory
3. **uv**: Python package manager (replaces traditional virtual environments)
4. **Smart Contract**: Deployed NFT membership contract

## Architecture

Each counter instance:
- Derives a **unique address** using DStack's `instance/{dstack_instance_id}` key path
- **Requires external funding** from NFT owner before participating in consensus
- **Generates signature proofs** for NFT owner to register the instance
- **Participates in Byzantine fault tolerant leader election** once registered

## Quick Start

### 1. Start DStack Simulator
```bash
cd simulator
rm -f *.sock  # Clean up any old sockets
./dstack-simulator &
```

### 2. Start a Counter Instance
```bash
./run_counter.sh node1 8080
```

The script will:
- Start the counter instance
- Extract the derived instance address  
- Fund the address with ETH (0.1 ETH by default)
- Display registration details for NFT owner

### 3. Check Instance Status
```bash
curl http://localhost:8080/status
curl http://localhost:8080/counter
curl http://localhost:8080/wallet-info
```

## Manual Process

### 1. Start DStack Simulator
```bash
cd simulator && ./dstack-simulator
```

### 2. Get Instance Address
```bash
source venv310/bin/activate
python3 -c "
from counter import DistributedCounter
import asyncio
counter = DistributedCounter('node1', '0xa85233C63b9Ee964Add6F2cffe00Fd84eb32338f', port=8080, dstack_socket='./simulator/dstack.sock')
print(f'Address: {counter.wallet_address}')
"
```

### 3. Fund the Instance
```bash
cast send \
  --rpc-url http://localhost:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --value 0.1ether \
  <INSTANCE_ADDRESS>
```

### 4. Start Counter
```bash
python3 counter.py \
  --instance-id node1 \
  --contract 0xa85233C63b9Ee964Add6F2cffe00Fd84eb32338f \
  --port 8080 \
  --dstack-socket ./simulator/dstack.sock
```

## Running Multiple Instances

For a 3-node cluster:

```bash
# Terminal 1: Start simulator
cd simulator && ./dstack-simulator

# Terminal 2: Start node1
./run_counter.sh node1 8080

# Terminal 3: Start node2  
./run_counter.sh node2 8081

# Terminal 4: Start node3
./run_counter.sh node3 8082
```

Each instance will have:
- **Unique DStack instance ID** (automatically assigned)
- **Unique derived address** (needs individual funding)
- **Unique signature proof** (for individual registration)

## Key Files

- `counter.py` - Main counter service with DStack integration
- `run_counter.sh` - Automated startup and funding script
- `signature_proof.py` - Signature chain proof generation
- `simulator/dstack-simulator` - DStack TEE simulator
- `contracts/src/DstackMembershipNFT.sol` - Smart contract

## Configuration

### Environment Variables
- `CONTRACT_ADDRESS` - NFT membership contract address
- `RPC_URL` - Ethereum RPC endpoint (default: http://localhost:8545)
- `FUNDING_AMOUNT` - ETH amount to fund instances (default: 0.1)
- `NFT_OWNER_KEY` - Private key of NFT owner for funding

### Default Values
- Contract: `0xa85233C63b9Ee964Add6F2cffe00Fd84eb32338f`
- RPC URL: `http://localhost:8545`
- Funding: `0.1 ETH`
- NFT Owner Key: `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80` (Anvil account #0)

## API Endpoints

Each counter instance exposes:

- `GET /status` - Node status and cluster info
- `GET /counter` - Current counter value
- `POST /increment` - Increment counter (leader only)
- `GET /log` - Operation history
- `GET /members` - Active cluster members
- `GET /health` - Health check
- `GET /wallet-info` - Instance wallet details

## Registration Process

1. **Instance starts** and derives unique address via DStack
2. **NFT owner funds** the instance address
3. **Instance generates** signature proof with registration details
4. **NFT owner calls** `registerInstanceWithProof()` on smart contract
5. **Instance participates** in consensus and leader election

## Troubleshooting

### DStack Connection Issues
- Ensure simulator is running: `ps aux | grep dstack-simulator`
- Check socket exists: `ls -la simulator/dstack.sock`
- Restart simulator: `cd simulator && rm -f *.sock && ./dstack-simulator`

### Port Conflicts
- Change port: `./run_counter.sh node1 8081`
- Check usage: `netstat -tlnp | grep 8080`

### Funding Issues
- Check balance: `cast balance --rpc-url http://localhost:8545 <ADDRESS>`
- Verify transaction: Check transaction hash from `cast send` output

### Instance Address Extraction
If shell script can't extract address, get it manually:
```bash
source venv310/bin/activate
python3 check_dstack_info.py
```

## Next Steps

1. **Register instances** with NFT owner calling smart contract
2. **Test leader election** and consensus mechanisms
3. **Deploy multiple instances** for Byzantine fault tolerance testing
4. **Package into Docker Compose** for production deployment