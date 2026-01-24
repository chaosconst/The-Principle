import requests
from bs4 import BeautifulSoup
import sys
import os

url = "https://www.nyenova.no/mystisk-nova-debut-nordlysets-hjerte/"
output_file = os.path.expanduser("~/pob_server/archive/Evidence_Nordlysets_Hjerte.txt")

print(f"📖 Fetching Full Page: {url} ...\n")

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.encoding = 'utf-8'
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        
        with open(output_file, "w", encoding="utf-8") as f:
            # 1. Title
            title = soup.find('h1')
            title_text = title.get_text().strip() if title else "Unknown Title"
            f.write(f"Title: {title_text}\n")
            f.write(f"URL: {url}\n")
            f.write("-" * 40 + "\n\n")
            
            # 2. Content
            # 尝试定位文章主体
            article = soup.find('article') or soup.find('div', class_='entry-content') or soup.body
            if article:
                paragraphs = article.find_all(['p', 'h2', 'h3', 'blockquote'])
                f.write("--- CONTENT ---\n")
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text:
                        f.write(text + "\n\n")
            
            # 3. Comments
            comments = soup.find_all('div', class_='comment-content')
            if comments:
                f.write("\n--- COMMENTS ---\n")
                for i, c in enumerate(comments, 1):
                    author = c.find_previous('cite', class_='fn')
                    author_name = author.get_text() if author else 'Unknown'
                    text = c.get_text().strip()
                    f.write(f"[Comment {i} by {author_name}]\n{text}\n\n")
            else:
                # Fallback: dump all text if structure is weird
                pass

        print(f"✅ Full content saved to: {output_file}")
        
        # 打印前 500 字符和最后 500 字符作为验证
        with open(output_file, "r") as f:
            content = f.read()
            print("\n--- HEAD ---")
            print(content[:500])
            print("\n...\n")
            print("--- TAIL ---")
            print(content[-500:])

    else:
        print(f"❌ HTTP Error: {r.status_code}")

except Exception as e:
    print(f"❌ Error: {e}")
