from playwright.sync_api import sync_playwright
import time
import sys

def run_server():
    print("🚀 Starting Persistent Browser (CDP Mode)...")
    with sync_playwright() as p:
        # 启动浏览器，开启 CDP 端口 9222
        #以此方式启动，playwright 脚本结束时浏览器不会关闭，除非我们显式关闭它
        # 但 sync_playwright 的上下文管理器会在退出时关闭浏览器。
        # 所以我们需要一种方式让它"挂起"。
        
        # 使用 launch_persistent_context 或者直接 launch 并保持脚本运行
        browser = p.chromium.launch(
            headless=True,
            args=['--remote-debugging-port=9222']
        )
        print("✅ Browser listening on port 9222")
        print("💤 Daemon is sleeping (waiting for commands)...")
        
        try:
            # 无限等待，保持浏览器存活
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            print("🛑 Stopping Browser...")
            browser.close()

if __name__ == "__main__":
    run_server()
