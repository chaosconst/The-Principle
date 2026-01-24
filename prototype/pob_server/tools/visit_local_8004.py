from playwright.sync_api import sync_playwright
import os

def run():
    print("🚀 Visiting http://127.0.0.1:8004 ...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 800, "height": 600})
        
        try:
            # 访问本地服务
            page.goto("http://127.0.0.1:8004", timeout=10000, wait_until="domcontentloaded")
            
            # 获取文本内容以确认
            content = page.content()
            print(f"📄 Content Preview: {content[:100]}")
            
            # 截图
            save_path = os.path.expanduser("~/pob_server/uploads/local_8004_v2.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Captured: {save_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
        browser.close()

if __name__ == "__main__":
    run()
