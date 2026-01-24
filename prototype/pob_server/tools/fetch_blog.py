import requests
from bs4 import BeautifulSoup
import os

url = "https://shcontrolstyle.blogspot.com/2014/05/bdsm.html?m=1"

try:
    print(f"Fetching {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    title = soup.title.string if soup.title else "Untitled"
    print(f"Title: {title}")
    
    content_div = soup.find(class_='post-body')
    if content_div:
        text = content_div.get_text(separator='\n', strip=True)
    else:
        text = soup.get_text(separator='\n', strip=True)
        
    filename = "matrix_bdsm.txt"
    save_path = os.path.join(os.path.expanduser("~/pob_server/uploads"), filename)
    
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write(f"Title: {title}\n")
        f.write("-" * 40 + "\n\n")
        f.write(text)
        
    print(f"✅ Content saved to: {save_path}")
    print("-" * 20)
    print(text[:1000]) 

except Exception as e:
    print(f"❌ Error: {e}")
