# NFT-Gated DStack Node Cluster

A Byzantine fault-tolerant P2P cluster system that uses NFT-based membership to control node deployment authorization in DStack networks.

## 🎯 Overview

This project provides a scarcity-based network where **1 NFT = 1 authorized node deployment** with full signature verification through DStack's KMS system. It implements:

- **NFT-based membership**: ERC721 tokens control node authorization  
- **DStack signature verification**: Complete KMS → App Key → Derived Key chain validation
- **P2P cluster discovery**: Nodes register connection URLs for peer discovery
- **Local development environment**: Anvil + DStack simulator for rapid testing

## 🏗️ Architecture

### Core Components

1. **DstackMembershipNFT Contract**: NFT-based membership with signature verification
2. **DStack P2P SDK**: Ultra-simple interface for cluster membership
3. **KMS Signature Verification**: Complete cryptographic validation chain
4. **Local Development Environment**: Anvil + DStack simulator for fast iteration

### Signature Verification Chain

The system implements DStack's complete cryptographic verification:

1. **KMS Root**: Hardware-backed root key signs app keys
2. **App Key**: Intermediate key signs derived keys for specific purposes  
3. **Derived Key**: Final key used for actual node operations
4. **Contract Verification**: Smart contract validates entire signature chain

```
KMS Root → App Key → Derived Key → Node Operations
   ↓         ↓          ↓
[Signature] [Signature] [Operations]
   ↓         ↓          ↓
[Contract validates all signatures before allowing registration]
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ with web3, eth-account, eth-keys packages
- Anvil (from Foundry) for local blockchain
- DStack simulator for signature generation

### 1. Environment Setup

```bash
# Start Anvil blockchain
anvil --host 0.0.0.0 --port 8545 &

# Start DStack simulator (in separate terminal)
cd simulator && ./dstack-simulator &
```

### 2. Deploy Contract

```bash
# Deploy the NFT membership contract
cd contracts
forge script script/DeployDstackMembershipNFT.s.sol --rpc-url http://localhost:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast
```

**Current Deployed Contract**: `0x2B0d36FACD61B71CC05ab8F3D2355ec3631C0dd5`

### 3. Test P2P Registration

```bash
# Test the complete signature verification and registration flow
python3 scripts/test_contract_signature_verification.py

# Or run the P2P SDK demo
python3 dstack_cluster.py
```

### 4. Expected Output

```
🎉 Full signature verification working!
INFO:__main__:Connected to cluster with peers: ['http://localhost:8080']
```

## 📁 Project Structure

```
dstack-nft-cluster/
├── contracts/                   # Smart contract development (Foundry)
│   ├── src/DstackMembershipNFT.sol       # Main NFT + signature verification contract
│   ├── script/DeployDstackMembershipNFT.s.sol  # Deployment script
│   └── test/DstackMembershipNFT.t.sol    # Contract tests
├── scripts/
│   └── test_contract_signature_verification.py  # Complete signature chain testing
├── simulator/                   # DStack simulator for local development
│   ├── dstack-simulator        # Binary for generating signatures
│   └── appkeys.json           # KMS configuration
├── dstack_cluster.py           # Main P2P SDK interface  
├── signature_proof.py          # DStack signature generation utilities
├── dstack_sdk.py              # DStack communication client
├── refs/                       # Reference implementations and research
│   └── dstack-kms-simulator/   # Working SimpleDstackVerifier reference
└── notes/                      # Development notes and analysis
```

### Key Files

- **`dstack_cluster.py`**: Ultra-simple 3-line P2P SDK interface
- **`DstackMembershipNFT.sol`**: Complete signature verification smart contract  
- **`test_contract_signature_verification.py`**: Comprehensive signature format testing
- **`signature_proof.py`**: DStack simulator integration utilities

## 🔧 Development

### P2P SDK Usage

Ultra-simple 3-line interface for P2P cluster membership:

```python
from dstack_cluster import DStackP2PSDK

# Connect to cluster with NFT-based authorization
sdk = DStackP2PSDK("0x2B0d36FACD61B71CC05ab8F3D2355ec3631C0dd5", "http://localhost:8080")
success = await sdk.register()  # Automatic signature verification
peers = await sdk.get_peers()   # Get all cluster endpoints
```

### Smart Contract Development  

The `DstackMembershipNFT` contract implements complete signature verification:

```solidity
contract DstackMembershipNFT is ERC721 {
    // Instance and peer registry
    mapping(string => uint256) public instanceToToken;
    mapping(string => string) public instanceToConnectionUrl;
    
    // KMS root for signature verification
    address public immutable kmsRootAddress;
    
    // Complete signature chain validation
    function _verifySignatureChain(
        string memory purpose,
        bytes memory derivedPublicKey, 
        bytes memory appPublicKey,
        bytes memory appSignature,
        bytes memory kmsSignature,
        bytes32 appId,
        address appKeyAddress
    ) internal view returns (bool);
}
```

### Signature Verification Details

Critical implementation notes for signature verification:

1. **Message Format**: Use raw `keccak256`, not Ethereum signed message format
2. **V Value Adjustment**: Add 27 to `v` component if `v < 27` for `ecrecover`
3. **App ID Format**: Use 20-byte app ID for KMS signature verification
4. **Complete Parameter Set**: `registerPeer` requires 9 parameters including `appKeyAddress`

```solidity
// Critical: Raw keccak256, not Ethereum signed message
bytes32 messageHash = keccak256(bytes(message));

