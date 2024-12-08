from openai import OpenAI
from web3 import Web3
from utils.load_abi import load_abi
import json
import os
from dotenv import load_dotenv

## Make sure to mint tokens and make approvals to the foundry test address we use during deployment
GRID_HOOK_ADDRESS = "0x9D71E6f99da38505b3c50cb0ec2ed754Ea13D040"
POOL_KEY = {
    "currency0": "0x0165878A594ca255338adfa4d48449f69242Eb8F",
    "currency1": "0xa513E6E4b8f2a923D98304ec87F64353C4D5C853",
    "fee": 1000,
    "tickSpacing": 60,
    "hooks": GRID_HOOK_ADDRESS
}

web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

account = web3.eth.account.from_key(private_key)

contract = web3.eth.contract(address=GRID_HOOK_ADDRESS, abi=load_abi("GridHook"))

tx = contract.functions.placeOrder(
    POOL_KEY,
    int(1),
    True,
    int(1e18)
).build_transaction({
    'from': account.address,
    'gas': 2000000,
    'gasPrice': web3.eth.gas_price,
    'nonce': web3.eth.get_transaction_count(account.address),
})

signed_tx = web3.eth.account.sign_transaction(tx, private_key)

tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

print(f"Transaction sent! Hash: {tx_hash.hex()}")

tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

print(tx_receipt)