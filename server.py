from flask import Flask, request, Response
import configparser
from tg_bot import TG_Bot
import pandas as pd
import requests
import json
from openai.error import InvalidRequestError
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
        bot.send_message(msg_dir["chat_id"], "歡迎使用，本服務串接ChatGPT API。\n\官方連結: https://chat.openai.com/chat\n請注意以下幾點:\n1. 模型僅更新到2021年。\n2. 受限於API字數限制，單一對話不可超過4000字元，請適時使用/reset重置對話內容\n3. 由於ChatGPT需要前後文才能進行預測，需將近期訊息紀錄在server，請不要傳送敏感文字如密碼或重要資訊。\n/reset 開啟新對話串，切換不同對話時使用。\n/role 角色(例如:英文翻譯)，指令會更精準。")

    elif msg_dir["text"] == "/reset":
        bot.reset(msg_dir["chat_id"])
        bot.send_message(msg_dir["chat_id"], "重置對話內容")

    elif msg_dir["text"] == "/help" :
        bot.send_message(msg_dir["chat_id"], "本服務串接ChatGPT API。\n\官方連結: https://chat.openai.com/chat\n請注意以下幾點:\n1. 模型僅更新到2021年。\n2. 受限於API字數限制，單一對話不可超過4000字元，請適時使用/reset重置對話內容\n3. 由於ChatGPT需要前後文才能進行預測，需將近期訊息紀錄在server，請不要傳送敏感文字如密碼或重要資訊。\n/reset 開啟新對話串，切換不同對話時使用。\n/role 角色(例如:英文翻譯)，指令會更精準。")

    elif "/role" in msg_dir["text"]:
        role = msg_dir["text"].replace("/role", "").strip()
        bot.set_role(msg_dir["chat_id"], role)
        bot.send_message(msg_dir["chat_id"], f"已經重設角色為-{role}")

    else:
        # first
        if msg_dir["chat_id"] not in bot.users:
            bot.users.add(msg_dir["chat_id"])
            bot.insert_user(msg_dir["chat_id"], msg_dir["first_name"], msg_dir["last_name"], msg_dir["username"])
        # not first
        
        # if reach max context length
        try:
            msg_dir['reply'] = bot.completion(msg_dir["chat_id"], msg_dir["text"])
        except InvalidRequestError:
            bot.send_message(msg_dir["chat_id"], "已經達到最大字數，請使用/reset指令重設訊息，再重新詢問。")
            return
        
        bot.send_message(msg_dir["chat_id"], msg_dir['reply'])
        bot.insert_msg(msg_dir["chat_id"], msg_dir["text"], msg_dir["reply"], msg_dir["date"])
        log_msg = f"{msg_dir['chat_id']}||{msg_dir['text']}||{msg_dir['reply']}\n"
        bot.send_message(channel_chat_id, log_msg)

@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.get_json()
    with open("log.txt", "a") as f:
        f.write(str(data)+"\n")
    
    if "reply_to_message" in data:
        return

    elif "message" in data and "text" in data["message"].keys():
        message = data["message"]
        if message["date"] < bot.init_time:
            return "old"
        handle_message(message)

    elif "callback_query" in data:
        query = data["callback_query"]
        callback_query_id = query["id"]
        data = query['data']
        handle_callback_query(callback_query_id, "Button pressed", True)

    return Response('ok', status=200)


if __name__ == '__main__':
    bot = TG_Bot()
    bot.set_webhook()
    bot.send_message(channel_chat_id, "The webhook has been set up.")
    app.run(host="0.0.0.0", port=5001)

