# DStack P2P SDK Specification

## Overview

The dstack-p2p SDK provides dead-simple peer discovery for distributed applications running in DStack TEEs. It consists of three main components:

1. **DstackClusterNFT Smart Contract**: Cluster definition and governance policy for membership management
2. **dstack-p2p Guest Module**: Runs within TEE to establish pairwise connections and provide simple peer lists
3. **Host/Deploy Tools**: Run outside TEE for cluster definition and node joining operations

## Core Value Proposition

**Before P2P SDK:** Applications must manually manage TEE attestation, VPN configuration, peer discovery, and network setup.

**With P2P SDK:** Applications get a simple list of connection strings. All complexity is hidden.

## Architecture

```
                           Governance & Customization
                          ┌─────────────────────────┐
                          │  Cluster Governance     │
                          │  • Max nodes per cluster│
                          │  • Network modes allowed│
                          │  • Access policies      │
                          └───────────┬─────────────┘
                                      │ Governs
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│         1. DstackClusterNFT Smart Contract                      │
│         • Cluster definition and governance                     │
│         • NFT-based membership control                          │
│         • Peer registry and access control                      │
│         • Configurable policies (voting, timeouts, limits)     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Contract calls & queries
                                  │
┌─────────────────────────────────▼─────────────────────────────────┐
│         2. Host/Deploy Tools                                     │
│         • Cluster deployment scripts                            │
│         • NFT minting and management                             │
│         • Cloud deployment orchestration                        │
│         • Node joining automation                               │
└─────────────────────────────────┬─────────────────────────────────┘
                                  │
                                  │ Deploys & provisions
                                  │
┌─────────────────────────────────▼─────────────────────────────────┐
│              TEE Environment (Base DStack Image)                 │
│  ┌───────────────────────────────────────────────────────────────┤
│  │              Guest Agent (Audited, Immutable)                │
│  │  • Key Derivation    • TDX Attestation    • KMS Integration  │
│  │                                                              │
│  │         3. dstack-p2p Guest Module                           │
│  │         • Simple Interface: register(), get_peers()          │
│  │         • Queries contract for peer discovery                │
│  │         • Automatic peer connection setup                    │
│  │                                                              │
│  │         Application Layer                                    │
│  │  ┌─────────────────────────────────────────────────────────┐ │
│  │  │  PostgreSQL    Redis     Kafka     Custom App          │ │
│  │  │      ▲          ▲          ▲          ▲                │ │
│  │  │      └──────────┴──────────┴──────────┘                │ │
│  │  │              Simple 3-line usage:                      │ │
│  │  │       sdk = DStackP2PSDK("0x123", "wireguard")         │ │
│  │  │       await sdk.register()                             │ │
│  │  │       peers = await sdk.get_peers()                    │ │
│  │  └─────────────────────────────────────────────────────────┘ │
└──┴───────────────────────────────────────────────────────────────┘
```

## Component 1: NFT Registration Policy

### Extended Smart Contract
```solidity
contract DstackClusterNFT {
    // Simplified peer registry
    mapping(string => string) public instanceToEndpoint;  // instanceId -> endpoint
    mapping(string => NetworkType) public instanceToNetworkType;
    
    enum NetworkType { TLS_GATEWAY, WIREGUARD }
    
    // Signature chain verification for registration
    function registerPeer(
        bytes32 instanceId,
        bytes memory derivedPublicKey,
        bytes memory appSignature,
        bytes memory kmsSignature,
        string memory endpoint
    ) external;
    // IDstackApp interface - core access control
    function isAppAllowed(AppBootInfo calldata bootInfo) external view returns (bool);
    function getPeerEndpoints() external view returns (string[] memory);
}
```

## Component 2: Within-TEE P2P Module

### Ultra-Simple Interface
```python
class DStackP2PSDK:
    def __init__(self, nft_contract_address: str, mode: str):
        """
        Args:
            nft_contract_address: Contract address for peer registry
            mode: 'tls' or 'wireguard'
        """
        
    async def register() -> bool:
        """
        Register this instance with the peer network.
        Auto-detects everything from TEE environment.
        Returns: Success boolean
        """
        
    async def get_peers() -> List[str]:
        """
        Get current list of active peer endpoints.
        Returns: List of connection strings ready for applications
        """
        
    async def monitor_peers(callback: Callable[[List[str]], None]):
        """
        Subscribe to peer list changes.
        Args:
            callback: Function called with new peer list when changes occur
        """
```

