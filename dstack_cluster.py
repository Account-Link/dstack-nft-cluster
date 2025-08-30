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
                    {"name": "appPublicKey", "type": "bytes"},
                    {"name": "appSignature", "type": "bytes"},
                    {"name": "kmsSignature", "type": "bytes"},
                    {"name": "connectionUrl", "type": "string"},
                    {"name": "purpose", "type": "string"},
                    {"name": "appId", "type": "bytes32"}
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
            proof = sig_gen.generate_proof("wallet/ethereum", "ethereum")
            
            app_signature = proof.app_signature
            kms_signature = proof.kms_signature
            app_id = proof.app_id
            
            # Get app public key from signature verification
            from eth_keys import keys
            from eth_utils import keccak
            from eth_account import Account
            derived_pubkey_sec1 = keys.PrivateKey(proof.derived_private_key).public_key.to_compressed_bytes()
            app_message = f"ethereum:{derived_pubkey_sec1.hex()}"
            app_message_hash = keccak(bytes(app_message, 'utf-8'))  # Use raw keccak256 like the contract
            app_signature_obj = keys.Signature(app_signature)
            app_pubkey_sec1 = app_signature_obj.recover_public_key_from_msg_hash(app_message_hash).to_compressed_bytes()
            
            
            # Convert app_id to bytes32
            app_id_bytes32 = bytes.fromhex(app_id.replace('0x', '')).ljust(32, b'\x00')[:32]
            
            # Actually call registerPeer on contract
            logger.info(f"Calling registerPeer with connection URL: {self.connection_url}")
            logger.info(f"Instance ID: {self.instance_id}")
            logger.info(f"Derived public key: {derived_pubkey_sec1.hex()}")
            logger.info(f"App public key: {app_pubkey_sec1.hex()}")
            logger.info(f"App signature: {app_signature.hex()}")
            logger.info(f"KMS signature: {kms_signature.hex()}")
            logger.info(f"App ID: {app_id}")
            logger.info(f"App ID bytes32: {app_id_bytes32.hex()}")
            
            # Get the default account (first account from anvil)
            accounts = self.w3.eth.accounts
            if not accounts:
                logger.error("No accounts available for transaction")
                return False
                
            # Use first account as transaction sender
            tx_account = accounts[0]
            logger.info(f"Using account {tx_account} for transaction")
            
            # First register the instance if not already registered
            try:
                logger.info(f"Registering instance {self.instance_id}")
                instance_tx = self.contract.functions.registerInstance(self.instance_id).transact({'from': tx_account})
                instance_receipt = self.w3.eth.wait_for_transaction_receipt(instance_tx)
                logger.info(f"registerInstance transaction successful: {instance_receipt.transactionHash.hex()}")
            except Exception as e:
                logger.warning(f"registerInstance failed (may already be registered): {e}")
            
            # Call registerPeer function
            try:
                tx_hash = self.contract.functions.registerPeer(
                    self.instance_id,
                    derived_pubkey_sec1,  # derived public key (SEC1 compressed)
                    app_pubkey_sec1,      # app public key (SEC1 compressed)
                    app_signature,
                    kms_signature,
                    self.connection_url,
                    "ethereum",           # purpose
                    app_id_bytes32        # app ID as bytes32
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

async def demo_p2p_usage():
    logging.basicConfig(level=logging.INFO)
    
    # Production: sdk = DStackP2PSDK("0x123...", "https://abc123-443s.dstack-pha-prod7.phala.network")
    # Dev/Testing: 
    sdk = DStackP2PSDK("0x5067457698Fd6Fa1C6964e416b3f42713513B3dD", "http://localhost:8080")
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
