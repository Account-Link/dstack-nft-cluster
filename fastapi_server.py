#!/usr/bin/env python3
"""
FastAPI Server for DStack P2P Cluster Management

Provides REST API endpoints to interact with the dstack P2P SDK:
- GET /peers - List all active peers in the cluster
- GET /health - Health check endpoint
- GET /info - Instance information
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
import uvicorn

from dstack_cluster import DStackP2PSDK
from eth_account import Account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global SDK instance
sdk: Optional[DStackP2PSDK] = None


async def mint_nft_if_needed(sdk_instance: DStackP2PSDK) -> bool:
    """
    Check if the NFT owner address already has an NFT, and mint one if needed.
    
    This implements the CORRECT approach where the NFT Owner Address (the address
    with the private key) owns the NFT, not a derived "instance address".
    
    Returns: True if NFT exists or was successfully minted, False otherwise
    """
    try:
        private_key = os.environ["PRIVATE_KEY"]
        account = Account.from_key(private_key)
        nft_owner_address = account.address
        
        logger.info(f"Checking NFT status for owner address: {nft_owner_address}")
        
        # Check if this address already has an NFT
        # try:
        #     token_id = sdk_instance.contract.functions.walletToTokenId(nft_owner_address).call()
            
        #     if token_id > 0:
        #         logger.info(f"Address already has NFT with token ID: {token_id}")
        #         return True
            
        # except Exception as e:
        #     logger.warning(f"Could not check existing NFT status: {e}")
        
        # Get instance ID for the NFT metadata
        info = sdk_instance.dstack.info()
        instance_id = info.instance_id
        
        if not instance_id:
            logger.error("Could not get instance ID from dstack")
            return False
        
        logger.info(f"Minting NFT for owner address {nft_owner_address} with instance ID: {instance_id}")
        
        # Build and send mint transaction
        mint_function = sdk_instance.contract.functions.mintNodeAccess(
            nft_owner_address,  # The NFT owner address (NOT derived from instance)
            instance_id         # Instance ID as metadata
        )
        
        # Build transaction
        tx = mint_function.build_transaction({
            'from': nft_owner_address,
            'nonce': sdk_instance.w3.eth.get_transaction_count(nft_owner_address),
            'gas': 2000000,
            'gasPrice': sdk_instance.w3.eth.gas_price,
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(tx)
        tx_hash = sdk_instance.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for confirmation
        receipt = sdk_instance.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            logger.info(f"NFT minted successfully! Transaction: {receipt['transactionHash'].hex()}")
            
            # Verify NFT was minted
            token_id = sdk_instance.contract.functions.walletToTokenId(nft_owner_address).call()
            logger.info(f"Verified NFT minted with token ID: {token_id}")
            
            return True
        else:
            logger.error(f"NFT minting transaction failed: {receipt['transactionHash'].hex()}")
            return False
            
    except Exception as e:
        logger.error(f"NFT minting failed: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown"""
    global sdk
    
    # Startup
    logger.info("Starting DStack P2P FastAPI Server...")
    
    # Get configuration from environment variables
    contract_address = os.environ.get("CONTRACT_ADDRESS", "0x33e081c002288F3301f48a5237D6b7e8703C39a3")
    connection_url = os.environ.get("CONNECTION_URL", "http://localhost:8080")
    rpc_url = os.environ.get("RPC_URL", "https://base.llamarpc.com")
    
    # Smart socket detection for different environments
    socket_paths = [
        "/var/run/dstack.sock",          # Phala Cloud production
        "./simulator/dstack.sock",       # Local development
        "/app/simulator/dstack.sock",    # Docker container
        "/tmp/dstack.sock"               # Alternative location
    ]
    
    dstack_socket = None
    for path in socket_paths:
        if os.path.exists(path):
            dstack_socket = path
            logger.info(f"Found DStack socket at: {path}")
            break
    
    if not dstack_socket:
        logger.warning("No DStack socket found. Using default path.")
        dstack_socket = "/var/run/dstack.sock"
    
    logger.info("Initializing DStack P2P SDK...")
    logger.info(f"Contract: {contract_address}")
    logger.info(f"Connection URL: {connection_url}")
    logger.info(f"RPC URL: {rpc_url}")
    logger.info(f"DStack Socket: {dstack_socket}")
    
    try:
        # Initialize SDK
        sdk = DStackP2PSDK(contract_address, connection_url, rpc_url, dstack_socket)
        
        # Wait for DStack agent to be ready
        max_retries = 30
        for attempt in range(max_retries):
            try:
                from dstack_sdk import DstackClient
                test_client = DstackClient(dstack_socket)
                test_client.info()
                logger.info(f"DStack agent ready after {attempt + 1} attempts")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.info(f"DStack agent not ready (attempt {attempt + 1}/{max_retries}), waiting...")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"DStack agent never became ready: {e}")
                    raise
        
        # Mint NFT and register with the cluster if PRIVATE_KEY is provided
        if os.environ.get("PRIVATE_KEY"):
            logger.info("PRIVATE_KEY provided - attempting NFT minting and registration...")
            
            # First, check if NFT already exists and mint if needed
            mint_success = await mint_nft_if_needed(sdk)
            if mint_success:
                logger.info("NFT minting completed successfully")
            else:
                logger.warning("NFT minting failed - continuing anyway")

            logger.info("Sleeping for 10 seconds...")
            time.sleep(10)
            
            # Then register with the P2P cluster
            logger.info("Registering with P2P cluster...")
            success = await sdk.register()
            if success:
                logger.info("Successfully registered with P2P cluster")
            else:
                logger.warning("Failed to register with P2P cluster - continuing anyway")
        else:
            logger.info("No PRIVATE_KEY provided - running in read-only mode")
            
    except Exception as e:
        logger.error(f"Failed to initialize SDK: {e}")
        # Continue anyway for basic functionality
        
    yield
    
    # Shutdown
    logger.info("Shutting down DStack P2P FastAPI Server...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="DStack P2P Cluster API",
    description="REST API for DStack P2P cluster management and peer discovery",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint with basic API information"""
    return {
        "message": "DStack P2P Cluster API",
        "version": "1.0.0",
        "endpoints": {
            "/peers": "List all active peers",
            "/health": "Health check",
            "/info": "Instance information",
            "/mint-nft": "Mint NFT for this instance",
            "/register": "Register with P2P cluster (includes NFT minting)",
            "/docs": "API documentation"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "sdk_initialized": sdk is not None
    }


@app.get("/peers")
async def list_peers() -> Dict[str, Any]:
    """
    List all active peers in the cluster
    
    Returns:
        Dict containing peer list and metadata
    """
    if not sdk:
        raise HTTPException(status_code=503, detail="SDK not initialized")
    
    try:
        peers = await sdk.get_peers()
        
        return {
            "peers": peers,
            "count": len(peers),
            "timestamp": time.time(),
            "instance_id": getattr(sdk, 'instance_id', None)
        }
        
    except Exception as e:
        logger.error(f"Failed to get peers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve peers: {str(e)}")


@app.get("/info")
async def instance_info() -> Dict[str, Any]:
    """
    Get information about this instance
    
    Returns:
        Dict containing instance information
    """
    if not sdk:
        raise HTTPException(status_code=503, detail="SDK not initialized")
    
    try:
        info = {
            "instance_id": getattr(sdk, 'instance_id', None),
            "connection_url": getattr(sdk, 'connection_url', None),
            "contract_address": getattr(sdk, 'contract_address', None),
            "rpc_url": getattr(sdk, 'rpc_url', None),
            "registered": getattr(sdk, 'registered', False),
            "timestamp": time.time()
        }
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get instance info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve instance info: {str(e)}")


@app.post("/mint-nft")
async def mint_nft():
    """
    Mint NFT for this instance's owner address
    
    Requires PRIVATE_KEY environment variable to be set.
    This implements the CORRECT approach where the NFT Owner Address owns the NFT.
    """
    if not sdk:
        raise HTTPException(status_code=503, detail="SDK not initialized")
    
    if not os.environ.get("PRIVATE_KEY"):
        raise HTTPException(status_code=400, detail="PRIVATE_KEY environment variable required for NFT minting")
    
    try:
        success = await mint_nft_if_needed(sdk)
        
        if success:
            # Get owner address and token info
            private_key = os.environ["PRIVATE_KEY"]
            account = Account.from_key(private_key)
            nft_owner_address = account.address
            token_id = sdk.contract.functions.walletToTokenId(nft_owner_address).call()
            
            return {
                "status": "success",
                "message": "NFT minting completed successfully",
                "owner_address": nft_owner_address,
                "token_id": int(token_id),
                "instance_id": getattr(sdk, 'instance_id', None),
                "timestamp": time.time()
            }
        else:
            raise HTTPException(status_code=500, detail="NFT minting failed")
            
    except Exception as e:
        logger.error(f"NFT minting failed: {e}")
        raise HTTPException(status_code=500, detail=f"NFT minting failed: {str(e)}")


@app.post("/register")
async def register():
    """
    Register this instance with the P2P cluster
    
    This will first attempt to mint an NFT if needed, then register the instance.
    Requires PRIVATE_KEY environment variable to be set.
    """
    if not sdk:
        raise HTTPException(status_code=503, detail="SDK not initialized")
    
    if not os.environ.get("PRIVATE_KEY"):
        raise HTTPException(status_code=400, detail="PRIVATE_KEY environment variable required for registration")
    
    try:
        # First ensure NFT is minted
        mint_success = await mint_nft_if_needed(sdk)
        if not mint_success:
            logger.warning("NFT minting failed, but continuing with registration")
        
        # Then register with the cluster
        success = await sdk.register()
        
        if success:
            return {
                "status": "success",
                "message": "Successfully registered with P2P cluster",
                # "nft_minted": mint_success,
                "instance_id": getattr(sdk, 'instance_id', None),
                "timestamp": time.time()
            }
        else:
            raise HTTPException(status_code=500, detail="Registration failed")
            
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/register-instance")
async def register_instance():
    """
    Register this instance with the P2P cluster
    
    This will first attempt to mint an NFT if needed, then register the instance.
    Requires PRIVATE_KEY environment variable to be set.
    """
    if not sdk:
        raise HTTPException(status_code=503, detail="SDK not initialized")
    
    if not os.environ.get("PRIVATE_KEY"):
        raise HTTPException(status_code=400, detail="PRIVATE_KEY environment variable required for registration")
    
    try:
        # Then register with the cluster
        success = await sdk.register_instance()
        
        if success:
            return {
                "status": "success",
                "message": "Successfully registered instance with P2P cluster",
                # "nft_minted": mint_success,
                "instance_id": getattr(sdk, 'instance_id', None),
                "timestamp": time.time()
            }
        else:
            raise HTTPException(status_code=500, detail="Registration failed")
            
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")



@app.post("/register-peer")
async def register_peer():
    """
    Register this peer with the P2P cluster
    
    This will first attempt to mint an NFT if needed, then register the instance.
    Requires PRIVATE_KEY environment variable to be set.
    """
    if not sdk:
        raise HTTPException(status_code=503, detail="SDK not initialized")
    
    if not os.environ.get("PRIVATE_KEY"):
        raise HTTPException(status_code=400, detail="PRIVATE_KEY environment variable required for registration")
    
    try:
        # Then register with the cluster
        success = await sdk.register_peer()
        
        if success:
            return {
                "status": "success",
                "message": "Successfully registered peer with P2P cluster",
                # "nft_minted": mint_success,
                "instance_id": getattr(sdk, 'instance_id', None),
                "timestamp": time.time()
            }
        else:
            raise HTTPException(status_code=500, detail="Registration failed")
            
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

def main():
    """Main entry point for the FastAPI server"""
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"Starting FastAPI server on {host}:{port}")
    
    uvicorn.run(
        "fastapi_server:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