## Network Instantiations

### TLS/Gateway Mode

**What Applications Get:**
```python
sdk = DStackP2PSDK("0x123...", "tls")
await sdk.register()

peers = await sdk.get_peers()
# Returns: ["https://gateway-abc.dstack.io", "https://gateway-def.dstack.io"]
```

**What SDK Handles Internally:**
- Auto-discovers dstack gateway URL from TEE environment
- Registers gateway endpoint with NFT contract
- Monitors contract for peer changes
- Returns clean HTTPS URLs

### Wireguard Mode

**What Applications Get:**
```python
sdk = DStackP2PSDK("0x123...", "wireguard")
await sdk.register()

peers = await sdk.get_peers()
# Returns: ["10.0.1.1", "10.0.1.2", "10.0.1.3"]
```

**What SDK Handles Internally:**
- Generates VPN keypair within TEE
- Gets KMS signature for peer authentication
- Configures Wireguard daemon automatically
- Assigns predictable IP addresses (10.0.1.x)
- Monitors contract and reconfigures VPN when peers change
- Returns clean IP addresses

## Application Integration Examples

### PostgreSQL with Patroni
```python
# Monitor script
async def update_patroni_cluster(peer_list):
    patroni.update_cluster_members([
        f"postgres://postgres@{peer}:5432/postgres" 
        for peer in peer_list
    ])
    patroni.reload_config()

sdk = DStackP2PSDK("0x123...", "wireguard")
await sdk.register()
await sdk.monitor_peers(update_patroni_cluster)

# Main application just uses the IPs normally
```

### Redis Cluster
```python
# Monitor script  
async def update_redis_cluster(peer_list):
    redis_client.cluster_meet_all([f"{peer}:6379" for peer in peer_list])

sdk = DStackP2PSDK("0x123...", "tls")
await sdk.register()
await sdk.monitor_peers(update_redis_cluster)
```

### Kafka Cluster
```python
# Monitor script
async def update_kafka_config(peer_list):
    kafka_config["bootstrap.servers"] = ",".join([f"{peer}:9092" for peer in peer_list])

sdk = DStackP2PSDK("0x123...", "wireguard")  
await sdk.register()
await sdk.monitor_peers(update_kafka_config)
```

## Key Design Principles

1. **Zero Configuration**: Guest module auto-detects from TEE environment
2. **Zero Parameters**: Guest `register()` takes no arguments (internally handles signature chains)
3. **Clean Abstractions**: Applications get connection strings, not crypto
4. **Event-Driven**: Real-time updates via `monitor_peers()`
5. **Network Agnostic**: Same interface for TLS and VPN modes

## Implementation Phases

### Phase 1: DstackClusterNFT Smart Contract
- [ ] Modify existing contract with P2P registry functions
- [ ] Add cluster configuration and governance
- [ ] Implement isAppAllowed access control
- [ ] Deploy and test on local anvil + mainnet

### Phase 2: dstack-p2p Guest Module
- [ ] Implement core Python SDK with 3-line interface
- [ ] Add automatic peer discovery and connection management
- [ ] Support TLS and Wireguard network modes
- [ ] Integrate with DStack SDK for key derivation

### Phase 3: Host/Deploy Tools
- [ ] Create cluster deployment scripts (Foundry-based)
- [ ] Build cloud deployment tools (Phala Cloud SDK)
- [ ] Implement NFT minting and management automation
- [ ] Add monitoring and cluster management interfaces


## Security Model

- **NFT Authorization**: 1 NFT = 1 authorized peer
- **TEE Attestation**: All peer identity verified through dstack KMS
- **Encrypted Transport**: TLS via gateway or Wireguard VPN
- **Byzantine Fault Tolerance**: Inherits existing contract consensus mechanisms
- **Zero Trust**: Each peer independently validates others through contract

---

## Engineering Implementation Notes

### Role 1: Cluster Definition (App Deployer)

**Responsibility:** Deploy and configure the IDstackApp contract that defines the P2P cluster.

