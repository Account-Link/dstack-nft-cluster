# Forge Test Environment - Agent Practice Guide

This guide provides hands-on practice with Foundry's Forge, Anvil, and Cast tools using a Counter/Bulletin Board contract.

## Contract Overview

The Counter contract serves as a simple bulletin board where:
- Users can increment a counter and post a message
- Messages are stored with their index and poster address
- Events are emitted for each interaction

## Quick Start

### 1. Setup and Testing
```bash
cd contracts
forge test                    # Run all tests
forge test -vv               # Verbose output
forge test --gas-report      # Show gas usage
```

### 2. Start Local Blockchain
```bash
anvil                         # Start local node (keep running)
```

### 3. Deploy Contract
```bash
# In new terminal
forge script script/Counter.s.sol --rpc-url http://localhost:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast
```

### 4. Interactive Contract Usage

#### Using Cast Commands
```bash
# Set environment variables (replace with actual deployed address)
export CONTRACT_ADDRESS=0x...

# Read current count
cast call $CONTRACT_ADDRESS "getCount()"

# Increment with message (requires private key)
cast send $CONTRACT_ADDRESS "increment(string)" "Hello from Cast!" --rpc-url http://localhost:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# Read specific message
cast call $CONTRACT_ADDRESS "getMessage(uint256)" 1

# Read latest message
cast call $CONTRACT_ADDRESS "getLatestMessage()"

# Read poster address
cast call $CONTRACT_ADDRESS "getPoster(uint256)" 1

# Convert hex output to string
cast --to-ascii 0x48656c6c6f20576f726c6421
```

#### Using Forge Scripts
```bash
# Deploy and interact
forge script script/Counter.s.sol --rpc-url http://localhost:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast

# Post message using script
COUNTER_ADDRESS=0x... MESSAGE="Script message!" forge script script/Interact.s.sol --rpc-url http://localhost:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --broadcast

# Read all messages
COUNTER_ADDRESS=0x... forge script script/Read.s.sol --rpc-url http://localhost:8545
```

## Practice Exercises

### Exercise 1: Basic Operations
1. Deploy the contract
2. Post 3 different messages from different addresses
3. Read all messages and verify posters

### Exercise 2: Testing Edge Cases
1. Try reading messages before any are posted
2. Try reading invalid message indices
3. Verify events are emitted correctly

### Exercise 3: Gas Analysis
1. Compare gas costs of different message lengths
2. Analyze gas usage for multiple increments
3. Use forge test --gas-report

### Exercise 4: Advanced Interactions
1. Use multiple Anvil accounts
2. Create a script that posts messages in a loop
3. Monitor events using cast logs

## Key Commands Reference

### Forge Commands
```bash
forge build                  # Compile contracts
forge test                   # Run tests
forge test -vv              # Verbose test output
forge script <script>       # Run deployment scripts
forge create <contract>     # Deploy single contract
```

### Anvil Commands
```bash
anvil                       # Start local node
anvil --fork-url <url>     # Fork existing network
anvil --accounts 20        # Create 20 test accounts
anvil --balance 1000       # Set account balance
```

### Cast Commands
```bash
cast call <addr> <sig>     # Read-only contract call
cast send <addr> <sig>     # State-changing transaction
cast balance <addr>        # Get address balance
cast nonce <addr>          # Get address nonce
cast logs <addr>           # Get contract events
cast --to-ascii <hex>      # Convert hex to ASCII
cast --from-utf8 <text>    # Convert text to hex
```

## Troubleshooting

### Common Issues
1. **"Invalid signature"**: Check function signature format
2. **"Insufficient funds"**: Use Anvil's funded test accounts
3. **"Contract not found"**: Verify contract address is correct
4. **"Invalid index"**: Message indices start from 1, not 0

### Useful Debug Commands
```bash
cast call $CONTRACT_ADDRESS "getCount()" --rpc-url http://localhost:8545
cast balance 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --rpc-url http://localhost:8545
cast nonce 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 --rpc-url http://localhost:8545
```

## Next Steps

After mastering this environment:
1. Modify the contract to add new features
2. Create more complex interaction scripts
3. Experiment with different Anvil configurations
4. Practice with mainnet forking
5. Explore Forge's advanced testing features (fuzzing, invariants)