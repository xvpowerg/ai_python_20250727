import os

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
import openai
import json

app = Flask(__name__)

# 設定您的 LINE 與 OpenAI 憑證
access_token = ''
channel_secret = ''
openAiKey = ''


configuration = Configuration(access_token=access_token)
handler = WebhookHandler(channel_secret)

@app.route("/", methods=['POST'])
def callback():
    # 取得來自 LINE 的 X-Line-Signature 標頭值
    signature = request.headers.get('X-Line-Signature')
    # 取得請求內容作為文字
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 處理 webhook 內容
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. 請確認您的 channel access token/channel secret 是否正確。")
        abort(400)
    
    return 'OK'

# 處理 LINE Webhook 事件
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    # 建立對話歷史，第一則訊息為 system 指令
    messages = [{"role": "system", "content": "你好!"}]
    ai_msg = user_message[:6].lower()  # 取前6個字，判斷是否為觸發 OpenAI 的關鍵字
    reply_msg = ''

    if ai_msg == 'hi ai:':
        app.logger.info("呼叫 OpenAI API")
        # 將使用者訊息(去除觸發字)加入對話歷史
        messages.append({"role": "user", "content": user_message[6:]})
        client = openai.OpenAI(api_key=openAiKey)  # 使用新版 OpenAI API client
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=256,
            temperature=0.5
        )
        reply_msg = response.choices[0].message.content.strip()

        # 根據新版回傳格式，使用字典存取取得回覆訊息
        #reply_msg = response['choices'][0]['message']['content'].replace('\n', '')
        app.logger.info(f"OpenAI 回覆：{reply_msg}")
    else:
        reply_msg = user_message

    # 回傳訊息給 LINE 使用者
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_msg)]
            )
        )

if __name__ == "__main__":
    app.run(debug=True)
