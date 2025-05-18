# -*- coding: utf-8 -*-
from loguru import logger
from typing import List, Tuple, Optional
from notify.dingding import DingTalkRobot
from config.config import cfg  # 从config导入配置

# 初始化钉钉机器人
_robot = None

def _get_robot():
    """获取钉钉机器人实例"""
    global _robot
    if _robot is None:
        if not cfg.dingtalk.token or not cfg.dingtalk.secret:
            logger.warning("钉钉机器人未启用或未配置Token/Secret,无法发送通知")
            return None
        _robot = DingTalkRobot(cfg.dingtalk.token, cfg.dingtalk.secret)
    return _robot

def send_notice_msg(content: str, title: str = "系统通知", btn_info: List[Tuple[str, str]] = []) -> bool:
    """
    发送通知消息,默认使用ActionCard格式
    
    Args:
        content: 消息内容
        title: 消息标题，默认为"系统通知"
        btn_info: 按钮信息列表，每个元素为(按钮标题, 按钮链接)元组,默认为None
        
    Returns:
        bool: 是否发送成功
    """
    try:
        robot = _get_robot()
        if not robot:
            return False
        
        # 如果提供了按钮信息，使用ActionCard格式
        if btn_info and len(btn_info) > 0:
            robot.send_action_card(title, f"📢 **{title}**\n\n{content}", "0", *btn_info)
        else:
            # 否则使用Markdown格式
            robot.send_markdown(title, f"📢 **{title}**\n\n{content}")
            
        logger.info(f"通知消息发送成功: {content[:50]}...")
        return True
    except Exception as e:
        logger.error(f"发送通知消息时出错: {str(e)}", exc_info=True)
        return False

def send_warn_action_card(title: str, text: str, btn_orientation: str = "0", *btns: Tuple[str, str]) -> bool:
    """
    发送警告ActionCard消息
    
    Args:
        title: 标题
        text: 正文内容(支持markdown)
        btn_orientation: 按钮排列方向,0-按钮竖直排列,1-按钮横向排列
        btns: 按钮列表，每个按钮为(标题, 链接)元组
        
    Returns:
        bool: 是否发送成功
    """
    try:
        robot = _get_robot()
        if not robot:
            return False
            
        # 调用钉钉机器人的send_action_card方法
        robot.send_action_card(title, text, btn_orientation, *btns)
        logger.info(f"警告ActionCard消息发送成功: {title}")
        return True
    except Exception as e:
        logger.error(f"发送警告ActionCard消息时出错: {str(e)}", exc_info=True)
        return False