from playwright.sync_api import sync_playwright
import os

def run():
    print("🚀 Visiting tools.infero.net...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True, viewport={"width": 1024, "height": 800})
        page = context.new_page()
        
        url = "https://tools.infero.net"
        
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            print(f"📄 Title: {page.title()}")
            
            save_path = os.path.expanduser("~/pob_server/uploads/tools_index.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Captured: {save_path}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
        browser.close()

if __name__ == "__main__":
    run()
