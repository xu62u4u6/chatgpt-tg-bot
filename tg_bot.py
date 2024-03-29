import requests
import configparser
import time
import openai
import sqlite3
import json
import urllib.request
from pydub import AudioSegment
import hashlib
from timeout_decorator import timeout, TimeoutError

config = configparser.ConfigParser()
config.read('config.ini')

class Database:
    def __init__(self, db_name='chatgpt-tg-bot.sqlite'):
        self.db_name = db_name

    def create(self):
        self.cursor.execute(
            '''CREATE TABLE user_info (
                chat_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                user_name TEXT,
                created_at DEFAULT CURRENT_TIMESTAMP    
            )'''      
        )
        self.cursor.execute(
            '''CREATE TABLE msg (
                msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                raw_text TEXT NOT NULL,
                translated_text TEXT,
                received_time TIMESTAMP NOT NULL,
                created_at DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chat_id) REFERENCES user_info(chat_id)
            )'''      
        )
        self.connection.commit()
        
    def user_exists(self, chat_id):
        connection = sqlite3.connect(self.db_name)
        c = connection.cursor()
        is_exist = c.execute(
            f"SELECT EXISTS(SELECT 1 FROM user_info WHERE chat_id = {chat_id} LIMIT 1)").fetchall()[0][0]
        connection.close()
        return is_exist
    
    def execute_query(self, query, params, commit=False):
        connection = sqlite3.connect(self.db_name)
        c = connection.cursor()
        result = c.execute(query, params)
        if commit:
           connection.commit()
        connection.close()
        return result

    def insert_msg(self, chat_id, text, reply, received):
        query = "INSERT INTO msg (chat_id, text, reply, received_time) VALUES (?, ?, ?, ?)"
        params = (chat_id, text, reply, received)
        self.execute_query(query, params, commit=True)

    def insert_user(self, chat_id, first_name, last_name, user_name):
        query = "INSERT INTO user_info (chat_id, first_name, last_name, user_name) VALUES (?, ?, ?, ?)"
        params = (chat_id, first_name, last_name, user_name)
        self.execute_query(query, params, commit=True)

    def insert_chat_id(self, chat_id):
        query = "INSERT INTO user_info (chat_id) VALUES (?)"
        params = (chat_id,)
        self.execute_query(query, params, commit=True)

    def find_users(self):
        connection = sqlite3.connect(self.db_name)
        c = connection.cursor()
        users = set(chat_id_tuple[0] for chat_id_tuple in c.execute(
            "SELECT chat_id FROM user_info").fetchall())
        connection.close()
        return users    

class TG_Bot:
    def __init__(self):
        openai.api_key = config["openai"]["key"]
        self.token = config["telegram"]["token"]
        self.webhook_url = config["telegram"]["webhook-url"]
        self.bot_url = f"https://api.telegram.org/bot{self.token}"
        self.init_time = time.time()
        self.users_msgs = {}
        self.db = Database()
        self.users = self.db.find_users()
        self.cx = config["google"]["cx"]
        self.google_key = config["google"]["key"]
        self.salt = config["openai"]["salt"]
        
    def send_message(self, chat_id, text, parse_mode="markdown"):
        payload = {'chat_id': chat_id, 'text': text, "parse_mode": parse_mode}
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

    @timeout(60, use_signals=False)
    def completion(self, chat_id_hash, msgs):
        res = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-0301", messages=msgs, user=chat_id_hash)
        reply = res.choices[0].message.content
        return reply
    
    def calculate_chat_id_hash(self, chat_id):
        salted = str(chat_id) + self.salt
        sha1 = hashlib.sha1()
        sha1.update(salted.encode("utf-8"))
        return sha1.hexdigest()

    def chat(self, chat_id, text):
        # if new
        if chat_id not in self.users_msgs.keys():
            self.reset(chat_id)
        chat_id_hash = self.calculate_chat_id_hash(chat_id)
        self.users_msgs[chat_id].append(
            {"role": "user", "content": text}
        )
        try:    
            reply = self.completion(chat_id_hash, self.users_msgs[chat_id])
            
        except TimeoutError:
            return "與伺服器連接超時，請稍後嘗試。"
        
        except openai.error.RateLimitError:
            return "目前受到速率限制，請稍後再詢問"
        
        except openai.error.InvalidRequestError:
            return "已經達到最大字數或目前無法使用\n，請使用/reset指令重設訊息，再重新詢問。"
        self.users_msgs[chat_id].append(
            {"role": "assistant", "content": reply}
        )
        return reply

    def search(self, chat_id):
        if chat_id not in self.users_msgs.keys():
            self.reset(chat_id)        
        tmp_msgs = self.users_msgs[chat_id] + [{"role": "user", "content": "從先前對話中提取最重要的三個英語關鍵字，以格式keywords: keyword1, keyword2"}]
        chat_id_hash = self.calculate_chat_id_hash(chat_id)
        try:    
            reply = self.completion(chat_id_hash, tmp_msgs)
            
        except TimeoutError:
            return "與伺服器連接超時，請稍後嘗試。"
        
        except openai.error.RateLimitError:
            return "目前受到速率限制，請稍後再詢問"
        
        except openai.error.InvalidRequestError:
            return "已經達到最大字數或目前無法使用\n，請使用/reset指令重設訊息，再重新詢問。"
        
        keywords = reply.replace("keywords: ", "")
        params = {
        "q": keywords,
        "cx": self.cx,
        "key": self.google_key
        }

        # 通過 API 查詢結果
        try:
            response = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
        except:
            return "目前無法進行搜尋"

        # 解析 JSON 結果
        result = json.loads(response.text)
        
        # 遍歷所有搜索結果
        results = []
        for item in result["items"][:10]:
            # 讀取標題、描述和網址
            results.append(f"{item['title']}\n{item['snippet']}\n{item['link']}\n")
            
        return "\n".join(results)

    def broadcast(self, text):
        chat_ids = self.db.find_users()
        
        for chat_id in chat_ids:
            self.send_message(chat_id, text)