# Foundry Environment Setup Notes

## Key Setup Steps

1. **Docker Anvil Setup**
   ```bash
   docker run -d --name anvil -p 8545:8545 ghcr.io/foundry-rs/foundry:latest "anvil --host 0.0.0.0"
   ```
   
2. **Deploy with forge create**
   ```bash
   forge create src/Counter.sol:Counter --rpc-url http://localhost:8545 --private-key 0xac0... --broadcast
   ```

## Common Pitfalls

1. **Directory Issues**: Commands must be run from the `contracts/` directory where `foundry.toml` is located
   - `forge create`, `forge test`, etc. look for contracts in `src/` relative to current directory

2. **Docker Command Quoting**: 
   - ❌ `docker run ... anvil --host 0.0.0.0` (docker interprets --host)
   - ✅ `docker run ... "anvil --host 0.0.0.0"` (quotes pass entire command to container)

3. **Anvil Host Binding**: 
   - Default `127.0.0.1` only accessible from within container
   - Need `--host 0.0.0.0` to bind to all interfaces for external access

4. **forge create --broadcast**: 
   - Without `--broadcast` it's only a dry run
   - Must include to actually deploy

## Verification
- `docker logs anvil` shows transactions in real-time
- `forge create` succeeded on first try once setup was correct
- `cast` commands work seamlessly for contract interaction