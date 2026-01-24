from playwright.sync_api import sync_playwright
import os
import time

def run():
    print("🔌 Connecting to Persistent Browser (Port 9222)...")
    try:
        with sync_playwright() as p:
            # 连接到已存在的浏览器
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            
            # 使用默认上下文或新建
            if not browser.contexts:
                context = browser.new_context()
            else:
                context = browser.contexts[0]
                
            page = context.new_page()
            
            url = "https://www.baidu.com"
            print(f"🌐 Visiting: {url}")
            page.goto(url)
            print(f"📄 Title: {page.title()}")
            
            # 截图验证
            save_path = os.path.expanduser("~/pob_server/uploads/persistent_test.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Captured: {save_path}")
            
            # 只关闭页面，保留浏览器存活
            page.close()
            print("✅ Task complete. Browser stays alive.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run()
