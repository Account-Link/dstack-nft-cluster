#!/usr/bin/env python3
"""
Verification script for dual simulator setup.
This script checks that both simulators can be started and accessed independently.
"""

import asyncio
import logging
import os
import sys
import subprocess
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DualSimulatorVerifier:
    def __init__(self):
        self.simulator1_dir = "./simulator"
        self.simulator2_dir = "./simulator2"
        self.socket1_path = "./simulator/dstack.sock"
        self.socket2_path = "./simulator2/dstack.sock"
        self.simulator1_process = None
        self.simulator2_process = None
    
    def check_directories(self) -> bool:
        """Check that both simulator directories exist with required files"""
        logger.info("Checking simulator directories...")
        
        for sim_dir, name in [(self.simulator1_dir, "Simulator 1"), (self.simulator2_dir, "Simulator 2")]:
            path = Path(sim_dir)
            if not path.exists():
                logger.error(f"❌ {name} directory not found: {sim_dir}")
                return False
            
            binary = path / "dstack-simulator"
            if not binary.exists():
                logger.error(f"❌ {name} binary not found: {binary}")
                return False
            
            if not binary.is_file():
                logger.error(f"❌ {name} binary is not a file: {binary}")
                return False
            
            logger.info(f"✅ {name} directory and binary found")
        
        return True
    
    def start_simulator(self, sim_dir: str, name: str) -> subprocess.Popen:
        """Start a simulator process"""
        try:
            logger.info(f"Starting {name}...")
            process = subprocess.Popen(
                ["./dstack-simulator"],
                cwd=sim_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for startup
            time.sleep(3)
            
            if process.poll() is None:
                logger.info(f"✅ {name} started successfully")
                return process
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ {name} failed to start:")
                logger.error(f"stdout: {stdout}")
                logger.error(f"stderr: {stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to start {name}: {e}")
            return None
    
    def stop_simulator(self, process: subprocess.Popen, name: str):
        """Stop a simulator process"""
        if process:
            logger.info(f"Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
                logger.info(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️  {name} didn't stop gracefully, forcing...")
                process.kill()
    
    async def test_socket_connectivity(self, socket_path: str, name: str) -> bool:
        """Test that we can connect to a socket"""
        max_retries = 15
        
        for attempt in range(max_retries):
            if os.path.exists(socket_path):
                try:
                    from dstack_sdk import DstackClient
                    client = DstackClient(socket_path)
                    info = client.info()
                    logger.info(f"✅ {name} socket connectivity verified")
                    logger.info(f"   Instance ID: {info.instance_id}")
                    return True
                except Exception as e:
                    logger.debug(f"{name} socket exists but not ready: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ {name} socket not ready (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(2)
        
        logger.error(f"❌ {name} socket never became ready")
        return False
    
    async def run_verification(self) -> bool:
        """Run the complete verification"""
        logger.info("🔍 Starting Dual Simulator Verification")
        
        try:
            # Step 1: Check directories
            if not self.check_directories():
                return False
            
            # Step 2: Start both simulators
            logger.info("Starting both simulators...")
            self.simulator1_process = self.start_simulator(self.simulator1_dir, "Simulator 1")
            if not self.simulator1_process:
                return False
            
            self.simulator2_process = self.start_simulator(self.simulator2_dir, "Simulator 2")
            if not self.simulator2_process:
                return False
            
            # Step 3: Test socket connectivity
            logger.info("Testing socket connectivity...")
            socket1_task = self.test_socket_connectivity(self.socket1_path, "Simulator 1")
            socket2_task = self.test_socket_connectivity(self.socket2_path, "Simulator 2")
            
            socket1_ok, socket2_ok = await asyncio.gather(socket1_task, socket2_task)
            
            if socket1_ok and socket2_ok:
                logger.info("🎉 VERIFICATION SUCCESSFUL!")
                logger.info("Both simulators are running independently and accessible")
                return True
            else:
                logger.error("❌ VERIFICATION FAILED!")
                logger.error("One or both simulators failed connectivity test")
                return False
                
        except Exception as e:
            logger.error(f"❌ Verification failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # Cleanup
            logger.info("Cleaning up...")
            self.stop_simulator(self.simulator1_process, "Simulator 1")
            self.stop_simulator(self.simulator2_process, "Simulator 2")

async def main():
    """Main entry point"""
    verifier = DualSimulatorVerifier()
    success = await verifier.run_verification()
    
    if success:
        logger.info("✅ Dual simulator setup is working correctly!")
        logger.info("You can now run: ./run_local_demo.sh")
    else:
        logger.error("❌ Dual simulator setup has issues")
        logger.error("Please check the error messages above")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
