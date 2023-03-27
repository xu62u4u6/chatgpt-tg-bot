# chatgpt-tg-bot
將gpt3.5-turbo model API串接到telegram bot，可以不受限於官網需要等待。
嘗試串接sqlite作為資料存儲，之後能開發其他功能例如每日單字等。

本服務串接ChatGPT API(gpt3.5-turbo)。
官方連結: https://chat.openai.com/chat

請注意以下幾點:
1. 模型僅更新到2021年。
2. 受限於API字數限制，單一對話不可超過4000字元，請適時使用/reset重置對話內容
3. 由於ChatGPT需要前後文才能進行預測，需將近期訊息紀錄在server，請不要傳送敏感文字如密碼或重要資訊。

# 指令列表
/help 查看說明
/reset 開啟新對話串，切換不同對話時使用。
/role 角色(例如:英文翻譯)，指令會更精準。
/search 擷取當前對話關鍵字，並進行google搜尋。
