# -*- coding: utf-8 -*-
import time
import hmac
import hashlib
import base64
import urllib.parse
import json

import logging
import requests

class DingTalkRobot(object):
    def __init__(self, robot_id, secret):
        super(DingTalkRobot, self).__init__()
        self.robot_id = robot_id
        self.secret = secret
        self.headers = {'Content-Type': 'application/json; charset=utf-8'}
        self.times = 0
        self.start_time = time.time()

    # 加密签名
    def __spliceUrl(self):
        timestamp = int(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = "https://oapi.dingtalk.com/robot/send?access_token="+f"{self.robot_id}&timestamp={timestamp}&sign={sign}"
        return url

    def send_markdown(self,title, markdown_msg, is_at_all=False, at_mobiles=[]):
        data = {"msgtype": "markdown", "at": {}}
        if self.is_not_null_and_blank_str(markdown_msg):
            data["markdown"] = {"title": title,"text": markdown_msg}
        else:
            logging.error("markdown类型，消息内容不能为空！")
            raise ValueError("markdown类型，消息内容不能为空！")

        if is_at_all:
            data["at"]["isAtAll"] = is_at_all

        if at_mobiles:
            at_mobiles = list(map(str, at_mobiles))
            data["at"]["atMobiles"] = at_mobiles

        logging.debug('markdown类型：%s' % data)
        return self.__post(data)

    def send_msg(self, *mssg):
        text = ''
        for i in mssg:
            text += str(i)
        self.send_markdown("交易通知",text)

    
    def send_text(self, msg, is_at_all=False, at_mobiles=[]):
        data = {"msgtype": "text", "at": {}}
        if self.is_not_null_and_blank_str(msg):
            data["text"] = {"content": msg}
        else:
            logging.error("text类型, 消息内容不能为空！")
            raise ValueError("text类型,消息内容不能为空！")

        if is_at_all:
            data["at"]["isAtAll"] = is_at_all

        if at_mobiles:
            at_mobiles = list(map(str, at_mobiles))
            data["at"]["atMobiles"] = at_mobiles

        logging.debug('text类型：%s' % data)
        return self.__post(data)


    def send_json(self, msg, is_at_all=False, at_mobiles=[]):
        data = {"msgtype": "text", "at": {}}
        if msg :
            json_msg = json.dumps(msg,ensure_ascii=False)
            data["text"] = {"content": json_msg}
        else:
            logging.error("text类型，消息内容不能为空！")
            raise ValueError("text类型，消息内容不能为空！")

        if is_at_all:
            data["at"]["isAtAll"] = is_at_all

        if at_mobiles:
            at_mobiles = list(map(str, at_mobiles))
            data["at"]["atMobiles"] = at_mobiles

        logging.debug('text类型：%s' % data)
        return self.__post(data)


    def send_image(self, title,image_url, is_at_all=False, at_mobiles=[]):
        markdown_msg = "!["+title+"]("+image_url+")\n"
        return self.send_markdown(title,markdown_msg,is_at_all)   
    
    def send_action_card(self, title, markdown_msg, btnOrientation: str = "0", *btn_info):
        """
        发送钉钉 ActionCard 类型的消息，支持传入多个按钮信息

        :param title: 卡片标题
        :param markdown_msg: 卡片的 Markdown 消息内容
        :param btnOrientation: 按钮排列方向，默认为 "0"
        :param btn_info: 可变参数，每个参数为一个元组 (title, actionURL)，表示一个按钮的标题和链接
        :return: 调用 __post 方法的返回值，即发送消息的结果
        """
        # 构建钉钉消息的基础结构，消息类型为 actionCard
        data = {"msgtype": "actionCard", "actionCard": {}}
        # 设置卡片标题
        data["actionCard"]["title"] = title
        # 设置卡片的 Markdown 消息内容
        data["actionCard"]["text"] = markdown_msg
        # 设置按钮排列方向
        data["actionCard"]["btnOrientation"] = btnOrientation
        # 处理按钮信息，将 btn_info 转换为符合钉钉消息格式的按钮列表
        btns = [{"title": title, "actionURL": url} for title, url in btn_info]
        data["actionCard"]["btns"] = btns

        # 记录 debug 日志，包含要发送的 actionCard 类型消息数据
        logging.debug('actionCard类型：%s' % data)
        # 调用 __post 方法发送消息并返回结果
        return self.__post(data)


    def __post(self, data):
        """
        发送消息（内容UTF-8编码）
        :param data: 消息数据（字典）
        :return: 返回发送结果
        """
        self.times += 1
        if self.times > 20:
            if time.time() - self.start_time < 60:
                logging.debug('钉钉官方限制每个机器人每分钟最多发送20条，当前消息发送频率已达到限制条件，休眠一分钟')
                time.sleep(60)
            self.start_time = time.time()

        post_data = json.dumps(data)
        try:
            response = requests.post(self.__spliceUrl(), headers=self.headers, data=post_data)
            logging.debug('成功发送钉钉%'+str(response))
        except Exception as e:
            logging.debug('发送钉钉失败:' +str(e))

    def is_not_null_and_blank_str(self,content):
        if content and content.strip():
            return True
        else:
            return False        