**Current Codebase Integration:**
- Modify existing `DstackClusterNFT.sol` to add P2P functionality directly (no inheritance)
- Keep existing Foundry setup (`contracts/script/`, forge deployment patterns)
- Deploy contract to blockchain (local anvil for testing, mainnet for production)

**Contract Extensions:**
```solidity
// Add to existing DstackClusterNFT.sol
mapping(string => string) public instanceToEndpoint;  
mapping(string => NetworkType) public instanceToNetworkType;

function registerPeer() external;
function isAppAllowed(AppBootInfo calldata bootInfo) external view returns (bool); 
function getPeerEndpoints() external view returns (string[] memory);
```

**Cluster Deployment Workflow:**
```bash
# 1. Deploy P2P-enabled NFT contract
KMS_ROOT_ADDRESS=0x... forge script script/DeployDstackClusterNFT.s.sol --broadcast --rpc-url $RPC_URL

# 2. Configure cluster parameters (max nodes, network type, etc.)
cast send --private-key $DEPLOYER_KEY $CONTRACT_ADDRESS \
  "setClusterConfig(uint256,uint8)" $MAX_NODES $NETWORK_TYPE

# 3. Set NFT minting permissions/pricing
cast send --private-key $DEPLOYER_KEY $CONTRACT_ADDRESS \
  "setMintingPolicy(uint256,bool)" $PRICE $PUBLIC_MINTING

# Contract address becomes the cluster identifier
echo "Cluster deployed at: $CONTRACT_ADDRESS"
echo "Share this address with node operators"
```

**App Deployer Tools (New):**
- `deploy-cluster.sh` - Full cluster deployment script
- `manage-cluster.js` - Web interface for cluster management
- `cluster-status.py` - Monitor cluster health and membership

### Role 2: Node Joining (Node Operator)

**Responsibility:** Join an existing P2P cluster by minting NFT and deploying TEE instance.

**Prerequisites:**
- Cluster contract address from app deployer
- Sufficient funds for NFT minting
- Phala Cloud account for TEE deployment

**Node Joining Workflow:**

**Step 1: Local Testing (Optional)**
```bash
# Test with existing simulator setup
CLUSTER_CONTRACT=0x... ./run_counter.sh node-test 8080

# Verify local P2P functionality
python3 test_p2p_integration.py --contract=$CLUSTER_CONTRACT
```

**Step 2: Cloud Deployment**
```bash
# Install cloud deployment dependencies  
npm install @phala/cloud viem

# Deploy single node to join cluster
node deploy_p2p_node.js \
  --cluster-contract=$CLUSTER_CONTRACT \
  --instance-id=$MY_NODE_ID \
  --network-mode=wireguard
```

```javascript
// deploy_p2p_node.js - Single node deployment
import { safeProvisionCvm, safeDeployAppAuth, safeCommitCvmProvision } from '@phala/cloud'

async function joinCluster(clusterContract, instanceId) {
  // 1. Provision CVM for this node
  const app = await safeProvisionCvm(client, {
    docker_compose: P2P_NODE_COMPOSE,
    // ... compose config
  })
  
  // 2. Deploy app auth (creates app_id for this node)
  const contract = await safeDeployAppAuth({
    kmsContractAddress: KMS_CONTRACT,
    composeHash: app.compose_hash,
    // ... auth params
  })
  
  // 3. Get encryption key
  const pubkey = await safeGetAppEnvEncryptPubKey(client, {
    app_id: contract.appId,
    kms: kmsSlug
  })
  
  // 4. Prepare node environment
  const nodeEnv = [
    { key: 'CLUSTER_CONTRACT', value: clusterContract },
    { key: 'INSTANCE_ID', value: instanceId },
    { key: 'P2P_MODE', value: 'wireguard' },
    { key: 'NODE_ROLE', value: 'peer' }
  ]
  
  // 5. Deploy the actual CVM
  const cvm = await safeCommitCvmProvision(client, {
    app_id: contract.appId,
    encrypted_env: await encryptEnvVars(nodeEnv, pubkey.public_key),
    compose_hash: app.compose_hash,
    kms_id: kmsSlug,
    contract_address: contract.appAuthAddress,
    deployer_address: contract.deployer
  })
  
  console.log(`Node deployed: ${cvm.vm_uuid}`)
  console.log(`App ID: ${contract.appId}`)
  console.log(`Must mint NFT for joining cluster`)
}
```

