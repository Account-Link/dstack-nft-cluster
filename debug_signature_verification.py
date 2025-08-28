#!/usr/bin/env python3
"""
Debug script for signature verification issues
"""
import sys
sys.path.append('.')

from signature_proof import SignatureProofGenerator
from web3 import Web3
from eth_account import Account

def debug_signature_verification():
    """Debug signature verification step by step"""
    
    # Generate proof using DStack
    generator = SignatureProofGenerator()
    proof = generator.generate_proof('node1', 'test/node', 'ethereum')
    
    print("=== PROOF DATA ===")
    print(f"Instance ID (bytes32): {proof.instance_id_bytes32.hex()}")
    print(f"Derived Public Key: {proof.derived_public_key.hex()}")
    print(f"App Signature: {proof.app_signature.hex()}")
    print(f"KMS Signature: {proof.kms_signature.hex()}")
    print(f"Purpose: {proof.purpose}")
    print(f"App ID: {proof.app_id.hex()}")
    print()
    
    # Python signature verification (matching Solidity logic)
    print("=== PYTHON VERIFICATION ===")
    
    # Step 1: Recover app public key from app signature (matching Solidity)
    purpose_hex = proof.purpose.encode().hex()
    derived_key_hex = "0x" + proof.derived_public_key.hex()
    
    # Match Solidity: keccak256(abi.encodePacked(purpose, ":", _toHex(derivedPublicKey)))
    message_parts = [
        proof.purpose.encode(),  # "ethereum"
        b":",                    # ":"  
        derived_key_hex.encode() # "0x37181dda18e75e1f7b8835f5b42f50ca4be02e9b"
    ]
    derived_key_message = b"".join(message_parts)
    print(f"Step 1: Derived key message: {derived_key_message}")
    
    derived_key_hash = Web3.keccak(derived_key_message)
    print(f"Step 1: Derived key hash: {derived_key_hash.hex()}")
    
    # Recover app public key from app signature
    try:
        app_public_key = Account._recover_hash(derived_key_hash, signature=proof.app_signature)
        print(f"Step 1: Recovered app public key: {app_public_key}")
    except Exception as e:
        print(f"Step 1: ERROR recovering app public key: {e}")
        return False
    
    # Step 2: Verify KMS signature over app key - try different message formats
    app_public_key_bytes = bytes.fromhex(app_public_key[2:])  # Remove 0x prefix
    
    print(f"Step 2: Trying different KMS message formats...")
    
    # Format 1: Original Solidity format
    kms_message_1 = b"dstack-kms-issued:" + proof.app_id + app_public_key_bytes
    kms_hash_1 = Web3.keccak(kms_message_1)
    print(f"  Format 1: {kms_message_1.hex()}")
    print(f"  Hash 1: {kms_hash_1.hex()}")
    try:
        signer_1 = Account._recover_hash(kms_hash_1, signature=proof.kms_signature)
        print(f"  Signer 1: {signer_1}")
    except Exception as e:
        print(f"  Error 1: {e}")
    
    # Format 2: What if the simulator signs over the derived key message directly?
    kms_hash_2 = derived_key_hash  # Reuse the derived key hash
    print(f"  Format 2 (derived key hash): {kms_hash_2.hex()}")
    try:
        signer_2 = Account._recover_hash(kms_hash_2, signature=proof.kms_signature)
        print(f"  Signer 2: {signer_2}")
    except Exception as e:
        print(f"  Error 2: {e}")
    
    # Format 3: What if it's just the app_id + app_public_key without prefix?
    kms_message_3 = proof.app_id + app_public_key_bytes
    kms_hash_3 = Web3.keccak(kms_message_3)
    print(f"  Format 3: {kms_message_3.hex()}")
    print(f"  Hash 3: {kms_hash_3.hex()}")
    try:
        signer_3 = Account._recover_hash(kms_hash_3, signature=proof.kms_signature)
        print(f"  Signer 3: {signer_3}")
    except Exception as e:
        print(f"  Error 3: {e}")
        
    # Format 4: What if it's the app public key alone?
    kms_hash_4 = Web3.keccak(app_public_key_bytes)
    print(f"  Format 4 (pubkey only): {kms_hash_4.hex()}")
    try:
        signer_4 = Account._recover_hash(kms_hash_4, signature=proof.kms_signature)
        print(f"  Signer 4: {signer_4}")
    except Exception as e:
        print(f"  Error 4: {e}")
    
    # Use Format 1 as the main result for now
    kms_signer = signer_1
    
    # Expected KMS root addresses to check
    deployed_kms = "0xa2eB90b26A1274fa10905da7A62ff15542f2EbFf"  # From original deployment
    simulator_kms = "0xf6F3Bb63C4238E5d25c64eBAB48F44a42FC03df4"  # From simulator private key
    print(f"Step 2: Deployed KMS root: {deployed_kms}")
    print(f"Step 2: Simulator KMS root: {simulator_kms}")
    
    # Check if any format matches either KMS address
    formats = [signer_1, signer_2, signer_3, signer_4]
    format_names = ["Format 1", "Format 2", "Format 3", "Format 4"]
    
    for i, signer in enumerate(formats):
        if signer.lower() == deployed_kms.lower():
            print(f"  ✓ {format_names[i]} matches deployed KMS!")
        elif signer.lower() == simulator_kms.lower():
            print(f"  ✓ {format_names[i]} matches simulator KMS!")
        else:
            print(f"  ✗ {format_names[i]} doesn't match either KMS")
    
    kms_root_address = simulator_kms  # Use simulator KMS for now
    print(f"Step 2: Expected KMS root: {kms_root_address}")
    print(f"Step 2: KMS verification: {'PASS' if kms_signer.lower() == kms_root_address.lower() else 'FAIL'}")
    
    verification_result = kms_signer.lower() == kms_root_address.lower()
    print(f"\nOverall verification: {'PASS' if verification_result else 'FAIL'}")
    
    return verification_result

if __name__ == "__main__":
    debug_signature_verification()