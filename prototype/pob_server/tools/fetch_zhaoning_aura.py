from playwright.sync_api import sync_playwright
import os
import time

def run():
    print("🔌 Connecting to Persistent Browser...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            if not browser.contexts:
                context = browser.new_context()
            else:
                context = browser.contexts[0]
            page = context.new_page()
            
            # 搜索赵宁的霸气剧照
            url = "https://image.baidu.com/search/index?tn=baiduimage&word=毛骗%20赵宁%20霸气"
            print(f"🌐 Visiting: {url}")
            
            # 设置视口大一点
            page.set_viewport_size({"width": 1280, "height": 800})
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # 稍微滚动一下加载图片
            page.evaluate("window.scrollTo(0, 300)")
            time.sleep(2)
            
            # 截图
            save_path = os.path.expanduser("~/pob_server/uploads/zhaoning_aura.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Captured: {save_path}")
            
            page.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run()