**Step 3: NFT Minting (Untrusted Host)**
```bash
# After CVM deployment, get instance details and pause to prevent boot loops
INSTANCE_ID=$(extract_instance_id $CVM_DEPLOYMENT)
INSTANCE_ADDRESS=$(get_tee_instance_address $CVM_ID)

# Pause CVM to prevent isAppAllowed failures during registration
pause_cvm $CVM_ID

# Mint NFT from untrusted host (extends current run_counter.sh pattern)
cast send --private-key $HOST_PRIVATE_KEY $CLUSTER_CONTRACT \
  "mintNodeAccess(address,string)" $INSTANCE_ADDRESS $INSTANCE_ID

# Verify NFT was minted
cast call --rpc-url $RPC_URL $CLUSTER_CONTRACT \
  "walletToTokenId(address)" $INSTANCE_ADDRESS

# Resume CVM - now isAppAllowed will pass and TEE boots successfully
resume_cvm $CVM_ID
```

**Step 4: P2P Network Usage (Inside TEE - Simple)**
```python
# Inside the deployed TEE application - ultra-simple interface
from dstack_p2p import DStackP2PSDK

# Application just uses the 3-line interface
sdk = DStackP2PSDK("0x123...", "wireguard")  # cluster contract address
await sdk.register()
peers = await sdk.get_peers()  # ["10.0.1.1", "10.0.1.2", "10.0.1.3"]

# Network is automatically set up - application uses peers directly
for peer in peers:
    connect_to_database(f"postgres://postgres@{peer}:5432/db")
```

**Environment Bridging:**
- Local testing: Uses `simulator/dstack.sock` with existing patterns
- Cloud production: Uses real Phala TEE environment
- Same Python `dstack_sdk.DstackClient()` interface for both environments
- Node operators only need the cluster contract address to join

### Key Implementation Constraints

**No Guest Agent Changes Required:**
- P2P SDK only uses application-layer `dstack_sdk` client
- Leverages signature chains for attestation (signature-chain-verification.md patterns)
- Guest agent remains audited/immutable base image component

**Codebase Evolution Strategy:**
- `counter.py` gets P2P methods alongside existing leader election
- `contracts/src/` gets P2P extensions to existing NFT contract
- New cloud deployment scripts alongside existing local scripts
- Same testing patterns (`anvil`, `cast`, Python integration tests)

**Files to Modify:**
- `contracts/src/DstackClusterNFT.sol` - Add P2P registry functions
- `counter.py` - Integrate P2P SDK alongside existing Web3 calls  
- `run_counter.sh` - Add P2P registration steps
- `requirements.txt` - Add `dstack-p2p` dependency

**Files to Add:**
- `dstack_p2p/` - New SDK module (Python package)
- `deploy_p2p_cluster.js` - Cloud deployment script
- `package.json` - Node.js dependencies for cloud deployment

## Alternative Deployment Approaches

### Docker Compose Startup Service Pattern

For environments where CVM pause/resume is not available, an alternative approach uses a startup service to handle registration timing:

**Modified isAppAllowed (Permissive):**
```solidity
function isAppAllowed(AppBootInfo calldata bootInfo) external view returns (bool) {
    // Allow any valid TEE to boot - registration checking happens later
    return verifyTeeAttestation(bootInfo);
}
```

**Docker Compose Integration:**
```yaml
services:
  dstack-cluster-startup:
    image: dstack/cluster-startup
    environment:
      - CLUSTER_CONTRACT=0x123...
      - INSTANCE_ID=${INSTANCE_ID}
    # Polls contract until this instance is registered
    
  postgres:
    depends_on:
      dstack-cluster-startup:
        condition: service_completed_successfully
    
  app:
    depends_on:
      dstack-cluster-startup:
        condition: service_completed_successfully
```

**Startup Service Implementation:**
```python
# dstack-cluster-startup service
while True:
    if contract.instanceIsRegistered(INSTANCE_ID):
        print("Instance registered, allowing application startup")
        exit(0)  # Success - dependent services can start
    time.sleep(5)
```

This approach allows TEEs to boot immediately but blocks application services until cluster registration is confirmed.

---

**Ready to simplify distributed TEE applications?** The dstack-p2p SDK turns complex peer discovery into a 3-line integration.