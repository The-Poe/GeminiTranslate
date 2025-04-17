# GeminiTranslate: 基於Google Gemini的翻譯API服務

[中文版本文檔](README_CN.md)

這是一個使用Google Gemini API技術的翻譯服務，可以與瀏覽器中的"沉浸式翻譯"插件集成。

## 功能特點

- 利用Google Gemini強大的AI模型進行高質量翻譯
- 支持多種語言之間的互譯
- 與"沉浸式翻譯"瀏覽器插件無縫集成
- 可部署在Render.com上作為持續運行的服務
- 使用更經濟高效的Gemini-2.0-flash模型

## 部署到Render.com

1. 在[Google AI Studio](https://makersuite.google.com/app/apikey)獲取免費的API密鑰

2. 在[Render.com](https://render.com)註冊賬號並創建新的Web Service

3. 從GitHub導入此項目，或者使用以下設置創建新服務：
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app`

4. 添加以下環境變量：
   - `GOOGLE_API_KEY`: 你的Google Gemini API密鑰
   - 可選: `API_URL`: 用於保持服務活躍的URL (例如: `https://你的應用名稱.onrender.com/health`)

5. 部署服務並等待構建完成

6. 服務部署完成後，你的API端點將是: `https://你的應用名稱.onrender.com/`

## 配置"沉浸式翻譯"插件

1. 在瀏覽器中安裝"沉浸式翻譯"插件

2. 在開發者設置中，打開"Beta測試特性"

3. 進入基本設置 -> 翻譯服務 -> 自定義API

4. 設置API URL為你的Render應用URL: `https://你的應用名稱.onrender.com/`

5. 推薦設置:
   - 每秒最大請求數: 1
   - 每次請求最大段落數: 20

## 注意事項

- Google Gemini API有免費使用限制，默認為每分鐘60次請求
- 如需更高限制，可以[在此申請更高配額](https://ai.google.dev/docs/increase_quota)
- 確保你的網絡環境可以訪問Google API，否則可能需要使用代理
- 當前項目使用的是gemini-2.0-flash模型，這是Google提供的快速文本模型，適合翻譯任務且價格更經濟（相比於gemini-pro或其他高階模型）

## 模型選擇

本項目現在使用Gemini-2.0-flash模型，它是：
- 更經濟實惠：每百萬tokens的價格低於其他模型
- 速度更快：適合需要快速回應的翻譯場景
- 效能適中：對於翻譯任務來說已經足夠優秀

如果需要更強大的翻譯能力，可以在main.py中將模型修改為"gemini-pro"或"gemini-1.5-pro"。

## Usage

To use the GeminiTranslate, follow the steps below:

1. [Obtain a free API key from Google.](https://makersuite.google.com/app/apikey) You can configure the API key by replacing `os.getenv('GOOGLE_API_KEY')` with your actual API key in `main.py`:

   ```python
   genai.configure(api_key="YOUR_API_KEY")
   ```

2. Install the required dependencies:

   ```bash
    pip install -r requirements.txt
   ```

3. Run the Flask application on the local server, default API address is `http://127.0.0.1/translate`:

   ```bash
   python ./main.py
   ```

4. Configure immersive translation plugin.
   - In developer settings, turn on `Beta features`.
   - Basic settings -> Translate service -> Custom API
   - Set `API URL` to your API address, default is `http://127.0.0.1/translate`.

5. Enjoy!

## Notes

- You can adjust the `safety_settings` and `generation_config` parameters according to your requirements, default is none.
- Make sure you can access the Google API, otherwise you may need to use a proxy.
- The API is limited to 60 times per minute, you can [apply for a higher limit here](https://ai.google.dev/docs/increase_quota), or set the maximum number of requests per second to 1 in the immersive translation custom options.
- Prompt injection may exist in the translation result.
- Gemini API is not allow to talk about OpenAI😑
- Recommended to use the maximum number of requests per second in the custom options: 1, the maximum number of paragraphs per request: 20, to avoid exceeding the limit.
