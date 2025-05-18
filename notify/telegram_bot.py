# -*- coding: utf-8 -*-
import telegram


class TgRobot(object):

    def __init__(self, token, chat_id):
        super(TgRobot, self).__init__()
        self.token = token
        self.chat_id = chat_id
        self.bot = telegram.Bot(token)

    
    def send_text(self,content):
      '''
      发送文本消息
      '''
      if content == None:
         return
      self.bot.send_message(self.chat_id,content)


    def send_html(self, html_text):
        if html_text:
            # 发送html格式的消息
            self.bot.send_message(
                chat_id=self.chat_id,
                text=html_text,
                parse_mode=telegram.ParseMode.HTML
            )  


    def send_dataframe(self,content):
      '''
      发送dataframe消息
      '''
      self.bot.send_message(self.chat_id,content.to_markdown(),parse_mode='Markdown')

    def send_photo(self, photo_path):
        if photo_path:
            self.bot.send_photo(
                chat_id=self.chat_id,
                photo=open(photo_path, 'rb'), 
            ) 

    def send_document(self, doc_path):
        if doc_path:
            self.bot.send_document(
            chat_id=self.chat_id,
            document=open(doc_path, 'rb'),
        )

    def send_msg(self, *mssg):
        text = ''
        for i in mssg:
            text += str(i)
        self.bot.send_message(self.chat_id,text)
