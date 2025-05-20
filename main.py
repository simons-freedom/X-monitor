import asyncio
import sys
from loguru import logger
from config.config import cfg 

from monitor.webhook_monitor import WebhookMonitor
from monitor.telegram_monitor import TelegramMonitor 

if __name__ == "__main__":
    # 根据驱动模式创建监控器
    if cfg.monitor.driver_type == "webhook":
        monitor = WebhookMonitor(host='0.0.0.0', port=9999)
    elif cfg.monitor.driver_type == "telegram":
        monitor = TelegramMonitor(cfg.telegram.api_id,cfg.telegram.api_hash,cfg.telegram.news_push_chat_id)
    else:
        logger.error(f"不支持的驱动模式: {cfg.monitor.driver_type}")
        sys.exit(1)

    # 统一启动逻辑
    try:
        monitor.start() 
    except KeyboardInterrupt:
        logger.info("正在停止监控服务...")
