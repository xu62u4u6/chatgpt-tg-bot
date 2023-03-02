from flask import Flask, request, Response
import configparser
from tg_bot import TG_Bot
import pandas as pd

# read config
config = configparser.ConfigParser()
config.read('config.ini')
token = config["telegram"]["token"]
channel_chat_id = config["telegram"]["channel_chat_id"]

# init instance
app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_msg():
    try:
        raw_msg = request.get_json()
    except:
        return "error"
    
    with open("log.txt", "a") as f:
        f.write(str(raw_msg))  
        f.write("\n")
    try:
        msg = raw_msg["message"]
        
    # pass reply msgs
    except KeyError:
        return "reply"
    
    # check msg received time
    if msg["date"] < bot.init_time:
        return "old"
    
    #date, chat_id, text
    msg_dir = bot.parse_massage(msg)
    
    # command 
    if msg_dir["text"] == "/start":
        bot.reset(msg_dir["chat_id"])
        bot.send_message(msg_dir["chat_id"], "歡迎使用，本服務是串接gpt-3.5-turbo模型。")
        
    elif msg_dir["text"] == "/reset":
        bot.reset(msg_dir["chat_id"])
        bot.send_message(msg_dir["chat_id"], "已經重置訊息")
        
    else:
        msg_dir['reply'] = bot.completion(msg_dir["chat_id"], msg_dir["text"])
        bot.send_message(msg_dir["chat_id"], msg_dir['reply'])
        log_msg = f"{msg_dir['date']}||{msg_dir['chat_id']}||{msg_dir['text']}||{msg_dir['reply']}\n"
        with open("log", "a") as f:
            f.write(log_msg)   
        bot.send_message(channel_chat_id, log_msg)
        
    return Response('ok', status=200)
     
if __name__ == '__main__':
    bot = TG_Bot()
    bot.set_webhook()
    app.run(port=5002)