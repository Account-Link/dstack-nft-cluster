// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Script, console} from "forge-std/Script.sol";
import {DstackMembershipNFT} from "../src/DstackMembershipNFT.sol";

contract DeployDstackMembershipNFTMainnet is Script {
    function run() public returns (DstackMembershipNFT) {
        // Get deployer private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        
        // Get KMS root address from environment (required for mainnet)
        address kmsRoot = vm.envAddress("KMS_ROOT_ADDRESS");
        
        console.log("=== DStack Membership NFT Mainnet Deployment ===");
        console.log("Network: Base Mainnet");
        console.log("Deployer:", deployer);
        console.log("KMS Root Address:", kmsRoot);
        
        // Verify deployer has sufficient balance
        uint256 balance = deployer.balance;
        console.log("Deployer balance:", balance / 1e18, "ETH");
        require(balance > 0.01 ether, "Insufficient ETH for deployment");
        
        vm.startBroadcast(deployerPrivateKey);
        
        // Deploy the contract
        DstackMembershipNFT nft = new DstackMembershipNFT(kmsRoot);
        
        console.log("Contract deployed at:", address(nft));
        
        // Set initial configuration for production
        // Max nodes: 1000, public minting: false, mint price: 0
        nft.setClusterConfig(1000, false, 0);
        console.log("Cluster configuration set: maxNodes=1000, publicMinting=false, mintPrice=0");
        
        // Disable dev mode for production
        nft.setDevMode(false);
        console.log("Dev mode disabled for production");
        
        // Add allowed base domains for production URLs
        // You can modify these based on your actual domains
        string[] memory allowedDomains = new string[](3);
        allowedDomains[0] = "dstack.network";
        allowedDomains[1] = "phala.network"; 
        allowedDomains[2] = "your-domain.com";
        
        for (uint i = 0; i < allowedDomains.length; i++) {
            nft.addBaseDomain(allowedDomains[i]);
            console.log("Added allowed base domain:", allowedDomains[i]);
        }
        
        vm.stopBroadcast();
        
        console.log("=== Deployment Summary ===");
        console.log("Contract Address:", address(nft));
        console.log("Owner:", nft.owner());
        console.log("KMS Root:", kmsRoot);
        console.log("Max Nodes:", nft.maxNodes());
        console.log("Public Minting:", nft.publicMinting());
        console.log("Dev Mode:", nft.devMode());
        console.log("Total Supply:", nft.totalSupply());
        
        console.log("=== Next Steps ===");
        console.log("1. Verify the contract on Basescan");
        console.log("2. Update your application with the new contract address");
        console.log("3. Test the deployment with a small transaction");
        
        return nft;
    }
}
