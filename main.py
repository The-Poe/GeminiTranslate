# Import the necessary packages
import google.generativeai as genai
from flask import Flask, request, jsonify
import os
import time
import requests
import threading
import re
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 從環境變數獲取API URL和密鑰
url = os.getenv('API_URL')
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise ValueError("需要設置GOOGLE_API_KEY環境變數")

# 設置LINE Bot
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN', ''))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET', ''))

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

# Create a Flask object for the REST API
app = Flask(__name__)

# 檢測文本語言（繁體中文/英文）
def detect_language(text):
    # 計算中文字符的比例
    chinese_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text)
    chinese_ratio = len(chinese_chars) / len(text) if len(text) > 0 else 0
    
    # 如果中文字符比例超過25%，認為是中文
    if chinese_ratio > 0.25:
        return "zh-TW"
    else:
        return "en"

# 健康檢查端點，用於Render.com的健康檢查
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})

# LINE Bot Webhook端點
@app.route("/callback", methods=['POST'])
def callback():
    # 獲取X-Line-Signature頭部
    signature = request.headers.get('X-Line-Signature', '')
    
    # 獲取請求體
    body = request.get_data(as_text=True)
    app.logger.info("Request body: %s", body)
    
    try:
        # 驗證簽名
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature")
        return jsonify({
            'code': 400,
            'message': 'Invalid signature'
        }), 400
        
    # 必須返回200狀態碼
    return 'OK'

# 處理文本消息
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    try:
        text = event.message.text
        
        # 自動偵測語言
        source_lang = detect_language(text)
        target_lang = "en" if source_lang == "zh-TW" else "zh-TW"
        
        # 檢查有效性
        if not text or text.strip() == "":
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請發送文字訊息")
            )
            return
            
        # 針對LINE群組聊天的優化翻譯提示
        prompt = f"""你是一位專業翻譯專家，擁有豐富的雙語轉換經驗，特別擅長處理日常對話、俚語、網路用語和非正式表達。將以下文本從{source_lang}翻譯成{target_lang}。

翻譯原則：
1. 保持原文的意思、語氣和情感
2. 使用目標語言中的自然表達方式，讓翻譯聽起來像是母語使用者的日常對話
3. 俚語、幽默、諷刺和網路流行語應轉換為目標語言中的對等表達
4. 保留特定名詞，如人名、品牌名、地名等
5. 如遇貼圖、表情符號和特殊標點，保持原樣
6. 根據上下文調整語氣，保持對話的自然流暢
7. 輕鬆的對話用輕鬆的語氣翻譯，正式的內容保持適當的正式性

請直接提供翻譯結果，不要添加任何解釋、注釋或額外內容。

原文：
{text}

翻譯："""

        # 直接使用模型進行翻譯
        response = model.generate_content(
            prompt,
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "block_none",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "block_none",
                "HARM_CATEGORY_HATE_SPEECH": "block_none",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "block_none",
            },
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                temperature=0.4,
            ),
        )
        
        # 獲取翻譯文本並清理
        translated_text = response.text.strip()  # 去除首尾空白
        
        # 回覆翻譯結果
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=translated_text)
        )
    except Exception as e:
        app.logger.error(f"Error handling message: {str(e)}")
        # 發生錯誤時回覆錯誤訊息
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"翻譯發生錯誤: {str(e)}")
            )
        except Exception:
            app.logger.error("Failed to send error message")
            pass

# 如果配置了API_URL，則啟動保活線程
def request_thread_func(url, interval):
    while True:
        try:
            response = requests.get(url)
            print(f"Keep-alive request status: {response.status_code}")
        except Exception as e:
            print(f"Keep-alive request failed: {str(e)}")
        time.sleep(interval)

# Run the app on the local server
if __name__ == "__main__":
    # 獲取Render.com分配的端口或默認使用5000
    port = int(os.getenv("PORT", 5000))
    
    # 如果設置了API_URL，啟動保活線程
    if url:
        interval = 800  # 保活請求間隔，單位為秒
        request_thread = threading.Thread(target=request_thread_func, args=(url, interval))
        request_thread.daemon = True  # 設置為守護線程，主程序退出時線程也會退出
        request_thread.start()
    
    # 啟動Flask應用
    app.run(host="0.0.0.0", port=port)
