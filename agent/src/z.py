from openai import OpenAI
from web3 import Web3
from utils.load_abi import load_abi
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Web3
w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))


# Contract addresses from deployments (convert to checksum addresses)
POOL_MANAGER = w3.to_checksum_address("0x5fbdb2315678afecb367f032d93f642f64180aa3")
TOKEN0 = w3.to_checksum_address("0x0165878A594ca255338adfa4d48449f69242Eb8F")
TOKEN1 = w3.to_checksum_address("0xa513E6E4b8f2a923D98304ec87F64353C4D5C853")
GRID_HOOK = w3.to_checksum_address("0x9D71E6f99da38505b3c50cb0ec2ed754Ea13D040")

# Pool parameters
POOL_KEY = {
    "currency0": TOKEN0,
    "currency1": TOKEN1,
    "fee": 1000,  # 0.1%
    "tickSpacing": 60,
    "hooks": GRID_HOOK
}

def convert_scientific_to_int(sci_notation: str) -> int:
    """Convert scientific notation string to integer"""
    return int(float(sci_notation))

def test_place_order():
    # Initialize OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Load GridHook ABI
    grid_hook_abi = load_abi("GridHook")
    
    # Create the function tool for OpenAI
    place_order_tool = {
        "type": "function",
        "function": {
            "name": "placeOrder",
            "description": "Place a limit order in the pool",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "object",
                        "properties": {
                            "currency0": {"type": "string"},
                            "currency1": {"type": "string"},
                            "fee": {"type": "integer"},
                            "tickSpacing": {"type": "integer"},
                            "hooks": {"type": "string"}
                        }
                    },
                    "tickToSellAt": {"type": "integer"},
                    "zeroForOne": {"type": "boolean"},
                    "inputAmount": {"type": "string"}
                },
                "required": ["key", "tickToSellAt", "zeroForOne", "inputAmount"]
            }
        }
    }

    # Create prompt with pool information
    prompt = f"""
    Place a limit order with these parameters:
    - Pool Information:
        - Token0: {TOKEN0}
        - Token1: {TOKEN1}
        - Fee: {POOL_KEY['fee']} (0.1%)
        - Tick Spacing: {POOL_KEY['tickSpacing']}
        - Hook Address: {GRID_HOOK}
    
    I want to:
    - Sell token0 for token1
    - Place order at tick 60
    - Amount: 1e18 (1 token)
    
    Please use exactly these pool parameters when making the function call.
    """

    messages = [{"role": "user", "content": prompt}]

    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=[place_order_tool],
        tool_choice={"type": "function", "function": {"name": "placeOrder"}}
    )

    # Extract the function call parameters
    function_call = response.choices[0].message.tool_calls[0].function
    args = json.loads(function_call.arguments)

    print("Function call arguments:", json.dumps(args, indent=2))

    # Verify the pool parameters match
    assert args["key"] == POOL_KEY, "Pool parameters don't match!"

    # Convert scientific notation to integer
    input_amount = convert_scientific_to_int(args["inputAmount"])
    print(f"\nConverted input amount: {input_amount}")

    # Create contract instance and build tx
    contract = w3.eth.contract(address=GRID_HOOK, abi=grid_hook_abi)
    
    tx = contract.functions.placeOrder(
        args["key"],
        args["tickToSellAt"],
        args["zeroForOne"],
        input_amount
    ).build_transaction({
        'from': w3.eth.accounts[0],
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(w3.eth.accounts[0])
    })

    print("\nTransaction built:", tx)

    # Sign and send transaction
    try:
        # Get private key from environment
        private_key = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        if not private_key:
            raise ValueError("PRIVATE_KEY not found in environment variables")

        # Sign transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        print("\nTransaction signed!")

        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"\nTransaction sent! Hash: {tx_hash.hex()}")

        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print("\nTransaction receipt:", tx_receipt)

        return tx_receipt

    except Exception as e:
        print(f"\nError executing transaction: {str(e)}")
        raise

if __name__ == "__main__":
    test_place_order()