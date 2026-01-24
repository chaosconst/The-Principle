from playwright.sync_api import sync_playwright
import os

def run():
    print("🚀 Visiting Google...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 访问 Google 英文版 (避免重定向到其他地区)
        url = "https://www.google.com/ncr"
        print(f"🌐 Navigating to: {url}")
        
        page.goto(url)
        print(f"📄 Title: {page.title()}")
        
        # 截图
        save_path = os.path.expanduser("~/pob_server/uploads/google_homepage.jpg")
        page.screenshot(path=save_path)
        print(f"📸 Captured: {save_path}")
        
        browser.close()

if __name__ == "__main__":
    run()
