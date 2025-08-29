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
        // Test that instance is properly registered
    }
    
    function test_RegisterPeer() public {
        // First mint an NFT and register instance
        vm.prank(owner);
        nft.mintNodeAccess(user1, INSTANCE_1);
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1);
        
        // Use a private key for signing
        uint256 privateKey = 0x1234567890123456789012345678901234567890123456789012345678901234;
        address signer = vm.addr(privateKey);
        bytes memory derivedPubKey = abi.encodePacked(signer);
        
        bytes memory appSignature = _createPeerSignature(privateKey, INSTANCE_1, derivedPubKey);
        bytes memory kmsSignature = _createKmsSignature(INSTANCE_1, signer);
        
        // Test dev mode - allows any URL
        nft.registerPeer(INSTANCE_1, derivedPubKey, appSignature, kmsSignature, "http://localhost:8080");
        
        assertEq(nft.instanceToConnectionUrl(INSTANCE_1), "http://localhost:8080");
    }
    
    function test_GetPeerEndpoints() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, INSTANCE_1);
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1);
        
        uint256 privateKey = 0x1234567890123456789012345678901234567890123456789012345678901234;
        address signer = vm.addr(privateKey);
        bytes memory derivedPubKey = abi.encodePacked(signer);
        
        bytes memory appSignature = _createPeerSignature(privateKey, INSTANCE_1, derivedPubKey);
        bytes memory kmsSignature = _createKmsSignature(INSTANCE_1, signer);
        
        nft.registerPeer(INSTANCE_1, derivedPubKey, appSignature, kmsSignature, "http://10.0.1.1:8080");
        
        string[] memory endpoints = nft.getPeerEndpoints();
        assertEq(endpoints.length, 1);
        assertEq(endpoints[0], "http://10.0.1.1:8080");
    }
    
    // Helper functions
    function _createPeerSignature(uint256 privateKey, string memory instanceId, bytes memory derivedPubKey) internal pure returns (bytes memory) {
        bytes32 messageHash = keccak256(abi.encodePacked(instanceId, ":", derivedPubKey));
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
