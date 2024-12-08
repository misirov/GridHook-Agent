from web3 import Web3
from utils.load_abi import load_abi
from eth_abi import encode

GRID_HOOK_ADDRESS = "0x9D71E6f99da38505b3c50cb0ec2ed754Ea13D040"
POOL_KEY = {
    "currency0": "0x0165878A594ca255338adfa4d48449f69242Eb8F",
    "currency1": "0xa513E6E4b8f2a923D98304ec87F64353C4D5C853",
    "fee": 1000,
    "tickSpacing": 60,
    "hooks": GRID_HOOK_ADDRESS
}

web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
contract = web3.eth.contract(address=GRID_HOOK_ADDRESS, abi=load_abi("GridHook"))

def get_pool_id(pool_key):
    # Encode the pool key parameters in the same way as Solidity
    encoded = encode(
        ['address', 'address', 'uint24', 'int24', 'address'],
        [
            Web3.to_checksum_address(pool_key['currency0']),
            Web3.to_checksum_address(pool_key['currency1']),
            pool_key['fee'],
            pool_key['tickSpacing'],
            Web3.to_checksum_address(pool_key['hooks'])
        ]
    )
    # Hash it to get the pool ID
    return web3.keccak(encoded)

def check_position(tick, zero_for_one=True):
    try:
        # Get position ID
        position_id = contract.functions.getPositionId(
            POOL_KEY,
            tick,
            zero_for_one
        ).call()
        
        # Get pending orders amount
        pool_id = get_pool_id(POOL_KEY)
        pending_amount = contract.functions.pendingOrders(
            pool_id,  # poolId
            tick,
            zero_for_one
        ).call()
        
        # Get claimable output tokens
        claimable = contract.functions.claimableOutputTokens(position_id).call()
        
        # Get total claim tokens supply
        claim_supply = contract.functions.claimTokensSupply(position_id).call()
        
        print(f"\nPosition at tick {tick} ({'sell token0' if zero_for_one else 'sell token1'}):")
        print(f"Position ID: {position_id}")
        print(f"Pool ID: {pool_id.hex()}")
        print(f"Pending order amount: {Web3.from_wei(pending_amount, 'ether')} tokens")
        print(f"Claimable output tokens: {Web3.from_wei(claimable, 'ether')} tokens")
        print(f"Total claim tokens supply: {Web3.from_wei(claim_supply, 'ether')} tokens")
    
    except Exception as e:
        print(f"Error checking position at tick {tick}: {str(e)}")

def main():
    print("Checking positions around current tick...")
    
    # Check a range of ticks
    nearby_ticks = [-60, -1, 0, 1, 60]
    for tick in nearby_ticks:
        # Check both directions (selling token0 and selling token1)
        check_position(tick, True)  # zeroForOne = True (selling token0)
        check_position(tick, False) # zeroForOne = False (selling token1)

if __name__ == "__main__":
    main()
