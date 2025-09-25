#!/usr/bin/env python3
"""
Two-Node DStack P2P Demo

This demo script shows how two different DStack nodes can register
to the same contract and discover each other through the P2P SDK.
"""

import asyncio
import logging
import os
import time
from typing import List
from dstack_cluster import DStackP2PSDK

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TwoNodeDemo:
    def __init__(self):
        # Common configuration
        self.contract_address = os.environ.get("CONTRACT_ADDRESS", "0x9d22D844690ff89ea5e8a6bb4Ca3F7DAc83a40c3")
        self.rpc_url = os.environ.get("RPC_URL", "https://base.llamarpc.com")
        
        # Node 1 configuration
        self.node1_connection_url = os.environ.get("NODE1_CONNECTION_URL", "http://localhost:8081")
        self.node1_socket = "./simulator/dstack1.sock"
        
        # Node 2 configuration (using separate simulator)
        self.node2_connection_url = os.environ.get("NODE2_CONNECTION_URL", "http://localhost:8082")
        self.node2_socket = "./simulator2/dstack2.sock"
        
        # Initialize SDK instances
        self.node1_sdk = None
        self.node2_sdk = None
    
    async def initialize_nodes(self):
        """Initialize both SDK instances"""
        logger.info("Initializing Node SDKs...")
        
        # Wait for both sockets to be available
        await self._wait_for_socket(self.node1_socket, "Node1")
        await self._wait_for_socket(self.node2_socket, "Node2")
        
        # Initialize SDKs
        self.node1_sdk = DStackP2PSDK(
            contract_address=self.contract_address,
            connection_url=self.node1_connection_url,
            rpc_url=self.rpc_url,
            dstack_socket=self.node1_socket
        )
        
        self.node2_sdk = DStackP2PSDK(
            contract_address=self.contract_address,
            connection_url=self.node2_connection_url,
            rpc_url=self.rpc_url,
            dstack_socket=self.node2_socket
        )
        
        logger.info("Both SDKs initialized successfully!")
    
    async def _wait_for_socket(self, socket_path: str, node_name: str, max_retries: int = 30):
        """Wait for a DStack socket to become available"""
        logger.info(f"Waiting for {node_name} socket at {socket_path}")
        
        for attempt in range(max_retries):
            if os.path.exists(socket_path):
                try:
                    # Test that we can actually connect
                    from dstack_sdk import DstackClient
                    test_client = DstackClient(socket_path)
                    test_client.info()
                    logger.info(f"{node_name} socket ready after {attempt + 1} attempts")
                    return
                except Exception as e:
                    logger.debug(f"{node_name} socket exists but not ready: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"{node_name} socket not ready (attempt {attempt + 1}/{max_retries}), waiting...")
                await asyncio.sleep(2)
            else:
                logger.error(f"{node_name} socket never became ready at {socket_path}")
                raise RuntimeError(f"Could not connect to {node_name} socket")
    
    async def register_both_nodes(self):
        """Register both nodes with the contract"""
        logger.info("=== REGISTERING BOTH NODES ===")
        
        # Register Node 1
        logger.info("Registering Node 1...")
        node1_success = await self.node1_sdk.register()
        if node1_success:
            logger.info("✅ Node 1 registered successfully!")
        else:
            logger.error("❌ Node 1 registration failed!")
            return False
        
        # Small delay between registrations
        await asyncio.sleep(2)
        
        # Register Node 2
        logger.info("Registering Node 2...")
        node2_success = await self.node2_sdk.register()
        if node2_success:
            logger.info("✅ Node 2 registered successfully!")
        else:
            logger.error("❌ Node 2 registration failed!")
            return False
        
        return True
    
    async def demonstrate_peer_discovery(self):
        """Show that both nodes can discover each other"""
        logger.info("=== DEMONSTRATING PEER DISCOVERY ===")
        
        # Wait a moment for contract state to update
        await asyncio.sleep(3)
        
        # Get peers from Node 1's perspective
        logger.info("Getting peers from Node 1...")
        node1_peers = await self.node1_sdk.get_peers()
        logger.info(f"Node 1 sees peers: {node1_peers}")
        
        # Get peers from Node 2's perspective  
        logger.info("Getting peers from Node 2...")
        node2_peers = await self.node2_sdk.get_peers()
        logger.info(f"Node 2 sees peers: {node2_peers}")
        
        # Analyze results
        if len(node1_peers) >= 2 and len(node2_peers) >= 2:
            logger.info("✅ SUCCESS: Both nodes can see each other in the peer list!")
            logger.info(f"Total peers discovered: {len(node1_peers)}")
            
            # Check if both connection URLs are present
            expected_urls = {self.node1_connection_url, self.node2_connection_url}
            found_urls = set(node1_peers)
            
            if expected_urls.issubset(found_urls):
                logger.info("✅ Both node connection URLs found in peer list!")
            else:
                logger.warning(f"⚠️  Expected URLs {expected_urls} but found {found_urls}")
            
            return True
        else:
            logger.error(f"❌ FAILED: Expected at least 2 peers, but Node 1 sees {len(node1_peers)} and Node 2 sees {len(node2_peers)}")
            return False
    
    async def run_demo(self):
        """Run the complete two-node demo"""
        logger.info("🚀 Starting Two-Node DStack P2P Demo")
        logger.info(f"Contract Address: {self.contract_address}")
        logger.info(f"Node 1 URL: {self.node1_connection_url}")
        logger.info(f"Node 2 URL: {self.node2_connection_url}")
        logger.info(f"RPC URL: {self.rpc_url}")
        
        try:
            # Step 1: Initialize both nodes
            await self.initialize_nodes()
            
            # Step 2: Register both nodes
            registration_success = await self.register_both_nodes()
            if not registration_success:
                logger.error("❌ Demo failed during registration phase")
                return False
            
            # Step 3: Demonstrate peer discovery
            discovery_success = await self.demonstrate_peer_discovery()
            
            if discovery_success:
                logger.info("🎉 TWO-NODE DEMO COMPLETED SUCCESSFULLY!")
                logger.info("Both nodes are registered and can discover each other through the P2P SDK")
                return True
            else:
                logger.error("❌ Demo failed during peer discovery phase")
                return False
                
        except Exception as e:
            logger.error(f"❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main entry point"""
    # Check required environment variables
    required_vars = ["PRIVATE_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set PRIVATE_KEY environment variable")
        return
    
    # Run the demo
    demo = TwoNodeDemo()
    success = await demo.run_demo()
    
    if success:
        logger.info("Demo completed successfully!")
    else:
        logger.error("Demo failed!")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
