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
                 host_private_key: str = None):
        self.instance_id = instance_id
        self.port = port
        self.dstack_socket = dstack_socket
        
        # Host key is mandatory for all blockchain transactions
        if not host_private_key:
            raise ValueError("host_private_key is required - app key is only for TEE attestation")
        
        self.host_account = Account.from_key(host_private_key)
        self.host_address = self.host_account.address
        
        # Initialize DStack for app key (TEE authentication)
        self._init_dstack_app_key()
        
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
        
        # Contract ABI (updated for new DstackMembershipNFT contract)
        self.contract_abi = [
            {"inputs": [], "name": "currentLeader", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "totalActiveNodes", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "requiredVotes", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "address"}, {"type": "bool"}], "name": "castVote", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [], "name": "electLeader", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [], "name": "getActiveInstances", "outputs": [{"type": "string[]"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "string"}], "name": "registerInstance", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "string"}, {"type": "uint256"}, {"type": "bytes"}, {"type": "bytes"}, {"type": "bytes"}, {"type": "string"}, {"type": "bytes32"}], "name": "submitCounterAttestation", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"type": "address"}], "name": "walletToTokenId", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "string"}], "name": "getInstanceInfo", "outputs": [{"type": "uint256", "name": "tokenId"}, {"type": "bool", "name": "active"}, {"type": "address", "name": "ownerAddr"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"type": "string"}], "name": "deactivateInstance", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"}
        ]
        
        self.contract = self.w3.eth.contract(address=contract_address, abi=self.contract_abi)
        
        # HTTP client for inter-node communication
        self.http_client = None
        
        # Background tasks
        self.leader_monitor_task = None
        self.heartbeat_task = None
        
    def _init_dstack_app_key(self):
        """Initialize DStack app key for TEE authentication"""
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
        logger.info(f"DStack Instance ID: {info.instance_id}")
        
        # Get app key for TEE authentication (shared across all instances of this app)
        app_key_response = self.dstack_client.get_key("app", "ethereum")
        
        # Convert to eth_account for signing
        from dstack_sdk.ethereum import to_account_secure
        self.app_account = to_account_secure(app_key_response)
        self.app_key_response = app_key_response
        
        logger.info(f"DStack app key initialized for TEE authentication")
        logger.info(f"App key address: {self.app_account.address}")
        if self.host_address:
            logger.info(f"Host key address: {self.host_address} (for transactions)")
        else:
            logger.info("No host key provided - using app key for transactions (not recommended)")
    
    def get_wallet_info(self):
        """Get wallet information for debugging"""
        return {
            'host_key_address': self.host_address,
            'instance_id': self.instance_id,
            'socket': self.dstack_socket or './simulator/dstack.sock'
        }
    
    def sign_with_app_key(self, message: str) -> bytes:
        """Sign a message with the TEE app key for authentication"""
        message_hash = Account.from_key(self.app_key_response.decode_key()).sign_message(message.encode()).signature
        return message_hash
    
    async def submit_counter_attestation(self, value: int):
        """Submit counter value with TEE attestation signature"""
        try:
            # Create message to sign with app key
            message = f"{self.instance_id}:{value}"
            app_signature = self.sign_with_app_key(message)
            
            # For now, we'll use a placeholder KMS signature
            # In production, this would come from the KMS service
            kms_signature = b'\x00' * 65  # Placeholder
            
            # Use host key for transaction (mandatory)
            tx_account = self.host_account
            
            # Build and send transaction
            tx = self.contract.functions.submitCounterAttestation(
                self.instance_id,
                value,
                app_signature,
                kms_signature
            ).build_transaction({
                'from': tx_account.address,
                'nonce': self.w3.eth.get_transaction_count(tx_account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = tx_account.sign_transaction(tx)
            
            # Handle different Web3.py versions
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
            
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            logger.info(f"Counter attestation submitted: value={value}, tx={tx_hash.hex()}")
            
        except Exception as e:
            logger.error(f"Error submitting counter attestation: {e}")
    
    async def prepare_for_deployment(self):
        """Prepare instance info for NFT owner pre-registration"""
        print("Preparing deployment information...")
        
        info = self.dstack_client.info()
        
        print("\n" + "="*60)
        print("DEPLOYMENT INFO FOR NFT OWNER")
        print("="*60)
        print(f"Instance ID: {self.instance_id}")
        print(f"DStack Instance ID: {info.instance_id}")
        print(f"App ID: {info.app_id}")
        print(f"Host Address: {self.host_address} (must be pre-funded)")
        print("="*60)
        print("NFT owner should:")
        print(f"1. Ensure host address {self.host_address} owns an NFT")
        print(f"2. Fund the host address: {self.host_address}")
        print(f"3. Register instance '{self.instance_id}' using the NFT")
        print("="*60 + "\n")
        
        return {
            "instance_id": self.instance_id,
            "dstack_instance_id": info.instance_id,
            "app_id": info.app_id,
            "host_key_address": self.host_address
        }
    
    async def register_instance(self):
        """Register this instance with the contract"""
        try:
            # Check if we already have a token ID
            self.token_id = self.contract.functions.walletToTokenId(self.host_address).call()
            
            if self.token_id == 0:
                logger.warning("No NFT found for this wallet. NFT owner must mint first.")
                return {"needs_nft": True, "address": self.host_address}
            
            logger.info(f"Found NFT token ID: {self.token_id}")
            
            # Check if instance is already registered
            instance_info = self.contract.functions.getInstanceInfo(self.instance_id).call()
            if instance_info[1]:  # active flag
                logger.info("Instance already registered and active")
                return {"ready": True, "token_id": self.token_id}
            
            # Register the instance
            tx_account = self.host_account
            
            tx = self.contract.functions.registerInstance(self.instance_id).build_transaction({
                'from': tx_account.address,
                'nonce': self.w3.eth.get_transaction_count(tx_account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = tx_account.sign_transaction(tx)
            
            # Handle different Web3.py versions
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            else:
                raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
            
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            logger.info(f"Instance registration transaction sent: {tx_hash.hex()}")
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            if receipt.status == 1:
                logger.info("Instance successfully registered!")
                return {"ready": True, "token_id": self.token_id}
            else:
                logger.error("Instance registration failed")
                return {"error": "Transaction failed"}
                
        except Exception as e:
            logger.error(f"Error registering instance: {e}")
            return {"error": str(e)}
    
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
        
        # Instance is ready to start - NFT should already be minted and instance registered by run_counter.sh
        logger.info("Instance starting - NFT should be minted and instance registered by external script")
        
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
            
            # Check if we are the leader (using host address)
            our_address = self.host_address
            
            if current_leader == our_address:
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
            # Use host key for transaction (mandatory)
            tx_account = self.host_account
            
            # Build transaction
            tx = self.contract.functions.castVote(target_leader, True).build_transaction({
                'from': tx_account.address,
                'nonce': self.w3.eth.get_transaction_count(tx_account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = tx_account.sign_transaction(tx)
            
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
            # Use host key for transaction (mandatory)
            tx_account = self.host_account
            
            # Build transaction
            tx = self.contract.functions.castVote(target_leader, False).build_transaction({
                'from': tx_account.address,
                'nonce': self.w3.eth.get_transaction_count(tx_account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = tx_account.sign_transaction(tx)
            
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
            'leader': self.host_address
        }
        self.operation_log.append(operation)
        
        logger.info(f"Counter incremented to {self.counter_value}")
        
        # Submit attestation to contract
        await self.submit_counter_attestation(self.counter_value)
        
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
                'host_key_address': self.host_address,
                'is_leader': self.is_leader,
                'counter_value': self.counter_value,
                'total_active_nodes': total_nodes,
                'required_votes': required_votes,
                'current_leader': current_leader,
                'last_leader_heartbeat': self.last_leader_heartbeat,
                'token_id': self.token_id
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
                'active_instances': active_instances,
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
    parser.add_argument('--contract', required=True, help='Contract address')
    parser.add_argument('--rpc-url', default='http://localhost:8545', help='Ethereum RPC URL')
    parser.add_argument('--port', type=int, default=8080, help='HTTP port')
    
    # Key options
    parser.add_argument('--host-key', help='Host private key for transactions (pre-funded)')
    parser.add_argument('--dstack-socket', help='DStack socket path (default: ./simulator/dstack.sock)')
    parser.add_argument('--prepare-only', action='store_true', help='Only prepare deployment info, do not start service')
    
    args = parser.parse_args()
    
    # Create counter service
    counter = DistributedCounter(
        instance_id=args.instance_id,
        contract_address=args.contract,
        rpc_url=args.rpc_url,
        port=args.port,
        dstack_socket=args.dstack_socket,
        host_private_key=args.host_key
    )
    
    if args.prepare_only:
        # Just output deployment info and exit
        await counter.prepare_for_deployment()
        print("\nDeployment info prepared. Exiting preparation mode.")
    else:
        # Start the full counter service
        await counter.start()

if __name__ == '__main__':
    asyncio.run(main())
