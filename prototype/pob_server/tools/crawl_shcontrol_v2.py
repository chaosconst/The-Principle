import requests
from bs4 import BeautifulSoup
import time
import os
import re

# 起始 URL (主页)
start_url = "https://shcontrolstyle.blogspot.com/?m=1"
output_file = os.path.expanduser("~/pob_server/uploads/shcontrol_full_archive.txt")

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

visited_links = set()
all_posts = []

def fetch_post_content(title, url):
    print(f"    ⬇️ Fetching: {title}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尝试提取正文
        content_div = soup.find(class_='post-body') or soup.find(class_='entry-content')
        
        if content_div:
            # 处理换行
            for br in content_div.find_all("br"):
                br.replace_with("\n")
            text = content_div.get_text(separator='\n', strip=True)
        else:
            # Fallback: 获取所有文本，但过滤掉太短的行
            lines = [line.strip() for line in soup.get_text(separator='\n').split('\n') if len(line.strip()) > 50]
            text = "\n".join(lines)
            
        post_data = f"\n{'='*60}\nTITLE: {title}\nURL: {url}\n{'='*60}\n\n{text}\n"
        all_posts.append(post_data)
        
    except Exception as e:
        print(f"    ❌ Failed: {e}")

def process_page(url):
    print(f"📄 Scanning Page: {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 暴力提取文章链接
        page_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Blogspot 文章链接特征: /yyyy/mm/xxx.html
            if re.search(r'/\d{4}/\d{2}/.*\.html', href) and '#comment' not in href:
                # 排除 archive 侧边栏链接 (通常只有月份没有标题，或者标题是日期)
                title = a.get_text(strip=True)
                if title and len(title) > 4 and href not in visited_links:
                    visited_links.add(href)
                    page_links.append((title, href))
        
        # 去重并抓取
        # 有时候同一个链接会出现多次（标题、阅读更多等），用 set 过滤
        unique_page_links = list({v: k for k, v in page_links}.items()) # href: title
        
        print(f"  Found {len(unique_page_links)} new posts.")
        
        for href, title in unique_page_links:
            fetch_post_content(title, href)
            time.sleep(0.5)

        # 2. 寻找下一页
        next_link = soup.select_one('a.blog-pager-older-link')
        if next_link:
            next_url = next_link['href']
            print(f"  👉 Next Page: {next_url}")
            time.sleep(1)
            process_page(next_url)
        else:
            print("✅ Reached end of blog.")

    except Exception as e:
        print(f"❌ Error processing page: {e}")

# 开始
process_page(start_url)

# 保存
if all_posts:
    # 按时间正序排列 (假设抓取是从新到旧，所以反转)
    all_posts.reverse()
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"SHCONTROL BLOG ARCHIVE\nGenerated: {time.strftime('%Y-%m-%d')}\nTotal Posts: {len(all_posts)}\n\n")
        for post in all_posts:
            f.write(post)
    print(f"\n🎉 Archive saved to: {output_file} ({len(all_posts)} posts)")
else:
    print("\n⚠️ No posts found.")
