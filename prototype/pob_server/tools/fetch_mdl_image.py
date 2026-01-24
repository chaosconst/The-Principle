import requests
from bs4 import BeautifulSoup
import sys
import os

def fetch_mdl(url, name):
    print(f"🖼️ Scouting MyDramaList: {url} ...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # MDL 的头像通常在 .col-lg-4 img 或 .cover img
            img = soup.find('img', class_='img-responsive')
            
            if img and img.get('src'):
                img_url = img['src']
                print(f"  Found Image: {img_url}")
                
                # 下载
                img_data = requests.get(img_url, headers=headers, timeout=10).content
                save_path = os.path.expanduser(f"~/pob_server/uploads/{name}.jpg")
                with open(save_path, 'wb') as f:
                    f.write(img_data)
                print(f"✅ Captured: {save_path}")
            else:
                print("❌ Image tag not found.")
        else:
            print(f"❌ HTTP Error: {r.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fetch_mdl(sys.argv[1], sys.argv[2])
