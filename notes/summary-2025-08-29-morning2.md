# DStack Signature Verification Debug Summary

**Date:** 2025-08-29 morning

## Problem
Contract signature verification was failing - DStack signature proofs generated correctly but contract couldn't verify them.

## Root Cause Discovery
**Key insight**: DStack returns the derived private key but **signs with the app key** instead.

### What DStack Actually Does
1. **App key signs**: `purpose + ":" + derived_public_key_hex` 
2. **Message format**: Uses Ethereum standard prefix (`\x19Ethereum Signed Message:\n`)
3. **Critical**: `app_signing_key = SigningKey::from_slice(k256_app_key)` - NOT the derived key!

### Contract Expected (Wrong)
- App signature over: `instanceId + ":" + derivedPublicKey_bytes`
- Using derived key to sign

## Pitfalls Avoided
1. **Raw vs Prefixed Keccak**: DStack uses standard Ethereum message format, not raw Keccak256
2. **Hex vs Bytes**: DStack signs hex string of pubkey, contract expected raw bytes
3. **Which Key Signs**: App key signs (not derived key), but derived key is returned
4. **Message Format**: Purpose (not instanceId) in the signed message

## Key Implementation Files
- **DStack guest-agent**: `refs/dstack/guest-agent/src/rpc_service.rs:get_key()` (lines ~380-400)
- **KMS crypto**: `refs/dstack/kms/src/crypto.rs:sign_message()` 
- **Contract**: `contracts/src/DstackMembershipNFT.sol:_verifySignatureChain()` (line 95)

## Useful Debug Scripts
- **`scripts/debug_signature_verification.py`**: Comprehensive signature format testing
- **`scripts/test_signature_proof_contract.py`**: End-to-end contract integration test
- **Manual verification**: Sign expected message with expected key and compare signatures

## Next Steps
Fix contract `_verifySignatureChain()` to match DStack's actual behavior:
- Change message format to `purpose + ":" + hex(derivedPublicKey)`
- Use app key address for signature verification (need to derive it)