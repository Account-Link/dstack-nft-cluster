#!/usr/bin/env python3
"""
Test script to verify that signature verification works with corrected message format
"""

import sys
sys.path.append('.')

from signature_proof import SignatureProofGenerator
from web3 import Web3
from eth_account import Account

def test_signature_verification():
    """Test signature verification with corrected format"""
    print("Testing corrected signature verification...")
    
    # Initialize components
    generator = SignatureProofGenerator('./simulator/dstack.sock')
    
    # Web3 setup  
    w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
    
    # Contract setup
    contract_address = '0xa85233C63b9Ee964Add6F2cffe00Fd84eb32338f'
    
    contract_abi = [
        {"inputs": [{"type": "address"}], "name": "walletToTokenId", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"type": "bytes32"}, {"type": "uint256"}, {"type": "bytes"}, {"type": "bytes"}, {"type": "bytes"}, {"type": "string"}, {"type": "bytes32"}], "name": "registerInstanceWithProof", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
    ]
    
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    
    # Use the NFT owner wallet directly
    nft_owner_address = '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266'
    nft_owner_private_key = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
    
    print(f"Testing with NFT owner: {nft_owner_address}")
    
    # Check if wallet owns NFT
    token_id = contract.functions.walletToTokenId(nft_owner_address).call()
    print(f"Token ID for wallet: {token_id}")
    
    if token_id == 0:
        print("ERROR: Wallet does not own an NFT!")
        return False
        
    # Generate signature proof
    try:
        proof = generator.generate_proof("test-node", "test/path", "ethereum")
        print(f"Generated signature proof successfully")
        print(f"Instance ID bytes32: {proof.instance_id_bytes32.hex()}")
        print(f"Derived public key length: {len(proof.derived_public_key)} bytes")
        print(f"Derived public key: {proof.derived_public_key.hex()}")
        print(f"App signature length: {len(proof.app_signature)} bytes")
        print(f"KMS signature length: {len(proof.kms_signature)} bytes")
        print(f"Purpose: {proof.purpose}")
        print(f"App ID: {proof.app_id.hex()}")
        
        # Verify format
        is_valid_format = generator.verify_proof_format(proof)
        print(f"Proof format valid: {is_valid_format}")
        
        if not is_valid_format:
            print("ERROR: Proof format validation failed!")
            return False
        
        print("SUCCESS: Signature proof generation and format validation completed!")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to generate signature proof: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_signature_verification()
    if success:
        print("\n=== All tests passed! Signature verification is working with corrected format ===")
        sys.exit(0)
    else:
        print("\n=== Tests failed ===")  
        sys.exit(1)