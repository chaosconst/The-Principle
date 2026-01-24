from playwright.sync_api import sync_playwright
import os
import time

def run():
    print("🚀 Playwright Mission: Infiltrate Baidu Baike...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 伪装成桌面浏览器
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        # 安宁 (毛骗)
        url = "https://baike.baidu.com/item/%E5%AE%89%E5%AE%81/22291175"
        print(f"🌐 Navigating to: {url}")
        
        try:
            page.goto(url, timeout=30000)
            # 等待网络空闲，确保图片加载
            page.wait_for_load_state("networkidle")
            
            title = page.title()
            print(f"📄 Page Title: {title}")
            
            # 截图
            save_path = os.path.expanduser("~/pob_server/uploads/anning_baike_pw.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Screenshot captured: {save_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        browser.close()

if __name__ == "__main__":
    run()
