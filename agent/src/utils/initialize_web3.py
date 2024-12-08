from web3 import Web3

def initialize_web3(RPC_URL: str):
    try:
        web3 = Web3(Web3.HTTPProvider(RPC_URL))
        return web3
    except Exception as e:
        print(f"An error occurred while initializing Web3: {str(e)}")
        raise