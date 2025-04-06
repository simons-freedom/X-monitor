from quart import Quart, request, jsonify 
import asyncio
import json
from loguru import logger
from typing import Optional, List, Dict, Any 
from config import cfg 
from analyzer import LlmAnalyzer, TokenSearcher
from data_def import PushMsg, User, Tweet
import notice  
from trader import ChainTrader  # 导入交易模块


# 假设这些类和函数已经定义
class TwitterMonitor:
    def __init__(self, host='0.0.0.0', port=9999):
        """
        初始化Twitter监控服务
        
        Args:
            host: 监听主机地址
            port: 监听端口
        """
        self.app = Quart(__name__)  # 创建 Quart 应用实例
        self.host = host
        self.port = port
        
        
        # 初始化AI分析器
        self.analyzer = LlmAnalyzer(
            api_key=cfg.llm.api_key,
            base_url=cfg.llm.base_url,
            model=cfg.llm.model
        )
        
        # 初始化代币搜索器
        self.token_searcher = TokenSearcher(max_retries=3, retry_delay=1.0)
        
        # 初始化交易执行器(如果启用)
        self.trader = None
        if cfg.trader.enabled and cfg.trader.private_keys:
            self.trader = ChainTrader()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.trader.initialize_chains())
            logger.info("自动交易功能已启用")
        else:
            logger.info("自动交易功能未启用")
        
        # 注册路由
        self._register_routes()
        
        logger.info(f"Twitter监控服务初始化完成,监听地址: {host}:{port}")

    def _register_routes(self):
        """注册API路由"""
        @self.app.route('/post/tweet', methods=['POST'])
        async def receive_tweet():
            try:
                data = await request.get_data()  # Quart 中获取数据需要异步操作
                data = data.decode('utf-8')
                if not data:
                    return jsonify({"status": "error", "message": "Invalid or missing json data"}), 400

                logger.debug(f"收到原始数据: {data}")

                # 解析推文数据
                push_msg: PushMsg = self._parse_tweet_data(data)
                if not push_msg:
                    return jsonify({"status": "error", "message": "Failed to parse tweet data"}), 400

                logger.info(f"解析后的推文数据: {push_msg}")

                # 发送通知
                notice.send_notice_msg(f'监听到X推文: {push_msg.title}-{push_msg.content}')

                # 异步执行任务
                asyncio.create_task(self._analyze_tweet(push_msg))

                return jsonify({
                    "status": "success",
                    "message": "Tweet received and analysis started asynchronously"
                }), 200
            except Exception as e:
                logger.error(f"处理推文时发生错误: {str(e)}", exc_info=True)
                return jsonify({"status": "error", "message": str(e)}), 500

    def _parse_tweet_data(self, raw_data) -> Optional[PushMsg]:
        """
        解析推文数据
        
        Args:
            raw_data: 原始JSON字符串
            
        Returns:
            Optional[PushMsg]: 解析后的推文数据，如果解析失败则返回None
        """
        try:
            data = json.loads(raw_data)
            user = User(**data["user"])
            
            # 根据推送类型处理不同的数据结构
            push_type = data.get("push_type", "")
            
            # 只有new_tweet类型才有tweet数据
            if push_type == "new_tweet" and "tweet" in data:
                tweet = Tweet(**data["tweet"])
            else:
                # 其他类型的推送，tweet对象设为None
                tweet = None
            
            return PushMsg(
                push_type=data["push_type"],
                title=data["title"],
                content=data["content"],
                user=user,
                tweet=tweet
            )
        except Exception as e:
            logger.error(f"解析JSON数据失败: {str(e)}", exc_info=True)
            return None

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

    async def _analyze_tweet(self, tweet_msg: PushMsg):
        """
        分析推文内容
        
        Args:
            tweet_data: 解析后的推文数据
        
        Returns:
            dict: 分析结果
        """
        try:
            tweet_author = tweet_msg.user.screen_name
            tweet_content = tweet_msg.content
            logger.info(f"开始分析推文内容: {tweet_author}-{tweet_content[:100]}...")
        
            # 调用AI分析器分析内容
            analysis_result = await self.analyzer.analyze_content(tweet_msg)
        
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

    def start(self):
        """启动Twitter监控服务"""
        logger.info("Twitter监控服务启动中...")
        try:
            self.app.run(host=self.host, port=self.port)
        except Exception as e:
            logger.error(f"服务启动失败: {str(e)}", exc_info=True)
        finally:
            logger.info("Twitter监控服务已停止")


if __name__ == "__main__":
    monitor = TwitterMonitor(host='0.0.0.0', port=9999)
    monitor.start()
