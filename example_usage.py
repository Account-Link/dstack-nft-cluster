#!/usr/bin/env python3
"""
Example usage of the DStack P2P FastAPI Server

This script demonstrates how to interact with the FastAPI server
to get peer information from the DStack P2P cluster.
"""

import asyncio
import requests
import json
import time
from typing import List, Dict


class DStackAPIClient:
    """Simple client for the DStack P2P FastAPI server"""
    
    def __init__(self, base_url: str = "https://7987d1133bc8ddfaf8639dbde4bb4d4d2f9152d0-8080.dstack-pha-prod7.phala.network"):
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> Dict:
        """Check if the API server is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_peers(self) -> Dict:
        """Get list of all peers in the cluster"""
        try:
            response = requests.get(f"{self.base_url}/peers")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_info(self) -> Dict:
        """Get instance information"""
        try:
            response = requests.get(f"{self.base_url}/info")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def mint_nft(self) -> Dict:
        """Mint NFT for this instance"""
        try:
            response = requests.post(f"{self.base_url}/mint-nft")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def get_contract_info(self) -> Dict:
        """Get contract configuration information"""
        try:
            response = requests.get(f"{self.base_url}/contract-info")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def register_instance(self) -> Dict:
        """Register this instance with the cluster (includes NFT minting)"""
        try:
            response = requests.post(f"{self.base_url}/register")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}


def print_json(data: Dict, title: str = ""):
    """Pretty print JSON data"""
    if title:
        print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2))


def main():
    """Main example function"""
    print("DStack P2P FastAPI Server - Example Usage")
    print("=" * 50)
    
    # Initialize client
    client = DStackAPIClient()
    
    # 1. Health Check
    print("\n1. Checking API health...")
    health = client.health_check()
    print_json(health, "Health Status")
    
    if health.get("error"):
        print("\n❌ API server is not accessible. Make sure it's running:")
        print("   docker-compose -f docker-compose-fastapi.yml up -d")
        print("   OR")
        print("   uv run python fastapi_server.py")
        return
    
    # 2. Get Contract Info (NEW - to debug minting issues)
    print("\n2. Getting contract configuration...")
    contract_info = client.get_contract_info()
    print_json(contract_info, "Contract Configuration")
    
    # 3. Get Instance Info
    print("\n3. Getting instance information...")
    info = client.get_info()
    print_json(info, "Instance Info")
    
    # # 3. Get Peers
    # print("\n3. Getting peer list...")
    # peers_data = client.get_peers()
    # print_json(peers_data, "Peers")
    
    # if peers_data.get("error"):
    #     print("\n❌ Failed to get peers. This might be expected if:")
    #     print("   - No PRIVATE_KEY is set (read-only mode)")
    #     print("   - Instance is not registered with the cluster")
    #     print("   - DStack socket is not available")
    # else:
    #     peers = peers_data.get("peers", [])
    #     count = peers_data.get("count", 0)
        
    #     print(f"\n✅ Found {count} peers in the cluster:")
    #     for i, peer in enumerate(peers, 1):
    #         print(f"   {i}. {peer}")
    
    # 4. NFT Minting (if PRIVATE_KEY available)
    # print("\n4. Testing NFT minting...")
    # nft_result = client.mint_nft()
    # print_json(nft_result, "NFT Minting Result")
    
    # if nft_result.get("error"):
    #     if "PRIVATE_KEY" in nft_result.get("error", ""):
    #         print("\n💡 NFT minting requires PRIVATE_KEY environment variable")
    #         print("   Set it in your environment or .env file for full functionality")
    #     else:
    #         print(f"\n❌ NFT minting failed: {nft_result.get('error')}")
    # else:
    #     print("\n✅ NFT minting completed successfully!")
    #     owner_address = nft_result.get("owner_address")
    #     token_id = nft_result.get("token_id")
    #     if owner_address and token_id:
    #         print(f"   Owner Address: {owner_address}")
    #         print(f"   Token ID: {token_id}")
    
    # 5. Registration (if PRIVATE_KEY available)
    print("\n5. Testing full registration...")
    registration = client.register_instance()
    print_json(registration, "Registration Result")
    
    if registration.get("error"):
        if "PRIVATE_KEY" in registration.get("error", ""):
            print("\n💡 Registration requires PRIVATE_KEY environment variable")
            print("   Set it in your environment or .env file for full functionality")
        else:
            print(f"\n❌ Registration failed: {registration.get('error')}")
    else:
        print("\n✅ Successfully registered with the cluster!")
        nft_minted = registration.get("nft_minted", False)
        print(f"   NFT was {'already minted or newly minted' if nft_minted else 'not minted'}")
    
    print("\n" + "=" * 50)
    print("Example completed! 🎉")
    print("\nNext steps:")
    print("- Set PRIVATE_KEY environment variable for registration")
    print("- Deploy to Phala Cloud for production usage")
    print("- Integrate with your applications using the API endpoints")


async def monitoring_example():
    """Example of continuous peer monitoring"""
    print("\nContinuous Peer Monitoring Example")
    print("=" * 40)
    
    client = DStackAPIClient()
    last_peers = []
    
    for i in range(10):  # Monitor for 10 iterations
        try:
            peers_data = client.get_peers()
            
            if peers_data.get("error"):
                print(f"Iteration {i+1}: Error - {peers_data['error']}")
            else:
                current_peers = peers_data.get("peers", [])
                count = len(current_peers)
                
                if current_peers != last_peers:
                    print(f"Iteration {i+1}: Peer list changed! Now {count} peers:")
                    for peer in current_peers:
                        print(f"  - {peer}")
                    last_peers = current_peers
                else:
                    print(f"Iteration {i+1}: No changes ({count} peers)")
            
            await asyncio.sleep(5)  # Wait 5 seconds
            
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"Iteration {i+1}: Unexpected error - {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="DStack P2P API Client Example")
    parser.add_argument("--monitor", action="store_true", 
                       help="Run continuous peer monitoring")
    parser.add_argument("--url", default="http://localhost:8080",
                       help="API server URL (default: http://localhost:8080)")
    
    args = parser.parse_args()
    
    if args.monitor:
        asyncio.run(monitoring_example())
    else:
        main()
