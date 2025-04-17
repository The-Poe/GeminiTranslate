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
            
        # 針對LINE群組聊天的優化翻譯提示，加強完整性要求，並防止添加不存在的表情符號
        prompt = f"""你是一位專業翻譯專家，精通中英文之間的轉換。你的任務是將以下文本從{source_lang}翻譯成{target_lang}，同時確保內容的完整性和口語的自然度。

翻譯原則（非常重要）：
1. 【完整性】：必須完整保留原文的所有內容和含義，不能省略任何重要元素或概念，即使是看似不重要的細節
2. 【準確性】：確保所有隱含的意思、文化背景和情感表達都被準確轉換
3. 【自然度】：使用目標語言中的自然表達方式，讓翻譯聽起來像母語使用者的日常對話
4. 【情感保留】：保持原文的語氣和情感強度，不添加原文中不存在的情感元素
5. 【表情符號處理】：
   - 嚴格保留原文中已有的表情符號，不增加、不刪減
   - 絕對不要添加原文中不存在的表情符號或是符號
   - 例如：如果原文沒有😊，翻譯中就不應出現😊
6. 【保留特定元素】：
   - 人名、品牌、地名等專有名詞應該保留
7. 【現代表達】：對俚語、網路用語、流行梗應找到最合適的對等表達
8. 【語境敏感】：根據上下文和場景確定最適合的翻譯

記住：在保持口語自然的同時，不允許省略原文中的任何元素或概念。每一個詞語和表達都應該有對應的翻譯，同時整體聽起來要流暢自然。
嚴格注意：絕對不要在翻譯中添加原文沒有的表情符號、符號或裝飾性元素。

請直接提供翻譯結果，不要添加任何解釋或額外內容。

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
                temperature=0.3,  # 稍微降低溫度來提高精確度
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
