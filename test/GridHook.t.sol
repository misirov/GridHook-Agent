// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import {Test} from "forge-std/Test.sol";
import {Deployers} from "@uniswap/v4-core/test/utils/Deployers.sol";
import {PoolSwapTest} from "v4-core/src/test/PoolSwapTest.sol";
import {MockERC20} from "solmate/src/test/utils/mocks/MockERC20.sol";
import {PoolManager} from "v4-core/src/PoolManager.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolId, PoolIdLibrary} from "v4-core/src/types/PoolId.sol";
import {Currency, CurrencyLibrary} from "v4-core/src/types/Currency.sol";
import {StateLibrary} from "v4-core/src/libraries/StateLibrary.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {TickMath} from "v4-core/src/libraries/TickMath.sol";
import {LiquidityAmounts} from "@uniswap/v4-core/test/utils/LiquidityAmounts.sol";
import {console} from "forge-std/console.sol";

import {GridHook} from "../src/GridHook.sol";



contract GridHookTest is Test, Deployers {
     // Use the libraries
    using StateLibrary for IPoolManager;
    using PoolIdLibrary for PoolKey;
    using CurrencyLibrary for Currency;

    // The two currencies (tokens) from the pool
    Currency token0;
    Currency token1;

    address public bob = makeAddr("Bob");
    address public alice = makeAddr("Alice");

    GridHook hook;

    function setUp() public {
        // Deploy uniswap v4 pool manager + periphery contracts
        // - https://github.com/Uniswap/v4-core/blob/main/test/utils/Deployers.sol#L86-L104
        deployFreshManagerAndRouters();

        // Deploy two test tokens
        (token0, token1) = deployMintAndApprove2Currencies();

        // Select hook trigger flags
        uint160 flags = uint160(Hooks.AFTER_INITIALIZE_FLAG | Hooks.AFTER_SWAP_FLAG);
        address hookAddress = address(flags);
        // Deploy to anvil with vm.etch: hook name + constructor + hook flags
        // @note Must use `HookMiner` library to deploy to actual blockchain
        deployCodeTo("GridHook.sol", abi.encode(manager, ""), hookAddress);
        hook = GridHook(hookAddress);

        // Approve hook address to spend these tokens as well
        MockERC20(Currency.unwrap(token0)).approve(address(hook), type(uint256).max);
        MockERC20(Currency.unwrap(token1)).approve(address(hook), type(uint256).max);

        // Create a pool
        (key, ) = initPool({
            _currency0: token0,           // Currency0
            _currency1: token1,           // Currency1
            hooks: hook,                  // GridHook
            fee: 1000,                    // 0.1% fee
            sqrtPriceX96: SQRT_PRICE_1_1  // Exchange rate 1:1
        });


        // Add liquidity from -60 to +60 tick range
        modifyLiquidityRouter.modifyLiquidity(
            key,
            IPoolManager.ModifyLiquidityParams({
                tickLower: -60,
                tickUpper: 60,
                liquidityDelta: 10 ether,
                salt: bytes32(0)
            }),
            ZERO_BYTES
        );
        // Add liquidity from -120 to +120 tick range
        modifyLiquidityRouter.modifyLiquidity(
            key,
            IPoolManager.ModifyLiquidityParams({
                tickLower: -120,
                tickUpper: 120,
                liquidityDelta: 10 ether,
                salt: bytes32(0)
            }),
            ZERO_BYTES
        );
        // Add liquidity for full range
        modifyLiquidityRouter.modifyLiquidity(
            key,
            IPoolManager.ModifyLiquidityParams({
                tickLower: TickMath.minUsableTick(60),
                tickUpper: TickMath.maxUsableTick(60),
                liquidityDelta: 10 ether,
                salt: bytes32(0)
            }),
            ZERO_BYTES
        );
    }


    function test_placeOrder() public {
        // Place a zeroForOne take-profit order
        // for 10e18 bitcoin tokens
        // at tick 100
        int24 tick = 60;
        uint256 amount = 10e18;
        bool zeroForOne = true;

        // Note the original balance of bitcoin we have
        uint256 originalBalance = token0.balanceOfSelf();

        // Place the order
        int24 tickLower = hook.placeOrder(key, tick, zeroForOne, amount);

        // Note the new balance of token0 we have
        uint256 newBalance = token0.balanceOfSelf();

        // Since we deployed the pool contract with tick spacing = 60
        // i.e. the tick can only be a multiple of 60
        // the tickLower should be 60 since we placed an order at tick 100
        assertEq(tickLower, 60);

        // Ensure that our balance of token0 was reduced by `amount` tokens
        assertEq(originalBalance - newBalance, amount);

        // Check the balance of ERC-1155 tokens we received
        uint256 positionId = hook.getPositionId(key, tickLower, zeroForOne);
        uint256 tokenBalance = hook.balanceOf(address(this), positionId);

        // Ensure that we were, in fact, given ERC-1155 tokens for the order
        // equal to the `amount` of token0 tokens we placed the order for
        assertTrue(positionId != 0);
        assertEq(tokenBalance, amount);

        // run some off chain computation, only delete
        GridHook.BurnToken memory burnToken = GridHook.BurnToken({
            key: key,
            tick: tickLower,
            zeroForOne: zeroForOne,
            owner: address(this),
            amount: amount,
            amountPendingRemove: amount
        });

        GridHook.NewOrder[] memory newOrders = new GridHook.NewOrder[](0);
        GridHook.Balances[] memory newBalances = new GridHook.Balances[](0);
        GridHook.BurnToken[] memory burns = new GridHook.BurnToken[](1);
        burns[0] = burnToken;
        hook.offChainComputation(burns, newOrders, newBalances);
    }

    function onERC1155Received(address, address, uint256, uint256, bytes calldata) external pure returns (bytes4) {
        return this.onERC1155Received.selector;
    }


    function test_orderExecute_zeroForOne() public {
        int24 tick = 100;
        uint256 amount = 1 ether;
        bool zeroForOne = true;

        // Place our order at tick 100 for 10e18 token0 tokens
        int24 tickLower = hook.placeOrder(key, tick, zeroForOne, amount);

        // Do a separate swap from oneForZero to make tick go up
        // Sell 1e18 token1 tokens for token0 tokens
        IPoolManager.SwapParams memory params = IPoolManager.SwapParams({
            zeroForOne: !zeroForOne,
            amountSpecified: -1 ether,
            sqrtPriceLimitX96: TickMath.MAX_SQRT_PRICE - 1
        });

        PoolSwapTest.TestSettings memory testSettings =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});

        // Conduct the swap - `afterSwap` should also execute our placed order
        swapRouter.swap(key, params, testSettings, ZERO_BYTES);

        // Check that the order has been executed
        // by ensuring no amount is left to sell in the pending orders
        uint256 pendingTokensForPosition = hook.pendingOrders(key.toId(), tick, zeroForOne);
        assertEq(pendingTokensForPosition, 0);

        // Check that the hook contract has the expected number of token1 tokens ready to redeem
        uint256 positionId = hook.getPositionId(key, tickLower, zeroForOne);
        uint256 claimableOutputTokens = hook.claimableOutputTokens(positionId);
        uint256 hookContracttoken1Balance = token1.balanceOf(address(hook));
        assertEq(claimableOutputTokens, hookContracttoken1Balance);

        // Ensure we can redeem the token1 tokens
        uint256 originaltoken1Balance = token1.balanceOf(address(this));
        hook.redeem(key, tick, zeroForOne, amount);
        uint256 newtoken1Balance = token1.balanceOf(address(this));

        assertEq(newtoken1Balance - originaltoken1Balance, claimableOutputTokens);
    }
