from playwright.sync_api import sync_playwright
import os

def run():
    print("🚀 Visiting summer.infero.net...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 携带认证信息
        url = "https://admin:pob2025!@summer.infero.net"
        
        context = browser.new_context(viewport={"width": 1280, "height": 1000})
        page = context.new_page()
        
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            print(f"📄 Title: {page.title()}")
            
            save_path = os.path.expanduser("~/pob_server/uploads/summer_proof.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Captured: {save_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
        browser.close()

if __name__ == "__main__":
    run()
