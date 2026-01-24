from playwright.sync_api import sync_playwright
import sys
import os
import time
import urllib.parse

def run(query, save_name):
    print(f"🚀 Google Image Search: {query} ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1000}
        )
        page = context.new_page()
        
        # 构造 Google 图片搜索 URL
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?tbm=isch&q={encoded_query}&hl=en" # 强制英文界面避免乱码
        
        print(f"🌐 Navigating to: {url}")
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        
        # 拒绝 Cookie 弹窗 (如果出现)
        try:
            page.get_by_role("button", name="Reject all").click(timeout=2000)
        except:
            pass

        # 稍微滚动加载更多图片
        page.evaluate("window.scrollTo(0, 500)")
        time.sleep(2)
        
        # 截图
        save_path = os.path.expanduser(f"~/pob_server/uploads/{save_name}.jpg")
        page.screenshot(path=save_path)
        print(f"📸 Captured: {save_path}")
        
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 search_google_images.py <query> <save_name>")
    else:
        run(sys.argv[1], sys.argv[2])
