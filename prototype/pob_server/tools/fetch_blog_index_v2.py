import requests
from bs4 import BeautifulSoup

# 直接访问历史归档页
url = "https://shcontrolstyle.blogspot.com/search?updated-max=2014-09-26T01:06:00-07:00&max-results=7&m=1"

try:
    print(f"Fetching Archive from {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 放宽选择器
    links = soup.select('.post-title a')
    if not links:
        # 尝试更通用的
        links = soup.select('h3 a')
    
    print(f"Found {len(links)} posts:\n")
    
    for i, link in enumerate(links):
        title = link.get_text(strip=True)
        href = link['href']
        print(f"{i+1}. {title}")
        print(f"   Link: {href}")

    # 继续寻找下一页
    next_link = soup.select_one('a.blog-pager-older-link')
    if next_link:
        print(f"\n[More] Even older posts at: {next_link['href']}")

except Exception as e:
    print(f"❌ Error: {e}")
