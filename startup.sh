#!/bin/bash

# Start anvil in the background
echo "Starting Anvil..."
anvil --host 0.0.0.0 &
ANVIL_PID=$!

# Wait for anvil to start
sleep 2

# Run Foundry tests
echo "Running Foundry tests..."
forge test -vv

# Deploy contracts
echo "Deploying contracts..."
forge script script/Deploy.s.sol --broadcast --rpc-url http://localhost:8545 --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# Activate Python virtual environment
source .venv/bin/activate

# Start the Python bot
echo "Starting Grid Trading Bot..."
python3 src/main.py

# If the Python bot exits, kill anvil
kill $ANVIL_PID