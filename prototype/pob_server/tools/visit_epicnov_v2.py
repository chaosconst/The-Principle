from playwright.sync_api import sync_playwright
import os
import time

def run():
    print("🚀 Visiting epicnov.com (Retry)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        
        try:
            url = "http://epicnov.com"
            print(f"🌐 Navigating to: {url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            print("⏳ Waiting for rendering (8s)...")
            time.sleep(8) # 增加等待时间
            
            print(f"📄 Title: {page.title()}")
            
            save_path = os.path.expanduser("~/pob_server/uploads/epicnov_site_v2.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Captured: {save_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
        browser.close()

if __name__ == "__main__":
    run()
