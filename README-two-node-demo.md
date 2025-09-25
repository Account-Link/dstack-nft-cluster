# Two-Node DStack P2P Demo

This demo shows how two separate DStack nodes can register to the same smart contract using the P2P SDK and discover each other through the `getPeers()` functionality.

## Overview

The demo creates:
- **Node 1**: Runs on port 8081, connection URL `http://localhost:8081`, uses `./simulator/` 
- **Node 2**: Runs on port 8082, connection URL `http://localhost:8082`, uses `./simulator2/`
- **Separate Simulators**: Each node runs its own DStack simulator instance (more realistic)
- Both nodes register to the same smart contract with different connection URLs
- Both nodes can discover each other via `getPeers()` SDK call

## Prerequisites

1. **Environment Variables**: Set your private key
   ```bash
   export PRIVATE_KEY="your_ethereum_private_key_here"
   ```

2. **Optional Configuration**:
   ```bash
   export CONTRACT_ADDRESS="0x9d22D844690ff89ea5e8a6bb4Ca3F7DAc83a40c3"  # Default
   export RPC_URL="https://base.llamarpc.com"                              # Default
   export NODE1_CONNECTION_URL="http://localhost:8081"                     # Default
   export NODE2_CONNECTION_URL="http://localhost:8082"                     # Default
   ```

3. **Dependencies**: Make sure you have Docker and Docker Compose installed

## Quick Start

### Option 1: Local Testing with Rye (Recommended for Development)

```bash
# Install rye if not already installed
curl -sSf https://rye-up.com/get | bash

# Verify dual simulator setup (optional)
python3 verify_dual_simulator_setup.py

# Run local demo (starts both simulators)
./run_local_demo.sh
```

### Option 2: Docker Containers (Production-like)

```bash
# Start the demo with Docker containers
./start_two_node_demo.sh

# Stop the demo
./stop_two_node_demo.sh
```

### Option 3: Manual Steps (Docker)

```bash
# 1. Build the Docker image
docker-compose -f docker-compose-node1.yml build

# 2. Start Node 1
docker-compose -f docker-compose-node1.yml up -d

# 3. Start Node 2
docker-compose -f docker-compose-node2.yml up -d

# 4. Wait for agents to initialize (10-15 seconds)
sleep 15

# 5. Run the demo
python3 demo_two_nodes.py

# 6. Clean up
docker-compose -f docker-compose-node1.yml down
docker-compose -f docker-compose-node2.yml down
```

## What the Demo Does

1. **Initialization**: 
   - Waits for both DStack sockets to be available
   - Creates SDK instances for both nodes

2. **Registration**:
   - Node 1 registers its connection URL (`http://localhost:8081`) to the contract
   - Node 2 registers its connection URL (`http://localhost:8082`) to the contract
   - Each registration includes cryptographic proof from the TEE

3. **Peer Discovery**:
   - Both nodes call `getPeers()` to retrieve all registered peer endpoints
   - Verifies that both nodes can see each other in the peer list

4. **Validation**:
   - Confirms both connection URLs are present in the peer list
   - Reports success/failure of the P2P discovery process

## Expected Output

```
🚀 Starting Two-Node DStack P2P Demo
Contract Address: 0x9d22D844690ff89ea5e8a6bb4Ca3F7DAc83a40c3
Node 1 URL: http://localhost:8081
Node 2 URL: http://localhost:8082

=== REGISTERING BOTH NODES ===
Registering Node 1...
✅ Node 1 registered successfully!
Registering Node 2...
✅ Node 2 registered successfully!

=== DEMONSTRATING PEER DISCOVERY ===
Getting peers from Node 1...
Node 1 sees peers: ['http://localhost:8081', 'http://localhost:8082']
Getting peers from Node 2...
Node 2 sees peers: ['http://localhost:8081', 'http://localhost:8082']
✅ SUCCESS: Both nodes can see each other in the peer list!
✅ Both node connection URLs found in peer list!

🎉 TWO-NODE DEMO COMPLETED SUCCESSFULLY!
```

## File Structure

```
├── docker-compose-node1.yml           # Docker Compose for Node 1
├── docker-compose-node2.yml           # Docker Compose for Node 2
├── demo_two_nodes.py                  # Main demo script (Docker version)
├── test_local_two_nodes.py            # Local demo script (dual simulators)
├── verify_dual_simulator_setup.py     # Setup verification script
├── start_two_node_demo.sh             # Automated Docker startup script
├── stop_two_node_demo.sh              # Docker cleanup script
├── run_local_demo.sh                  # Local demo with rye support
├── pyproject.toml                     # Rye/Python project configuration
├── simulator/                         # DStack simulator files (Node 1)
├── simulator2/                        # DStack simulator files (Node 2)
└── dstack_cluster.py                 # P2P SDK implementation
```

## Troubleshooting

### Socket Connection Issues
- Ensure both `simulator/` and `simulator2/` directories exist with DStack simulator files
- **Docker**: Check that DStack agents are running in both containers
- **Local**: Make sure both simulator binaries are executable and start properly
- Verify socket files are created: `ls -la simulator*/dstack.sock`
- Run verification script: `python3 verify_dual_simulator_setup.py`

### Registration Failures
- Verify `PRIVATE_KEY` environment variable is set
- Check that the private key has sufficient ETH for gas fees
- Ensure RPC URL is accessible and working

### Port Conflicts
- Make sure ports 8081 and 8082 are available
- Modify `NODE1_CONNECTION_URL` and `NODE2_CONNECTION_URL` if needed

### Container Logs
```bash
# View Node 1 logs
docker-compose -f docker-compose-node1.yml logs -f

# View Node 2 logs
docker-compose -f docker-compose-node2.yml logs -f
```

## Integration with Applications

Once both nodes are registered and discovering each other, applications can:

1. **Connect to Either Node**: Use either `http://localhost:8081` or `http://localhost:8082`
2. **Discover All Peers**: Call `getPeers()` to find all available nodes in the cluster
3. **Load Balance**: Distribute connections across discovered peer endpoints
4. **Fault Tolerance**: Switch to other peers if one becomes unavailable

## Next Steps

- Scale to more than 2 nodes by creating additional docker-compose files
- Implement application-level communication between discovered peers
- Add health checking and automatic failover logic
- Deploy to production environments with proper networking
