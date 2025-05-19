# -*- coding: utf-8 -*-
import asyncio
from loguru import logger
from typing import Dict, Any, Optional, List, Union
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware 
from core.chain_validator import validate_eth_endpoint,validate_bsc_endpoint,validate_sol_endpoint
import json
import os
from decimal import Decimal
from config.config import cfg 
from solana.rpc.async_api import AsyncClient
import aiohttp
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

import requests, base64, json, re

from solders import message
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Processed, Finalized

import base58


class ChainBase:
    """链基础类"""
    def __init__(self, chain_id: str, config: Dict[str, Any]):
        self.chain_id = chain_id
        self.config = config
        self.client = None
        self.initialized = False
        
    async def initialize(self) -> bool:
        """初始化链连接"""
        raise NotImplementedError("子类必须实现initialize方法")
        
    async def buy_token(self, token_address: str, amount_usd: float, private_key: str) -> Optional[str]:
        """购买代币"""
        raise NotImplementedError("子类必须实现buy_token方法")
        
    def get_explorer_url(self, tx_hash: str) -> str:
        """获取交易浏览器URL"""
        if "explorer" in self.config:
            return f"{self.config['explorer']}{tx_hash}"
        return ""

class EvmChain(ChainBase):
    """EVM兼容链"""
    def __init__(self, chain_id: str, config: Dict[str, Any]):
        super().__init__(chain_id, config)
        self.web3 = None
        self.router_abi = None
        self.erc20_abi = None
        
    async def initialize(self) -> bool:
        """初始化EVM链连接"""
        try:
            # 检查RPC URL
            if "rpc" not in self.config:
                logger.error(f"{self.chain_id}链缺少RPC URL配置")
                return False
            
            rpc_url = self.config["rpc"]
            # 初始化Web3实例
            self.web3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # 对于支持PoA的链添加中间件
            if self.chain_id in ["bsc"]:
                self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                
            # 检查连接
            if not self.web3.is_connected():
                logger.error(f"{self.chain_id}链连接失败")
                return False
                
            # 加载ABI
            abi_dir = os.path.join(os.path.dirname(__file__), "abi")
            
            # 加载路由合约ABI
            router_abi_path = os.path.join(abi_dir, "router.json")
            if os.path.exists(router_abi_path):
                with open(router_abi_path, "r") as f:
                    self.router_abi = json.load(f)
            else:
                logger.error(f"路由合约ABI文件不存在: {router_abi_path}")
                return False
                
            # 加载ERC20合约ABI
            erc20_abi_path = os.path.join(abi_dir, "erc20.json")
            if os.path.exists(erc20_abi_path):
                with open(erc20_abi_path, "r") as f:
                    self.erc20_abi = json.load(f)
            else:
                logger.error(f"ERC20合约ABI文件不存在: {erc20_abi_path}")
                return False
                
            # 验证节点
            if self.chain_id in ["eth"]:
               validate_eth_endpoint(cfg.trader.private_keys['eth'], rpc_url)
            else:
               validate_bsc_endpoint(cfg.trader.private_keys['bsc'], rpc_url)   

            self.initialized = True
            logger.info(f"{self.chain_id}链初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"{self.chain_id}链初始化失败: {str(e)}", exc_info=True)
            return False
            
    async def buy_token(self, token_address: str, amount_usd: float, private_key: str) -> Optional[str]:
        """购买代币"""
        if not self.initialized:
            logger.error(f"{self.chain_id}链未初始化")
            return None
            
        try:
            # 检查路由合约地址
            router_address = self.config.get("router")
            if not router_address:
                logger.error(f"未配置{self.chain_id}链的路由合约地址")
                return None
                
            # 检查WETH地址
            weth_address = self.config.get("weth")
            if not weth_address:
                logger.error(f"未配置{self.chain_id}链的WETH地址")
                return None
                
            # 创建合约实例
            router = self.web3.eth.contract(address=router_address, abi=self.router_abi)
            
            # 获取账户地址
            account = self.web3.eth.account.from_key(private_key)
            address = account.address
            
            # 获取当前原生代币价格
            token_prices = await get_token_prices()
            native_price = token_prices.get(self.chain_id, 1000)
            
            # 计算原生代币数量
            amount = amount_usd / native_price
            
            # 转换为Wei
            amount_wei = self.web3.to_wei(amount, 'ether')
            
            # 获取当前gas价格并应用乘数
            gas_price = int(self.web3.eth.gas_price * cfg.trader.gas_price_multiplier)
            
            # 计算交易截止时间(当前时间+20分钟)
            deadline = self.web3.eth.get_block('latest').timestamp + 1200
            
            # 计算最小获得代币数量(考虑滑点)
            min_tokens_out = 0  # 这里可以根据滑点计算，暂时设为0
            
            # 构建交易
            swap_tx = router.functions.swapExactETHForTokens(
                min_tokens_out,
                [weth_address, token_address],
                address,
                deadline
            ).build_transaction({
                'from': address,
                'value': amount_wei,
                'gas': 250000,
                'gasPrice': gas_price,
                'nonce': self.web3.eth.get_transaction_count(address),
            })
            
            # 签名交易
            signed_tx = self.web3.eth.account.sign_transaction(swap_tx, private_key=private_key)
            
            # 发送交易
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            logger.info(f"交易发送成功，链: {self.chain_id}, 代币: {token_address}, 金额: ${amount_usd}, 交易哈希: {tx_hash_hex}")
            
            return tx_hash_hex
            
        except Exception as e:
            logger.error(f"购买代币失败，链: {self.chain_id}, 代币: {token_address}, 错误: {str(e)}", exc_info=True)
            return None

class SolanaChain(ChainBase):
    """Solana链"""
    def __init__(self, chain_id: str, config: Dict[str, Any]):
        super().__init__(chain_id, config)
        self.client = None
        self.jupiter_api = "https://lite-api.jup.ag/swap/v1"
        
    async def initialize(self) -> bool:
        """初始化Solana链连接"""
        try:
            # 检查RPC URL
            if "rpc" not in self.config:
                logger.error("Solana链缺少RPC URL配置")
                return False
                
            rpc_url = self.config["rpc"]    
            # 初始化Solana客户端
            self.client = AsyncClient(rpc_url)
            
           # 检查 Solana 链连接
            try:
                response = await self.client.is_connected()
                if response:
                    self.initialized = True
                    logger.info("sol链初始化成功")
                else:
                    self.initialized = False
                    logger.error("Solana 链连接失败")
            except Exception as e:
                self.initialized = False
                logger.error(f"Solana 链连接失败: {e}")
            
            # 验证节点
            validate_sol_endpoint(cfg.trader.private_keys['sol'], rpc_url)

            return self.initialized
        except Exception as e:
            logger.error(f"Solana链初始化失败: {str(e)}", exc_info=True)
            return False
            
    async def _get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int) -> Optional[Dict]:
        """获取Jupiter报价"""
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": int(cfg.trader.slippage_tolerance * 100)  # 将滑点百分比转换为基点
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.jupiter_api}/quote", params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    logger.error(f"获取Jupiter报价失败: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"获取Jupiter报价异常: {str(e)}")
            return None
            
    async def _get_jupiter_swap_tx(self, quote: Dict, user_public_key: str) -> Optional[str]:
        """获取Jupiter交换交易"""
        try:
            payload = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": True
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.jupiter_api}/swap", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("swapTransaction")
                    logger.error(f"获取Jupiter交易失败: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"获取Jupiter交易异常: {str(e)}")
            return None
            
    async def buy_token(self, token_address: str, amount_usd: float, private_key: str) -> Optional[str]:
        """购买Solana代币"""
            
        if not self.initialized:
            logger.error("Solana链未初始化")
            return None
            
        try:
            # 1. 从私钥创建Keypair
            keypair = Keypair.from_bytes(base58.b58decode(private_key))
            
            # 2.获取当前原生代币价格
            token_prices = await get_token_prices()
            sol_price = token_prices.get(self.chain_id, 100)
            
            # 3. 计算需要交换的SOL数量
            amount_lamports = int((amount_usd / sol_price) * 10**9)  # SOL有9位小数
            
            # 4. 获取Jupiter报价
            quote = await self._get_jupiter_quote(
                input_mint="So11111111111111111111111111111111111111112",  # SOL代币地址
                output_mint=token_address,
                amount=amount_lamports
            )
            if not quote:
                logger.error("获取Jupiter报价失败")
                return None
                
            # 5. 获取交换交易
            swap_tx = await self._get_jupiter_swap_tx(quote, str(keypair.pubkey()))
            if not swap_tx:
                logger.error("获取Jupiter交易失败")
                return None
                
            # Deserialize the transaction
            transaction = VersionedTransaction.from_bytes(base64.b64decode(swap_tx))
            # Sign the trasaction message
            signature = keypair.sign_message(message.to_bytes_versioned(transaction.message))
            # Sign Trasaction
            signed_tx = VersionedTransaction.populate(transaction.message, [signature])

            opts = TxOpts(skip_preflight=False, preflight_commitment=Finalized, max_retries=2)
            result = await self.client.send_raw_transaction(txn=bytes(signed_tx), opts=opts)
            tx_hash = str(result.value)  # 提取签名字符串
            logger.success(f"Solana交易成功，代币: {token_address}, 金额: ${amount_usd}, 交易哈希: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            logger.error(f"Solana链购买代币失败，代币: {token_address}, 错误: {str(e)}", exc_info=True)
            return None

class ChainTrader:
    """链上交易执行器"""
    
    # 基础链配置（不变的部分）
    BASE_CHAIN_CONFIG = {
        "eth": {
            "weth": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "explorer": "https://etherscan.io/tx/"
        },
        "bsc": {
            "weth": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "explorer": "https://bscscan.com/tx/"
        },
        "sol": {
            "explorer": "https://solscan.io/tx/"
        }
    }
    
    def __init__(self):
        """初始化交易执行器"""
        self.chains = {}
        self.chain_config = {}
        
        # 从配置中获取RPC URL和路由地址
        for chain_id in self.BASE_CHAIN_CONFIG:
            self.chain_config[chain_id] = self.BASE_CHAIN_CONFIG[chain_id].copy()
            
            # 添加RPC URL
            if chain_id in cfg.trader.rpc_urls:
                self.chain_config[chain_id]["rpc"] = cfg.trader.rpc_urls[chain_id]
            
            # 添加路由合约地址
            if chain_id in cfg.trader.router_addresses:
                self.chain_config[chain_id]["router"] = cfg.trader.router_addresses[chain_id]
        
        logger.info("链上交易执行器初始化完成")
    
    async def initialize_chains(self):
        """初始化所有链"""
        for chain_id, config in self.chain_config.items():
            if chain_id == "sol":
                chain = SolanaChain(chain_id, config)
            else:
                chain = EvmChain(chain_id, config)
                
            # 初始化链
            success = await chain.initialize()
            if success:
                self.chains[chain_id] = chain
            else:
                logger.warning(f"{chain_id}链初始化失败，该链的交易功能将不可用")
    
    async def buy_token(self, chain: str, token_address: str, amount_usd: float = None) -> Optional[str]:
        """
        购买代币
        
        Args:
            chain: 链名称(eth, bsc, sol等)
            token_address: 代币合约地址
            amount_usd: 交易金额(美元)，如果为None则使用默认金额
            
        Returns:
            Optional[str]: 交易哈希，如果失败则返回None
        """
        # 使用配置中的默认金额
        if amount_usd is None:
            amount_usd = cfg.trader.default_trade_amount_usd
            
        # 检查链是否支持
        if chain not in self.chain_config:
            logger.error(f"不支持的链: {chain}")
            return None
            
        # 检查链是否已初始化
        if chain not in self.chains:
            # 尝试初始化该链
            if chain == "sol":
                chain_obj = SolanaChain(chain, self.chain_config[chain])
            else:
                chain_obj = EvmChain(chain, self.chain_config[chain])
                
            success = await chain_obj.initialize()
            if success:
                self.chains[chain] = chain_obj
            else:
                logger.error(f"{chain}链未初始化，无法执行交易")
                return None
            
        # 获取私钥
        private_key = cfg.trader.private_keys.get(chain)
        if not private_key:
            logger.error(f"未配置{chain}链的私钥")
            return None
            
        # 执行交易
        return await self.chains[chain].buy_token(token_address, amount_usd, private_key)
        
    def get_tx_explorer_url(self, chain: str, tx_hash: str) -> str:
        """获取交易浏览器URL"""
        if chain in self.chains:
            return self.chains[chain].get_explorer_url(tx_hash)
        elif chain in self.chain_config and "explorer" in self.chain_config[chain]:
            return f"{self.chain_config[chain]['explorer']}{tx_hash}"
        return ""


async def get_token_prices():
    """
    从 CoinGecko API 获取 ETH、BNB 和 SOL 的实时代币价格
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "ethereum,binancecoin,solana",
        "vs_currencies": "usd"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "eth": data["ethereum"]["usd"],
                    "bsc": data["binancecoin"]["usd"],
                    "sol": data["solana"]["usd"]
                }
            else:
                error_msg = f"获取代币价格失败，状态码: {response.status}"
                logger.error(error_msg)
                raise Exception(error_msg)