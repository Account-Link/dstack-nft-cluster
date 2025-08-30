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
        bytes32 appId = keccak256("test-app-id");
        bytes memory appPubKey = abi.encodePacked(bytes1(0x02), bytes32(uint256(uint160(signer)))); // Mock SEC1 compressed pubkey
        nft.registerPeer(INSTANCE_1, derivedPubKey, appPubKey, appSignature, kmsSignature, "http://localhost:8080", "ethereum", appId);
        
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
        
        bytes32 appId = keccak256("test-app-id");
        bytes memory appPubKey = abi.encodePacked(bytes1(0x02), bytes32(uint256(uint160(signer)))); // Mock SEC1 compressed pubkey
        nft.registerPeer(INSTANCE_1, derivedPubKey, appPubKey, appSignature, kmsSignature, "http://10.0.1.1:8080", "ethereum", appId);
        
        string[] memory endpoints = nft.getPeerEndpoints();
        assertEq(endpoints.length, 1);
        assertEq(endpoints[0], "http://10.0.1.1:8080");
    }
    
    // Helper functions
    function _createPeerSignature(uint256 privateKey, string memory instanceId, bytes memory derivedPubKey) internal pure returns (bytes memory) {
        // DStack message format: purpose + ":" + hex(derivedPublicKey) without 0x prefix
        string memory derivedHex = _bytesToHexWithoutPrefix(derivedPubKey);
        string memory message = string(abi.encodePacked("ethereum:", derivedHex));
        
        // Use Ethereum signed message format
        bytes32 messageHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n", _toString(bytes(message).length), message));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(privateKey, messageHash);
        return abi.encodePacked(r, s, v);
    }
    
    function _createKmsSignature(string memory instanceId, address appKeyAddr) internal pure returns (bytes memory) {
        // KMS message format: "dstack-kms-issued:" + appId_bytes + appPublicKey_sec1
        bytes32 appId = keccak256("test-app-id");
        bytes memory appIdBytes = abi.encodePacked(appId);
        bytes memory appPubKey = abi.encodePacked(bytes1(0x02), bytes32(uint256(uint160(appKeyAddr)))); // Mock SEC1 compressed pubkey
        
        bytes32 kmsMessage = keccak256(abi.encodePacked("dstack-kms-issued:", appIdBytes, appPubKey));
        // Use the known KMS private key
        uint256 kmsPrivateKey = 0x1234567890123456789012345678901234567890123456789012345678901235;
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(kmsPrivateKey, kmsMessage);
        return abi.encodePacked(r, s, v);
    }
    
    function _bytesToHexWithoutPrefix(bytes memory data) internal pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(data.length * 2);
        for (uint256 i = 0; i < data.length; i++) {
            str[i * 2] = alphabet[uint256(uint8(data[i] >> 4))];
            str[i * 2 + 1] = alphabet[uint256(uint8(data[i] & 0x0f))];
        }
        return string(str);
    }
    
    function _toString(uint256 value) internal pure returns (string memory) {
        if (value == 0) {
            return "0";
        }
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
}
