// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Script, console} from "forge-std/Script.sol";
import {DstackMembershipNFT} from "../src/DstackMembershipNFT.sol";

contract DeployDstackMembershipNFT is Script {
    function run() public returns (DstackMembershipNFT) {
        // Get deployer account (first account in anvil)
        uint256 deployerPrivateKey = vm.envOr("PRIVATE_KEY", uint256(0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80));
        address deployer = vm.addr(deployerPrivateKey);
        
        // Mock KMS root address for testing (can be changed later)
        address kmsRoot = vm.envOr("KMS_ROOT_ADDRESS", address(0x1234567890123456789012345678901234567890));
        
        console.log("Deploying DstackMembershipNFT...");
        console.log("Deployer:", deployer);
        console.log("KMS Root:", kmsRoot);
        
        vm.startBroadcast(deployerPrivateKey);
        
        DstackMembershipNFT nft = new DstackMembershipNFT(kmsRoot);
        
        console.log("Contract deployed at:", address(nft));
        
        // Mint some test NFTs to the first 3 anvil accounts
        address account1 = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;
        address account2 = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;
        address account3 = 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC;
        
        uint256 tokenId1 = nft.mintNodeAccess(account1, "Node 1");
        uint256 tokenId2 = nft.mintNodeAccess(account2, "Node 2");
        uint256 tokenId3 = nft.mintNodeAccess(account3, "Node 3");
        
        console.log("Minted NFT #1 to:", account1);
        console.log("Minted NFT #2 to:", account2);
        console.log("Minted NFT #3 to:", account3);
        
        vm.stopBroadcast();
        
        console.log("Deployment completed!");
        console.log("Contract address:", address(nft));
        console.log("Total supply:", nft.totalSupply());
        
        return nft;
    }
}