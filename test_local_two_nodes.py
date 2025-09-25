#!/usr/bin/env python3
"""
Local Two-Node DStack P2P Demo (Rye Compatible)

This script runs the two-node demo locally using rye for Python management.
It simulates two nodes using the same DStack simulator but with different connection URLs.
"""

import asyncio
import logging
import os
import subprocess
import time
import signal
import sys
from pathlib import Path
from typing import Optional, List
from dstack_cluster import DStackP2PSDK

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LocalTwoNodeDemo:
    def __init__(self):
        # Common configuration
        self.contract_address = os.environ.get("CONTRACT_ADDRESS", "0x9d22D844690ff89ea5e8a6bb4Ca3F7DAc83a40c3")
        self.rpc_url = os.environ.get("RPC_URL", "https://base.llamarpc.com")
        
        # Node configurations (each uses separate simulator socket)
        self.node1_connection_url = os.environ.get("NODE1_CONNECTION_URL", "http://localhost:8081")
        self.node2_connection_url = os.environ.get("NODE2_CONNECTION_URL", "http://localhost:8082") 
        self.node1_socket = "./simulator/dstack1.sock"
        self.node2_socket = "./simulator2/dstack2.sock"
        
        # Process management for both simulators
        self.simulator1_process = None
        self.simulator2_process = None
        self.node1_sdk = None
        self.node2_sdk = None
    
    def check_rye_available(self) -> bool:
        """Check if rye is available"""
        try:
            result = subprocess.run(["rye", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Rye available: {result.stdout.strip()}")
                return True
            return False
        except FileNotFoundError:
            return False
    
    def start_simulator(self, simulator_name: str, simulator_dir: str) -> subprocess.Popen:
        """Start a DStack simulator in the specified directory"""
        sim_path = Path(simulator_dir)
        if not sim_path.exists():
            logger.error(f"{simulator_name} directory not found at {simulator_dir}")
            return None
        
        simulator_binary = sim_path / "dstack-simulator"
        if not simulator_binary.exists():
            logger.error(f"Simulator binary not found at {simulator_binary}")
            logger.info(f"Please ensure the dstack-simulator binary is available in {simulator_dir}")
            return None
        
        try:
            logger.info(f"Starting {simulator_name}...")
            # Start simulator in the simulator directory
            process = subprocess.Popen(
                ["./dstack-simulator"],
                cwd=str(sim_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit for simulator to start
            time.sleep(2)
            
            # Check if simulator is running
            if process.poll() is None:
                logger.info(f"✅ {simulator_name} started successfully")
                return process
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ {simulator_name} failed to start:")
                logger.error(f"stdout: {stdout}")
                logger.error(f"stderr: {stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to start {simulator_name}: {e}")
            return None
    
    def start_both_simulators(self) -> bool:
        """Start both DStack simulators"""
        logger.info("Starting both DStack simulators...")
        
        # Start simulator 1
        self.simulator1_process = self.start_simulator("Simulator 1", "./simulator")
        if not self.simulator1_process:
            return False
        
        # Start simulator 2
        self.simulator2_process = self.start_simulator("Simulator 2", "./simulator2")
        if not self.simulator2_process:
            # If simulator 2 fails, cleanup simulator 1
            self.stop_simulator(self.simulator1_process, "Simulator 1")
            self.simulator1_process = None
            return False
        
        logger.info("✅ Both simulators started successfully")
        return True
    
    def stop_simulator(self, process: subprocess.Popen, name: str):
        """Stop a specific DStack simulator"""
        if process:
            logger.info(f"Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} didn't stop gracefully, forcing...")
                process.kill()
    
    def stop_both_simulators(self):
        """Stop both DStack simulators"""
        self.stop_simulator(self.simulator1_process, "Simulator 1")
        self.stop_simulator(self.simulator2_process, "Simulator 2")
        self.simulator1_process = None
        self.simulator2_process = None
    
    async def wait_for_socket(self, socket_path: str, socket_name: str, max_retries: int = 30) -> bool:
        """Wait for a specific DStack socket to become available"""
        logger.info(f"Waiting for {socket_name} socket at {socket_path}")
        
        for attempt in range(max_retries):
            if os.path.exists(socket_path):
                try:
                    # Test that we can actually connect
                    from dstack_sdk import DstackClient
                    test_client = DstackClient(socket_path)
                    test_client.info()
                    logger.info(f"{socket_name} socket ready after {attempt + 1} attempts")
                    return True
                except Exception as e:
                    logger.debug(f"{socket_name} socket exists but not ready: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"{socket_name} socket not ready (attempt {attempt + 1}/{max_retries}), waiting...")
                await asyncio.sleep(2)
            else:
                logger.error(f"{socket_name} socket never became ready at {socket_path}")
                return False
        
        return False
    
    async def wait_for_both_sockets(self) -> bool:
        """Wait for both DStack sockets to become available"""
        logger.info("Waiting for both DStack sockets...")
        
        # Wait for both sockets concurrently
        socket1_task = self.wait_for_socket(self.node1_socket, "Node 1")
        socket2_task = self.wait_for_socket(self.node2_socket, "Node 2")
        
        socket1_ready, socket2_ready = await asyncio.gather(socket1_task, socket2_task, return_exceptions=True)
        
        if socket1_ready is True and socket2_ready is True:
            logger.info("✅ Both sockets are ready")
            return True
        else:
            logger.error("❌ One or both sockets failed to become ready")
            if socket1_ready is not True:
                logger.error(f"Node 1 socket issue: {socket1_ready}")
            if socket2_ready is not True:
                logger.error(f"Node 2 socket issue: {socket2_ready}")
            return False
    
    async def initialize_sdks(self) -> bool:
        """Initialize both SDK instances"""
        try:
            logger.info("Initializing SDK instances...")
            
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
            
            logger.info("✅ Both SDK instances initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize SDKs: {e}")
            return False
    
    async def register_nodes(self) -> bool:
        """Register both nodes with the contract"""
        logger.info("=== REGISTERING NODES ===")
        
        try:
            # Register Node 1
            logger.info(f"Registering Node 1 ({self.node1_connection_url})...")
            node1_success = await self.node1_sdk.register()
            if node1_success:
                logger.info("✅ Node 1 registered successfully!")
            else:
                logger.error("❌ Node 1 registration failed!")
                return False
            
            # Small delay between registrations
            await asyncio.sleep(2)
            
            # Register Node 2
            logger.info(f"Registering Node 2 ({self.node2_connection_url})...")
            node2_success = await self.node2_sdk.register()
            if node2_success:
                logger.info("✅ Node 2 registered successfully!")
            else:
                logger.error("❌ Node 2 registration failed!")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Registration failed: {e}")
            return False
    
    async def test_peer_discovery(self) -> bool:
        """Test that both nodes can discover each other"""
        logger.info("=== TESTING PEER DISCOVERY ===")
        
        try:
            # Wait for contract state to update
            await asyncio.sleep(3)
            
            # Get peers from both nodes
            logger.info("Getting peers from Node 1...")
            node1_peers = await self.node1_sdk.get_peers()
            logger.info(f"Node 1 sees peers: {node1_peers}")
            
            logger.info("Getting peers from Node 2...")
            node2_peers = await self.node2_sdk.get_peers()
            logger.info(f"Node 2 sees peers: {node2_peers}")
            
            # Verify results
            expected_urls = {self.node1_connection_url, self.node2_connection_url}
            node1_peers_set = set(node1_peers)
            node2_peers_set = set(node2_peers)
            
            if expected_urls.issubset(node1_peers_set) and expected_urls.issubset(node2_peers_set):
                logger.info("✅ SUCCESS: Both nodes can discover each other!")
                logger.info(f"Total unique peers: {len(node1_peers_set)}")
                return True
            else:
                logger.error("❌ FAILED: Peer discovery incomplete")
                logger.error(f"Expected: {expected_urls}")
                logger.error(f"Node 1 found: {node1_peers_set}")
                logger.error(f"Node 2 found: {node2_peers_set}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Peer discovery test failed: {e}")
            return False
    
    async def run_demo(self) -> bool:
        """Run the complete local demo"""
        logger.info("🚀 Starting Local Two-Node DStack P2P Demo")
        logger.info(f"Contract: {self.contract_address}")
        logger.info(f"Node 1: {self.node1_connection_url} (socket: {self.node1_socket})")
        logger.info(f"Node 2: {self.node2_connection_url} (socket: {self.node2_socket})")
        logger.info(f"RPC: {self.rpc_url}")
        
        try:
            # Step 1: Start both simulators
            if not self.start_both_simulators():
                return False
            
            # Step 2: Wait for both sockets
            if not await self.wait_for_both_sockets():
                return False
            
            # Step 3: Initialize SDKs
            if not await self.initialize_sdks():
                return False
            
            # Step 4: Register nodes
            if not await self.register_nodes():
                return False
            
            # Step 5: Test peer discovery
            if not await self.test_peer_discovery():
                return False
            
            logger.info("🎉 LOCAL TWO-NODE DEMO COMPLETED SUCCESSFULLY!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # Always cleanup both simulators
            self.stop_both_simulators()

def setup_signal_handlers(demo):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        demo.stop_both_simulators()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main entry point"""
    # Check required environment variables
    if not os.environ.get("PRIVATE_KEY"):
        logger.error("❌ PRIVATE_KEY environment variable is required")
        logger.info("Set it with: export PRIVATE_KEY=your_private_key_here")
        return False
    
    # Create demo instance
    demo = LocalTwoNodeDemo()
    
    # Setup signal handlers
    setup_signal_handlers(demo)
    
    # Check if rye is available (optional but recommended)
    if demo.check_rye_available():
        logger.info("✅ Rye detected - you can also run this with: rye run python test_local_two_nodes.py")
    else:
        logger.info("ℹ️  Rye not detected - running with system Python")
    
    # Run the demo
    success = await demo.run_demo()
    
    if success:
        logger.info("✅ Demo completed successfully!")
        return True
    else:
        logger.error("❌ Demo failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
