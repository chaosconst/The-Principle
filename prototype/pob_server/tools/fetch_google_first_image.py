from playwright.sync_api import sync_playwright
import sys
import os
import time
import urllib.parse
import requests

def run(query):
    print(f"🚀 Fetching HD Image for: {query} ...")
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
        
        # 拒绝 Cookie
        try:
            page.get_by_role("button", name="Reject all").click(timeout=2000)
        except:
            pass

        # 点击第一张图片 (通常在 div[data-ri="0"] 或类似结构中)
        # Google 图片结构的 selector 可能会变，尝试通用的
        try:
            print("👆 Clicking first image result...")
            # 尝试点击第一个图片容器
            first_img = page.locator("div[data-ri='0']").first
            first_img.click()
            
            # 等待右侧大图加载 (通常 img[src^='http'])
            # 这是一个启发式等待
            time.sleep(3)
            
            # 提取大图 URL
            # 这是一个难点，Google 的大图 selector 很复杂且动态
            # 我们尝试查找点击后出现的、尺寸较大的图片
            
            # 备选方案：直接从 data-ri="0" 的元素中提取缩略图的更高清版本（如果有）
            # 或者截取大图区域
            
            # 这里我们尝试截图“预览区域”，这比提取 URL 更稳健（防止防盗链）
            # 假设右侧预览区弹出
            
            print("📸 Taking HD screenshot of the preview...")
            save_path = os.path.expanduser("~/pob_server/uploads/zhaoning_hd_01.jpg")
            page.screenshot(path=save_path) # 截全屏，因为大图通常占据很大版面
            
            print(f"✅ Captured: {save_path}")
            
        except Exception as e:
            print(f"❌ Error clicking/capturing: {e}")
            # Fallback: 截取第一张缩略图的特写
            try:
                box = page.locator("div[data-ri='0']").bounding_box()
                if box:
                    page.screenshot(path=save_path, clip=box)
                    print(f"⚠️ Fallback: Captured thumbnail clip.")
            except:
                pass
        
        browser.close()

if __name__ == "__main__":
    run("赵宁 毛骗")
