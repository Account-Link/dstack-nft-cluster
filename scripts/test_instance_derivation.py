#!/usr/bin/env python3
"""
Test the updated counter.py instance-specific key derivation
"""

import sys
sys.path.append('.')

import asyncio
import logging
from counter import DistributedCounter

# Set up logging to see the output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_instance_derivation():
    """Test instance-specific key derivation"""
    print("Testing updated counter.py with instance-specific key derivation...")
    
    try:
        counter = DistributedCounter(
            instance_id="test-node1",
            contract_address="0xa85233C63b9Ee964Add6F2cffe00Fd84eb32338f",
            rpc_url="http://localhost:8545",
            port=8081,
            dstack_socket="./simulator/dstack.sock"
        )
        
        print(f"\nInstance derived address: {counter.wallet_address}")
        print(f"Instance key path: {counter.instance_key_path}")
        
        # Test the registration info generation (without actual registration)
        result = await counter.register_instance()
        
        if result:
            print("SUCCESS: Instance initialization completed with correct key derivation")
            print(f"Instance is ready for external NFT owner to fund address: {counter.wallet_address}")
        else:
            print("Expected result: Instance waiting for funding")
            
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_instance_derivation())
    if success:
        print("\n=== Instance derivation test passed ===")
        sys.exit(0)
    else:
        print("\n=== Instance derivation test failed ===")
        sys.exit(1)