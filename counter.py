#!/usr/bin/env python3
"""
Distributed Counter Service with NFT-based Membership and Byzantine Fault Tolerance

This application demonstrates:
- NFT-based node authorization
- Byzantine fault tolerant leader election
- Distributed consensus for counter operations
- Automatic failover when leader becomes unresponsive
- DStack integration for secure key derivation
"""

import asyncio
import logging
import argparse
import json
import time
import os
from typing import Dict, Any, Optional
from aiohttp import web
import aiohttp

from dstack_sdk import DstackClient

try:
    from web3 import Web3
    from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware as geth_poa_middleware
    from eth_account import Account
    from web3.types import bytes32
except ImportError:
    # Fallback for older web3 versions
    try:
        from web3.types import bytes32
    except ImportError:
        bytes32 = bytes

# Import our signature proof module
from signature_proof import SignatureProofGenerator, RegistrationData

logger = logging.getLogger(__name__)

class DistributedCounter:
    def __init__(self, instance_id: str, contract_address: str = None, 
                 rpc_url: str = "http://localhost:8545", 
                 port: int = 8080, dstack_socket: str = None,
                 dstack_key_path: str = None, dstack_key_purpose: str = None):
        self.instance_id = instance_id
        self.port = port
        self.dstack_socket = dstack_socket
        self.dstack_key_path = dstack_key_path or f"node/{instance_id}"
        self.dstack_key_purpose = dstack_key_purpose or "ethereum"
        
        # Initialize DStack wallet (required for signature chain verification)
        self._init_dstack_wallet()
        
        # Web3 setup
        if not contract_address:
            raise ValueError("contract_address is required")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.contract_address = contract_address
        
        # Counter state
        self.counter_value = 0
        self.operation_log = []
        self.is_leader = False
        self.last_leader_heartbeat = 0
        
        # Instance registration state
        self.token_id = None
        self.instance_id_bytes32 = bytes32(0)
        
        # Contract ABI (simplified for demo)
        self.contract_abi = [
            {"inputs": [], "name": "currentLeader", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "totalActiveNodes", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "requiredVotes", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "address"}, {"type": "bool"}], "name": "castVote", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [], "name": "electLeader", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [], "name": "getActiveInstances", "outputs": [{"type": "bytes32[]"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "bytes32"}, {"type": "uint256"}], "name": "registerInstance", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "bytes32"}, {"type": "uint256"}, {"type": "bytes"}, {"type": "bytes"}, {"type": "bytes"}, {"type": "string"}, {"type": "bytes32"}], "name": "registerInstanceWithProof", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "address"}], "name": "walletToTokenId", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "updateClusterSize", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
        ]
        
        self.contract = self.w3.eth.contract(address=contract_address, abi=self.contract_abi)
        
        # HTTP client for inter-node communication
        self.http_client = None
        
        # Background tasks
        self.leader_monitor_task = None
        self.heartbeat_task = None
        
    def _init_dstack_wallet(self):
        """Initialize wallet using dstack-sdk for instance-specific key derivation"""
        # Create dstack client
        if self.dstack_socket:
            self.dstack_client = DstackClient(self.dstack_socket)
        else:
            # Try to auto-detect socket
            if os.path.exists('./simulator/dstack.sock'):
                self.dstack_client = DstackClient('./simulator/dstack.sock')
            else:
                raise ValueError("No dstack socket specified and ./simulator/dstack.sock not found")
        
        # Get instance information
        info = self.dstack_client.info()
        logger.info(f"Connected to dstack: {info.app_name} (ID: {info.app_id})")
        logger.info(f"Instance ID: {info.instance_id}")
        
        # Use instance-specific key derivation for truly unique keys per instance
        instance_key_path = f"instance/{info.instance_id}"
        logger.info(f"Using instance-specific key path: {instance_key_path}")
        
        # Derive instance-specific key 
        key_response = self.dstack_client.get_key(instance_key_path, self.dstack_key_purpose)
        private_key_bytes = key_response.decode_key()
        
        # Convert to eth_account
        from dstack_sdk.ethereum import to_account_secure
        self.account = to_account_secure(key_response)
        self.wallet_address = self.account.address
        self.instance_key_path = instance_key_path
        
        logger.info(f"DStack instance wallet initialized: {self.wallet_address}")
        logger.info(f"Key derived from path: {instance_key_path}, purpose: {self.dstack_key_purpose}")
        logger.info(f"This address is unique to this DStack instance and needs funding from NFT owner")
    
    def get_wallet_info(self):
        """Get wallet information for debugging"""
        return {
            'type': 'dstack',
            'address': self.wallet_address,
            'key_path': self.dstack_key_path,
            'key_purpose': self.dstack_key_purpose,
            'socket': self.dstack_socket or './simulator/dstack.sock'
        }
    
    async def register_instance(self, nft_owner_address=None):
        """Prepare instance for registration by external NFT owner
        
        This method prepares the signature proof and outputs registration details
        for the external NFT owner to use. The instance does not register itself.
        
        Args:
            nft_owner_address: Address of NFT owner (external), if None will just generate proof
        """
        logger.info("Preparing instance for external registration...")
        logger.info(f"Instance address: {self.wallet_address}")
        logger.info(f"Instance unique key path: {self.instance_key_path}")
        
        try:
            # Check if instance address has sufficient balance for transactions
            balance = self.w3.eth.get_balance(self.wallet_address)
            logger.info(f"Instance address balance: {self.w3.from_wei(balance, 'ether')} ETH")
            
            # Use signature proof generator with instance-specific path
            proof_generator = SignatureProofGenerator(self.dstack_socket)
            
            # Generate signature proof using instance-specific key path
            proof = proof_generator.generate_proof(
                self.instance_id, 
                self.instance_key_path, 
                self.dstack_key_purpose
            )
            
            # Convert instance_id to bytes32
            import hashlib
            instance_hash = hashlib.sha256(self.instance_id.encode()).digest()
            instance_id_bytes32 = bytes(instance_hash)
            
            # Get app ID from dstack client
            info = self.dstack_client.info()
            app_id = info.app_id
            app_id_bytes = bytes.fromhex(app_id[2:])  # Remove 0x prefix
            app_id_bytes32 = app_id_bytes.ljust(32, b'\x00')  # Pad to 32 bytes
            
            # Store instance registration data
            self.instance_id_bytes32 = instance_id_bytes32
            self.registration_proof = proof
            
            # Output registration info for external NFT owner
            logger.info("\n" + "="*60)
            logger.info("REGISTRATION INFO FOR NFT OWNER")
            logger.info("="*60)
            logger.info(f"Instance Address: {self.wallet_address}")
            logger.info(f"  -> This address needs ETH funding for gas")
            logger.info(f"Instance ID (bytes32): 0x{instance_id_bytes32.hex()}")
            logger.info(f"Derived Public Key: 0x{proof.derived_public_key.hex()}")
            logger.info(f"App Signature: 0x{proof.app_signature.hex()}")
            logger.info(f"KMS Signature: 0x{proof.kms_signature.hex()}")
            logger.info(f"Purpose: {proof.purpose}")
            logger.info(f"App ID: 0x{app_id_bytes32.hex()}")
            logger.info("="*60)
            logger.info("NFT owner should:")
            logger.info("1. Fund instance address with ETH")
            logger.info("2. Call contract.registerInstanceWithProof() with above data")
            logger.info("="*60 + "\n")
            
            # Check if we're funded for basic operations
            if balance == 0:
                logger.warning("Instance address needs funding before it can participate in consensus")
                return {"ready": False, "needs_funding": True, "address": self.wallet_address}
            else:
                logger.info("Instance has sufficient balance for operations")
                return {"ready": True, "needs_funding": False, "address": self.wallet_address}
                
        except Exception as e:
            logger.error(f"Instance preparation failed: {e}")
            return {"ready": False, "error": str(e)}
    
    async def start(self):
        """Start the counter service"""
        logger.info(f"Starting distributed counter on port {self.port}")
        
        # Initialize HTTP client
        self.http_client = aiohttp.ClientSession()
        
        # Start background tasks
        self.leader_monitor_task = asyncio.create_task(self.monitor_leader_health())
        self.heartbeat_task = asyncio.create_task(self.leader_heartbeat())
        
        # Start HTTP server
        app = web.Application()
        app.router.add_get('/counter', self.get_counter)
        app.router.add_post('/increment', self.increment_counter)
        app.router.add_get('/log', self.get_log)
        app.router.add_get('/status', self.get_status)
        app.router.add_get('/members', self.get_members)
        app.router.add_get('/health', self.health_check)
        app.router.add_get('/wallet-info', self.get_wallet_info_endpoint)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"Counter service started on port {self.port}")
        
        # Prepare instance for external registration
        registration_result = await self.register_instance()
        
        if registration_result.get("needs_funding"):
            logger.info(f"Instance waiting for NFT owner to fund address: {registration_result['address']}")
        elif registration_result.get("ready"):
            logger.info("Instance is funded and ready for consensus participation")
        else:
            logger.error("Instance preparation failed - check logs above")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources"""
        if self.leader_monitor_task:
            self.leader_monitor_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.http_client:
            await self.http_client.close()
    
    async def monitor_leader_health(self):
        """Monitor leader health and participate in consensus"""
        while True:
            try:
                await self.check_leader_status()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in leader monitoring: {e}")
                await asyncio.sleep(5)
    
    async def check_leader_status(self):
        """Check current leader status and participate in consensus"""
        try:
            current_leader = self.contract.functions.currentLeader().call()
            
            if current_leader == self.wallet_address:
                # I am the leader
                if not self.is_leader:
                    logger.info("I am now the leader!")
                    self.is_leader = True
            else:
                # I am not the leader
                if self.is_leader:
                    logger.info("I am no longer the leader")
                    self.is_leader = False
                
                # Check if leader is responsive
                if current_leader != '0x0000000000000000000000000000000000000000':
                    is_responsive = await self.ping_leader(current_leader)
                    if not is_responsive:
                        logger.info(f"Leader {current_leader} is unresponsive, voting no confidence")
                        await self.vote_no_confidence(current_leader)
                    else:
                        # Leader is responsive, clear any no-confidence vote
                        await self.vote_confidence(current_leader)
                        
        except Exception as e:
            logger.error(f"Error checking leader status: {e}")
    
    async def ping_leader(self, leader_address: str, timeout: float = 5.0) -> bool:
        """Ping the leader to check responsiveness"""
        try:
            # Get leader's instance ID from contract
            active_instances = self.contract.functions.getActiveInstances().call()
            
            # For demo purposes, we'll try to ping a known endpoint
            # In production, this would use the actual instance discovery
            leader_url = f"http://localhost:8080/health"  # Simplified for demo
            
            async with aiohttp.ClientTimeout(total=timeout):
                async with self.http_client.get(leader_url) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"Leader ping failed: {e}")
            return False
    
    async def vote_no_confidence(self, target_leader: str):
        """Vote no confidence against a leader"""
        try:
            # Build transaction
            tx = self.contract.functions.castVote(target_leader, True).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = self.account.sign_transaction(tx)
            
            # Handle different Web3.py versions
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
            
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            
            logger.info(f"Voted no confidence against {target_leader}, tx: {tx_hash.hex()}")
            
        except Exception as e:
            logger.error(f"Error voting no confidence: {e}")
    
    async def vote_confidence(self, target_leader: str):
        """Vote confidence in a leader"""
        try:
            # Build transaction
            tx = self.contract.functions.castVote(target_leader, False).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = self.account.sign_transaction(tx)
            
            # Handle different Web3.py versions
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
            
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            
            logger.debug(f"Voted confidence in {target_leader}, tx: {tx_hash.hex()}")
            
        except Exception as e:
            logger.error(f"Error voting confidence: {e}")
    
    async def leader_heartbeat(self):
        """Send heartbeat if I am the leader"""
        while True:
            try:
                if self.is_leader:
                    # Leader heartbeat logic could go here
                    # For now, just log that we're alive
                    logger.debug("Leader heartbeat")
                    self.last_leader_heartbeat = time.time()
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
            except Exception as e:
                logger.error(f"Error in leader heartbeat: {e}")
                await asyncio.sleep(5)
    
    async def get_counter(self, request):
        """Get current counter value"""
        return web.json_response({
            'value': self.counter_value,
            'instance_id': self.instance_id,
            'is_leader': self.is_leader
        })
    
    async def increment_counter(self, request):
        """Increment counter (only leader can do this)"""
        if not self.is_leader:
            return web.json_response({
                'error': 'Only leader can increment counter'
            }, status=403)
        
        # Increment counter
        self.counter_value += 1
        
        # Log operation
        operation = {
            'timestamp': time.time(),
            'operation': 'increment',
            'new_value': self.counter_value,
            'leader': self.wallet_address
        }
        self.operation_log.append(operation)
        
        logger.info(f"Counter incremented to {self.counter_value}")
        
        return web.json_response({
            'success': True,
            'new_value': self.counter_value,
            'operation_id': len(self.operation_log)
        })
    
    async def get_log(self, request):
        """Get operation log"""
        return web.json_response({
            'operations': self.operation_log,
            'total_operations': len(self.operation_log)
        })
    
    async def get_status(self, request):
        """Get node status"""
        try:
            total_nodes = self.contract.functions.totalActiveNodes().call()
            required_votes = self.contract.functions.requiredVotes().call()
            current_leader = self.contract.functions.currentLeader().call()
            
            return web.json_response({
                'instance_id': self.instance_id,
                'wallet_address': self.wallet_address,
                'is_leader': self.is_leader,
                'counter_value': self.counter_value,
                'total_active_nodes': total_nodes,
                'required_votes': required_votes,
                'current_leader': current_leader,
                'last_leader_heartbeat': self.last_leader_heartbeat
            })
        except Exception as e:
            return web.json_response({
                'error': str(e)
            }, status=500)
    
    async def get_members(self, request):
        """Get active cluster members"""
        try:
            active_instances = self.contract.functions.getActiveInstances().call()
            return web.json_response({
                'active_instances': [instance.hex() for instance in active_instances],
                'total_active': len(active_instances)
            })
        except Exception as e:
            return web.json_response({
                'error': str(e)
            }, status=500)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'instance_id': self.instance_id,
            'timestamp': time.time()
        })

    async def get_wallet_info_endpoint(self, request):
        """Get wallet information for debugging"""
        return web.json_response(self.get_wallet_info())

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Distributed Counter Service')
    parser.add_argument('--instance-id', required=True, help='Unique instance ID')
    parser.add_argument('--wallet', help='Wallet private key (required when not using dstack)')
    parser.add_argument('--contract', required=True, help='Contract address')
    parser.add_argument('--rpc-url', default='http://localhost:8545', help='Ethereum RPC URL')
    parser.add_argument('--port', type=int, default=8080, help='HTTP port')
    
    # DStack options
    parser.add_argument('--dstack-socket', help='DStack socket path (default: ./simulator/dstack.sock)')
    parser.add_argument('--dstack-key-path', help='DStack key derivation path (default: node/{instance-id})')
    parser.add_argument('--dstack-key-purpose', help='DStack key purpose (default: ethereum)')
    
    args = parser.parse_args()
    
    # Create and start counter service
    counter = DistributedCounter(
        instance_id=args.instance_id,
        contract_address=args.contract,
        rpc_url=args.rpc_url,
        port=args.port,
        dstack_socket=args.dstack_socket,
        dstack_key_path=args.dstack_key_path,
        dstack_key_purpose=args.dstack_key_purpose
    )
    
    await counter.start()

if __name__ == '__main__':
    asyncio.run(main())
