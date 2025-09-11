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

from web3 import Web3

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
            
            # Get transaction account from private key
            import os
            private_key = os.environ["PRIVATE_KEY"]  # Required
            
            from eth_account import Account
            account = Account.from_key(private_key)
            tx_account = account.address
            logger.info(f"Using private key account {tx_account} for transaction")
            
            # Helper function to send transaction
            def send_transaction(contract_function, description):
                # Build and sign transaction with private key
                tx = contract_function.build_transaction({
                    'from': tx_account,
                    'nonce': self.w3.eth.get_transaction_count(tx_account),
                    'gas': 2000000,
                    'gasPrice': self.w3.eth.gas_price,
                })
                signed_tx = account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                logger.info(f"{description} transaction successful: {receipt.transactionHash.hex()}")
                return receipt
            
            # First register the instance if not already registered
            try:
                logger.info(f"Registering instance {self.instance_id}")
                send_transaction(
                    self.contract.functions.registerInstance(self.instance_id),
                    "registerInstance"
                )
            except Exception as e:
                logger.warning(f"registerInstance failed (may already be registered): {e}")
            
            # Call registerPeer function
            try:
                send_transaction(
                    self.contract.functions.registerPeer(
                        self.instance_id,
                        derived_pubkey_sec1,  # derived public key (SEC1 compressed)
                        app_pubkey_sec1,      # app public key (SEC1 compressed)
                        app_signature,
                        kms_signature,
                        self.connection_url,
                        "ethereum",           # purpose
                        app_id_bytes32        # app ID as bytes32
                    ),
                    "registerPeer"
                )
                
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
    import os
    logging.basicConfig(level=logging.INFO)
    
    # Use environment variables
    contract_address = os.environ.get("CONTRACT_ADDRESS", "0x9d22D844690ff89ea5e8a6bb4Ca3F7DAc83a40c3")
    connection_url = os.environ.get("CONNECTION_URL", "https://dstack-node.phala.network")
    rpc_url = os.environ.get("RPC_URL", "https://base.llamarpc.com")
    
    # Smart socket detection for different environments
    # Try different socket paths in order of preference
    socket_paths = [
        "/var/run/dstack.sock",          # Phala Cloud production
        "./simulator/dstack.sock",       # Local development
        "/app/simulator/dstack.sock",    # Docker container
        "/tmp/dstack.sock"               # Alternative location
    ]
    
    for path in socket_paths:
        if os.path.exists(path):
            dstack_socket = path
            logger.info(f"Found DStack socket at: {path}")
            break
    
    if not dstack_socket:
        logger.error("No DStack socket found. Tried paths:")
        for path in socket_paths:
            logger.error(f"  - {path} (not found)")
        dstack_socket = "/var/run/dstack.sock"  # Default fallback
    
    logger.info(f"Initializing DStack P2P SDK...")
    logger.info(f"Contract: {contract_address}")
    logger.info(f"Connection URL: {connection_url}")
    logger.info(f"RPC URL: {rpc_url}")
    logger.info(f"DStack Socket: {dstack_socket}")
    
    # Wait for DStack agent to be ready (Phala Cloud startup timing)
    import time
    max_retries = 30
    for attempt in range(max_retries):
        try:
            # Test DStack connection first
            from dstack_sdk import DstackClient
            test_client = DstackClient(dstack_socket)
            test_client.info()  # This will fail if agent not ready
            logger.info(f"DStack agent ready after {attempt + 1} attempts")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.info(f"DStack agent not ready (attempt {attempt + 1}/{max_retries}), waiting...")
                time.sleep(2)
            else:
                logger.error(f"DStack agent never became ready: {e}")
                return
    
    try:
        sdk = DStackP2PSDK(contract_address, connection_url, rpc_url, dstack_socket)
        success = await sdk.register()
        
        if success:
            peers = await sdk.get_peers()
            logger.info(f"Connected to cluster with peers: {peers}")
            
            # Example of using peers for application connectivity
            for peer in peers:
                logger.info(f"Could connect to: {peer}")
        else:
            logger.error("Failed to register with cluster")
            
    except ConnectionRefusedError:
        logger.error("Could not connect to DStack socket - check if DStack agent is running")
        logger.error(f"Tried socket path: {dstack_socket}")
        logger.error("On Phala Cloud, ensure volume mount: /var/run/dstack.sock:/var/run/dstack.sock")
    except FileNotFoundError:
        logger.error(f"DStack socket not found at: {dstack_socket}")
        logger.error("Check if DStack agent is properly installed and running")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_p2p_usage())
