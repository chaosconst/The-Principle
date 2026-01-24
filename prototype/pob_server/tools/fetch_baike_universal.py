from playwright.sync_api import sync_playwright
import os
import time
import sys

def run(url, name):
    print(f"🚀 Playwright Mission: Target {name}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1000}
        )
        page = context.new_page()
        
        print(f"🌐 Navigating to: {url}")
        save_path = os.path.expanduser(f"~/pob_server/uploads/{name}.jpg")
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # 模拟滚动
            page.evaluate("window.scrollTo(0, 500)")
            time.sleep(2)
            
            title = page.title()
            print(f"📄 Page Title: {title}")
            
            # 截图
            page.screenshot(path=save_path)
            print(f"📸 Screenshot captured: {save_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            # 尝试抢救性截图
            try:
                page.screenshot(path=save_path)
            except:
                pass
        
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 fetch_baike_universal.py <url> <save_name>")
    else:
        run(sys.argv[1], sys.argv[2])
