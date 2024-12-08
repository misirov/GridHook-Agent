// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Script.sol";
import {IHooks} from "v4-core/src/interfaces/IHooks.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {PoolManager} from "v4-core/src/PoolManager.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolModifyLiquidityTest} from "v4-core/src/test/PoolModifyLiquidityTest.sol";
import {PoolSwapTest} from "v4-core/src/test/PoolSwapTest.sol";
import {PoolDonateTest} from "v4-core/src/test/PoolDonateTest.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {MockERC20} from "solmate/src/test/utils/mocks/MockERC20.sol";
import {Constants} from "v4-core/src/../test/utils/Constants.sol";
import {TickMath} from "v4-core/src/libraries/TickMath.sol";
import {CurrencyLibrary, Currency} from "v4-core/src/types/Currency.sol";
import {HookMiner} from "../test/utils/HookMiner.sol";
import {IPositionManager} from "v4-periphery/src/interfaces/IPositionManager.sol";
import {PositionManager} from "v4-periphery/src/PositionManager.sol";
import {EasyPosm} from "../test/utils/EasyPosm.sol";
import {IAllowanceTransfer} from "permit2/src/interfaces/IAllowanceTransfer.sol";
import {DeployPermit2} from "../test/utils/forks/DeployPermit2.sol";
import {IERC20} from "forge-std/interfaces/IERC20.sol";
import {IPositionDescriptor} from "v4-periphery/src/interfaces/IPositionDescriptor.sol";
import {IWETH9} from "v4-periphery/src/interfaces/external/IWETH9.sol";
import {GridHook} from "../src/GridHook.sol";

