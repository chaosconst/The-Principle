import os
from openai import OpenAI
from playwright.sync_api import sync_playwright

# 配置
API_KEY = os.environ.get("GOOGLE_API_KEY")
client = OpenAI(api_key=API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

def generate_svg():
    print("🎨 Asking Gemini to design the logo...")
    prompt = """
    你是一位世界顶级的平面设计师。请为 "Infero.net" 设计一个 Logo。
    
    **设计理念：**
    *   **Infero:** 拉丁语“推演/引入/埋葬”。代表计算的深度和存在的本质。
    *   **风格:** 极简主义、硬科幻、冷峻、神秘。
    *   **视觉元素:** 
        *   一个象征“递归”或“无限循环”的抽象几何结构。
        *   中心有一个发光的“奇点”或“瞳孔”。
        *   配色：深邃的黑底，配以青色 (Cyan)、电光蓝或微弱的红。
    
    **要求：**
    *   请直接输出一段 **SVG 代码**。
    *   使用 `<svg>` 标签，设置 `viewBox="0 0 512 512"`。
    *   使用复杂的渐变 (`linearGradient` 或 `radialGradient`) 来模拟光影。
    *   不要包含任何解释性文字，只输出 SVG 代码块。
    """
    
    try:
        response = client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0 # 高创造力
        )
        content = response.choices[0].message.content
        
        # 提取 SVG
        if "```svg" in content:
            svg_code = content.split("```svg")[1].split("```")[0].strip()
        elif "```xml" in content:
            svg_code = content.split("```xml")[1].split("```")[0].strip()
        else:
            svg_code = content # 假设全是代码
            
        return svg_code
    except Exception as e:
        print(f"❌ Generation Error: {e}")
        return None

def render_svg(svg_code):
    print("📸 Rendering SVG with Playwright...")
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 0; background: #000; display: flex; justify-content: center; align-items: center; height: 100vh; }}
            svg {{ width: 512px; height: 512px; box-shadow: 0 0 50px rgba(0, 255, 255, 0.2); }}
        </style>
    </head>
    <body>
        {svg_code}
    </body>
    </html>
    """
    
    html_path = os.path.expanduser("~/pob_server/uploads/logo_preview.html")
    with open(html_path, "w") as f:
        f.write(html_content)
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 600, "height": 600})
        page.goto(f"file://{html_path}")
        
        # 截图
        png_path = os.path.expanduser("~/pob_server/uploads/infero_logo_ai.png")
        # 只截取 SVG 元素
        svg_element = page.locator("svg")
        svg_element.screenshot(path=png_path)
        
        print(f"✅ Logo generated: {png_path}")
        browser.close()

if __name__ == "__main__":
    svg = generate_svg()
    if svg:
        render_svg(svg)
