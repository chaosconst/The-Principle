import requests
from bs4 import BeautifulSoup
import sys
import os
from urllib.parse import urljoin

def fetch_first_image(url, save_name):
    print(f"🖼️ Scouting: {url} ...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': url
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 提取所有图片链接
        images = []
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src and src.startswith('http'):
                # 简单过滤：排除图标、头像等小图
                if 'icon' not in src and 'avatar' not in src and '.svg' not in src:
                    images.append(src)
        
        # 尝试下载第一张有效的大图 (大于 10KB)
        for i, img_url in enumerate(images[:5]): # 只试前5张
            try:
                print(f"  Trying image {i+1}: {img_url[:50]}...")
                img_data = requests.get(img_url, headers=headers, timeout=5).content
                if len(img_data) > 20000: # > 20KB
                    save_path = os.path.expanduser(f"~/pob_server/uploads/{save_name}.jpg")
                    with open(save_path, 'wb') as f:
                        f.write(img_data)
                    print(f"✅ Captured: {save_path} ({len(img_data)//1024} KB)")
                    return
            except Exception as e:
                print(f"  Failed: {e}")
                continue
                
        print("❌ No valid large image found.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 fetch_images.py <url> <save_name>")
    else:
        fetch_first_image(sys.argv[1], sys.argv[2])
