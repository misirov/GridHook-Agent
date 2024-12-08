from web3 import Web3
from config import Config
from utils.load_abi import load_abi

# Initialize Web3
web3 = Web3(Web3.HTTPProvider(Config.RPC_URL))

def test_swap():
    account = web3.eth.account.from_key(Config.PRIVATE_KEY)
    
    # Convert addresses to checksum format
    pool_swap_test = web3.to_checksum_address(Config.POOL_SWAP_TEST)
    token0 = web3.to_checksum_address(Config.TOKEN0)
    token1 = web3.to_checksum_address(Config.TOKEN1)
    grid_hook = web3.to_checksum_address(Config.GRID_HOOK_ADDRESS)

    # Initialize contracts
    token0_contract = web3.eth.contract(address=token0, abi=Config.MOCK_TOKEN_ABI)
    token1_contract = web3.eth.contract(address=token1, abi=Config.MOCK_TOKEN_ABI)
    swap_router = web3.eth.contract(address=pool_swap_test, abi=Config.POOL_SWAP_TEST_ABI)

    # Check and set approvals if needed
    for token in [token0_contract, token1_contract]:
        allowance = token.functions.allowance(account.address, pool_swap_test).call()
        print(f"Current allowance for {token.address}: {allowance}")
        if allowance == 0:
            print(f"Approving {token.address}...")
            tx = token.functions.approve(pool_swap_test, 2**256-1).build_transaction({
                'from': account.address,
                'gas': 100000,
                'gasPrice': web3.eth.gas_price,
                'nonce': web3.eth.get_transaction_count(account.address),
            })
            signed_tx = web3.eth.account.sign_transaction(tx, account._private_key.hex())
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            web3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Approved {token.address}")

    # Create pool key with checksum addresses and fee 3000 (0.3%)
    pool_key = {
        'currency0': token0,
        'currency1': token1,
        'fee': 3000,  # Changed from 1000 to match Anvil.s.sol
        'tickSpacing': Config.POOL_KEY['tickSpacing'],
        'hooks': grid_hook
    }

    # Get initial balances
    balance0_before = token0_contract.functions.balanceOf(account.address).call()
    balance1_before = token1_contract.functions.balanceOf(account.address).call()
    print(f"\nInitial balances:")
    print(f"Token0: {balance0_before / 1e18} A")
    print(f"Token1: {balance1_before / 1e18} B")

    # Create the SwapParams struct
    swap_params = {
        'zeroForOne': True,
        'amountSpecified': int(10e18),  # negative for exact input
        'sqrtPriceLimitX96': 4295128739 + 1  # MIN_SQRT_PRICE + 1
    }

    # Create the TestSettings struct
    test_settings = {
        'takeClaims': False,
        'settleUsingBurn': False
    }

    print(f"\nSwap Parameters:")
    print(f"Pool Key: {pool_key}")
    print(f"Swap Params: {swap_params}")
    print(f"Test Settings: {test_settings}")

    # Execute swap
    tx = swap_router.functions.swap(
        pool_key,
        swap_params,
        test_settings,
        b""  # hookData
    ).build_transaction({
        'from': account.address,
        'gas': 500000,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(account.address),
    })

    signed_tx = web3.eth.account.sign_transaction(tx, account._private_key.hex())
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"\nSwap transaction sent! Hash: {tx_hash.hex()}")

    # Get receipt and verify
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction status: {'Success' if tx_receipt['status'] == 1 else 'Failed'}")
    print(f"Gas used: {tx_receipt['gasUsed']}")

    # Verify balances changed
    balance0_after = token0_contract.functions.balanceOf(account.address).call()
    balance1_after = token1_contract.functions.balanceOf(account.address).call()
    
    print(f"\nBalance changes:")
    print(f"Token0: {(balance0_after - balance0_before) / 1e18} A")
    print(f"Token1: {(balance1_after - balance1_before) / 1e18} B")

if __name__ == "__main__":
    test_swap()