/// @notice Forge script for deploying v4 & hooks to **anvil**
/// @dev This script only works on an anvil RPC because v4 exceeds bytecode limits
contract GridHookScript is Script, DeployPermit2 {
    using EasyPosm for IPositionManager;

    address constant CREATE2_DEPLOYER = address(0x4e59b44847b379578588920cA78FbF26c0B4956C);

    function setUp() public {}

    function run() public {
        vm.broadcast();
        IPoolManager manager = deployPoolManager();

        // hook contracts must have specific flags encoded in the address
        uint160 permissions = uint160(
            Hooks.AFTER_INITIALIZE_FLAG | Hooks.AFTER_SWAP_FLAG
        );

        // Mine a salt that will produce a hook address with the correct permissions
        (address hookAddress, bytes32 salt) =
            HookMiner.find(CREATE2_DEPLOYER, permissions, type(GridHook).creationCode, abi.encode(address(manager)));

        // ----------------------------- //
        // Deploy the hook using CREATE2 //
        // ----------------------------- //
        vm.broadcast();
        GridHook hook = new GridHook{salt: salt}(manager);
        require(address(hook) == hookAddress, "GridHookScript: hook address mismatch");
        address hook_address = address(hook);
        //console.log("--> Pool manager deployed to: ", manager);
        console.log("--> GridHook address deployed to: ", hook_address);

        // Additional helpers for interacting with the pool
        vm.startBroadcast();
        IPositionManager posm = deployPosm(manager);
        (PoolModifyLiquidityTest lpRouter, PoolSwapTest swapRouter,) = deployRouters(manager);
        vm.stopBroadcast();

        // test the lifecycle (create pool, add liquidity, swap)
        vm.startBroadcast();
        (MockERC20 token0, MockERC20 token1) = testLifecycle(manager, address(hook), posm, lpRouter, swapRouter);
        vm.stopBroadcast();

        // After all broadcasts, set up approvals for our user
        address USER = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;
        
        // Additional minting if needed
        vm.startPrank(msg.sender);
        token0.mint(USER, 100_000 ether);
        token1.mint(USER, 100_000 ether);
        vm.stopPrank();

        // Approvals from USER's perspective
        vm.startPrank(USER);
        token0.approve(hook_address, type(uint256).max);
        token1.approve(hook_address, type(uint256).max);
        vm.stopPrank();

        console.log("--> Additional tokens minted and approved for: ", USER);
        console.log("--> Token0 balance: ", token0.balanceOf(USER));
        console.log("--> Token1 balance: ", token1.balanceOf(USER));
        console.log("--> Token0 allowance: ", token0.allowance(USER, hook_address));
        console.log("--> Token1 allowance: ", token1.allowance(USER, hook_address));
    }

    // Update testLifecycle to return the tokens
    function testLifecycle(
        IPoolManager manager,
        address hook,
        IPositionManager posm,
        PoolModifyLiquidityTest lpRouter,
        PoolSwapTest swapRouter
    ) internal returns (MockERC20 token0, MockERC20 token1) {
        (MockERC20 token0, MockERC20 token1) = deployTokens();
        
        // Mint tokens to our specific address
        address USER = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;
        token0.mint(USER, 100_000 ether);
        token1.mint(USER, 100_000 ether);

        bytes memory ZERO_BYTES = new bytes(0);

        // initialize the pool
        int24 tickSpacing = 60;
        PoolKey memory poolKey =
            PoolKey(Currency.wrap(address(token0)), Currency.wrap(address(token1)), 3000, tickSpacing, IHooks(hook));
        manager.initialize(poolKey, Constants.SQRT_PRICE_1_1);

        // approve the tokens to the routers
        token0.approve(address(lpRouter), type(uint256).max);
        token1.approve(address(lpRouter), type(uint256).max);
        token0.approve(address(swapRouter), type(uint256).max);
        token1.approve(address(swapRouter), type(uint256).max);

        // Approve tokens for GridHook
        token0.approve(hook, type(uint256).max);
        token1.approve(hook, type(uint256).max);

        // Stop broadcast to do pranks
        vm.stopBroadcast();

        // Do approvals from USER's perspective
        vm.startPrank(USER);
        token0.approve(hook, type(uint256).max);
        token1.approve(hook, type(uint256).max);
        vm.stopPrank();

        // Restart broadcast for remaining operations
        vm.startBroadcast();

        approvePosmCurrency(posm, Currency.wrap(address(token0)));
        approvePosmCurrency(posm, Currency.wrap(address(token1)));

        // add full range liquidity to the pool
        lpRouter.modifyLiquidity(
            poolKey,
            IPoolManager.ModifyLiquidityParams(
                TickMath.minUsableTick(tickSpacing), TickMath.maxUsableTick(tickSpacing), 100 ether, 0
            ),
            ZERO_BYTES
        );

        posm.mint(
            poolKey,
            TickMath.minUsableTick(tickSpacing),
            TickMath.maxUsableTick(tickSpacing),
            100e18,
            10_000e18,
            10_000e18,
            msg.sender,
            block.timestamp + 300,
            ZERO_BYTES
        );

        // swap some tokens
        bool zeroForOne = true;
        int256 amountSpecified = 1 ether;
        IPoolManager.SwapParams memory params = IPoolManager.SwapParams({
            zeroForOne: zeroForOne,
            amountSpecified: amountSpecified,
            sqrtPriceLimitX96: zeroForOne ? TickMath.MIN_SQRT_PRICE + 1 : TickMath.MAX_SQRT_PRICE - 1 // unlimited impact
        });
        PoolSwapTest.TestSettings memory testSettings =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});
        swapRouter.swap(poolKey, params, testSettings, ZERO_BYTES);
    
    
    
        console.log("--> token0 address: ", address(token0));
        console.log("--> token1 address: ", address(token1));

        // Return the tokens so we can use them in run()
        return (token0, token1);
    }

    // -----------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------
    function deployPoolManager() internal returns (IPoolManager) {
        return IPoolManager(address(new PoolManager(address(0))));
    }

    function deployRouters(IPoolManager manager)
        internal
        returns (PoolModifyLiquidityTest lpRouter, PoolSwapTest swapRouter, PoolDonateTest donateRouter)
    {
        lpRouter = new PoolModifyLiquidityTest(manager);
        swapRouter = new PoolSwapTest(manager);
        donateRouter = new PoolDonateTest(manager);
    }

    function deployPosm(IPoolManager poolManager) public returns (IPositionManager) {
        anvilPermit2();
        return IPositionManager(new PositionManager(poolManager, permit2, 300_000, IPositionDescriptor(address(0)), IWETH9(address(0))));
    }

    function approvePosmCurrency(IPositionManager posm, Currency currency) internal {
        // Because POSM uses permit2, we must execute 2 permits/approvals.
        // 1. First, the caller must approve permit2 on the token.
        IERC20(Currency.unwrap(currency)).approve(address(permit2), type(uint256).max);
        // 2. Then, the caller must approve POSM as a spender of permit2
        permit2.approve(Currency.unwrap(currency), address(posm), type(uint160).max, type(uint48).max);
    }

    function deployTokens() internal returns (MockERC20 token0, MockERC20 token1) {
        MockERC20 tokenA = new MockERC20("MockA", "A", 18);
        MockERC20 tokenB = new MockERC20("MockB", "B", 18);
        if (uint160(address(tokenA)) < uint160(address(tokenB))) {
            token0 = tokenA;
            token1 = tokenB;
        } else {
            token0 = tokenB;
            token1 = tokenA;
        }

    }
}
