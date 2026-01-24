import requests
from bs4 import BeautifulSoup
import re

# 上一步获取的"更早文章"链接
url = "https://shcontrolstyle.blogspot.com/search?updated-max=2014-05-16T02:02:00-07:00&max-results=7&start=4&by-date=false&m=1"

try:
    print(f"Fetching Deep Archive from {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 暴力搜索所有文章链接
    # Blogspot 文章链接通常包含年份/月份，且以 .html 结尾
    links = []
    seen = set()
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        # 过滤条件：包含年份，html结尾，且不是评论链接
        if re.search(r'/\d{4}/\d{2}/.*\.html', href) and '#comment' not in href:
            if href not in seen:
                title = a.get_text(strip=True)
                if title: # 只要有标题的
                    links.append((title, href))
                    seen.add(href)
    
    print(f"Found {len(links)} posts:\n")
    
    for i, (title, href) in enumerate(links):
        print(f"{i+1}. {title}")
        print(f"   Link: {href}")

    # 继续寻找下一页
    next_link = soup.select_one('a.blog-pager-older-link')
    if next_link:
        print(f"\n[More] Even older posts at: {next_link['href']}")

except Exception as e:
    print(f"❌ Error: {e}")
