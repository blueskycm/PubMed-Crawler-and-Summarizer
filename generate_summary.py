import os
import gspread
from openai import OpenAI
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# === 載入 .env 環境變數 ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS")  # 指向 credentials.json

# === 初始化 OpenAI 客戶端 ===
client = OpenAI(api_key=OPENAI_API_KEY)

# === Google Sheets 授權 ===
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_PATH, SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SPREADSHEET_ID).worksheet("literature_data")

# === 讀取工作表資料 ===
data = sheet.get_all_values()

# === 開始摘要處理 ===
for i, row in enumerate(data[1:], start=2):  # 第2列開始（跳過表頭）
    title = row[0] if len(row) > 0 else ""
    abstract = row[1] if len(row) > 1 else ""
    summary = row[13] if len(row) > 13 else ""

    if not title or summary:  # 如果標題為空或摘要已存在就跳過
        continue

    # 使用 OpenAI 產生摘要
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "你是專業的醫學文獻摘要專家、功能營養醫學專家、實證醫學專家，幫助用戶總結摘要的繁體中文重點（盡可能用條列式來說明）。"
                },
                {
                    "role": "user",
                    "content": f"文獻摘要：{abstract}。請用繁體中文總結重點（盡可能用條列式來說明）。"
                }
            ]
        )
        key_points = response.choices[0].message.content
    except Exception as e:
        print(f"❌ 第 {i} 行摘要失敗：{e}")
        continue

    # 寫入 N 欄（第14欄）
    try:
        sheet.update_cell(i, 14, key_points)
        print(f"✅ 第 {i} 行摘要完成")
    except Exception as e:
        print(f"❌ 第 {i} 行寫入失敗：{e}")