// Critical: V adjustment for signature recovery  
if (v < 27) {
    v += 27;
}
address recovered = ecrecover(messageHash, v, r, s);

// Critical: 20-byte app ID for KMS verification
bytes20 appIdBytes20 = bytes20(appId);
bytes32 kmsMessage = keccak256(abi.encodePacked("dstack-kms-issued:", appIdBytes20, appPublicKey));
```

## 🧪 Testing

### Signature Verification Testing

```bash
# Comprehensive signature format testing
python3 scripts/test_contract_signature_verification.py
```

Expected output:
```
🎉 Full signature verification working!
   Format Analysis: ✅ PASS
   KMS Verification: ✅ PASS  
   Contract Call: ✅ PASS
```

### P2P Registration Testing

```bash
# Test complete P2P registration flow
python3 dstack_cluster.py
```

Expected output:
```
INFO:__main__:registerInstance transaction successful: 4fb9d4818e...
INFO:__main__:registerPeer transaction successful: 78ac1ede70f7...
INFO:__main__:Connected to cluster with peers: ['http://localhost:8080']
```

## 🔄 Development Status

### ✅ Phase 1: Signature Verification (Complete)
- [x] Complete DStack signature chain verification 
- [x] Smart contract with signature validation
- [x] KMS → App Key → Derived Key verification
- [x] P2P SDK with ultra-simple 3-line interface
- [x] Comprehensive signature format testing
- [x] Working end-to-end integration with DStack simulator

### 🚀 Phase 2: Byzantine Fault Tolerance (Next)
- [ ] Leader election with NFT voting weights
- [ ] Automatic failover mechanisms
- [ ] Distributed consensus for cluster state
- [ ] Health monitoring and challenge voting

### 🌐 Phase 3: Production Deployment  
- [ ] Base mainnet smart contract deployment
- [ ] Real TEE node integration
- [ ] Production KMS integration
- [ ] Multi-cluster coordination

## 🎓 Technical Achievements

This project demonstrates key cryptographic and distributed systems concepts:

1. **Complete Signature Verification**: Multi-level cryptographic validation chain
2. **Smart Contract Integration**: On-chain verification of TEE attestations  
3. **P2P Network Formation**: Automatic peer discovery and registration
4. **Local Development Tools**: Simulator integration for rapid iteration
5. **Ultra-Simple SDK**: 3-line interface hiding complex cryptography

## 🔮 Future Extensions

- **Byzantine Fault Tolerance**: Leader election and consensus algorithms
- **Multi-cluster Support**: Different NFT collections for different clusters
- **Cross-chain Integration**: Multi-blockchain cluster coordination
- **TEE Integration**: Real hardware attestation validation
- **Production Scaling**: Base mainnet deployment with real nodes

## ⚠️ Important Notes for Continuation

### Contract Deployment
- **Current deployed address**: `0x2B0d36FACD61B71CC05ab8F3D2355ec3631C0dd5`
- **KMS Root address**: `0x5e5132F15a9aa4AA91A6bCaE35Adf34e27A13516`
- **Test account**: `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` (owns NFT token #1)

### Critical Signature Verification Fixes Applied
1. **V adjustment**: Added `if (v < 27) v += 27;` in `_recoverAddress`
2. **Raw keccak256**: Using `keccak256(bytes(message))` not Ethereum signed message
3. **20-byte app ID**: KMS verification uses `bytes20(appId)` not full 32 bytes
4. **Complete parameters**: `registerPeer` requires 9 parameters including `appKeyAddress`

### Development Environment  
- **Anvil**: Local blockchain at `http://localhost:8545`
- **DStack Simulator**: Running at `./simulator/dstack.sock`  
- **Test Scripts**: Use `scripts/test_contract_signature_verification.py` for validation

---

## 🙏 Acknowledgments

- **DStack**: For the underlying TEE infrastructure and signature system
- **OpenZeppelin**: For secure smart contract libraries  
- **Foundry**: For excellent smart contract development tools
- **Phala Network**: For TEE infrastructure and KMS concepts

---

**Ready to build NFT-gated P2P clusters?** 🚀

Start with `python3 dstack_cluster.py` and experience complete signature verification in action!
