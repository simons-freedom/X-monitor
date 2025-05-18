import requests
from datetime import datetime
from openai import AsyncOpenAI
from typing import Dict, List, Optional, Any
import json
import base64
from core.processor import TwitterLinkProcessor
from core.data_def import Msg


import asyncio

import time
from loguru import logger
from dataclasses import dataclass
from typing import List, Optional

class LlmAnalyzer:
    """大模型分析器，用于分析推文内容"""

    def __init__(self, api_key: str , base_url: str , model: str):
        """初始化 AI 处理器

        Args:
            api_key (str): API密钥
            base_url (str, optional): API基础URL. Defaults to OPENAI_BASE_URL.
            model (str, optional): 模型名称. Defaults to OPENAI_MODEL.
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url.rstrip('/'),
        )
        self.model = model


    def _encode_image_from_url(self, image_url: str) -> Optional[str]:
        """
        从URL获取图片并转换为base64格式

        Args:
            image_url: 图片URL

        Returns:
            str: base64编码的图片数据
        """
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            return base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            logger.error(f"获取图片失败: {str(e)}")
            return None

    def _encode_image_from_file(self, image_path: str) -> Optional[str]:
        """
        从本地文件读取图片并转换为base64格式

        Args:
            image_path: 图片文件路径

        Returns:
            str: base64编码的图片数据
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"读取图片文件失败: {str(e)}")
            return None



    async def analyze_image(
            self,
            image_source: str,
            is_url: bool = False,
            prompt: str = "请详细描述这张图片的内容",
            max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        分析图片内容

        Args:
            image_source: 图片URL或本地文件路径
            is_url: 是否为URL
            prompt: 分析提示
            max_tokens: 最大返回token数

        Returns:
            Dict: 分析结果
        """
        try:
            logger.info(f'开始分析图片{image_source}')
            # 获取base64编码的图片
            image_base64 = (
                self._encode_image_from_url(image_source) if is_url
                else self._encode_image_from_file(image_source)
            )

            if not image_base64:
                return {"error": "图片编码失败"}

            # 准备API请求，使用await等待异步操作完成
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens
            )

            # 保存结果
            result = {
                "timestamp": datetime.now().isoformat(),
                "analysis": response.choices[0].message.content,
                "prompt": prompt,
                "status": "success"
            }

            return result

        except Exception as e:
            logger.error(f"分析图片时出错: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "status": "error"
            }


    async def analyze_content(self, tweet_msg: Msg) -> Optional[dict]:
        """
        统一的内容分析方法，可以同时处理文本和图片内容
        Args:
            tweet_text: 推文文本内容
        Returns:
            AIAnalysisResult: 分析结果，包含发现的代币信息
        """
        try:
            tweet_text = tweet_msg.content
            image_ai_analysis = None
            try:
                image_url = await TwitterLinkProcessor.extract_image_url(tweet_text)
                if image_url:
                    logger.info(f"找到推文中的图片链接{image_url}")
                    result = await self.analyze_image(
                        image_source=image_url,
                        is_url=True,
                        prompt="请详细描述这张图片中的内容，包括主要元素、场景和任何值得注意的细节"
                    )
                    if result["status"] == "success":
                        logger.info(f"分析结果:{result}")
                        result_ana = result.get("analysis")
                        if result_ana:
                            image_ai_analysis = result_ana
                    else:
                        logger.error(f'图片分析失败, {result}')
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f'图片解析处理失败， {e}')
            # 后续代码确保没有对字典对象使用 await
            if tweet_msg.push_type == "new_description":
               tweet_text  = f'修改了用户简介,新的简介为:{tweet_text}'
            # 准备消息内容
            messages = [
                {
                    "role": "system",
                    "content": """你是一个加密货币领域的专家，特别擅长识别新发行的代币和小市值代币。
                    你了解加密货币市场的各种现象，包括：
                    1. 土狗币的常见命名模式（如模因、热点话题等）
                    2. 营销话术和炒作手法
                    3. 代币发行和预售的典型流程
                    4. 社区运营和传播策略
                    请基于这些知识，帮助分析内容中可能涉及的新代币。"""
                }
            ]

            # 构建用户消息
            user_content = [
                {
                    "type": "text",
                    "text": f"""分析这条推文内容，重点关注以下几个方面：

推文内容：
{tweet_text}

分析要点：
1. 直接相关信息：
   - 代币名称或符号
   - 价格信息和走势
   - 交易所信息
   - 图表或技术指标

2. 潜在影响因素：
   - 是否包含知名人物（如Elon Musk）或热门话题
   - 是否涉及热门meme元素或梗图
   - 是否包含可能引发新meme代币的关键词或概念
   - 是否有病毒式传播的潜力

3. 市场影响分析：
   - 内容与现有meme代币的关联度
   - 可能对哪些代币价格产生影响
   - 传播影响力评估

4. 情感分析：
   - 推文的整体情感倾向
   - 社区反应预测
   - 市场情绪影响

请用JSON格式返回分析结果,格式如下:
{{
    "speculate_result": [
        {{
            "token_name": "已有或潜在的代币名称（这个字段只展示代币名，不要附加任何额外的信息",
            "reason": "详细分析原因",
            "key_elements": ["关键影响元素"]
        }}
    ]
}}
如果没有发现比较确定的代币信息，请返回空。

注意：
1. 代币名称为单个英文单词
2. reason 需要详细解释为什么认为这是土狗币
3. 如果提到多个代币,按可能性从高到低排序,最多返回3个
4. 严格过滤:BTC、ETH、USDT、SOL、TON、DOGE、XRP、BCH、LTC、BNB等主流代币和已上架大型交易所的代币都不应该包含在结果中
5. 如果无法确定是土狗币，返回空列表
6. 如果不是推文中提到,不要给代币名添加Token或者Coin之类的字符
7. 推文内容存在"@xxx"格式，大概率是某个用户用户名，不要分析为代币，请忽略
8. 返回的代币名称,不能包含币对信息,例如BTC-USDT,只返回BTC
9. 如果只是提到主流代币（如比特币、以太坊等）或者只是讨论行情，应该返回空列表


{f"推文中存在图片,以下内容为图片内容描述,请结合起来分析,图片中也可能包含meme币信息: {image_ai_analysis}" if image_ai_analysis else ""}
"""

                }
            ]

            messages.append({
                "role": "user",
                "content": user_content
            })

            request_start_time = time.time()
            # 调用 API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            logger.info(f"AI analysis took {time.time() - request_start_time:.2f} seconds")

            if not response.choices:
                logger.error(f"Invalid API response: {response}")
                return None

            result = response.choices[0].message.content
            logger.info(f"API Response: {result}")

            try:
                # 处理可能的 markdown 代码块
                if '```' in result:
                    parts = result.split('```')
                    for part in parts:
                        if '{' in part and '}' in part:
                            # 移除可能的语言标识符 (如 'json')
                            if part.strip().startswith('json'):
                                part = part[4:]
                            result = part.strip()
                            break

                # 解析JSON并创建AIAnalysisResult实例
                parsed_result = json.loads(result)
                # return AIAnalysisResult.from_dict(parsed_result)
                return parsed_result
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response as JSON: {result}")
                return None
            except Exception as e:
                logger.error(f"Error processing AI response: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Error analyzing content: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None



@dataclass
class TokenInfo:
    chain: str                          # 链名：ETH/BSC等
    symbol: str                         # 代币符号
    name: str                           # 代币名称
    decimals: int                       # 代币精度
    address: str                        # 合约地址
    price: float                        # 当前价格
    price_1h: float                     # 1小时前价格
    price_24h: float                    # 24小时前价格
    swaps_5m: int                       # 5分钟内交易次数
    swaps_1h: int                       # 1小时内交易次数
    swaps_6h: int                       # 6小时内交易次数
    swaps_24h: int                      # 24小时内交易次数
    volume_24h: float                   # 24小时交易量
    liquidity: float                    # 流动性
    total_supply: int                   # 总供应量
    symbol_len: int                     # 符号长度
    name_len: int                       # 名称长度
    is_in_token_list: bool              # 是否在官方代币列表中
    logo: Optional[str] = None          # logo地址
    hot_level: int = 0                  # 热度等级，默认值为 0
    is_show_alert: bool = False         # 是否显示警告，默认值为 False
    buy_tax: Optional[float] = None     # 买入税
    sell_tax: Optional[float] = None    # 卖出税
    is_honeypot: Optional[bool] = None  # 是否为蜜罐
    renounced: Optional[bool] = None    # 是否放弃所有权
    top_10_holder_rate: Optional[float] = None  # 前10持有者占比
    renounced_mint: Optional[int] = None  # 铸币权限状态
    renounced_freeze_account: Optional[int] = None  # 冻结账户权限状态
    burn_ratio: str = '0%'              # 销毁比例，默认值为 0%
    burn_status: str = '未知'           # 销毁状态，默认值为 未知
    pool_create_time: Optional[Any] = None  # 新增字段，用于存储池创建时间，设置默认值为 None
    is_open_source: Optional[bool] = None    # 是否开源，设置默认值为 None

    """
    {'symbol': 'TABBY', 'name': "Trump's Tender Tabby", 'decimals': 9, 'logo': '', 'address': '0xec533e2b6a64f861cdfa47257f95d7f1d976c12e', 'price': '0.00000000000000000000', 'price_1h': '0.00000000000000000000', 'price_24h': '0.00000000000000000000', 'swaps_5m': 0, 'swaps_1h': 0, 'swaps_6h': 0, 'swaps_24h': 0, 'volume_24h': '0.00000000000000000000', 'liquidity': '922324.72420832840000000000', 'total_supply': 0, 'symbol_len': 5, 'name_len': 20, 'is_in_token_list': False, 'pool_create_time': None, 'buy_tax': None, 'sell_tax': None, 'is_honeypot': None, 'is_open_source': None, 'renounced': None, 'chain': 'bsc'}
    """

@dataclass
class TokenSearchResponse:
    tokens: List[TokenInfo]
    time_taken: int

@dataclass
class TokenSearchResult:
    code: int
    msg: str
    data: TokenSearchResponse


class TokenSearcher:
    """代币搜索器，用于搜索代币信息"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        初始化代币搜索器
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟时间(秒)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def parse_token_search_response(self, response_data: dict) -> TokenSearchResult:
        """
        解析API响应数据为TokenSearchResult对象
        
        Args:
            response_data: API原始响应数据
            
        Returns:
            TokenSearchResult: 解析后的结果对象
        """
        try:
            # 获取data字段，如果不存在则使用空字典
            data = response_data.get('data', {})

            # 解析代币列表
            tokens = [TokenInfo(**token_data) for token_data in data.get('tokens', [])]
            
            # 过滤并处理代币列表
            filtered_tokens = self._filter_tokens(tokens)

            # 创建TokenSearchResponse
            search_response = TokenSearchResponse(
                tokens=filtered_tokens,
                time_taken=data.get('timeTaken', 0)
            )

            # 创建并返回最终结果
            return TokenSearchResult(
                code=response_data.get('code', 0),
                msg=response_data.get('msg', ''),
                data=search_response
            )
        except Exception as e:
            logger.error(f"解析响应数据时出错: {str(e)}")
            logger.debug(f"原始响应数据: {response_data}")
            raise
    
    def _filter_tokens(self, tokens: List[TokenInfo]) -> List[TokenInfo]:
        """
        过滤代币列表，移除不符合条件的代币
        
        过滤条件:
        1. 过滤掉被警告的币种
        2. 过滤掉蜜罐币种
        3. 过滤掉没有放弃所有权的币种
        4. 过滤掉前10持有者占比超过30%的币种
        5. 过滤掉24小时交易量小于5000的币种
        
        Args:
            tokens: 原始代币列表
            
        Returns:
            List[TokenInfo]: 过滤后的代币列表
        """
        if not tokens:
            return []
            
        # 第一步：过滤掉不符合安全条件的代币
        safe_tokens = []
        for token in tokens:
            # 跳过被警告的币种
            if token.is_show_alert:
                logger.debug(f"过滤掉被警告的币种: {token.name} ({token.symbol})")
                continue
                
            # 跳过蜜罐币种
            if token.is_honeypot is True:
                logger.debug(f"过滤掉蜜罐币种: {token.name} ({token.symbol})")
                continue
                
            # 跳过没有放弃所有权的币种
            if token.renounced is False:
                # 增加打印 address 信息
                logger.debug(f"过滤掉没有放弃所有权的币种: {token.name} ({token.symbol}), 地址: {token.address}")
                continue
                
            # 跳过前10持有者占比超过30%的币种
            if token.top_10_holder_rate is not None and token.top_10_holder_rate > 0.3:
                # 增加打印 address 信息
                logger.debug(f"过滤掉前10持有者占比超过30%的币种: {token.name} ({token.symbol}), 占比: {token.top_10_holder_rate}, 地址: {token.address}")
                continue
                
            # 跳过24小时交易量小于5000的币种
            try:
                volume_24h = float(token.volume_24h)
                if volume_24h < 5000:
                    # 增加打印 address 信息
                    logger.debug(f"过滤掉24小时交易量小于5000的币种: {token.name} ({token.symbol}), 交易量: {volume_24h}, 地址: {token.address}")
                    continue
            except ValueError:
                logger.error(f"无法将 {token.volume_24h} 转换为浮点数，跳过 {token.name} ({token.symbol})")
                continue

            safe_tokens.append(token)

        # 按24小时交易量从大到小排序
        safe_tokens.sort(key=lambda x: float(x.volume_24h), reverse=True)
        
        logger.info(f"原始代币数量: {len(tokens)}, 过滤后代币数量: {len(safe_tokens)}")
        return safe_tokens

    async def search_token_inner(self, token_name: str, chain: str) -> TokenSearchResponse:
        from curl_cffi import requests

        # 请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Referer': 'https://gmgn.ai/',
            'Origin': 'https://gmgn.ai'
        }

        try:
            # 构建请求 URL
            url = f'https://gmgn.ai/defi/quotation/v1/tokens/{chain}/search?q={token_name}'
            # 使用curl_cffi进行请求，它支持更好的浏览器模拟
            response = requests.get(
                url,
                headers=headers,
                impersonate='chrome120',
                verify=False
            )

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"API响应数据获取成功，链: {chain}")
                token_search_response = self.parse_token_search_response(data).data
                return token_search_response
            else:
                logger.error(f"请求失败，链: {chain}, 状态码: {response.status_code}")
                raise Exception(f"请求失败，链: {chain}, 状态码: {response.status_code}")

        except Exception as e:

            logger.error(f"发生错误，链: {chain}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())


            raise Exception(f"发生错误，链: {chain}: {str(e)}")

    async def search_token(self, token_name: str) -> Optional[TokenSearchResponse]:
        """
        搜索代币信息，并发查询 sol 和 bsc 链，并合并结果，不做去重
        
        Args:
            token_name: 代币名称
            
        Returns:
            TokenSearchResponse: 合并后的代币搜索结果，失败返回None
        """
        chains = ['sol', 'bsc']
        tasks = [self.search_token_inner(token_name, chain) for chain in chains]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_tokens = []
        total_time_taken = 0
        valid_results_count = 0

        for chain, result in zip(chains, results):
            if isinstance(result, Exception):
                logger.error(f"查询 {chain} 链失败: {result}")
            else:
                all_tokens.extend(result.tokens)
                total_time_taken += result.time_taken
                valid_results_count += 1

        if valid_results_count == 0:
            return None

        average_time_taken = total_time_taken // valid_results_count if valid_results_count > 0 else 0
        merged_response = TokenSearchResponse(
            tokens=all_tokens,
            time_taken=average_time_taken
        )

        return merged_response

    
    async def batch_search_tokens(self, token_names: List[str], concurrency: int = 3) -> Dict[str, Optional[TokenSearchResponse]]:
        """
        批量搜索多个代币，并发执行
        
        Args:
            token_names: 代币名称列表
            concurrency: 最大并发数
            
        Returns:
            Dict[str, TokenSearchResponse]: 代币名称到搜索结果的映射
        """
        results = {}
        semaphore = asyncio.Semaphore(concurrency)
        
        async def search_with_semaphore(token_name: str):
            async with semaphore:
                return token_name, await self.search_token(token_name)
        
        tasks = [search_with_semaphore(name) for name in token_names]
        for completed_task in asyncio.as_completed(tasks):
            name, result = await completed_task
            results[name] = result
        
        return results


async def main():
    """测试函数"""
    try:
        # 创建代币搜索器
        searcher = TokenSearcher(max_retries=3, retry_delay=1.0)
        
        # 测试单个代币搜索
        print('正在搜索单个代币...')
        token_result = await searcher.search_token('Trump')
        if token_result:
            print(f"找到 {len(token_result.tokens)} 个代币")
            for token in token_result.tokens[:3]:  # 只显示前3个结果
                print(f"代币: {token.name} ({token.symbol}),链:{token.chain}, 合约地址:{token.address} 价格: {token.price}")
        else:
            print("未找到代币或搜索失败")
        
        # 测试批量搜索
        print('\n正在批量搜索代币...')
        batch_results = await searcher.batch_search_tokens(['Trump', 'Pepe', 'Doge'], concurrency=2)
        for name, result in batch_results.items():
            if result:
                print(f"{name}: 找到 {len(result.tokens)} 个代币")
            else:
                print(f"{name}: 搜索失败")
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('搜索过程中出错:', e)

if __name__ == "__main__":
    asyncio.run(main())