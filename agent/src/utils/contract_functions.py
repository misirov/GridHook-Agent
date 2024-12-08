from web3 import Web3
from eth_account import Account
from eth_abi import encode
from typing import Dict, Any
from config import Config
from utils.initialize_web3 import initialize_web3


class ContractFunctions:
    def __init__(self, config: Config):
        """Initialize with Config class"""
        self.web3 = initialize_web3(config.RPC_URL)
        self.config = config
        self.account = Account.from_key(config.PRIVATE_KEY)
        
        # Convert addresses to checksum format
        self.grid_hook_address = self.web3.to_checksum_address(config.GRID_HOOK_ADDRESS)
        self.pool_swap_test = self.web3.to_checksum_address(config.POOL_SWAP_TEST)
        self.token0 = self.web3.to_checksum_address(config.TOKEN0)
        self.token1 = self.web3.to_checksum_address(config.TOKEN1)
        
        # Initialize contracts
        self.grid_hook = self.web3.eth.contract(
            address=self.grid_hook_address,
            abi=config.GRID_HOOK_ABI
        )
        
        # Create pool key with checksum addresses and fee 3000 (0.3%)
        self.pool_key = {
            'currency0': self.token0,
            'currency1': self.token1,
            'fee': 3000,
            'tickSpacing': config.POOL_KEY['tickSpacing'],
            'hooks': self.grid_hook_address
        }


    def build_and_send_tx(self, function, value: int = 0) -> Dict[str, Any]:
        """Helper method to build and send transactions"""
        try:
            tx = function.build_transaction({
                'from': self.account.address,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
                'gas': function.estimate_gas({'from': self.account.address}),
                'gasPrice': self.web3.eth.gas_price,
                'value': value
            })
            
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.account._private_key.hex())
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return tx_receipt
        except Exception as e:
            print(f"Transaction failed: {str(e)}")
            raise


    def place_order(self, tick: int, zero_for_one: bool, amount: str) -> str:
        """Place a limit order in the GridHook"""
        try:        
            # Convert to Wei (multiply by 10^18)
            input_amount = int(float(amount) * 10**18)
            function = self.grid_hook.functions.placeOrder(
                self.pool_key,
                tick,
                zero_for_one,
                input_amount
            )
            tx_receipt = self.build_and_send_tx(function)
            if not tx_receipt:
                raise
            return f"tx hash: 0x{tx_receipt.transactionHash.hex()}"

        except Exception as e:
            return f"Error placing order: {str(e)}"

    
    def check_positions(self, tick: int = None) -> str:
        """Check pending orders and claimable tokens at specific ticks"""
        try:
            result = []
            ticks_to_check = [tick] if tick is not None else [-60, -1, 0, 1, 60]
            
            for current_tick in ticks_to_check:
                for zero_for_one in [True, False]:
                    try:
                        # Get position ID
                        position_id = self.grid_hook.functions.getPositionId(
                            self.pool_key,
                            current_tick,
                            zero_for_one
                        ).call()
                        
                        # Get pending orders amount
                        pool_id = self._get_pool_id()
                        pending_amount = self.grid_hook.functions.pendingOrders(
                            pool_id,
                            current_tick,
                            zero_for_one
                        ).call()
                        
                        # Get claimable output tokens
                        claimable = self.grid_hook.functions.claimableOutputTokens(position_id).call()
                        
                        # Get total claim tokens supply
                        claim_supply = self.grid_hook.functions.claimTokensSupply(position_id).call()
                        
                        # Only add to results if there's any activity
                        if pending_amount > 0 or claimable > 0 or claim_supply > 0:
                            result.append(
                                f"\nPosition at tick {current_tick} "
                                f"({'sell token0' if zero_for_one else 'sell token1'}):\n"
                                f"Position ID: {position_id}\n"
                                f"Pending order amount: {self.format_amount(pending_amount)} tokens\n"
                                f"Claimable output tokens: {self.format_amount(claimable)} tokens\n"
                                f"Total claim tokens supply: {self.format_amount(claim_supply)} tokens"
                            )
                    
                    except Exception as e:
                        result.append(f"Error checking position at tick {current_tick}: {str(e)}")
            
            return "\n".join(result) if result else "No active positions found"
                   
        except Exception as e:
            return f"Error checking positions: {str(e)}"
        

    def swap(self, zero_for_one: bool, amount: str) -> str:
        """
        Perform a swap in the pool using the same implementation as swap.py
        """
        try:
            swap_router = self.web3.eth.contract(
                address=self.pool_swap_test,
                abi=self.config.POOL_SWAP_TEST_ABI
            )

            # Convert amount to Wei and make negative for exact input
            amount_in_wei = -int(float(amount) * 10**18)

            # Create the SwapParams struct
            swap_params = {
                'zeroForOne': zero_for_one,
                'amountSpecified': amount_in_wei,
                'sqrtPriceLimitX96': 4295128739 + 1 if zero_for_one else 1461446703485210103287273052203988822378723970342 - 1
            }

            # Create the TestSettings struct
            test_settings = {
                'takeClaims': False,
                'settleUsingBurn': False
            }

            tx = swap_router.functions.swap(
                self.pool_key,
                swap_params,
                test_settings,
                b""  # hookData
            ).build_transaction({
                'from': self.account.address,
                'gas': 500000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
            })

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.account._private_key.hex())
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            return f"Swap transaction sent! Hash: {tx_hash.hex()}\nTransaction status: {'Success' if tx_receipt['status'] == 1 else 'Failed'}\nGas used: {tx_receipt['gasUsed']}"

        except Exception as e:
            return f"Error performing swap: {str(e)}"


    def _get_pool_id(self) -> bytes:
        """Helper function to get pool ID from pool key"""
        encoded = encode(
            ['address', 'address', 'uint24', 'int24', 'address'],
            [
                Web3.to_checksum_address(self.pool_key['currency0']),
                Web3.to_checksum_address(self.pool_key['currency1']),
                self.pool_key['fee'],
                self.pool_key['tickSpacing'],
                Web3.to_checksum_address(self.pool_key['hooks'])
            ]
        )
        return self.web3.keccak(encoded)
    

    def get_hook_permissions(self) -> str:
        """Get permissions for the GridHook contract to understand which hooks are enabled"""
        try:
            permissions = self.grid_hook.functions.getHookPermissions().call()
            result = "GridHook Permissions:\n"
            result += "-------------------\n"
            result += f"beforeInitialize: {'✅' if permissions[0] else '❌'}\n"
            result += f"afterInitialize: {'✅' if permissions[1] else '❌'}\n"
            result += f"beforeAddLiquidity: {'✅' if permissions[2] else '❌'}\n"
            result += f"afterAddLiquidity: {'✅' if permissions[3] else '❌'}\n"
            result += f"beforeRemoveLiquidity: {'✅' if permissions[4] else '❌'}\n"
            result += f"afterRemoveLiquidity: {'✅' if permissions[5] else '❌'}\n"
            result += f"beforeSwap: {'✅' if permissions[6] else '❌'}\n"
            result += f"afterSwap: {'✅' if permissions[7] else '❌'}\n"
            result += f"beforeDonate: {'✅' if permissions[8] else '❌'}\n"
            result += f"afterDonate: {'✅' if permissions[9] else '❌'}\n"
            result += f"beforeSwapReturnDelta: {'✅' if permissions[10] else '❌'}\n"
            result += f"afterSwapReturnDelta: {'✅' if permissions[11] else '❌'}\n"
            result += f"afterAddLiquidityReturnDelta: {'✅' if permissions[12] else '❌'}\n"
            result += f"afterRemoveLiquidityReturnDelta: {'✅' if permissions[13] else '❌'}\n"
            
            return result

        except Exception as e:
            return f"Error getting hook permissions: {str(e)}"


    def format_amount(self, amount: int) -> str:
        eth_amount = Web3.from_wei(amount, 'ether')
        return f"{float(eth_amount):.4f}"  # Show only 4 decimal places


    def get_balances(self, address: str = None) -> str:
        """Get token balances for a specific address or default to user's address"""
        try:
            # Determine target address
            if not address or address == "user":
                target_address = self.account.address
            elif address == "gridhook":
                target_address = self.grid_hook_address
            elif address == "pool":
                target_address = self.pool_swap_test
            else:
                # Handle raw address input
                target_address = self.web3.to_checksum_address(address)
            
            # Initialize token contracts
            token0_contract = self.web3.eth.contract(address=self.token0, abi=self.config.MOCK_TOKEN_ABI)
            token1_contract = self.web3.eth.contract(address=self.token1, abi=self.config.MOCK_TOKEN_ABI)
            
            # Get token names and symbols
            token0_name = token0_contract.functions.name().call()
            token0_symbol = token0_contract.functions.symbol().call()
            token1_name = token1_contract.functions.name().call()
            token1_symbol = token1_contract.functions.symbol().call()
            
            # Get balances
            balance0 = token0_contract.functions.balanceOf(target_address).call() / 1e18
            balance1 = token1_contract.functions.balanceOf(target_address).call() / 1e18
            eth_balance = self.web3.eth.get_balance(target_address) / 1e18
            
            # Create readable address label
            address_label = {
                self.account.address: "Your",
                self.grid_hook_address: "GridHook's",
                self.pool_swap_test: "Pool's"
            }.get(target_address, f"Address {target_address}'s")
            
            return f"""
{address_label} balances:
• {balance0:.6f} {token0_symbol} ({token0_name})
• {balance1:.6f} {token1_symbol} ({token1_name})
• {eth_balance:.6f} ETH
"""
        except Exception as e:
            return f"Error getting balances: {str(e)}"


    @property
    def available_tools(self):
        """Load function signatures from JSON file"""
        return [
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Place a buy or sell order in the pool.\n- To buy token1: set zero_for_one=true (selling token0 to buy token1)\n- To buy token0: set zero_for_one=false (selling token1 to buy token0)\nExamples:\n- 'buy 100 token1 at tick 123' -> tick=123, zero_for_one=true, amount=100\n- 'sell 50 token0 at tick -100' -> tick=-100, zero_for_one=true, amount=50",
            "parameters": {
                "type": "object",
                "properties": {
                    "tick": {"type": "integer", "description": "The tick price at which to place the order"},
                    "zero_for_one": {"type": "boolean", "description": "True if buying token1 (selling token0), False if buying token0 (selling token1)"},
                    "amount": {"type": "string", "description": "Amount of tokens to buy/sell"}
                },
                "required": ["tick", "zero_for_one", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_positions",
            "description": "Check pending orders and claimable tokens at specific ticks.\nIf no tick is provided, checks positions around current tick (-60, -1, 0, 1, 60).\nExamples:\n- 'show all positions'\n- 'check position at tick 100'\n- 'what orders are pending at tick 0'",
            "parameters": {
                "type": "object",
                "properties": {
                    "tick": {
                        "type": "integer",
                        "description": "Specific tick to check. If not provided, checks multiple ticks around 0"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hook_permissions",
            "description": "Get the permissions for the GridHook contract to understand which hooks are enabled",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "swap",
            "description": "Perform a swap in the pool.\n- To swap token0 for token1: set zero_for_one=true\n- To swap token1 for token0: set zero_for_one=false\nExamples:\n- 'swap 1.5 token0 for token1' -> zero_for_one=true, amount=1.5\n- 'swap 2 token1 for token0' -> zero_for_one=false, amount=2",
            "parameters": {
                "type": "object",
                "properties": {
                    "zero_for_one": {
                        "type": "boolean",
                        "description": "True if swapping token0 for token1, False if swapping token1 for token0"
                    },
                    "amount": {
                        "type": "string",
                        "description": "Amount to swap (in human readable format, e.g. '1.5')"
                    }
                },
                "required": ["zero_for_one", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_balances",
            "description": "Get token balances and names for an address. Shows balances of both tokens and ETH.\nExamples:\n- 'what is my balance'\n- 'show gridhook balance'\n- 'check pool balance'\n- 'what tokens do I have'\n- 'balance of 0x123...'",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Address to check balances for. Can be 'user', 'gridhook', 'pool', or a specific Ethereum address"
                    }
                },
                "required": []
            }
        }
    }
]