`

    function test_orderExecute_zeroForOne_rebuy() public {
        int24 tick = 100;
        uint256 amount = 1 ether;
        bool zeroForOne = true;

        // Place our order at tick 100 for 10e18 token0 tokens
        int24 tickLower = hook.placeOrder(key, tick, zeroForOne, amount);

        // Do a separate swap from oneForZero to make tick go up
        // Sell 1e18 token1 tokens for token0 tokens
        IPoolManager.SwapParams memory params = IPoolManager.SwapParams({
            zeroForOne: !zeroForOne,
            amountSpecified: -1 ether,
            sqrtPriceLimitX96: TickMath.MAX_SQRT_PRICE - 1
        });

        PoolSwapTest.TestSettings memory testSettings =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});

        // Conduct the swap - `afterSwap` should also execute our placed order
        swapRouter.swap(key, params, testSettings, ZERO_BYTES);

        // Check that the order has been executed
        // by ensuring no amount is left to sell in the pending orders
        uint256 pendingTokensForPosition = hook.pendingOrders(key.toId(), tick, zeroForOne);
        assertEq(pendingTokensForPosition, 0);

        // Check that the hook contract has the expected number of token1 tokens ready to redeem
        uint256 positionId = hook.getPositionId(key, tickLower, zeroForOne);
        uint256 claimableOutputTokens = hook.claimableOutputTokens(positionId);
        uint256 hookContracttoken1Balance = token1.balanceOf(address(hook));
        assertEq(claimableOutputTokens, hookContracttoken1Balance);

        // Ensure we can redeem the token1 tokens
        //uint256 originaltoken1Balance = token1.balanceOf(address(this));
        //hook.redeem(key, tick, zeroForOne, amount);
        //uint256 newtoken1Balance = token1.balanceOf(address(this));

        //assertEq(newtoken1Balance - originaltoken1Balance, claimableOutputTokens);

        // now lets do a rebuy using the offChainComputation
        GridHook.BurnToken[] memory burns = new GridHook.BurnToken[](1);
        GridHook.BurnToken memory burnToken = GridHook.BurnToken({
            key: key,
            tick: tickLower,
            zeroForOne: zeroForOne,
            owner: address(this),
            amount: hook.balanceOf(address(this), positionId),
            amountPendingRemove: 0
        });
        burns[0] = burnToken;

        GridHook.NewOrder[] memory newOrders = new GridHook.NewOrder[](1);
        newOrders[0] = GridHook.NewOrder({
            owner: address(this),
            key: key,
            tickToSellAt: tickLower + 1,
            zeroForOne: zeroForOne,
            inputAmount: amount
        });

        GridHook.Balances[] memory newBalances = new GridHook.Balances[](1);
        newBalances[0] = GridHook.Balances({
            idClaimable: positionId,
            claimableOutputTokensPrev: claimableOutputTokens,
            claimableOutputTokensNew: 0,
            idPending: key,
            tick: tickLower + 1,
            zeroForOne: zeroForOne,
            pendingOrdersPrev: 0,
            pendingOrdersNew: 0
        });
        
        // this will recalculate the balances, update the state and create a new order
        hook.offChainComputation(burns, newOrders, newBalances);
    }

    function test_orderExecute_oneForZero() public {
        int24 tick = -100;
        uint256 amount = 10 ether;
        bool zeroForOne = false;

        // Place our order at tick -100 for 10e18 token1 tokens
        int24 tickLower = hook.placeOrder(key, tick, zeroForOne, amount);

        // Do a separate swap from zeroForOne to make tick go down
        // Sell 1e18 token0 tokens for token1 tokens
        IPoolManager.SwapParams memory params = IPoolManager.SwapParams({
            zeroForOne: true,
            amountSpecified: -1 ether,
            sqrtPriceLimitX96: TickMath.MIN_SQRT_PRICE + 1
        });

        PoolSwapTest.TestSettings memory testSettings =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});

        swapRouter.swap(key, params, testSettings, ZERO_BYTES);

        // Check that the order has been executed
        uint256 tokensLeftToSell = hook.pendingOrders(key.toId(), tick, zeroForOne);
        assertEq(tokensLeftToSell, 0);

        // Check that the hook contract has the expected number of token0 tokens ready to redeem
        uint256 positionId = hook.getPositionId(key, tickLower, zeroForOne);
        uint256 claimableOutputTokens = hook.claimableOutputTokens(positionId);
        uint256 hookContracttoken0Balance = token0.balanceOf(address(hook));
        assertEq(claimableOutputTokens, hookContracttoken0Balance);

        // Ensure we can redeem the token0 tokens
        uint256 originaltoken0Balance = token0.balanceOfSelf();
        hook.redeem(key, tick, zeroForOne, amount);
        uint256 newtoken0Balance = token0.balanceOfSelf();

        assertEq(newtoken0Balance - originaltoken0Balance, claimableOutputTokens);
    }

    function test_multiple_orderExecute_zeroForOne_onlyOne() public {
        PoolSwapTest.TestSettings memory testSettings =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});

        // Setup two zeroForOne orders at ticks 0 and 60
        uint256 amount = 0.01 ether;

        hook.placeOrder(key, 0, true, amount);
        hook.placeOrder(key, 60, true, amount);

        (, int24 currentTick,,) = manager.getSlot0(key.toId());
        assertEq(currentTick, 0);

        // Do a swap to make tick increase beyond 60
        IPoolManager.SwapParams memory params = IPoolManager.SwapParams({
            zeroForOne: false,
            amountSpecified: -0.1 ether,
            sqrtPriceLimitX96: TickMath.MAX_SQRT_PRICE - 1
        });

        swapRouter.swap(key, params, testSettings, ZERO_BYTES);

        // Only one order should have been executed
        // because the execution of that order would lower the tick
        // so even though tick increased beyond 60
        // the first order execution will lower it back down
        // so order at tick = 60 will not be executed
        uint256 tokensLeftToSell = hook.pendingOrders(key.toId(), 0, true);
        assertEq(tokensLeftToSell, 0);

        // Order at Tick 60 should still be pending
        tokensLeftToSell = hook.pendingOrders(key.toId(), 60, true);
        assertEq(tokensLeftToSell, amount);
    }

    function test_multiple_orderExecute_zeroForOne_both() public {
        PoolSwapTest.TestSettings memory testSettings =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});

        // Setup two zeroForOne orders at ticks 0 and 60
        uint256 amount = 0.01 ether;

        hook.placeOrder(key, 0, true, amount);
        hook.placeOrder(key, 60, true, amount);

        // Do a swap to make tick increase
        IPoolManager.SwapParams memory params = IPoolManager.SwapParams({
            zeroForOne: false,
            amountSpecified: -0.5 ether,
            sqrtPriceLimitX96: TickMath.MAX_SQRT_PRICE - 1
        });

        swapRouter.swap(key, params, testSettings, ZERO_BYTES);

        uint256 tokensLeftToSell = hook.pendingOrders(key.toId(), 0, true);
        assertEq(tokensLeftToSell, 0);

        tokensLeftToSell = hook.pendingOrders(key.toId(), 60, true);
        assertEq(tokensLeftToSell, 0);
    }

    function onERC1155BatchReceived(address, address, uint256[] calldata, uint256[] calldata, bytes calldata)
        external
        pure
        returns (bytes4)
    {
        return this.onERC1155BatchReceived.selector;
    }



}