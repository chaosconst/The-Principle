import requests
from bs4 import BeautifulSoup
import time
import os
import re

start_url = "https://shcontrolstyle.blogspot.com/search?updated-max=2015-01-01T00:00:00-07:00&max-results=50&by-date=false&m=1"
output_file = os.path.expanduser("~/pob_server/uploads/shcontrol_full_archive.txt")

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

visited_links = set()
all_posts = []

def fetch_posts_from_page(url):
    print(f"📄 Crawling page: {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取文章链接
        # Blogspot 移动版通常在 h3.mobile-index-title a
        links = soup.select('h3.mobile-index-title a')
        if not links:
            links = soup.select('h3.post-title a')
            
        for link in links:
            href = link['href']
            title = link.get_text(strip=True)
            
            if href not in visited_links:
                visited_links.add(href)
                print(f"  Found post: {title}")
                # 获取文章内容
                fetch_post_content(title, href)

        # 寻找下一页
        next_link = soup.select_one('a.blog-pager-older-link')
        if next_link:
            time.sleep(1) # 礼貌爬取
            fetch_posts_from_page(next_link['href'])
        else:
            print("✅ Reached end of blog.")

    except Exception as e:
        print(f"❌ Error crawling page: {e}")

def fetch_post_content(title, url):
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_div = soup.find(class_='post-body')
        if content_div:
            # 处理换行，把 <br> 换成 \n
            for br in content_div.find_all("br"):
                br.replace_with("\n")
            text = content_div.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
            
        post_data = f"\n{'='*40}\nTITLE: {title}\nURL: {url}\n{'='*40}\n\n{text}\n"
        all_posts.append(post_data)
        
    except Exception as e:
        print(f"  ❌ Failed to fetch content: {e}")

# 开始爬取
# 由于 Blogspot 的结构，直接从主页或者一个较新的日期开始
# 这里尝试从主页开始，或者直接用之前的 search url
fetch_posts_from_page("https://shcontrolstyle.blogspot.com/?m=1")

# 写入文件
if all_posts:
    # 倒序排列（按时间正序，如果是从新到旧爬的话）
    # Blogspot 默认从新到旧，我们翻转一下变成从旧到新阅读
    all_posts.reverse()
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"SHCONTROL BLOG ARCHIVE\nGenerated: {time.strftime('%Y-%m-%d')}\nTotal Posts: {len(all_posts)}\n\n")
        for post in all_posts:
            f.write(post)
    print(f"\n🎉 Archive saved to: {output_file}")
else:
    print("\n⚠️ No posts found.")

