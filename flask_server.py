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
        bot.send_message(msg_dir["chat_id"], "開啟新的對話串")

    elif msg_dir["text"] == "/help" :
        bot.send_message(msg_dir["chat_id"], "/reset 開啟新對話串，切換不同對話時使用。\n/role 角色(例如:英文翻譯)，指令會更精準。")

    elif "/role" in msg_dir["text"]:
        role = msg_dir["text"].replace("/role", "").strip()
        bot.set_role(msg_dir["chat_id"], role)
        bot.send_message(msg_dir["chat_id"], "已經重設角色為-{role}")
    
    #elif msg_dir["text"] == "/summarize":
    #    summary = bot.summarize(msg_dir["chat_id"])
    #    bot.send_message(msg_dir["chat_id"], "摘要內容如下:\n"+summary)
        
    else:
        # first
        if msg_dir["chat_id"] not in bot.users:
            bot.users.add(msg_dir["chat_id"])
            bot.insert_user(msg_dir["chat_id"], msg_dir["first_name"], msg_dir["last_name"], msg_dir["username"])
        # not first
        if msg_dir["chat_id"] in bot.users_msgs.keys():
            characters_number = sum([len(d["content"]) for d in bot.users_msgs[msg_dir["chat_id"]]])
        else:
            characters_number = 0
        
        # if too many characters
        if characters_number + len(msg_dir["text"]) > 3500:
            bot.reset(msg_dir["chat_id"])
            bot.send_message(msg_dir["chat_id"], "當前對話字數過多，已經自動開啟新對話串。")
            
        msg_dir['reply'] = bot.completion(msg_dir["chat_id"], msg_dir["text"])
        bot.send_message(msg_dir["chat_id"], msg_dir['reply']+f"\n目前總字數: {characters_number+len(msg_dir['text'])+len(msg_dir['reply'])}/3500")
        bot.insert_msg(msg_dir["chat_id"], msg_dir["text"], msg_dir["reply"], msg_dir["date"])
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

