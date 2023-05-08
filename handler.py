from tg_bot import TG_Bot
import json 
import requests

class Handler:
    def __init__(self, bot):
        self.bot = bot

    
    def handle_callback_query(self, callback_query_id, text, alert):
        url = f"https://api.telegram.org/self.bot{token}/answerCallbackQuery"
        payload = {
            'callback_query_id': callback_query_id,
            'text': text,
            'show_alert': alert
        }
        response = requests.post(url, json=payload)
        return json.loads(response.content)

    def handle_voice(self, chat_id, voice, date):
        #self.bot.send_message(channel_chat_id, f"voice, {voice['file_id']}, {voice['duration']}")
        oga_path = self.bot.get_file_path(voice["file_id"])
        mp3_path = oga_path.replace("oga", "mp3")
        self.bot.download_audio(oga_path)
        self.bot.convert_oga_to_mp3(oga_path, mp3_path)
        text = self.bot.convert_mp3_to_text(mp3_path)

        reply = self.bot.completion(chat_id, text)

        self.bot.send_message(chat_id, reply)
        self.bot.db.insert_msg(chat_id, text, reply, date)
        
    def handle_command(self, chat_id, command):
        if command == "/start":
            self.bot.reset(chat_id)
            self.bot.send_message(chat_id, "歡迎使用，本服務串接ChatGPT API。\n官方連結: https://chat.openai.com/chat\n\n請注意以下幾點:\n1. 模型僅更新到2021年。\n2. 受限於API字數限制，單一對話不可超過4000字元，請適時使用/reset重置對話內容\n3. 由於ChatGPT需要前後文才能進行預測，需將近期訊息紀錄在server，請不要傳送敏感文字如密碼或重要資訊。\n\n/reset 開啟新對話串，切換不同對話時使用。\n/role 角色(例如:英文翻譯)，指令會更精準。")

        elif command == "/reset":
            self.bot.reset(chat_id)
            self.bot.send_message(chat_id, "重置對話內容")

        elif command == "/help" :
            self.bot.send_message(chat_id, "\n本服務串接ChatGPT API。\n官方連結: https://chat.openai.com/chat\n\n請注意以下幾點:\n1. 模型僅更新到2021年。\n2. 受限於API字數限制，單一對話不可超過4000字元，請適時使用/reset重置對話內容\n3. 由於ChatGPT需要前後文才能進行預測，需將近期訊息紀錄在server，請不要傳送敏感文字如密碼或重要資訊。\n\n/reset 開啟新對話串，切換不同對話時使用。\n/role 角色(例如:英文翻譯)，指令會更精準。")
        
        elif command == "/search" :
            results = self.bot.search(chat_id) 
            self.bot.send_message(chat_id, results)
        
        elif "/role" in command:
            role = command.replace("/role", "").strip()
            self.bot.set_role(chat_id, role)
            self.bot.send_message(chat_id, f"已經重設角色為-{role}")

    def handle_text(self, chat_id, text, date):
        if text[0] == "/":
            self.handle_command(chat_id, text)
        else:
            reply = self.bot.chat(chat_id, text)
            self.bot.send_message(chat_id, reply)
            self.bot.db.insert_msg(chat_id, text, reply, date)
            log_msg = f"{chat_id}||{text}||{reply}\n"
            self.bot.send_message(self.bot.channel_chat_id, log_msg)