# Forge/Anvil/Cast Capabilities Reference

## Forge - Smart Contract Development Toolkit

### Core Capabilities
- **Build**: Compile Solidity contracts with configurable compiler settings
- **Test**: Advanced testing framework with fuzzing, invariants, and gas reporting
- **Deploy**: Script-based deployment with transaction broadcasting
- **Verify**: Source code verification on block explorers
- **Debug**: Step-through debugging and trace analysis

### Key Features
- **Fast Compilation**: Parallel compilation with incremental builds
- **Comprehensive Testing**: Unit tests, fuzz tests, invariant tests
- **Gas Analysis**: Detailed gas usage reporting
- **Scripting**: Deployments and interactions via Solidity scripts
- **Formatting**: Code formatting with forge fmt

### Testing Features
- `vm.expectRevert()`: Test expected failures
- `vm.prank()`: Simulate calls from different addresses
- `makeAddr()`: Generate test addresses
- `vm.expectEmit()`: Verify event emissions
- Fuzz testing with automatic input generation
- Gas usage analysis and optimization

## Anvil - Local Ethereum Node

### Core Capabilities
- **Local Development**: Fast local blockchain for testing
- **Mainnet Forking**: Fork existing networks for testing
- **Account Management**: Pre-funded test accounts
- **State Control**: Load/dump blockchain state
- **JSON-RPC**: Full Ethereum JSON-RPC API compliance

### Key Features
- **Instant Mining**: Zero-latency transactions for fast development
- **Multiple Accounts**: Pre-configured test accounts with private keys
- **Network Forking**: Test against real network state
- **State Snapshots**: Save and restore blockchain state
- **Custom Configuration**: Configurable gas limits, block times, etc.

### Common Usage
```bash
anvil                          # Start with defaults
anvil --fork-url <URL>        # Fork mainnet/testnet
anvil --accounts 20           # Create 20 test accounts
anvil --balance 1000          # Set initial balance (ETH)
anvil --port 8546            # Custom port
```

## Cast - Command Line Interaction Tool

### Core Capabilities
- **Contract Calls**: Read and write contract functions
- **Transaction Management**: Send transactions and query status
- **Utility Functions**: Unit conversions, encoding/decoding
- **Network Interaction**: Works with any Ethereum-compatible network
- **Debugging**: Transaction tracing and analysis

### Key Features
- **Function Calls**: Direct contract interaction via CLI
- **Data Encoding**: ABI encoding/decoding utilities
- **Unit Conversion**: ETH/wei/gwei conversions
- **Address Utilities**: ENS resolution, checksum validation
- **Event Filtering**: Query and filter contract events

### Essential Commands
```bash
# Contract Interaction
cast call <address> <signature>                    # Read-only call
cast send <address> <signature> <args>            # State-changing tx
cast call <address> <signature> <args> --rpc-url <url>

# Data Utilities
cast --to-ascii <hex>                             # Hex to ASCII
cast --from-utf8 <text>                           # Text to hex
cast --to-wei <amount> <unit>                     # Convert to wei
cast --from-wei <amount> <unit>                   # Convert from wei

# Network Queries
cast balance <address>                            # Get ETH balance
cast nonce <address>                              # Get account nonce
cast block <number>                               # Get block info
cast tx <hash>                                    # Get transaction info

# Event Monitoring
cast logs <address>                               # Get contract events
cast logs --from-block <num> --to-block <num>    # Filter by block range
```

## Advanced Forge Features

### Fuzz Testing
```solidity
function testFuzz_Transfer(uint256 amount) public {
    // Automatically tests with various amount values
    vm.assume(amount <= 1000 ether);
    // Test logic here
}
```

### Invariant Testing
```solidity
contract InvariantTest is Test {
    function invariant_totalSupplyEqualsSum() public {
        // This should always be true
    }
}
```

### Cheatcodes (VM)
- `vm.prank(address)`: Next call from address
- `vm.startPrank(address)`: All calls from address until stopPrank
- `vm.warp(timestamp)`: Set block timestamp  
- `vm.roll(blockNumber)`: Set block number
- `vm.deal(address, amount)`: Set ETH balance
- `vm.expectRevert()`: Expect next call to revert

### Configuration (foundry.toml)
```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
optimizer = true
optimizer_runs = 200
via_ir = false
gas_reports = ["*"]

[rpc_endpoints]
mainnet = "https://eth-mainnet.alchemyapi.io/v2/..."
polygon = "https://polygon-mainnet.alchemyapi.io/v2/..."
```

## Best Practices

### Testing Strategy
1. Unit tests for individual functions
2. Integration tests for contract interactions
3. Fuzz tests for edge cases
4. Invariant tests for system properties
5. Gas optimization analysis

### Script Organization
1. Separate deployment and interaction scripts
2. Use environment variables for configuration
3. Log important addresses and values
4. Handle different network configurations

### Development Workflow
1. Write tests first (TDD approach)
2. Use Anvil for rapid iteration
3. Script deployments for reproducibility
4. Verify contracts on testnets before mainnet
5. Monitor gas usage throughout development

This reference covers the essential capabilities needed for smart contract development with the Foundry toolkit.