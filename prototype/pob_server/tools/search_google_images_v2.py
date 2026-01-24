from playwright.sync_api import sync_playwright
import sys
import os
import time
import urllib.parse

def run(query, save_name):
    print(f"🚀 Google Image Search (Full View): {query} ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1500} # 增加高度，一次看更多
        )
        page = context.new_page()
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?tbm=isch&q={encoded_query}&hl=en"
        
        print(f"🌐 Navigating to: {url}")
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        
        # 拒绝 Cookie
        try:
            page.get_by_role("button", name="Reject all").click(timeout=2000)
        except:
            pass

        # 战术动作：下潜再上浮
        print("📜 Scrolling to load more...")
        page.evaluate("window.scrollTo(0, 1000)")
        time.sleep(2)
        print("⬆️ Scrolling back to top...")
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)
        
        # 截图
        save_path = os.path.expanduser(f"~/pob_server/uploads/{save_name}.jpg")
        page.screenshot(path=save_path)
        print(f"📸 Captured: {save_path}")
        
        browser.close()

if __name__ == "__main__":
    run("赵宁 毛骗", "google_zhaoning_full")
