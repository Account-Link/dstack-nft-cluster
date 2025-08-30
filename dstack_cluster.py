#!/usr/bin/env python3
"""
DStack P2P Cluster SDK - TLS Gateway Mode

Ultra-simple interface for P2P cluster membership:
    sdk = DStackP2PSDK("0x123...", "tls")
    await sdk.register()
    peers = await sdk.get_peers()
"""

import asyncio
import logging
from typing import List, Optional
from dstack_sdk import DstackClient
from signature_proof import SignatureProofGenerator

try:
    from web3 import Web3
    from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    pass

logger = logging.getLogger(__name__)

class DStackP2PSDK:
    def __init__(self, contract_address: str, connection_url: str,
                 rpc_url: str = "http://localhost:8545", dstack_socket: str = "./simulator/dstack.sock"):
        """
        Ultra-simple P2P SDK interface.
        
        Args:
            contract_address: Contract address for peer registry  
            connection_url: This instance's connection URL
                           - Production: https://<prefix>.<basedomain>/
                           - Dev: any URL (http://localhost:8080, 10.0.1.1:5432, etc)
            rpc_url: Blockchain RPC endpoint
            dstack_socket: Path to dstack socket (for simulator)
        """
            
        self.contract_address = contract_address
        self.connection_url = connection_url
        self.rpc_url = rpc_url
        self.dstack_socket = dstack_socket
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Initialize DStack client
        self.dstack = DstackClient(dstack_socket)
        
        # Contract ABI (minimal for our needs)
        self.contract_abi = [
            {
                "inputs": [{"name": "instanceId", "type": "string"}],
                "name": "registerInstance",
                "outputs": [],
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "instanceId", "type": "string"},
                    {"name": "derivedPublicKey", "type": "bytes"},
                    {"name": "appSignature", "type": "bytes"},
                    {"name": "kmsSignature", "type": "bytes"},
                    {"name": "connectionUrl", "type": "string"}
                ],
                "name": "registerPeer",
                "outputs": [],
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getPeerEndpoints",
                "outputs": [{"name": "", "type": "string[]"}],
                "type": "function"
            }
        ]
        
        self.contract = self.w3.eth.contract(
            address=contract_address,
            abi=self.contract_abi
        )
        
        self.instance_id = None
        self.registered = False
        
    async def register(self) -> bool:
        """
        Register this instance with the peer network.
        Auto-detects everything from TEE environment.
        Returns: Success boolean
        """
        try:
            # Get instance info from DStack
            info = self.dstack.info()
            self.instance_id = info.instance_id
            
            if not self.instance_id:
                logger.error("Could not get instance ID from dstack")
                return False
                
            logger.info(f"Registering instance {self.instance_id} with URL: {self.connection_url}")
            
            # Generate signature proof for peer registration
            sig_gen = SignatureProofGenerator(self.dstack_socket)
            
            # Create signature proof using correct API
            proof = sig_gen.generate_proof(self.instance_id, "ethereum/register", "ethereum")
            
            derived_public_key = proof.derived_public_key
            app_signature = proof.app_signature
            kms_signature = proof.kms_signature
            
            # Actually call registerPeer on contract
            logger.info(f"Calling registerPeer with connection URL: {self.connection_url}")
            logger.info(f"Instance ID: {self.instance_id}")
            logger.info(f"Derived public key: {derived_public_key.hex()}")
            logger.info(f"App signature: {app_signature.hex()}")
            logger.info(f"KMS signature: {kms_signature.hex()}")
            
            # Get the default account (first account from anvil)
            accounts = self.w3.eth.accounts
            if not accounts:
                logger.error("No accounts available for transaction")
                return False
                
            # Use first account as transaction sender
            tx_account = accounts[0]
            logger.info(f"Using account {tx_account} for transaction")
            
            # Call registerPeer function
            try:
                tx_hash = self.contract.functions.registerPeer(
                    self.instance_id,
                    derived_public_key,
                    app_signature,
                    kms_signature,
                    self.connection_url
                ).transact({'from': tx_account})
                
                # Wait for transaction receipt
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                logger.info(f"registerPeer transaction successful: {receipt.transactionHash.hex()}")
                
                self.registered = True
                return True
                
            except Exception as e:
                logger.error(f"registerPeer transaction failed: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False
    
    async def get_peers(self) -> List[str]:
        """
        Get current list of active peer endpoints.
        Returns: List of connection strings ready for applications
        """
        try:
            # Query contract for peer endpoints
            endpoints = self.contract.functions.getPeerEndpoints().call()
            
            logger.info(f"Retrieved {len(endpoints)} peer endpoints")
            return endpoints
            
        except Exception as e:
            logger.error(f"Failed to get peers: {e}")
            return []
    
    async def monitor_peers(self, callback):
        """
        Subscribe to peer list changes.
        Args:
            callback: Function called with new peer list when changes occur
        """
        # Simple polling implementation for now
        last_peers = []
        
        while True:
            try:
                current_peers = await self.get_peers()
                
                if current_peers != last_peers:
                    logger.info(f"Peer list changed: {current_peers}")
                    await callback(current_peers)
                    last_peers = current_peers
                    
                await asyncio.sleep(10)  # Poll every 10 seconds
                
            except Exception as e:
                logger.error(f"Monitor peers error: {e}")
                await asyncio.sleep(10)

# Demo usage
async def demo_p2p_usage():
    """Demo of the ultra-simple 3-line interface"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # The magical 3-line interface:
    # Production: sdk = DStackP2PSDK("0x123...", "https://abc123-443s.dstack-pha-prod7.phala.network")
    # Dev/Testing: 
    sdk = DStackP2PSDK("0x123...", "http://localhost:8080")
    success = await sdk.register()
    
    if success:
        peers = await sdk.get_peers()
        logger.info(f"Connected to cluster with peers: {peers}")
        
        # Example of using peers for application connectivity
        for peer in peers:
            logger.info(f"Could connect to: {peer}")
    else:
        logger.error("Failed to register with cluster")

if __name__ == "__main__":
    asyncio.run(demo_p2p_usage())