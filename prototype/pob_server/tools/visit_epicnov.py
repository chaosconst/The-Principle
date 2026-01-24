from playwright.sync_api import sync_playwright
import os

def run():
    print("🚀 Visiting epicnov.com...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        
        try:
            # 尝试访问
            url = "http://epicnov.com"
            print(f"🌐 Navigating to: {url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            print(f"📄 Title: {page.title()}")
            
            # 截图
            save_path = os.path.expanduser("~/pob_server/uploads/epicnov_site.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Captured: {save_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
        browser.close()

if __name__ == "__main__":
    run()
