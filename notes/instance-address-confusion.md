# Instance Address Confusion - Important Note

## The Problem
During development, we mistakenly created a concept of "instance address" by deriving an Ethereum address from the instance ID using:
```python
instance_address = '0x' + hashlib.sha256(info.instance_id.encode()).hexdigest()[:40]
```

This was wrong and caused confusion.

## The Correct Concepts

1. **NFT Owner Address**: The Ethereum address that owns the NFT (e.g., `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`)
   - This is a real Ethereum address with a private key
   - This address can make transactions on the blockchain
   - This address owns the NFT that grants access to the P2P cluster

2. **Instance ID**: A string identifier from the DStack TEE (e.g., `59df8036b824b0aac54f8998b9e1fb2a0cfc5d3a`)
   - This is just a string identifier, not an address
   - It uniquely identifies a TEE instance
   - It cannot make blockchain transactions

3. **Instance Address**: **This concept should NOT exist**
   - We mistakenly derived addresses from instance IDs
   - This caused confusion about which address should own NFTs
   - This is not needed in the architecture

## The Correct Flow

1. NFT Owner Address calls `mintNodeAccess()` to get an NFT
2. NFT Owner Address calls `registerInstance(instanceId)` to activate the instance
3. Instance (running in TEE) calls `registerPeer()` with signature proofs to register its connection URL
4. Other instances can discover peers via `getPeerEndpoints()`

## Lesson Learned
Don't create derived addresses from instance IDs. Keep the concepts separate and clear.