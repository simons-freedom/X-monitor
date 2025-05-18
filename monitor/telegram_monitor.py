from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel, PeerChat
from monitor.base import BaseMonitor  # 继承基类
from core.data_def import  Msg
import requests,re


class TelegramMonitor(BaseMonitor):
    """Telegram监控器"""
    
    def __init__(self, api_id, api_hash,target_chat_id):
        super().__init__()
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = TelegramClient('transfer', api_id, api_hash)
        self.monitor_targets = {
            "消息推送Chanel/Group": target_chat_id,
        }
        self.target_list = self._build_target_list()
        self._register_handlers()

    def _build_target_list(self):
        """构建监控目标列表"""
        return [
            PeerChannel(target_id) if str(target_id).startswith("-100") 
            else PeerChat(target_id)
            for target_id in self.monitor_targets.values()
        ]

    def _register_handlers(self):
        """注册消息处理器"""
        @self.client.on(events.NewMessage(chats=self.target_list))
        async def event_handler(event):
            await self._handle_message(event.message)

    async def _handle_message(self, message):
        """消息处理核心逻辑"""
        msg:Msg = self.parse_message(message)
        await self.process_message(msg)

    def  parse_message(self, message):
        """解析消息内容"""
        # 使用正则表达式解析出链接
        text = message.raw_text
        url_pattern = r'<url[^>]*>(https?://[^<]+)</url>'
        match = re.search(url_pattern, text)
        msg = Msg()
        if match:
            source_url = match.group(1)
            print("解析出的原文链接为:", source_url)
            
            try:
                # 尝试获取链接内容
                response = requests.get(source_url)
                if response.status_code == 200:
                    print("获取到的原文内容为:")
                    print(response.text)
                    msg.content = response.text
                else:
                    raise ValueError(f"无法获取链接内容，状态码为: {response.status_code}")
            except requests.RequestException as e:
                 raise ValueError(f"获取链接内容时出错: {e}")
        return msg  

    async def _client_main(self):
        """客户端主循环"""
        me = await self.client.get_me()
        self._show_login_info(me)
        await self.client.run_until_disconnected()

    def _show_login_info(self, me):
        """显示登录信息"""
        print("-----****************-----")
        print(f"Name: {me.username}")
        print(f"ID: {me.id}")
        print("-----login successful-----")

    def start(self):
        """启动监控"""
        with self.client:
            self.client.loop.run_until_complete(self._client_main())

if __name__ == '__main__':
    from config.config import cfg 
    monitor = TelegramMonitor(cfg.telegram.api_id,cfg.telegram.api_hash,cfg.telegram.news_push_chat_id)
    monitor.start()