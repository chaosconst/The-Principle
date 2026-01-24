import requests
from bs4 import BeautifulSoup

url = "https://shcontrolstyle.blogspot.com/?m=1"

try:
    print(f"Fetching Index from {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Blogspot 通常把文章链接放在 .post-title a 或 .post-title.entry-title a
    posts = []
    
    # 尝试多种选择器
    links = soup.select('h3.post-title a')
    if not links:
        links = soup.select('.post-title a')
    
    print(f"Found {len(links)} posts on the main page:\n")
    
    for i, link in enumerate(links):
        title = link.get_text(strip=True)
        href = link['href']
        print(f"{i+1}. {title}")
        print(f"   Link: {href}")
        posts.append((title, href))

    # 检查是否有"上一页/下一页"
    next_link = soup.select_one('a.blog-pager-older-link')
    if next_link:
        print(f"\n[More] Older posts available at: {next_link['href']}")

except Exception as e:
    print(f"❌ Error: {e}")
