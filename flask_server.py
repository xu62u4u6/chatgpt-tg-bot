from flask import Flask, request, Response
import configparser
from tg_bot import TG_Bot
import pandas as pd
import requests
import json

# read config
config = configparser.ConfigParser()
config.read('config.ini')
token = config["telegram"]["token"]
channel_chat_id = config["telegram"]["channel_chat_id"]

# init instance
app = Flask(__name__)


def handle_callback_query(callback_query_id, text, alert):
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    payload = {
        'callback_query_id': callback_query_id,
        'text': text,
        'show_alert': alert
    }
    response = requests.post(url, json=payload)
    return json.loads(response.content)


def handle_message(message):
    msg_dir = bot.parse_message(message)
    
    # command 
    if msg_dir["text"] == "/start":
        bot.reset(msg_dir["chat_id"])
        bot.send_message(msg_dir["chat_id"], "歡迎使用，本服務是串接gpt-3.5-turbo模型。")
        
    elif msg_dir["text"] == "/reset":
        bot.reset(msg_dir["chat_id"])
        bot.send_message(msg_dir["chat_id"], "已經重置訊息")
        
    elif "/role" in msg_dir["text"]:
        role = msg_dir["text"].replace("/role ")
        bot.reset(msg_dir["chat_id"], role)
    else:
        msg_dir['reply'] = bot.completion(msg_dir["chat_id"], msg_dir["text"])
        bot.send_message(msg_dir["chat_id"], msg_dir['reply'])
        log_msg = f"{msg_dir['date']}||{msg_dir['chat_id']}||{msg_dir['text']}||{msg_dir['reply']}\n"
        with open("log", "a") as f:
            f.write(log_msg)   
        bot.send_message(channel_chat_id, log_msg) 

@app.route('/', methods=['POST'])
def handle_msg():
    
    data = request.get_json()
    if "reply_to_message" in data:
        return
    
    elif "message" in data:
        message = data["message"]
        if message["date"] < bot.init_time:
            return "old"
        chat_id = message["chat"]["id"]
        text = message["text"]
        handle_message(message)
        
    elif "callback_query" in data:
        query = data["callback_query"]
        callback_query_id = query["id"]
        data = query['data']
        handle_callback_query(callback_query_id, "Button pressed", True)
    
    with open("log.txt", "a") as f:
        f.write(str(data))  
        f.write("\n")
 
        
    return Response('ok', status=200)
     
if __name__ == '__main__':
    bot = TG_Bot()
    bot.set_webhook()
    app.run(port=5001)