# DStack P2P SDK Specification

## Overview

The dstack-p2p SDK provides dead-simple peer discovery for distributed applications running in DStack TEEs. It consists of two main components:

1. **NFT Registration Policy**: Smart contract-based membership system extending the existing DstackMembershipNFT
2. **Within-TEE P2P Module**: Ultra-simple library that handles all complexity internally

## Core Value Proposition

**Before P2P SDK:** Applications must manually manage TEE attestation, VPN configuration, peer discovery, and network setup.

**With P2P SDK:** Applications get a simple list of connection strings. All complexity is hidden.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DStack P2P SDK                               │
├─────────────────────┬───────────────────────────────────────────┤
│   NFT Registration  │         Within-TEE P2P Module             │
│      Policy         │                                           │
│                     │  ┌─────────────────┬─────────────────────┤
│  - Smart Contract   │  │ Simple Interface│  Hidden Complexity  │
│  - Membership Mgmt  │  │                 │                     │
│  - Byzantine FT     │  │ register()      │ • TEE Discovery     │
│  - Leader Election  │  │ get_peers()     │ • VPN Setup         │
│                     │  │ monitor_peers() │ • Authentication    │
└─────────────────────┴──┴─────────────────┴─────────────────────┘
```

## Component 1: NFT Registration Policy

### Extended Smart Contract
```solidity
contract DstackP2PMembership is DstackMembershipNFT {
    // Simplified peer registry
    mapping(string => string) public instanceToEndpoint;  // instanceId -> endpoint
    mapping(string => NetworkType) public instanceToNetworkType;
    mapping(string => uint256) public lastHeartbeat;
    
    enum NetworkType { TLS_GATEWAY, WIREGUARD }
    
    // Zero-parameter registration
    function registerPeer() external;  // Auto-detects instance ID from TEE
    function updateHeartbeat() external;
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

1. **Zero Configuration**: Everything auto-detected from TEE environment
2. **Zero Parameters**: `register()` takes no arguments
3. **Clean Abstractions**: Applications get connection strings, not crypto
4. **Async/Await**: Modern Python async patterns
5. **Event-Driven**: Real-time updates via `monitor_peers()`
6. **Network Agnostic**: Same interface for TLS and VPN modes

## Implementation Phases

### Phase 1: Core SDK
- [ ] Extend DstackMembershipNFT contract
- [ ] Implement basic Python SDK
- [ ] TLS mode with gateway discovery
- [ ] Simple peer registration and discovery

### Phase 2: VPN Integration  
- [ ] Wireguard mode implementation
- [ ] Automatic VPN key management
- [ ] IP address assignment strategy
- [ ] Real-time VPN reconfiguration

### Phase 3: Production Hardening
- [ ] Error handling and retries
- [ ] Health monitoring and failover
- [ ] Performance optimization
- [ ] Multi-language SDK support (Go, Rust)

## Benefits Over Manual Approach

**Manual Approach:**
```python
# Applications must handle:
- TEE instance ID discovery
- KMS signature verification  
- VPN key generation and exchange
- Wireguard configuration management
- Peer endpoint resolution
- Contract interaction complexity
- Network failure handling
```

**P2P SDK Approach:**
```python
# Applications only need:
sdk = DStackP2PSDK("0x123...", "wireguard")
await sdk.register()
peers = await sdk.get_peers()  # ["10.0.1.1", "10.0.1.2"]
```

The SDK transforms a 200+ line complex setup into 3 lines of simple code.

## Security Model

- **NFT Authorization**: 1 NFT = 1 authorized peer
- **TEE Attestation**: All peer identity verified through dstack KMS
- **Encrypted Transport**: TLS via gateway or Wireguard VPN
- **Byzantine Fault Tolerance**: Inherits existing contract consensus mechanisms
- **Zero Trust**: Each peer independently validates others through contract

---

**Ready to simplify distributed TEE applications?** The dstack-p2p SDK turns complex peer discovery into a 3-line integration.