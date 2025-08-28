# Python Contract Interaction Guide

This guide demonstrates how to interact with the Counter/Bulletin Board contract using Python and Web3.py.

## Setup

### 1. Prerequisites
- Python 3.10+
- Running Anvil instance on localhost:8545
- Deployed Counter contract

### 2. Environment Setup
```bash
# Create virtual environment
python3.10 -m venv venv

# Install dependencies
./venv/bin/pip install web3 eth-account
```

### 3. Configuration
Update the following variables in `counter_interaction.py`:
- `CONTRACT_ADDRESS`: Address of deployed contract
- `PRIVATE_KEY`: Private key for transactions
- `RPC_URL`: Anvil RPC endpoint (default: http://localhost:8545)

## Features

### Read Functions
- `get_count()`: Returns current message count
- `get_message(index)`: Returns message at specific index (1-based)
- `get_latest_message()`: Returns the most recent message
- `get_poster(index)`: Returns address that posted message at index
- `display_all_messages()`: Shows all messages with posters

### Write Functions
- `increment(message)`: Posts new message and increments counter
- Returns transaction details: hash, block number, gas used

## Usage Examples

### Basic Usage
```python
from counter_interaction import CounterContract

# Initialize contract
counter = CounterContract()

# Read current state
count = counter.get_count()
print(f"Current count: {count}")

# Post a message
result = counter.increment("Hello from Python!")
print(f"Transaction hash: {result['tx_hash']}")

# Read all messages
counter.display_all_messages()
```

### Interactive Script
Run the full interactive interface:
```bash
./venv/bin/python counter_interaction.py
```

### Test Script
Run automated tests:
```bash
./venv/bin/python test_counter.py
```

## Key Components

### Web3 Connection
```python
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
```

### Contract Instance
```python
contract = w3.eth.contract(
    address=Web3.to_checksum_address(contract_address),
    abi=CONTRACT_ABI
)
```

### Transaction Signing
```python
from eth_account import Account
account = Account.from_key(private_key)

transaction = contract.functions.increment(message).build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 200000,
    'gasPrice': w3.to_wei('20', 'gwei'),
})

signed_txn = account.sign_transaction(transaction)
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
```

## Error Handling

The script includes comprehensive error handling:
- Connection failures to RPC endpoint
- Invalid contract addresses
- Transaction failures
- Invalid message indices

## Contract ABI

The script includes the complete ABI for the Counter contract with all functions and events:
- Read functions (view/pure)
- Write functions (state-changing)
- Events for transaction monitoring

## Demo Results

Successful test run shows:
```
Connected to contract at 0x5FbDB2315678afecb367f032d93F642f64180aa3
Current count: 2
Latest message: Second message from account 2!
Posting message: Hello from Python! 🐍
✅ Success! TX: 588b8936ac9c1279b1bc4e31131e305b63dad57f37f1086a8c0bdeb953c60dae
Block: 4, Gas: 75866
```

## Next Steps

1. **Event Monitoring**: Add event listening for real-time updates
2. **Multiple Accounts**: Support for multiple signing accounts
3. **Batch Operations**: Multiple message posting in single transaction
4. **Error Recovery**: Retry mechanisms for failed transactions
5. **Gas Optimization**: Dynamic gas price estimation

The Python interface provides a complete programmatic way to interact with the Counter contract, complementing the Cast CLI tools for different use cases.