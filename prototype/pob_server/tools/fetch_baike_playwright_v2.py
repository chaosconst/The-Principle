from playwright.sync_api import sync_playwright
import os
import time

def run():
    print("🚀 Playwright Mission: Force Capture...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1000}
        )
        page = context.new_page()
        
        # 安宁 (毛骗)
        url = "https://baike.baidu.com/item/%E5%AE%89%E5%AE%81/22291175"
        print(f"🌐 Navigating to: {url}")
        
        save_path = os.path.expanduser("~/pob_server/uploads/anning_baike_pw.jpg")
        
        try:
            # 放宽等待条件至 domcontentloaded，超时加倍
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            print("📄 DOM Loaded.")
            
            # 模拟滚动以触发懒加载
            page.evaluate("window.scrollTo(0, 500)")
            time.sleep(2)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            
            title = page.title()
            print(f"📄 Page Title: {title}")
            
        except Exception as e:
            print(f"⚠️ Navigation Warning: {e}")
            
        finally:
            # 无论如何，强制截图
            try:
                page.screenshot(path=save_path)
                print(f"📸 Screenshot captured: {save_path}")
            except Exception as e:
                print(f"❌ Screenshot failed: {e}")
        
        browser.close()

if __name__ == "__main__":
    run()
