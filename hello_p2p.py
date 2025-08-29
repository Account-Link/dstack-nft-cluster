#!/usr/bin/env python3
"""
Simple P2P Hello Application using DStack Cluster SDK

Demonstrates:
- Ultra-simple 3-line P2P SDK usage
- Peer discovery and communication
- Basic HTTP server for inter-peer communication
"""

import asyncio
import logging
import argparse
import json
import time
from typing import List
from aiohttp import web, ClientSession
import aiohttp

from dstack_cluster import DStackP2PSDK

logger = logging.getLogger(__name__)

class HelloP2PApp:
    def __init__(self, contract_address: str, port: int = 8080):
        self.instance_id = None  # Will be obtained from DStack SDK
        self.port = port
        self.peers = []
        self.peer_info = {}  # Store info about discovered peers
        
        # Initialize P2P SDK - the magical 3-line interface!
        connection_url = f"http://localhost:{self.port}"
        self.sdk = DStackP2PSDK(contract_address, connection_url)
        
        # HTTP server for peer communication
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Setup HTTP endpoints for peer communication"""
        self.app.router.add_get('/hello', self.handle_hello)
        self.app.router.add_get('/info', self.handle_info)
        self.app.router.add_get('/peers', self.handle_peers)
        
    async def handle_hello(self, request):
        """Handle incoming hello requests from peers"""
        remote_id = request.query.get('from', 'unknown')
        logger.info(f"Received hello from peer: {remote_id}")
        
        return web.json_response({
            'message': f'Hello from {self.instance_id}!',
            'timestamp': time.time(),
            'peers_known': len(self.peers)
        })
        
    async def handle_info(self, request):
        """Return info about this instance"""
        return web.json_response({
            'instance_id': self.instance_id,
            'connection_url': self.connection_url,
            'peers_count': len(self.peers),
            'uptime': time.time()
        })
        
    async def handle_peers(self, request):
        """Return list of known peers"""
        return web.json_response({
            'peers': self.peers,
            'peer_info': self.peer_info
        })
        
    async def register_with_cluster(self):
        """Register with the P2P cluster using SDK"""
        logger.info("🔗 Registering with P2P cluster...")
        
        try:
            # The magical 3-line interface:
            success = await self.sdk.register()
            
            if success:
                # Get instance ID from SDK after registration
                self.instance_id = self.sdk.instance_id
                logger.info(f"✅ Successfully registered with cluster as {self.instance_id}")
                return True
            else:
                logger.error("❌ Failed to register with cluster")
                return False
                
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False
            
    async def discover_peers(self):
        """Discover other peers in the cluster"""
        try:
            # The magical peer discovery:
            current_peers = await self.sdk.get_peers()
            
            # Filter out our own URL
            new_peers = [peer for peer in current_peers if peer != self.connection_url]
            
            if new_peers != self.peers:
                logger.info(f"🔍 Peer list updated: {len(new_peers)} peers found")
                self.peers = new_peers
                
                # Say hello to new peers
                await self.greet_peers()
                
        except Exception as e:
            logger.error(f"Peer discovery failed: {e}")
            
    async def greet_peers(self):
        """Send hello messages to all known peers"""
        if not self.peers:
            logger.info("💭 No peers to greet yet")
            return
            
        logger.info(f"👋 Greeting {len(self.peers)} peers...")
        
        async with ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            for peer_url in self.peers:
                try:
                    # Extract base URL for HTTP requests
                    if peer_url.startswith('http'):
                        hello_url = f"{peer_url}/hello?from={self.instance_id}"
                    else:
                        # Handle IP:port format
                        hello_url = f"http://{peer_url}/hello?from={self.instance_id}"
                        
                    async with session.get(hello_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"📨 Response from peer: {data.get('message')}")
                            
                            # Store peer info
                            self.peer_info[peer_url] = {
                                'last_contact': time.time(),
                                'response': data
                            }
                        else:
                            logger.warning(f"⚠️  Peer {peer_url} returned status {response.status}")
                            
                except Exception as e:
                    logger.debug(f"Could not reach peer {peer_url}: {e}")
                    
    async def peer_monitor_loop(self):
        """Continuously monitor for new peers and communicate"""
        while True:
            try:
                await self.discover_peers()
                await asyncio.sleep(10)  # Check for new peers every 10 seconds
                
            except Exception as e:
                logger.error(f"Peer monitor error: {e}")
                await asyncio.sleep(5)
                
    async def start_server(self):
        """Start the HTTP server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"🚀 HTTP server started on port {self.port}")
        
    async def run(self):
        """Main application loop"""
        logger.info("🌟 Starting Hello P2P App")
        
        # Start HTTP server
        await self.start_server()
        
        # Register with cluster (this will set self.instance_id)
        if await self.register_with_cluster():
            # Start peer monitoring
            monitor_task = asyncio.create_task(self.peer_monitor_loop())
            
            logger.info(f"✨ Hello P2P App ({self.instance_id}) is running! Press Ctrl+C to stop")
            
            try:
                await monitor_task
            except KeyboardInterrupt:
                logger.info(f"👋 Shutting down Hello P2P App ({self.instance_id})")
                monitor_task.cancel()
        else:
            logger.error("💥 Failed to start - could not register with cluster")

async def main():
    parser = argparse.ArgumentParser(description="Simple P2P Hello Application")
    parser.add_argument("contract_address", help="Smart contract address")
    parser.add_argument("--port", type=int, default=8080, help="HTTP server port")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run the app - ultra-simple interface!
    app = HelloP2PApp(
        contract_address=args.contract_address,
        port=args.port
    )
    
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())