from playwright.sync_api import sync_playwright
import sys
import os
import time
import urllib.parse

def run(query):
    print(f"🚀 Targeting First Thumbnail: {query} ...")
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
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        
        try:
            # 拒绝 Cookie
            try:
                page.get_by_role("button", name="Reject all").click(timeout=2000)
            except:
                pass

            # 等待图片加载
            page.wait_for_selector("img.rg_i", timeout=10000)
            
            # 定位第一张图
            # Google 图片搜索结果通常带有 rg_i 类
            first_img = page.locator("img.rg_i").first
            
            if first_img.is_visible():
                print("📸 Capturing element screenshot...")
                save_path = os.path.expanduser("~/pob_server/uploads/zhaoning_closeup.jpg")
                first_img.screenshot(path=save_path)
                print(f"✅ Captured: {save_path}")
            else:
                print("❌ First image not visible.")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            # 备选：截取左上角区域
            page.screenshot(path=os.path.expanduser("~/pob_server/uploads/zhaoning_fallback.jpg"), clip={"x":0, "y":150, "width":400, "height":400})
        
        browser.close()

if __name__ == "__main__":
    run("赵宁 毛骗")
