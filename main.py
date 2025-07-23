import requests
from bs4 import BeautifulSoup
import datetime
from tqdm import tqdm
from urllib.parse import quote
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os

# === PubMed URL 生成器 ===
class PubMedURLGenerator:
    def __init__(self, base_url="https://pubmed.ncbi.nlm.nih.gov/?term="):
        self.base_url = base_url

    def clean_query(self, search_query):
        return search_query.replace("\n", "").strip()

    def generate_url(self, search_query, filters=None, size=200):
        cleaned_query = self.clean_query(search_query)
        encoded_query = quote(cleaned_query)
        filter_params = "&".join([f"filter={quote(f)}" for f in (filters or [])])
        return f"{self.base_url}{encoded_query}&{filter_params}&size={size}"

# === Google Sheets 初始化 ===
load_dotenv()
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SOURCE_SHEET = "爬蟲紀錄"
TARGET_SHEET = "literature_data"
DEFAULT_FILTERS = ["pubt.meta-analysis", "pubt.randomizedcontrolledtrial", "pubt.systematicreview"]

creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv("GOOGLE_CREDENTIALS"), SCOPES)
client = gspread.authorize(creds)

# === Google Sheets 操作 ===
def read_search_queries():
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SOURCE_SHEET)
    return sheet.get("A2:E")

def find_first_empty_row(sheet_name, column="A"):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
    col = sheet.col_values(ord(column.upper()) - 64)
    return len(col) + 1 if col else 2

def read_existing_pmids():
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(TARGET_SHEET)
    pmid_col = sheet.get("K2:K")
    return set(row[0] for row in pmid_col if row)

def update_search_sheet(row_index, pmid_count, status="DONE"):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SOURCE_SHEET)
    sheet.update(range_name=f"C{row_index}", values=[[pmid_count, status]])

def write_to_sheets(data, start_row):
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(TARGET_SHEET)
    cell_range = f"A{start_row}"
    sheet.update(range_name=cell_range, values=data)
    print("✅ 資料已成功寫入 Google Sheets！")

# === PubMed 爬蟲處理 ===
def extract_pmids_from_meta(soup):
    meta_tag = soup.find("meta", {"name": "log_displayeduids"})
    if meta_tag:
        return re.findall(r"\b\d+\b", meta_tag.get("content", ""))
    return []

def fetch_pmids_from_manual_input():
    content = input("請手動貼上 meta 標籤內容：\n")
    return re.findall(r"\b\d+\b", content)

def format_pub_date(pub_date):
    try:
        parts = pub_date.split()
        year = parts[0]
        month = datetime.datetime.strptime(parts[1].split("-")[0], "%b").month
        day = parts[2] if len(parts) > 2 else "01"
        return f"{year}/{int(month):02}/{int(day):02}"
    except:
        return "無效日期"

def detect_article_type(soup, title, abstract):
    content = (title + " " + abstract).lower()
    if "systematic" in content:
        return "Systematic Review"
    elif "meta-analysis" in content:
        return "Meta-Analysis"
    elif "randomized controlled trial" in content or "randomized" in content:
        return "Randomized Controlled Trial"
    elif "clinical trial" in content:
        return "Clinical Trial"
    elif "book" in content:
        return "Books and Documents"
    elif "review" in content:
        return "Review"
    else:
        return "Unknown"

def scrape_pmid_data(session, pmid, base_url, custom_topic=""):
    url = f"{base_url}{pmid}/"
    res = session.get(url, timeout=10)
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.find("h1", class_="heading-title")
        title = title.get_text(strip=True) if title else "未找到標題"

        abstract_tag = soup.find("div", id="abstract")
        if abstract_tag:
            abstract = "\n".join(line.strip() for line in abstract_tag.stripped_strings if line.lower() != "abstract")
        else:
            abstract = "未找到摘要"

        article_type = detect_article_type(soup, title, abstract)
        journal = soup.find("button", class_="journal-actions-trigger trigger")
        journal_name = journal.get_text(strip=True) if journal else "未找到期刊名稱"
        citation = soup.find("span", class_="cit")
        citation_info = citation.get_text(strip=True) if citation else "未找到發表資訊"

        pub_date = citation_info.split(";")[0].strip() if ";" in citation_info else citation_info
        sort_pub_date = format_pub_date(pub_date)

        doi_tag = soup.find("span", class_="citation-doi")
        doi = doi_tag.get_text(strip=True).replace("doi:", "").strip() if doi_tag else "未找到 DOI"

        epub_tag = soup.find("span", class_="secondary-date")
        epub_date = epub_tag.get_text(strip=True).replace("Epub", "").strip() if epub_tag else "未找到線上發表日期"

        return [
            title, abstract, article_type, journal_name, pub_date, sort_pub_date,
            citation_info, doi, epub_date, url, pmid, custom_topic
        ]
    else:
        print(f"❌ 無法訪問 PMID {pmid} 的頁面：{url}")
        return None

# === 主程式 ===
def main():
    BASE_URL = "https://pubmed.ncbi.nlm.nih.gov/"
    session = requests.Session()
    generator = PubMedURLGenerator()

    queries = read_search_queries()
    existing_pmids = read_existing_pmids()

    for idx, row in enumerate(queries, start=2):
        search_term = row[0]
        custom_topic = row[1] if len(row) > 1 else "未自訂主題"
        status = row[3] if len(row) > 3 else ""
        if status == "DONE":
            print(f"➡️ 跳過已完成：{custom_topic}")
            continue

        filters = DEFAULT_FILTERS if len(row) <= 4 or not row[4].strip() else ([] if row[4].strip().lower() == 'none' else [f.strip() for f in row[4].split(',')])

        search_url = generator.generate_url(search_term, filters=filters)
        try:
            res = session.get(search_url)
            if res.status_code == 414 or len(search_url) > 2000:
                print("⚠️ URL 過長或 414，改用手動輸入")
                pmids = fetch_pmids_from_manual_input()
            else:
                soup = BeautifulSoup(res.text, 'html.parser')
                pmids = extract_pmids_from_meta(soup)
        except Exception as e:
            print(f"❌ 搜尋失敗：{e}")
            continue

        print(f"🔍 {custom_topic} 提取到 {len(pmids)} 筆 PMIDs")
        new_pmids = [pmid for pmid in pmids if pmid not in existing_pmids]
        print(f"✨ 實際新增 {len(new_pmids)} 筆")

        update_search_sheet(idx, len(pmids))
        start_row = find_first_empty_row(TARGET_SHEET)

        results = []
        for pmid in tqdm(new_pmids, desc=f"📘 爬取中：{custom_topic}"):
            try:
                data = scrape_pmid_data(session, pmid, BASE_URL, custom_topic)
                if data:
                    results.append(data)
            except Exception as e:
                print(f"❌ 抓取 PMID {pmid} 失敗：{e}")

        if results:
            write_to_sheets(results, start_row)

        update_search_sheet(idx, len(pmids), status="DONE")

if __name__ == "__main__":
    main()
