from playwright.sync_api import sync_playwright
import os

def run():
    print("🚀 Verifying HTTPS Access...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 忽略 HTTPS 证书错误（虽然我们是正规证书，但以防万一）
        context = browser.new_context(ignore_https_errors=True, viewport={"width": 1280, "height": 1000})
        page = context.new_page()
        
        # 携带认证信息访问
        url = "https://admin:pob2025!@infero.net"
        print(f"🌐 Navigating to: {url}")
        
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            print(f"📄 Title: {page.title()}")
            
            save_path = os.path.expanduser("~/pob_server/uploads/https_proof.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Captured: {save_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
        browser.close()

if __name__ == "__main__":
    run()
