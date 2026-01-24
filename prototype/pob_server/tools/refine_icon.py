import os
import PIL.Image
from google import genai
from google.genai import types

API_KEY = os.environ.get('GOOGLE_API_KEY')
client = genai.Client(api_key=API_KEY)

def refine():
    input_path = os.path.expanduser("~/pob_server/vision/infero_favicon_v4.png")
    output_black = os.path.expanduser("~/pob_server/uploads/infero_refine_black.png")
    output_trans = os.path.expanduser("~/pob_server/uploads/infero_refine_final.png")
    
    if not os.path.exists(input_path):
        print("Input not found")
        return

    print("🎨 Sending image to Gemini for background cleaning...")
    
    # 1. AI 清洗背景
    img = PIL.Image.open(input_path)
    
    prompt = "Look at this icon. Output the SAME icon but with a PURE BLACK background (#000000). Remove any gray artifacts or gradients in the background. Keep the central neon symbol sharp and unchanged. Do not redesign."
    
    try:
        response = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=[prompt, img],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
        )
        
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if part.inline_data:
                with open(output_black, "wb") as f:
                    f.write(part.inline_data.data)
                print(f"✅ Cleaned image saved: {output_black}")
                
                # 2. Python 转透明 (Black -> Transparent)
                print("✂️ Converting Black to Transparent...")
                img_black = PIL.Image.open(output_black).convert("RGBA")
                datas = img_black.getdata()
                new_data = []
                for item in datas:
                    # 严格过滤纯黑 (允许极小误差)
                    if item[0] < 10 and item[1] < 10 and item[2] < 10:
                        new_data.append((0, 0, 0, 0))
                    else:
                        new_data.append(item)
                
                img_black.putdata(new_data)
                # 缩放
                img_black = img_black.resize((256, 256), PIL.Image.Resampling.LANCZOS)
                img_black.save(output_trans, "PNG")
                print(f"✅ Final Icon Saved: {output_trans}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    refine()
