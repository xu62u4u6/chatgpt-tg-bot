import requests
import configparser
import time 
import openai

config = configparser.ConfigParser()
config.read('config.ini')
"""
class Message:
:
    def __init__(self, msg):
        self.date = msg["date"]
        self.chat_id  = msg["chat"]["id"]
        self. = msg["text"]
        for i in ["username", "first_name", "last_name"]:
            if i in msg.keys():
                msg_dir[i] = msg[i]
            else:
                msg_dir[i] = None
        pass
"""

class TG_Bot:
    def __init__(self):
        openai.api_key = config["openai"]["key"]
        self.token = config["telegram"]["token"]
        self.webhook_url = config["telegram"]["webhook-url"]
        self.init_time = time.time()
        # chat_id: [msg]
        self.users_msgs = {}
        
    def send_message(self, chat_id, text):
        url = f'https://api.telegram.org/bot{self.token}/sendMessage'
        payload = {'chat_id': chat_id, 'text': text}
        return requests.post(url,json=payload)
    
    def parse_massage(self, msg):
        msg_dir = {}
        msg_dir["date"] = msg["date"]
        msg_dir["chat_id"]  = msg["chat"]["id"]
        msg_dir["text"] = msg["text"]
        for i in ["username", "first_name", "last_name"]:
            if i in msg.keys():
                msg_dir[i] = msg[i]
            else:
                msg_dir[i] = None
        
        return msg_dir
    
    def set_webhook(self):
        url = f'https://api.telegram.org/bot{self.token}/setWebhook?url={self.webhook_url}'
        res = requests.post(url)
        return res.status_code, res.text
    

    def reset(self, chat_id, role="assistant"):
        self.users_msgs[chat_id] = [
            {"role": "system", "content": f"You are a {role}."}
        ]

    def completion(self, chat_id, text):
        # if new
        if chat_id not in self.users_msgs.keys():
            self.reset(chat_id)
        
        self.users_msgs[chat_id].append(
            {"role": "user", "content": text}
        )
        
        res = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.users_msgs[chat_id])
        reply = res.choices[0].message.content
        self.users_msgs[chat_id].append(
            {"role": "assistant", "content": reply}
        )
        return reply
        
