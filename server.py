from flask import Flask, request, Response
import configparser
from tg_bot import TG_Bot
import pandas as pd
import requests
import json
from openai.error import InvalidRequestError
# read config
from handler import Handler
config = configparser.ConfigParser()
config.read('config.ini')
token = config["telegram"]["token"]
channel_chat_id = config["telegram"]["channel_chat_id"]

# init instance
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    post = request.get_json()
    if "update_id" not in post:
        return 
    with open("log.txt", "a") as f:
        f.write(str(post)+"\n")
    # is telegram format
    if "reply_to_message" in post:
        return
    
    elif "message" in post:
        message = post["message"]
        if message["date"] < bot.init_time:
            return "old"
        date = message["date"]
        chat_id = message["from"]["id"]
        
        # 非用戶則新增到資料庫
        if chat_id not in bot.users:
            bot.users.add(chat_id)
            bot.db.insert_chat_id(chat_id)
            # bot.db.insert_user(msg_dir["chat_id"], msg_dir["first_name"], msg_dir["last_name"], msg_dir["username"])
        
        if not bot.is_paid(chat_id):
            bot.send_message(chat_id, "目前僅供特定用戶使用!")
            return Response('ok', status=200)
  
        if "text" in message.keys():
            handler.handle_text(chat_id, message["text"], date)
            return Response('ok', status=200)
        
        elif "voice" in message.keys():
            handler.handle_voice(chat_id, message["voice"])
            return Response('ok', status=200)
        
        elif "audio" in message.keys():
            return Response('audio', status=404)
        
        elif "photo" in message.keys():
            photo_list = message["photo"]
            low_quality = photo_list[0]
            photo_path = bot.get_file_path(low_quality["file_id"])
            return Response('photo', status=404)
            
    elif "callback_query" in post:
        query = post["callback_query"]
        callback_query_id = query["id"]
        post = query['post']
        handler.handle_callback_query(callback_query_id, "Button pressed", True)
        
    return Response('ok', status=200)


if __name__ == '__main__':
    bot = TG_Bot()
    handler = Handler(bot)
    status_code, _ = bot.set_webhook()
    if status_code == 200:
        bot.send_message(channel_chat_id, "The webhook has been set up.")
    else:
        bot.send_message(channel_chat_id, "The webhook setting is fail.") 
        
    app.run(host="0.0.0.0", port=5001)

