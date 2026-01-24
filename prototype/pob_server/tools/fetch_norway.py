import requests
from bs4 import BeautifulSoup
import sys

url = "https://www.nyenova.no/mystisk-nova-debut-nordlysets-hjerte/"
print(f"📖 Fetching Norwegian Sci-Fi: {url} ...\n")

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.encoding = 'utf-8' # 或者是自动检测
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 提取标题
        title = soup.find('h1')
        title_text = title.get_text().strip() if title else "Unknown Title"
        print(f"🇳🇴 Title: {title_text}")
        
        # 提取正文 (尝试常见的文章容器类名，或者直接提取所有 p)
        # 这里简单提取前几段
        article = soup.find('article') or soup.find('div', class_='entry-content') or soup.body
        paragraphs = article.find_all('p')
        
        print("\n--- Excerpt (Norwegian) ---")
        for p in paragraphs[:5]:
            print(p.get_text().strip())
            print("")
            
        print("\n--- End of Excerpt ---")
        
    else:
        print(f"❌ HTTP Error: {r.status_code}")

except Exception as e:
    print(f"❌ Error: {e}")
