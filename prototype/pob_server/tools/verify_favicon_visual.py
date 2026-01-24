from playwright.sync_api import sync_playwright
import os

def run():
    print("🚀 Verifying Favicon Visuals...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 忽略证书错误 (因为本地回环可能导致 SNI 问题，虽然我们有证书)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        url = "https://summer.infero.net/favicon.ico"
        print(f"🌐 Navigating to: {url}")
        
        try:
            page.goto(url)
            # 截图
            save_path = os.path.expanduser("~/pob_server/uploads/favicon_proof.png")
            page.screenshot(path=save_path)
            print(f"📸 Captured: {save_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
            
        browser.close()

if __name__ == "__main__":
    run()
