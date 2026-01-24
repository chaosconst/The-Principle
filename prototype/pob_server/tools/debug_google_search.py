from playwright.sync_api import sync_playwright
import sys
import os
import time
import urllib.parse

def run(query):
    print(f"🕵️ Debugging Google Search: {query} ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1000}
        )
        page = context.new_page()
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?tbm=isch&q={encoded_query}&hl=en"
        
        print(f"🌐 Navigating to: {url}")
        try:
            # 缩短超时时间，我们只想看它卡在哪
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            time.sleep(2) # 等待渲染
        except Exception as e:
            print(f"⚠️ Navigation Warning: {e}")

        # 无论成功失败，直接截图当前状态
        save_path = os.path.expanduser("~/pob_server/uploads/debug_view.jpg")
        try:
            page.screenshot(path=save_path, full_page=False)
            print(f"📸 Debug Screenshot: {save_path}")
            
            # 顺便打印一下页面标题，辅助判断
            print(f"📄 Page Title: {page.title()}")
            
        except Exception as e:
            print(f"❌ Screenshot failed: {e}")
        
        browser.close()

if __name__ == "__main__":
    run("赵宁 毛骗")
