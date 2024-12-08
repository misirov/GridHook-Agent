# Grid Trading Bot for Uniswap v4

An interactive bot that helps you manage grid trading positions using Uniswap v4's hooks. Communicate with smart contracts using natural language!

## Features

### Natural Language Trading Terminal
```
User: "what is my balance?"
Bot: "Your balances:
• 98,422.022655 TK0 (Token0)
• 99,916.167762 TK1 (Token1)
• 9,999.981657 ETH"

User: "create position 100 token0 for token1 at tick 60"
Bot: "Position created! Transaction: 0xcfd568a..."

User: "swap 100 token0 for token1"
Bot: "Swap successful! 
Swap Summary:
100.000000 token0 for 98.234567 token1"
```

### Available Commands
- Check balances: `what is my balance`, `show gridhook balance`, `check pool balance`
- Create positions: `create position [amount] token0/token1 for token1/token0 at tick [tick]`
- Execute swaps: `swap [amount] token0/token1 for token1/token0`
- View permissions: `what gridhook permissions exist?`
- Check positions: `how many open orders do we have?`

### Technical Details
- Pool fee: 0.1% (1000)
- Default grid size: 0.1
- Default grid spacing: 200 ticks
- Tick spacing: 60

## Quick Start

### Local Development
1. Start Anvil:
```bash
anvil
```

2. Deploy contracts:
```bash
forge script script/Deploy.s.sol --broadcast \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```

3. Start the bot:
```bash
python src/main.py
```

### Docker Setup
1. Create a `.env` file:
```bash
OPENAI_API_KEY=your_key_here
```

2. Build and run:
```bash
docker-compose up --build
```

This will:
- Install Foundry
- Start Anvil
- Run tests
- Deploy contracts
- Start interactive bot

## Contract Addresses (Local)
- Grid Hook: 0x9D71E6f99da38505b3c50cb0ec2ed754Ea13D040
- Pool Swap Test: 0xdc64a140aa3e981100a9beca4e685f962f0cf6c9
- Pool Manager: 0x5fbdb2315678afecb367f032d93f642f64180aa3
- Token0: 0x0165878A594ca255338adfa4d48449f69242Eb8F
- Token1: 0xa513E6E4b8f2a923D98304ec87F64353C4D5C853

## How Grid Trading Works
- Price Range: Define upper and lower price limits
- Grid Lines: Range divided into equally spaced price levels
- Order Placement: Buy orders below current price, sell orders above
- Profit Generation: Buy low, sell high within small movements

### Example Grid Setup
```
Range: $40,000 - $42,000
Grid spacing: $200
At $41,000:
- Buy orders: $40,800, $40,600, $40,400...
- Sell orders: $41,200, $41,400, $41,600...
```

### Key Considerations
- Works best in sideways/ranging markets
- Requires sufficient funds for multiple orders
- Risk of holding positions outside range
- Grid spacing affects profit per trade vs frequency
- Fee considerations for profitability

## Development

### Contract ABIs
Located in `/out/CONTRACT_NAME/contract_name.json`

### Testing
```bash
forge test -vvv
```

## Future Enhancements
- Strategy analysis and recommendations
- Risk management features
- Portfolio optimization
- Automated grid rebalancing
- Multi-platform support (Discord, Telegram)