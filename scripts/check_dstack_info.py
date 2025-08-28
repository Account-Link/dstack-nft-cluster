#!/usr/bin/env python3
"""
Check what information DStack client provides for instance-specific key derivation
"""

import sys
sys.path.append('.')

from dstack_sdk import DstackClient

def check_dstack_info():
    """Check DStack instance information"""
    print("Checking DStack instance information...")
    
    try:
        client = DstackClient('./simulator/dstack.sock')
        info = client.info()
        
        print(f"App Name: {info.app_name}")
        print(f"App ID: {info.app_id}")
        print(f"Instance ID: {info.instance_id}")
        print(f"Device ID: {info.device_id}")
        
        # Test instance-specific key derivation
        instance_path = f"instance/{info.instance_id}"
        print(f"\nTesting instance-specific key path: {instance_path}")
        
        key_response = client.get_key(instance_path, "ethereum")
        from dstack_sdk.ethereum import to_account_secure
        account = to_account_secure(key_response)
        
        print(f"Instance-derived address: {account.address}")
        print(f"This address should be unique per DStack instance")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_dstack_info()