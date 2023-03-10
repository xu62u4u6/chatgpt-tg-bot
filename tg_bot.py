import requests
import configparser
import time
import openai
import sqlite3
import urllib.request
from pydub import AudioSegment

config = configparser.ConfigParser()
config.read('config.ini')


class TG_Bot:
    def __init__(self):
        openai.api_key = config["openai"]["key"]
        self.token = config["telegram"]["token"]
        self.webhook_url = config["telegram"]["webhook-url"]
        self.bot_url = f"https://api.telegram.org/bot{self.token}"
        self.init_time = time.time()
        self.users_msgs = {}
        #self.connection = sqlite3.connect('chatgpt-tg-bot.sqlite')
        #self.cursor = self.connection.cursor()
        self.users = self.find_users()

    def send_message(self, chat_id, text):
        payload = {'chat_id': chat_id, 'text': text}
        return requests.post(self.bot_url+"/sendMessage", json=payload)

    def get_file_path(self, file_id):
        url = f"https://api.telegram.org/bot{self.token}/getFile?file_id={file_id}"
        res = requests.get(url)
        return res.json()["result"]["file_path"]
    
    def download_audio(self, file_path):
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        urllib.request.urlretrieve(url, file_path)#.replace("oga", "mp3"))
    
    def convert_oga_to_mp3(self, oga_path, mp3_path):
        audio = AudioSegment.from_file(oga_path, format="ogg")
        audio.export(mp3_path, format="mp3") 
           
    def convert_mp3_to_text(self, audio_path):
        with open(audio_path, "rb") as audio:
            return openai.Audio.transcribe("whisper-1", audio)["text"]

    def send_inline_keyboard(self, chat_id, text):
        payload = {'chat_id': chat_id,
                   'text': text,
                   'reply_markup': {"inline_keyboard": [[{"text": "Button 1", "callback_data": "data1"}],
                                                        [{"text": "Button 2", "callback_data": "data2"}]]}}
        return requests.post(self.bot_url+"/sendMessage", json=payload)

    def send_keyboard(self, chat_id, text):
        payload = {'chat_id': chat_id,
                   'text': text,
                   'replyMarkup': {"keyboard": [["Option 1", "Option 2"],
                                                ["Option 3", "Option 4"]],
                                   "one_time_keyboard": True}}
        return requests.post(self.bot_url+"/sendMessage", json=payload)

    def parse_message(self, msg):
        msg_dir = {}
        msg_dir["date"] = msg["date"]
        msg_dir["chat_id"] = msg["chat"]["id"]
        msg_dir["text"] = msg["text"]
        for i in ["username", "first_name", "last_name"]:
            if i in msg["chat"].keys():
                msg_dir[i] = msg["chat"][i]
            else:
                msg_dir[i] = None

        return msg_dir

    def set_webhook(self):
        payload = {'url': self.webhook_url}
        res = requests.post(self.bot_url+"/setWebhook", json=payload)
        return res.status_code, res.text

    def reset(self, chat_id, role="assistant"):
        self.users_msgs[chat_id] = [
            {"role": "system", "content": f"You are a {role}."}
        ]

    def set_role(self, chat_id, role):
        self.users_msgs[chat_id][0]["content"] = f"You are a {role}."

    def completion(self, chat_id, text):
        # if new
        if chat_id not in self.users_msgs.keys():
            self.reset(chat_id)

        self.users_msgs[chat_id].append(
            {"role": "user", "content": text}
        )

        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=self.users_msgs[chat_id])
        reply = res.choices[0].message.content
        self.users_msgs[chat_id].append(
            {"role": "assistant", "content": reply}
        )
        return reply

    def user_exists(self, chat_id):
        connection = sqlite3.connect('chatgpt-tg-bot.sqlite')
        c = connection.cursor()
        is_exist = c.execute(
            f"SELECT EXISTS(SELECT 1 FROM user_info WHERE chat_id = {chat_id} LIMIT 1)").fetchall()[0][0]
        connection.close()
        return is_exist

    def insert_msg(self, chat_id, text, reply, received):
        connection = sqlite3.connect('chatgpt-tg-bot.sqlite')
        c = connection.cursor()
        c.execute("INSERT INTO msg (chat_id, text, reply, received_time) VALUES (?, ?, ?, ?)",
                  (chat_id, text, reply, received))
        connection.commit()
        connection.close()

    def insert_user(self, chat_id, first_name, last_name, user_name):
        connection = sqlite3.connect('chatgpt-tg-bot.sqlite')
        c = connection.cursor()
        c.execute(
            f"INSERT INTO user_info (chat_id, first_name, last_name, user_name) VALUES (?, ?, ?, ?)",
            (chat_id, first_name, last_name, user_name))
        connection.commit()
        connection.close()

    def find_users(self):
        connection = sqlite3.connect('chatgpt-tg-bot.sqlite')
        c = connection.cursor()
        users = set(chat_id_tuple[0] for chat_id_tuple in c.execute(
            "SELECT chat_id FROM user_info").fetchall())
        connection.close()
        return users
