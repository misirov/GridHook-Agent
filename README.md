# Grid Trading Bot for Uniswap v4

An interactive bot that helps you manage grid trading positions using Uniswap v4's hooks. Communicate with smart contracts using natural language!

## Demo

Check video demo here! 
- https://x.com/p_misirov/status/1865670128412619070

Check website here!
- https://grid-orders-hook.webflow.io/#initial

Some fun interactions
```
> hello! lets do some trading! are there any open positions on the gridhook?

Assistant: Hello! It looks like there are currently no open positions on the Grid Hook. Would you like to create a new position or explore other operations?

> cool! lets open a buy order for 100 token0 at tick 60

Assistant: Your buy order for 100 Token0 at tick 60 has been successfully placed!  🎉 If you want to manage or view this position in the future, just let me know. Is there anything else you'd like to do?

> and also... a sell order for 200 token1 at tick -60

Assistant: Your buy order for 100 token0 at tick 60 has been successfully placed with transaction hash 0x78794396d9cfff84eec7ea02f8512df5e0f5980ba8153fd165c784db29436fca.
And, your sell order for 200 token1 at tick -60 has also been processed successfully with transaction hash 0x208622e54a7cf98cf8b0212ee819baf4ed1f0d96f9b9b3ba3a9040406eb9b6a8.
Would you like to check the status of your positions or perform any other operations?

> amazing, can i see my orders?

Assistant: Here are your current orders:
1. **Sell Order for token0 at tick -60:**
   - Position ID: 98503915914194906783043586618936865486115098976371611728845358547292137225057
   - Pending order amount: 200.0000 tokens (token0)
   - Claimable output tokens (token1): 0.0000 tokens
   - You have a total of 200.0000 tokens (token0) in this order awaiting to be sold.

2. **Sell Order for token1 at tick 60:**
   - Position ID: 42787834252947494562182276410994600832354159539974871410613245068748826899716
   - Pending order amount: 100.0000 tokens (token1)
   - Claimable output tokens (token0): 0.0000 tokens
   - You have a total of 100.0000 tokens (token1) in this order awaiting to be sold.

Let me know if you would like to perform more operations or need assistance with anything else!

> great!! what is my current balance by the way?

Assistant: Your current balances are:
- 99,598.991951 MockA (Token0)
- 99,701.000000 MockB (Token1)
- 9,999.986737 ETH
Looks like you're well-stocked to continue trading!

> nice, lets swap 1 token0 for token1

Assistant: Your swap of 1 Token0 for Token1 was successful! 🎉
Would you like to perform any other operations or check on the status of your positions again?

> i want to know the difference between my current balance and the previous one

Assistant: After the swap transaction:
- **Token0 (MockA):** You used 1 Token0 for the swap. Your balance changed from 99598.991951 to 99597.991951.
- **Token1 (MockB):** You received some amount of Token1 in exchange. Your balance increased from 99701.000000 to 99701.982183.
- **ETH:** The slight decrease in ETH balance (from 9999.986737 to 9999.986577) represents the gas used for the transaction.

In summary, you spent 1 Token0 (MockA) and received approximately 0.982183 Token1 (MockB) in return, with a bit of ETH spent on gas for the transaction.

> nice! thank you! bye

Assistant: You're welcome! If you have more questions in the future or need further assistance with your trades, don't hesitate to reach out. Have a great day and bye for now!
```

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
