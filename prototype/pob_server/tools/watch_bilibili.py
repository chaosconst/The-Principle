from playwright.sync_api import sync_playwright
import os
import time

def run():
    print("🚀 Going to Bilibili...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        # 目标：毛骗剧组被抓的新闻/解说视频
        url = "https://search.bilibili.com/all?keyword=毛骗%20剧组%20被抓"
        print(f"🌐 Navigating to: {url}")
        
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # 稍微等待加载
            time.sleep(5)
            
            # 截图
            save_path = os.path.expanduser("~/pob_server/uploads/bilibili_search.jpg")
            page.screenshot(path=save_path)
            print(f"📸 Screenshot captured: {save_path}")
            
            # 尝试提取第一个视频的标题
            first_video = page.locator(".bili-video-card__info--right .bili-video-card__info--tit").first
            if first_video.count() > 0:
                print(f"📺 First Video Title: {first_video.inner_text()}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            # 尝试抢救性截图
            page.screenshot(path=os.path.expanduser("~/pob_server/uploads/bilibili_error.jpg"))
        
        browser.close()

if __name__ == "__main__":
    run()
