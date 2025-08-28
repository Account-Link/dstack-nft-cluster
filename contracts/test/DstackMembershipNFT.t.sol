// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {DstackMembershipNFT} from "../src/DstackMembershipNFT.sol";

contract DstackMembershipNFTTest is Test {
    DstackMembershipNFT public nft;
    
    address public owner;
    address public user1;
    address public kmsRoot;
    
    string constant INSTANCE_1 = "instance1";
    string constant INSTANCE_2 = "instance2";
    string constant INSTANCE_3 = "instance3";
    
    function setUp() public {
        owner = makeAddr("owner");
        user1 = makeAddr("user1");
        
        // Use a known private key for KMS root so we can sign with it
        uint256 kmsPrivateKey = 0x1234567890123456789012345678901234567890123456789012345678901235;
        kmsRoot = vm.addr(kmsPrivateKey);
        
        vm.prank(owner);
        nft = new DstackMembershipNFT(kmsRoot);
    }
    
    function test_InitialState() public {
        assertEq(nft.owner(), owner);
        assertEq(nft.kmsRootAddress(), kmsRoot);
        assertEq(nft.totalSupply(), 0);
    }
    
    function test_MintNodeAccess() public {
        vm.prank(owner);
        uint256 tokenId = nft.mintNodeAccess(user1, "User 1 Node");
        
        assertEq(tokenId, 1);
        assertEq(nft.ownerOf(1), user1);
        assertEq(nft.walletToTokenId(user1), 1);
        assertEq(nft.totalSupply(), 1);
    }
    
    function test_RegisterInstance() public {
        // First mint an NFT
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        // Then register an instance
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1);
        
        assertTrue(nft.activeInstances(INSTANCE_1));
        assertEq(nft.instanceToToken(INSTANCE_1), 1);
        assertEq(nft.tokenToInstance(1), INSTANCE_1);
        assertEq(nft.totalActiveNodes(), 1);
    }
    
    function test_SubmitCounterAttestation() public {
        // First mint an NFT and register instance
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1);
        
        // Use a private key for signing
        uint256 privateKey = 0x1234567890123456789012345678901234567890123456789012345678901234;
        address signer = vm.addr(privateKey);
        
        // Submit counter attestation with both signatures
        uint256 counterValue = 42;
        bytes memory appSignature = _createAttestSignature(privateKey, INSTANCE_1, counterValue);
        bytes memory kmsSignature = _createKmsSignature(INSTANCE_1, signer);
        
        nft.submitCounterAttestation(INSTANCE_1, counterValue, appSignature, kmsSignature);
        
        assertEq(nft.latestCounterValue(INSTANCE_1), counterValue);
        assertTrue(nft.lastAttestationTime(INSTANCE_1) > 0);
    }
    
    function test_VerifySignatureChain() public {
        // Test the view function for signature verification
        uint256 privateKey = 0x1234567890123456789012345678901234567890123456789012345678901234;
        address signer = vm.addr(privateKey);
        
        uint256 counterValue = 42;
        bytes memory appSignature = _createAttestSignature(privateKey, INSTANCE_1, counterValue);
        bytes memory kmsSignature = _createKmsSignature(INSTANCE_1, signer);
        
        bool isValid = nft.verifySignatureChain(INSTANCE_1, counterValue, appSignature, kmsSignature);
        assertTrue(isValid);
    }
    
    // Helper functions
    function _createAttestSignature(uint256 privateKey, string memory instanceId, uint256 value) internal pure returns (bytes memory) {
        bytes32 messageHash = keccak256(abi.encodePacked(instanceId, ":", value));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(privateKey, messageHash);
        return abi.encodePacked(r, s, v);
    }
    
    function _createKmsSignature(string memory instanceId, address appKeyAddr) internal pure returns (bytes memory) {
        bytes32 kmsMessage = keccak256(abi.encodePacked("dstack-kms-issued:", instanceId, appKeyAddr));
        // Use the known KMS private key
        uint256 kmsPrivateKey = 0x1234567890123456789012345678901234567890123456789012345678901235;
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(kmsPrivateKey, kmsMessage);
        return abi.encodePacked(r, s, v);
    }
}
