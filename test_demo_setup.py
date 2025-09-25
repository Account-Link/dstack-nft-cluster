#!/usr/bin/env python3
"""
Test script to verify the two-node demo setup is working correctly.
"""

import os
import sys
import asyncio
import logging
from demo_two_nodes import TwoNodeDemo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_setup():
    """Test that the demo setup is working"""
    
    # Check environment variables
    if not os.environ.get("PRIVATE_KEY"):
        logger.error("PRIVATE_KEY environment variable is required")
        return False
    
    # Check that simulator directory exists
    if not os.path.exists("simulator"):
        logger.error("simulator directory not found")
        return False
    
    # Check that shared socket file exists (if containers/simulator are running)
    shared_socket_exists = os.path.exists("simulator/dstack.sock")
    
    logger.info(f"Shared socket exists: {shared_socket_exists}")
    
    if not shared_socket_exists:
        logger.warning("DStack socket not found - make sure containers or local simulator is running")
        logger.info("Run: ./start_two_node_demo.sh (for Docker) or ./run_local_demo.sh (for local)")
        return False
    
    # Try to initialize the demo
    try:
        demo = TwoNodeDemo()
        await demo.initialize_nodes()
        logger.info("✅ Demo setup test passed!")
        return True
    except Exception as e:
        logger.error(f"❌ Demo setup test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_setup())
    sys.exit(0 if success else 1)
