import requests
from bs4 import BeautifulSoup
import sys

# 目标：Devs S01E05 剧本
url = "https://transcripts.simpleremix.com/script.php/devs-2020-Y84Y/s1/e5"
print(f"📖 Fetching Transcript: {url} ...\n")

try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers, timeout=15)
    
    if r.status_code == 200:
        # 这个网站通常是纯文本或简单的 HTML
        text = r.text
        
        # 简单清洗 HTML 标签 (如果存在)
        soup = BeautifulSoup(text, 'html.parser')
        clean_text = soup.get_text()
        
        # 定位关键词 "China"
        if "China" in clean_text:
            # 找到关键词位置
            idx = clean_text.find("China")
            # 提取前后 500 字符
            start = max(0, idx - 500)
            end = min(len(clean_text), idx + 1000)
            
            print("--- Kenton's Monologue (Excerpt) ---")
            print(clean_text[start:end])
        else:
            print("❌ Keyword 'China' not found in the fetched text.")
            
    else:
        print(f"❌ HTTP Error: {r.status_code}")

except Exception as e:
    print(f"❌ Error: {e}")
