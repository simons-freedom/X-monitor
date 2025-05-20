
from quart import Quart, request, jsonify 
import asyncio
import json
from loguru import logger
from typing import Optional
from core.data_def import PushMsg, User, Tweet,Msg
from monitor.base import BaseMonitor

class WebhookMonitor(BaseMonitor):
    def __init__(self, host='0.0.0.0', port=9999):
        super().__init__()  # 继承基类初始化
        self.app = Quart(__name__)
        self.host = host
        self.port = port
        self._register_routes()
        logger.info(f"HTTP监控服务初始化完成,监听地址: {host}:{port}")

    def _register_routes(self):
        """注册API路由"""
        @self.app.route('/post/tweet', methods=['POST'])
        async def receive_tweet():
            try:
                data = await request.get_data() 
                data = data.decode('utf-8')
                if not data:
                    return jsonify({"status": "error", "message": "Invalid or missing json data"}), 400

                logger.debug(f"收到原始数据: {data}")

                # 解析推文数据
                push_msg: PushMsg = self._parse_tweet_data(data)
                if not push_msg:
                    return jsonify({"status": "error", "message": "Failed to parse tweet data"}), 400

                logger.info(f"解析后的推文数据: {push_msg}")

                msg:Msg = Msg(
                    push_type=push_msg.push_type,
                    title=push_msg.title,
                    content=push_msg.content,
                    name=push_msg.user.name,
                    screen_name=push_msg.user.screen_name
                )

                # 异步处理推文
                asyncio.create_task(self.process_message(msg))

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



    def start(self):
        """启动Twitter监控服务"""
        logger.info("Twitter监控服务启动中...")
        try:
            self.app.run(host=self.host, port=self.port)
        except Exception as e:
            logger.error(f"服务启动失败: {str(e)}", exc_info=True)
        finally:
            logger.info("Twitter监控服务已停止")