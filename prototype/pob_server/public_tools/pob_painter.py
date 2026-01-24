# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai",
#     "Pillow",
# ]
# ///

import os
import sys
import argparse

# 优雅的依赖检查
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ Missing Dependency: google-genai")
    print("👉 Please run: pip install google-genai")
    sys.exit(1)

# 配置
API_KEY = os.getenv('GOOGLE_API_KEY')
# 切换回 Gemini 3 Pro
MODEL_ID = 'gemini-3-pro-image-preview'

def generate_image(output_filename, prompt):
    if not API_KEY:
        print("❌ Error: GOOGLE_API_KEY environment variable not set.")
        return False

    client = genai.Client(api_key=API_KEY)
    
    print(f"🎨 Generating: {output_filename}")
    print(f"🤖 Model: {MODEL_ID}")
    print(f"📝 Prompt: {prompt}")

    try:
        # 使用 generate_content 接口 (Gemini 原生)
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
        )

        # 提取图像数据
        image_data = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_data = part.inline_data.data
                    break
        
        if image_data:
            # 确保目录存在
            output_dir = os.path.dirname(os.path.abspath(output_filename))
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            with open(output_filename, "wb") as f:
                f.write(image_data)
            print(f"✅ Success! Image saved to {output_filename}")
            return True
        else:
            print("❌ Error: No image data returned.")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PoB Universal Painter (Gemini Edition)')
    parser.add_argument('filename', help='Output filename (e.g., scene3.png)')
    parser.add_argument('prompt', help='Image description prompt')
    args = parser.parse_args()

    generate_image(args.filename, args.prompt)
