// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test, console} from "forge-std/Test.sol";
import {DstackMembershipNFT} from "../src/DstackMembershipNFT.sol";
import {IDstackApp} from "../src/DstackMembershipNFT.sol";

contract DstackMembershipNFTTest is Test {
    DstackMembershipNFT public nft;
    
    address public owner;
    address public user1;
    address public user2;
    address public user3;
    address public kmsRoot;
    
    bytes32 constant INSTANCE_1 = keccak256("instance1");
    bytes32 constant INSTANCE_2 = keccak256("instance2");
    bytes32 constant INSTANCE_3 = keccak256("instance3");
    
    event LeaderElected(address indexed leader, uint256 indexed tokenId, bytes32 instanceId);
    event VoteCast(address indexed voter, address indexed target, bool isNoConfidence);
    event LeaderChallenged(address indexed newLeader, address indexed oldLeader, uint256 voteCount);
    event InstanceRegistered(bytes32 indexed instanceId, uint256 indexed tokenId);

    function setUp() public {
        owner = makeAddr("owner");
        user1 = makeAddr("user1");
        user2 = makeAddr("user2");
        user3 = makeAddr("user3");
        kmsRoot = makeAddr("kmsRoot");
        
        vm.prank(owner);
        nft = new DstackMembershipNFT(kmsRoot);
    }
    
    function test_InitialState() public {
        assertEq(nft.owner(), owner);
        assertEq(nft.kmsRootAddress(), kmsRoot);
        assertEq(nft.totalSupply(), 0);
        assertEq(nft.currentLeader(), address(0));
        assertEq(nft.totalActiveNodes(), 0);
        assertEq(nft.requiredVotes(), 0);
    }
    
    function test_MintNodeAccess() public {
        vm.prank(owner);
        uint256 tokenId = nft.mintNodeAccess(user1, "User 1 Node");
        
        assertEq(tokenId, 1);
        assertEq(nft.ownerOf(1), user1);
        assertEq(nft.walletToTokenId(user1), 1);
        assertEq(nft.totalSupply(), 1);
    }
    
    function test_MintNodeAccess_DuplicateWallet() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.expectRevert("Wallet already has NFT");
        vm.prank(owner);
        nft.mintNodeAccess(user1, "Another node");
    }
    
    function test_MintNodeAccess_OnlyOwner() public {
        vm.expectRevert();
        vm.prank(user1);
        nft.mintNodeAccess(user2, "Unauthorized mint");
    }
    
    function test_RegisterInstance() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.expectEmit(true, true, false, false);
        emit InstanceRegistered(INSTANCE_1, 1);
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        
        assertEq(nft.tokenToInstance(1), INSTANCE_1);
        assertEq(nft.instanceToToken(INSTANCE_1), 1);
        assertTrue(nft.activeInstances(INSTANCE_1));
        assertEq(nft.totalActiveNodes(), 1);
        assertEq(nft.requiredVotes(), 1);
    }
    
    function test_RegisterInstance_MustOwnNFT() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.expectRevert("Must own NFT");
        vm.prank(user2);
        nft.registerInstance(INSTANCE_1, 1);
    }
    
    function test_RegisterInstance_DuplicateInstance() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        
        vm.prank(owner);
        nft.mintNodeAccess(user2, "User 2 Node");
        
        vm.expectRevert("Instance already registered");
        vm.prank(user2);
        nft.registerInstance(INSTANCE_1, 2);
    }
    
    function test_RegisterInstance_TokenAlreadyHasInstance() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        
        vm.expectRevert("Token already has instance");
        vm.prank(user1);
        nft.registerInstance(INSTANCE_2, 1);
    }
    
    function test_ElectLeader() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        
        vm.expectEmit(true, true, true, false);
        emit LeaderElected(user1, 1, INSTANCE_1);
        
        vm.prank(user1);
        nft.electLeader();
        
        assertEq(nft.currentLeader(), user1);
        assertEq(nft.currentLeaderTokenId(), 1);
    }
    
    function test_ElectLeader_MustOwnNFT() public {
        vm.expectRevert("Must own NFT");
        vm.prank(user1);
        nft.electLeader();
    }
    
    function test_ElectLeader_InstanceMustBeActive() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.expectRevert("Instance not active");
        vm.prank(user1);
        nft.electLeader();
    }
    
    function test_ElectLeader_OnlyOneLeader() public {
        // Setup two nodes
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user2, "User 2 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        vm.prank(user2);
        nft.registerInstance(INSTANCE_2, 2);
        
        vm.prank(user1);
        nft.electLeader();
        
        assertEq(nft.currentLeader(), user1);
        
        // Second election should not change leader
        vm.prank(user2);
        nft.electLeader();
        
        assertEq(nft.currentLeader(), user1);
    }
    
    function test_CastVote() public {
        // Setup nodes
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user2, "User 2 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        vm.prank(user2);
        nft.registerInstance(INSTANCE_2, 2);
        
        vm.expectEmit(true, true, true, false);
        emit VoteCast(user1, user2, true);
        
        vm.prank(user1);
        nft.castVote(user2, true);
        
        assertEq(nft.noConfidenceCount(user2), 1);
        
        (address voter, address target, uint256 tokenId, bool isNoConfidence, uint256 timestamp) = nft.currentVotes(user1);
        assertEq(voter, user1);
        assertEq(target, user2);
        assertEq(tokenId, 1);
        assertTrue(isNoConfidence);
        assertTrue(timestamp > 0);
    }
    
    function test_CastVote_MustOwnNFT() public {
        vm.expectRevert("Must own NFT");
        vm.prank(user1);
        nft.castVote(user2, true);
    }
    
    function test_CastVote_InstanceMustBeActive() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.expectRevert("Instance not active");
        vm.prank(user1);
        nft.castVote(user2, true);
    }
    
    function test_CastVote_ChangeVote() public {
        // Setup nodes
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user2, "User 2 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user3, "User 3 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        vm.prank(user2);
        nft.registerInstance(INSTANCE_2, 2);
        vm.prank(user3);
        nft.registerInstance(INSTANCE_3, 3);
        
        // Vote no confidence in user2
        vm.prank(user1);
        nft.castVote(user2, true);
        assertEq(nft.noConfidenceCount(user2), 1);
        
        // Change vote to user3
        vm.prank(user1);
        nft.castVote(user3, true);
        
        assertEq(nft.noConfidenceCount(user2), 0);
        assertEq(nft.noConfidenceCount(user3), 1);
    }
    
    function test_LeaderChallenge() public {
        // Setup 3 nodes (2f+1 = 3, so f+1 = 2 votes needed)
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user2, "User 2 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user3, "User 3 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        vm.prank(user2);
        nft.registerInstance(INSTANCE_2, 2);
        vm.prank(user3);
        nft.registerInstance(INSTANCE_3, 3);
        
        // Elect user1 as leader
        vm.prank(user1);
        nft.electLeader();
        assertEq(nft.currentLeader(), user1);
        assertEq(nft.requiredVotes(), 2); // (3/2)+1 = 2
        
        // First no-confidence vote (not enough)
        vm.prank(user2);
        nft.castVote(user1, true);
        assertEq(nft.currentLeader(), user1);
        
        // Second no-confidence vote (should trigger leader change)
        vm.expectEmit(true, true, false, false);
        emit LeaderChallenged(user2, user1, 2);
        
        vm.prank(user3);
        nft.castVote(user1, true);
        
        // Leader should change to user2 (lowest tokenId among non-challenged)
        assertEq(nft.currentLeader(), user2);
        assertEq(nft.currentLeaderTokenId(), 2);
    }
    
    function test_DeactivateInstance() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        
        vm.prank(user1);
        nft.electLeader();
        
        assertTrue(nft.activeInstances(INSTANCE_1));
        assertEq(nft.currentLeader(), user1);
        
        vm.prank(user1);
        nft.deactivateInstance(INSTANCE_1);
        
        assertFalse(nft.activeInstances(INSTANCE_1));
        assertEq(nft.currentLeader(), address(0)); // Leader should be cleared
        assertEq(nft.totalActiveNodes(), 0);
    }
    
    function test_DeactivateInstance_MustOwnNFT() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        
        vm.expectRevert("Must own NFT");
        vm.prank(user2);
        nft.deactivateInstance(INSTANCE_1);
    }
    
    function test_IsAppAllowed() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        
        IDstackApp.AppBootInfo memory bootInfo = IDstackApp.AppBootInfo({
            appId: address(0x123),
            instanceId: INSTANCE_1,
            composeHash: keccak256("compose"),
            manifestHash: keccak256("manifest"),
            configHash: keccak256("config"),
            secretHash: keccak256("secret"),
            runner: "docker",
            allowedEnvVars: new string[](0)
        });
        
        (bool allowed, string memory reason) = nft.isAppAllowed(bootInfo);
        assertTrue(allowed);
        assertEq(reason, "");
    }
    
    function test_IsAppAllowed_InstanceNotRegistered() public {
        IDstackApp.AppBootInfo memory bootInfo = IDstackApp.AppBootInfo({
            appId: address(0x123),
            instanceId: INSTANCE_1,
            composeHash: keccak256("compose"),
            manifestHash: keccak256("manifest"),
            configHash: keccak256("config"),
            secretHash: keccak256("secret"),
            runner: "docker",
            allowedEnvVars: new string[](0)
        });
        
        (bool allowed, string memory reason) = nft.isAppAllowed(bootInfo);
        assertFalse(allowed);
        assertEq(reason, "Instance not registered with NFT");
    }
    
    function test_IsAppAllowed_InstanceInactive() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        
        vm.prank(user1);
        nft.deactivateInstance(INSTANCE_1);
        
        IDstackApp.AppBootInfo memory bootInfo = IDstackApp.AppBootInfo({
            appId: address(0x123),
            instanceId: INSTANCE_1,
            composeHash: keccak256("compose"),
            manifestHash: keccak256("manifest"),
            configHash: keccak256("config"),
            secretHash: keccak256("secret"),
            runner: "docker",
            allowedEnvVars: new string[](0)
        });
        
        (bool allowed, string memory reason) = nft.isAppAllowed(bootInfo);
        assertFalse(allowed);
        assertEq(reason, "Instance marked inactive");
    }
    
    function test_GetActiveInstances() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user2, "User 2 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user3, "User 3 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        vm.prank(user2);
        nft.registerInstance(INSTANCE_2, 2);
        vm.prank(user3);
        nft.registerInstance(INSTANCE_3, 3);
        
        bytes32[] memory activeInstances = nft.getActiveInstances();
        assertEq(activeInstances.length, 3);
        assertEq(activeInstances[0], INSTANCE_1);
        assertEq(activeInstances[1], INSTANCE_2);
        assertEq(activeInstances[2], INSTANCE_3);
        
        // Deactivate one instance
        vm.prank(user2);
        nft.deactivateInstance(INSTANCE_2);
        
        activeInstances = nft.getActiveInstances();
        assertEq(activeInstances.length, 2);
        assertEq(activeInstances[0], INSTANCE_1);
        assertEq(activeInstances[1], INSTANCE_3);
    }
    
    function test_GetInstanceInfo() public {
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        
        (uint256 tokenId, bool active, address ownerAddr) = nft.getInstanceInfo(INSTANCE_1);
        assertEq(tokenId, 1);
        assertTrue(active);
        assertEq(ownerAddr, user1);
    }
    
    function test_SetKmsRootAddress() public {
        address newKmsRoot = makeAddr("newKmsRoot");
        
        vm.prank(owner);
        nft.setKmsRootAddress(newKmsRoot);
        
        assertEq(nft.kmsRootAddress(), newKmsRoot);
    }
    
    function test_SetKmsRootAddress_OnlyOwner() public {
        address newKmsRoot = makeAddr("newKmsRoot");
        
        vm.expectRevert();
        vm.prank(user1);
        nft.setKmsRootAddress(newKmsRoot);
    }
    
    function test_UpdateClusterSize() public {
        assertEq(nft.totalActiveNodes(), 0);
        assertEq(nft.requiredVotes(), 0);
        
        // Add 3 nodes
        vm.prank(owner);
        nft.mintNodeAccess(user1, "User 1 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user2, "User 2 Node");
        vm.prank(owner);
        nft.mintNodeAccess(user3, "User 3 Node");
        
        vm.prank(user1);
        nft.registerInstance(INSTANCE_1, 1);
        assertEq(nft.totalActiveNodes(), 1);
        assertEq(nft.requiredVotes(), 1);
        
        vm.prank(user2);
        nft.registerInstance(INSTANCE_2, 2);
        assertEq(nft.totalActiveNodes(), 2);
        assertEq(nft.requiredVotes(), 2);
        
        vm.prank(user3);
        nft.registerInstance(INSTANCE_3, 3);
        assertEq(nft.totalActiveNodes(), 3);
        assertEq(nft.requiredVotes(), 2);
        
        // Deactivate one
        vm.prank(user1);
        nft.deactivateInstance(INSTANCE_1);
        assertEq(nft.totalActiveNodes(), 2);
        assertEq(nft.requiredVotes(), 2);
    }
}