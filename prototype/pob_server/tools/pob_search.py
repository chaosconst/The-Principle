import sys
import requests
from bs4 import BeautifulSoup
import argparse

def search(query, max_results=5):
    print(f"🔍 Searching: '{query}' ...")
    url = "https://lite.duckduckgo.com/lite/"
    data = {'q': query}
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        r = requests.post(url, data=data, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"❌ HTTP Error: {r.status_code}")
            return

        soup = BeautifulSoup(r.text, 'html.parser')
        
        # DuckDuckGo Lite 的结构通常是 table 布局
        # 标题在 a.result-link
        # 摘要在 td.result-snippet
        
        # 获取所有结果行
        # 这里的逻辑需要一点技巧，因为标题和摘要可能在不同的 tr 里
        # 但通常它们是成对出现的顺序
        
        links = soup.find_all('a', class_='result-link')
        snippets = soup.find_all('td', class_='result-snippet')
        
        if not links:
            print("No results found.")
            return

        print(f"✅ Found {len(links)} results:\n")
        
        count = 0
        for i, link in enumerate(links):
            if count >= max_results: break
            
            title = link.get_text().strip()
            href = link['href']
            
            # 尝试获取对应的摘要
            snippet_text = "No snippet available."
            if i < len(snippets):
                snippet_text = snippets[i].get_text().strip()
            
            print(f"### {count+1}. {title}")
            print(f"- **Link:** {href}")
            print(f"- **Snippet:** {snippet_text}")
            print("-" * 40)
            count += 1
            
    except Exception as e:
        print(f"❌ Search Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PoB Web Search Tool (Enhanced)")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("-n", "--num", type=int, default=5, help="Number of results")
    
    args = parser.parse_args()
    search(args.query, args.num)
