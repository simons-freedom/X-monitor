import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv
from loguru import logger

# 加载.env文件
load_dotenv()

@dataclass
class LlmConfig:
    """大模型配置"""
    api_key: str
    base_url: str
    model: str

@dataclass
class TraderConfig:
    """交易配置"""
    enabled: bool = False  # 是否启用自动交易
    private_keys: Dict[str, str] = None  # 各链的钱包私钥
    rpc_urls: Dict[str, str] = None  # 各链的RPC URL
    router_addresses: Dict[str, str] = None  # 各链的路由合约地址
    gas_price_multiplier: float = 1.1  # gas价格乘数
    slippage_tolerance: float = 0.05  # 滑点容忍度
    max_trade_amount_usd: float = 100  # 最大交易金额(美元)
    min_liquidity_usd: float = 10000  # 最小流动性要求(美元)
    min_volume_usd: float = 5000  # 最小交易量要求(美元)
    default_trade_amount_usd: float = 20  # 默认交易金额(美元)
    high_confidence_amount_usd: float = 50  # 高置信度交易金额(美元)
    medium_confidence_amount_usd: float = 30  # 中置信度交易金额(美元)
    min_confidence: float = 0.6  # 最小置信度要求
    max_price_change_1h: float = 20  # 最大1小时价格变化百分比

    def __post_init__(self):
        # 确保字典字段初始化
        if self.private_keys is None:
            self.private_keys = {}
        if self.rpc_urls is None:
            self.rpc_urls = {}
        if self.router_addresses is None:
            self.router_addresses = {}

@dataclass
class DingTalkConfig:
    """钉钉机器人配置"""
    token: str = ""  # 钉钉机器人token
    secret: str = ""  # 钉钉机器人加签密钥


class Config:
    """全局配置"""
    def __init__(self, llm: LlmConfig = None, trader: TraderConfig = None, dingtalk: DingTalkConfig = None):
        self.llm = llm
        self.trader = trader if trader else TraderConfig()
        self.dingtalk = dingtalk if dingtalk else DingTalkConfig()

def load_config() -> Config:
    """加载配置"""
    try:
        # 加载LLM配置
        llm_config = LlmConfig(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("LLM_MODEL", "gpt-4")
        )
        
        # 加载交易配置
        trader_config = TraderConfig(
            enabled=os.getenv("TRADER_ENABLED", "false").lower() == "true",
            private_keys={
                "eth": os.getenv("ETH_PRIVATE_KEY", ""),
                "bsc": os.getenv("ETH_PRIVATE_KEY", ""),
                "sol": os.getenv("SOL_PRIVATE_KEY", "")
            },
            rpc_urls={
                "eth": os.getenv("ETH_RPC_URL", ""),
                "bsc": os.getenv("BSC_RPC_URL", ""),
                "sol": os.getenv("SOL_RPC_URL", "")
            },
            router_addresses={
                "eth": os.getenv("ETH_ROUTER_ADDRESS", ""),
                "bsc": os.getenv("BSC_ROUTER_ADDRESS", "")
            },
            gas_price_multiplier=float(os.getenv("GAS_PRICE_MULTIPLIER", "1.1")),
            slippage_tolerance=float(os.getenv("SLIPPAGE_TOLERANCE", "0.05")),
            max_trade_amount_usd=float(os.getenv("MAX_TRADE_AMOUNT_USD", "100")),
            min_liquidity_usd=float(os.getenv("MIN_LIQUIDITY_USD", "10000")),
            min_volume_usd=float(os.getenv("MIN_VOLUME_USD", "5000")),
            default_trade_amount_usd=float(os.getenv("DEFAULT_TRADE_AMOUNT_USD", "20")),
            high_confidence_amount_usd=float(os.getenv("HIGH_CONFIDENCE_AMOUNT_USD", "50")),
            medium_confidence_amount_usd=float(os.getenv("MEDIUM_CONFIDENCE_AMOUNT_USD", "30")),
            min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.6")),
            max_price_change_1h=float(os.getenv("MAX_PRICE_CHANGE_1H", "20"))
        )
        
        # 加载钉钉配置
        dingtalk_config = DingTalkConfig(
            token=os.getenv("DINGTALK_TOKEN", ""),
            secret=os.getenv("DINGTALK_SECRET", ""),
        )
        
        # 创建全局配置
        config = Config(
            llm=llm_config,
            trader=trader_config,
            dingtalk=dingtalk_config
        )
        
        logger.info("配置加载成功")
        return config
    except Exception as e:
        logger.error(f"加载配置时出错: {str(e)}", exc_info=True)
        raise

# 创建全局配置实例
cfg = load_config()