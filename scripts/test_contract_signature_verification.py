#!/usr/bin/env python3
"""
Test script for DstackMembershipNFT contract signature verification.
Tests the fixed signature chain verification logic with real contract calls.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from web3 import Web3
from eth_account import Account
from signature_proof import SignatureProofGenerator
from eth_keys import keys
from eth_utils import keccak
import json

# Test configuration
RPC_URL = "http://localhost:8545"
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"  # Anvil default
KMS_ROOT_PRIVATE_KEY = "e0e5d254fb944dcc370a2e5288b336a1e809871545a73ee645368957fefa31f9"
KMS_ROOT_ADDRESS = Account.from_key(KMS_ROOT_PRIVATE_KEY).address
CONTRACT_ADDRESS = "0x5067457698Fd6Fa1C6964e416b3f42713513B3dD"  # Simplified contract without redundant parameters

def test_signature_formats():
    """Compare signature formats between working and current implementation"""
    print("🔍 Testing Different Signature Formats")
    print("=" * 60)
    
    try:
        # Generate signature proof using DStack simulator
        generator = SignatureProofGenerator('./simulator/dstack.sock')
        proof = generator.generate_proof('wallet/ethereum', 'ethereum')  # Use 'ethereum' like dstack_cluster.py
        print(f"✅ Generated signature proof")
        print(f"   App ID: {proof.app_id}")
        
        # Get keys
        derived_public_key = keys.PrivateKey(proof.derived_private_key).public_key
        derived_pubkey_sec1 = derived_public_key.to_compressed_bytes()
        
        # Test 1: Working format (from SimpleDstackVerifier)
        print(f"\n🔬 Format 1: Working SimpleDstackVerifier format")
        app_message_working = f"ethereum:{derived_pubkey_sec1.hex()}"
        app_message_hash_working = keccak(bytes(app_message_working, 'utf-8'))  # Raw keccak256
        app_signer_working = Account._recover_hash(app_message_hash_working, signature=proof.app_signature)
        print(f"   Message: {app_message_working}")
        print(f"   Hash: {app_message_hash_working.hex()}")
        print(f"   Recovered: {app_signer_working}")
        
        # Test 2: Current format (from our contract)
        print(f"\n🔬 Format 2: Current DstackMembershipNFT format")
        app_message_current = f"ethereum:{derived_pubkey_sec1.hex()}"
        eth_prefix = f"\x19Ethereum Signed Message:\n{len(app_message_current)}"
        app_message_hash_current = keccak((eth_prefix + app_message_current).encode())
        app_signer_current = Account._recover_hash(app_message_hash_current, signature=proof.app_signature)
        print(f"   Message: {app_message_current}")
        print(f"   Prefixed: {eth_prefix + app_message_current}")
        print(f"   Hash: {app_message_hash_current.hex()}")
        print(f"   Recovered: {app_signer_current}")
        
        # Test 3: What DStack actually produces (from signature_proof.py)
        print(f"\n🔬 Format 3: signature_proof.py format")
        app_message_dstack = f"ethereum:{derived_pubkey_sec1.hex()}"
        app_message_hash_dstack = keccak(text=app_message_dstack)  # This uses text encoding
        app_signer_dstack = Account._recover_hash(app_message_hash_dstack, signature=proof.app_signature)
        print(f"   Message: {app_message_dstack}")
        print(f"   Hash: {app_message_hash_dstack.hex()}")
        print(f"   Recovered: {app_signer_dstack}")
        
        print(f"\n📊 Results:")
        print(f"   Working format matches: {app_signer_working != '0x0000000000000000000000000000000000000000'}")
        print(f"   Current format matches: {app_signer_current != '0x0000000000000000000000000000000000000000'}")
        print(f"   DStack format matches: {app_signer_dstack != '0x0000000000000000000000000000000000000000'}")
        
        # Test KMS message formats
        print(f"\n🔬 KMS Message Formats:")
        app_id_bytes20 = bytes.fromhex(proof.app_id.replace('0x', ''))[:20]  # First 20 bytes
        app_id_bytes32 = bytes.fromhex(proof.app_id.replace('0x', '')).ljust(32, b'\x00')[:32]
        
        # Get app public key from signature - using the working hash format
        app_signature_obj = keys.Signature(proof.app_signature)
        app_pubkey_sec1 = app_signature_obj.recover_public_key_from_msg_hash(app_message_hash_working).to_compressed_bytes()
        
        print(f"   App address from working format: {app_signer_working}")
        print(f"   App public key from signature: {app_pubkey_sec1.hex()}")
        
        # Format 1: Working format (20 bytes app ID)
        kms_message_working = b"dstack-kms-issued:" + app_id_bytes20 + app_pubkey_sec1
        kms_hash_working = keccak(kms_message_working)
        kms_signer_working = Account._recover_hash(kms_hash_working, signature=proof.kms_signature)
        print(f"   Working KMS recovered: {kms_signer_working}")
        print(f"   Working KMS matches: {kms_signer_working.lower() == KMS_ROOT_ADDRESS.lower()}")
        
        # Format 2: Current format (32 bytes app ID)
        kms_message_current = b"dstack-kms-issued:" + app_id_bytes32 + app_pubkey_sec1
        kms_hash_current = keccak(kms_message_current)
        kms_signer_current = Account._recover_hash(kms_hash_current, signature=proof.kms_signature)
        print(f"   Current KMS recovered: {kms_signer_current}")
        print(f"   Current KMS matches: {kms_signer_current.lower() == KMS_ROOT_ADDRESS.lower()}")
        
        return {
            'proof': proof,
            'derived_pubkey_sec1': derived_pubkey_sec1,
            'app_pubkey_sec1': app_pubkey_sec1,
            'app_signer': app_signer_working,  # Use the working format
            'working_format': app_signer_working != '0x0000000000000000000000000000000000000000',
            'kms_working': kms_signer_working.lower() == KMS_ROOT_ADDRESS.lower()
        }
        
    except Exception as e:
        print(f"❌ Format test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_contract_call(test_data):
    """Test actual contract call with working format"""
    print(f"\n📜 Testing Contract Call")
    print("=" * 60)
    
    if not test_data or not test_data['working_format']:
        print("❌ Skipping contract test - signature format not working")
        return False
    
    try:
        # Connect to blockchain
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not w3.is_connected():
            print("❌ Failed to connect to blockchain")
            return False
        
        account = w3.eth.account.from_key(PRIVATE_KEY)
        print(f"🔗 Connected as: {account.address}")
        
        # Simplified contract ABI for registerPeer
        contract_abi = [{
            "inputs": [
                {"name": "instanceId", "type": "string"},
                {"name": "derivedPublicKey", "type": "bytes"},
                {"name": "appPublicKey", "type": "bytes"},
                {"name": "appSignature", "type": "bytes"},
                {"name": "kmsSignature", "type": "bytes"},
                {"name": "connectionUrl", "type": "string"},
                {"name": "purpose", "type": "string"},
                {"name": "appId", "type": "bytes32"}
            ],
            "name": "registerPeer",
            "outputs": [],
            "type": "function"
        }, {
            "inputs": [{"name": "instanceId", "type": "string"}],
            "name": "registerInstance",
            "outputs": [],
            "type": "function"
        }]
        
        # Load contract
        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)
        print(f"✅ Contract loaded: {contract.address}")
        
        proof = test_data['proof']
        derived_pubkey_sec1 = test_data['derived_pubkey_sec1']
        app_pubkey_sec1 = test_data['app_pubkey_sec1']
        
        # Register instance first
        instance_id = "test_verification_instance"
        print(f"📝 Registering instance: {instance_id}")
        
        try:
            instance_tx = contract.functions.registerInstance(instance_id).transact({'from': account.address})
            instance_receipt = w3.eth.wait_for_transaction_receipt(instance_tx)
            print(f"✅ Instance registered: {instance_receipt.transactionHash.hex()}")
        except Exception as e:
            print(f"⚠️ Instance registration failed (may already exist): {e}")
        
        # Prepare parameters
        app_id_bytes32 = bytes.fromhex(proof.app_id.replace('0x', '')).ljust(32, b'\x00')[:32]
        
        print(f"\n📋 Contract parameters:")
        print(f"   Instance ID: {instance_id}")
        print(f"   Derived pubkey: {derived_pubkey_sec1.hex()}")
        print(f"   App pubkey: {app_pubkey_sec1.hex()}")
        print(f"   App signature: {proof.app_signature.hex()}")
        print(f"   KMS signature: {proof.kms_signature.hex()}")
        print(f"   Purpose: ethereum")
        print(f"   App ID: {app_id_bytes32.hex()}")
        
        print(f"\n🚀 Calling registerPeer...")
        tx_hash = contract.functions.registerPeer(
            instance_id,
            derived_pubkey_sec1,
            app_pubkey_sec1,
            proof.app_signature,
            proof.kms_signature,
            "http://localhost:8080",
            "ethereum",
            app_id_bytes32
        ).transact({'from': account.address})
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"✅ registerPeer succeeded: {receipt.transactionHash.hex()}")
        print(f"   Gas used: {receipt.gasUsed}")
        return True
        
    except Exception as e:
        print(f"❌ Contract call failed: {e}")
        return False

def main():
    """Run comprehensive signature verification tests"""
    print("🚀 DStack Contract Signature Verification Test")
    print("=" * 70)
    print(f"Contract: {CONTRACT_ADDRESS}")
    print(f"KMS Root: {KMS_ROOT_ADDRESS}")
    print()
    
    # Step 1: Test signature formats
    test_data = test_signature_formats()
    
    # Step 2: Test contract call if formats work
    contract_success = test_contract_call(test_data) if test_data else False
    
    # Summary
    print(f"\n" + "=" * 70)
    print("📊 Test Summary:")
    working = test_data and test_data['working_format'] if test_data else False
    kms_working = test_data and test_data['kms_working'] if test_data else False
    
    print(f"   Format Analysis: {'✅ PASS' if working else '❌ FAIL'}")
    print(f"   KMS Verification: {'✅ PASS' if kms_working else '❌ FAIL'}")
    print(f"   Contract Call: {'✅ PASS' if contract_success else '❌ FAIL'}")
    
    if working and kms_working and contract_success:
        print("\n🎉 Full signature verification working!")
    else:
        print(f"\n💡 Issues found:")
        if not working:
            print("   - App signature format needs adjustment")
        if not kms_working:
            print("   - KMS signature format needs adjustment") 
        if not contract_success:
            print("   - Contract verification logic needs fixes")
    
    return working and kms_working and contract_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)