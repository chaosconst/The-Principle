import requests
from bs4 import BeautifulSoup
import sys
import os

def fetch_og_image(url, save_name):
    print(f"🖼️ Scouting Meta Data: {url} ...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 优先查找 og:image
        img_url = None
        meta_img = soup.find('meta', property='og:image')
        if meta_img:
            img_url = meta_img.get('content')
            print(f"  Found og:image: {img_url}")
        
        # 如果没有，尝试查找第一个大图
        if not img_url:
            print("  No og:image found, scanning img tags...")
            for img in soup.find_all('img'):
                src = img.get('src')
                # 简单过滤
                if src and src.startswith('http') and 'icon' not in src and 'logo' not in src:
                    img_url = src
                    break
        
        if img_url:
            try:
                print(f"  Downloading: {img_url}...")
                img_data = requests.get(img_url, headers=headers, timeout=10).content
                save_path = os.path.expanduser(f"~/pob_server/uploads/{save_name}.jpg")
                with open(save_path, 'wb') as f:
                    f.write(img_data)
                print(f"✅ Captured: {save_path} ({len(img_data)//1024} KB)")
            except Exception as e:
                print(f"❌ Download failed: {e}")
        else:
            print("❌ No suitable image found.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fetch_og_image(sys.argv[1], sys.argv[2])
