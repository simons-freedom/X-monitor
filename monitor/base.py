import asyncio
from loguru import logger
from config.config import cfg 
from core.analyzer import LlmAnalyzer, TokenSearcher
from core.data_def import Msg
import notify.notice as notice  
from core.trader import ChainTrader 


class BaseMonitor:
    """监控器基类，包含公共逻辑"""
    def __init__(self):
        # 初始化公共组件
        self.analyzer = LlmAnalyzer(
            api_key=cfg.llm.api_key,
            base_url=cfg.llm.base_url,
            model=cfg.llm.model
        )
        self.token_searcher = TokenSearcher(max_retries=3, retry_delay=1.0)
        self.trader = self._init_trader()
        
    def _init_trader(self):
        """初始化交易模块（公共方法）"""
        if cfg.trader.enabled and cfg.trader.private_keys:
            trader = ChainTrader()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(trader.initialize_chains())
            logger.info("自动交易功能已启用")
            return trader
        logger.info("自动交易功能未启用")
        return None

    async def process_message(self, message:Msg):
        return await self._analyze_message(message)

    async def _analyze_message(self, msg: Msg): 

        try:
            tweet_author = msg.screen_name
            tweet_content = msg.content
            logger.info(f"开始分析推文内容: {tweet_author}-{tweet_content[:100]}...")
        
            # 调用AI分析器分析内容
            analysis_result = await self.analyzer.analyze_content(msg)
        
            # 记录分析结果
            logger.info(f"推文分析完成，结果: {analysis_result}")
        
            # 如果发现了代币信息，搜索代币并发送详细通知
            if analysis_result and "speculate_result" in analysis_result:
                tokens = analysis_result["speculate_result"]
                if tokens and len(tokens) > 0:
                    # 提取代币名称
                    token_names = [token["token_name"] for token in tokens]
                    logger.info(f"发现潜在代币: {token_names}")
        
                    # 搜索代币信息
                    search_results = await self._search_tokens(token_names)
        
                    # 格式化通知信息，同时获取 token 列表
                    notification, token_list = self._format_token_notification(token_names, search_results, tweet_author, tweet_content)
        
                    # 生成按钮信息
                    btn_info = []
                    
                    # 执行自动交易并记录交易结果
                    trade_results = []
                    
                    for token in token_list:
                        chain = str(token.chain).lower()
                        address = token.address
                        token_symbol = token.symbol
                        
                        # 添加按钮信息
                        btn_info.append((f'BUY-{chain.upper()}-{token_symbol}', f"https://gmgn.ai/{chain}/token/{address}"))
                        
                        # 执行自动交易(如果启用)
                        if self.trader and self._should_trade(token):
                            tx_hash = await self.trader.buy_token(chain, address)
                            if tx_hash:
                                explorer_url = self.trader.get_tx_explorer_url(chain, tx_hash)
                                trade_results.append({
                                    "chain": chain,
                                    "token": token_symbol,
                                    "address": address,
                                    "tx_hash": tx_hash,
                                    "explorer_url": explorer_url
                                })
                                
                                # 添加交易查看按钮
                                if explorer_url:
                                    btn_info.append((f'查看交易-{chain.upper()}-{token_symbol}', explorer_url))
                    
                    # 如果有交易结果，添加到通知中
                    if trade_results:
                        notification += "\n\n🔄 **自动交易执行结果**:\n"
                        for result in trade_results:
                            notification += f"- **{result['token']}** ({result['chain'].upper()}):\n"
                            notification += f"  - 交易哈希: `{result['tx_hash']}`\n"
                    
                    # 发送钉钉 ActionCard 消息
                    notice.send_warn_action_card(
                        "交易通知",  
                        notification,
                        "0",
                        *btn_info
                    )
        
            return analysis_result
        except Exception as e:
            logger.error(f"分析推文内容时出错: {str(e)}", exc_info=True)
            return {"error": str(e)}

    async def _search_tokens(self, token_names):
        """
        搜索代币信息
        
        Args:
            token_names: 代币名称列表
            
        Returns:
            dict: 代币名称到搜索结果的映射
        """
        try:
            # 使用代币搜索器批量搜索代币
            search_results = await self.token_searcher.batch_search_tokens(token_names, concurrency=3)
            logger.info(f"代币搜索完成，找到 {len(search_results)} 个结果")
            return search_results
        except Exception as e:
            logger.error(f"搜索代币时出错: {str(e)}", exc_info=True)
            return {}


    def _format_token_notification(self, token_names, search_results, tweet_author, tweet_content):
        """
        格式化代币通知信息

        Args:
            token_names: 代币名称列表
            search_results: 搜索结果
            tweet_content: 推文内容

        Returns:
            tuple: 包含格式化后的通知信息和对应的 token 列表
        """
        # 基本通知信息
        notification = f"🚨 发现潜在代币信息!\n\n"
        notification += f"📱 推文内容:\n{tweet_author}-{tweet_content[:150]}...\n\n"
        notification += f"🔍 发现代币: {', '.join(token_names)}\n\n"

        # 存储 token 信息
        token_list = []

        # 添加代币详细信息
        if search_results:
            notification += "📊 代币详情:\n"
            for token_name in token_names:
                result = search_results.get(token_name)
                if not result or not result.tokens:
                    notification += f"- {token_name}: 未找到详细信息\n"
                    continue

                # 只取第一个结果（已经按交易量排序）
                token = result.tokens[0]
                # 将 token 添加到列表中
                token_list.append(token)

                # 格式化价格变化百分比
                price_change_1h = ((token.price / token.price_1h) - 1) * 100 if token.price_1h else 0
                price_change_24h = ((token.price / token.price_24h) - 1) * 100 if token.price_24h else 0

                # 添加代币信息，使用代码格式便于复制
                notification += f"- **{token.name} ({token.symbol})** \n"
                notification += f"  - **链**: {token.chain}\n"
                notification += f"  - **地址**: `{token.address}`\n"
                notification += f"  - **价格**: ${token.price:.8f}\n"
                notification += f"  - **1小时变化**: {price_change_1h:.2f}%\n"
                notification += f"  - **24小时变化**: {price_change_24h:.2f}%\n"
                notification += f"  - **24小时交易量**: ${token.volume_24h:.2f}\n"
                notification += f"  - **流动性**: ${token.liquidity:.2f}\n"

        return notification, token_list


    def _should_trade(self, token) -> bool:
        """
        判断是否应该交易该代币
        
        Args:
            token: 代币信息
            
        Returns:
            bool: 是否应该交易
        """
        try:
            # 检查流动性
            if token.liquidity < cfg.trader.min_liquidity_usd:
                logger.info(f"代币 {token.symbol} 流动性不足 (${token.liquidity:.2f} < ${cfg.trader.min_liquidity_usd})")
                return False
                
            # 检查1小时价格变化
            if token.price_1h:
                price_change_1h = abs(((token.price / token.price_1h) - 1) * 100)
                if price_change_1h > cfg.trader.max_price_change_1h:
                    logger.info(f"代币 {token.symbol} 1小时价格变化过大 ({price_change_1h:.2f}% > {cfg.trader.max_price_change_1h}%)")
                    return False
            
            # 通过所有检查
            return True
            
        except Exception as e:
            logger.error(f"判断是否应该交易代币时出错: {str(e)}")
            return False
