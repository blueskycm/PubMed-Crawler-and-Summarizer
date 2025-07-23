# 🧠 PubMed Crawler & Summarizer

本專案是一套自動化工具，旨在從 [PubMed](https://pubmed.ncbi.nlm.nih.gov/) 搜尋並擷取文獻資料，並可選擇性使用 OpenAI API 生成繁體中文摘要。所有結果將寫入 Google Sheets，方便後續分析與彙整。

---

## 🧩 專案功能

1. **查詢與擷取 PubMed 文獻**
   - 根據 Google Sheets 的關鍵字搜尋欄進行 PubMed 查詢。
   - 支援進階條件（Filters）如：系統性回顧、隨機對照試驗、Meta分析等。
   - 抓取資料欄位：標題、摘要、文獻類型、期刊、發表日期、DOI、PMID 等。

2. **整合 Google Sheets**
   - 所有搜尋關鍵字、結果與處理狀態記錄在 `爬蟲紀錄` 工作表。
   - 擷取之文獻寫入 `literature_data` 工作表。
   - 可自訂搜尋主題與篩選條件。

3. **（選用）使用 OpenAI 自動摘要**
   - 使用 GPT-4 模型將英文摘要轉換為繁體中文重點條列式摘要。
   - 將摘要寫入 Google Sheets 的 N 欄（第 14 欄）。

---

## 🔗 參考資源

- 📄 Google Sheets 範例（含功能選單、字串組合公式）  
  👉 https://docs.google.com/spreadsheets/d/1RMjDLFVo1FlMkfYfoW6NNBuRN5qT3LgpP2-SYXanQ4A/edit?usp=sharing

- 📚 PubMed 搜尋語法與篩選教學  
  👉 https://pubmed.ncbi.nlm.nih.gov/help/

---

## 📝 Google Sheets 操作說明

### 📋 Step 1：設定搜尋關鍵字（於 `搜尋字串組合` 工作表）

| 欄位 | 說明 |
|------|------|
| A欄 (A3起) | **營養素**（或其他主題） |
| B欄 (B3起) | **疾病**（與 A 組合搜尋） |
| C欄 (C3起) | **排除詞彙**（例："cancer"） |
| D欄 (D3起) | **其他篩選條件**（例："humans"） |
| E欄        | **搜尋參數**（請勿修改 E1）<br> E3: 詞組間隔單字數<br> E5: 起始搜尋時間範圍（如 5）<br> E7: 時間單位（年/月/日） |

### 📋 Step 2：設定好後，請點選：上方工具列的"功能選單">"搜尋字串組合"，系統將跳出輸入框，輸入自訂主題後按下確認。該組字串就會被複製到 `爬蟲紀錄` 工作表供後續爬蟲與摘要處理。

---
### 1. 安裝所需套件

```bash
pip install -r requirements.txt
```
### 2. 建立 .env 檔案
請在專案根目錄建立 `.env` 檔案並加入以下內容：
```ini
# Google Sheets 認證 JSON 檔路徑
GOOGLE_CREDENTIALS=credentials.json

# Google 試算表 ID（網址中間那一段）
SPREADSHEET_ID=你的試算表ID

# （選用）OpenAI API Key，用於中文摘要
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
---
## 🧪 執行步驟
### ✳️ Step 1：執行 PubMed 爬蟲主程式
```bash
python main.py
```
- 讀取 Google Sheets 爬蟲紀錄 工作表 A~E 欄：
  - A欄：搜尋字串
  - B欄：自訂主題（可空）
  - C欄：自動填入抓取筆數與狀態
  - D欄：狀態（DONE 表示跳過）
  - E欄：Filters（逗號分隔，或填入 none 表示無過濾）
- 將文獻結果寫入 literature_data 工作表


### ✳️ Step 2：執行中文摘要生成器(選用)
```bash
python summarize.py
```
- 自動遍歷 literature_data 工作表
- 若 N 欄為空，則使用 GPT-4 將英文摘要轉為繁體中文重點摘要
- 寫入 N 欄（第14欄）
---
### 📌 注意事項
- OpenAI GPT-4 使用需計費，請留意 Token 消耗。
- 若 PubMed 查詢過長導致錯誤，程式會提示使用者手動協助處理。
- 請避免重複提交相同字串以節省資源。
---
## 📝 授權與貢獻
此專案僅供學習與展示用途，如需商用請自行擴充與保護安全驗證。

---
## 📬 聯絡方式
- 作者：陳宗葆
- Email：blueskycm@gmail.com