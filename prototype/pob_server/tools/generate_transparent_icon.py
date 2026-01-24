import os
import sys
from PIL import Image
from google import genai
from google.genai import types

API_KEY = os.environ.get('GOOGLE_API_KEY')
client = genai.Client(api_key=API_KEY)

def generate_on_black():
    print("🎨 Generating Logo on Solid Black Background...")
    prompt = "Design a favicon for 'Infero.net'. Visual: A circular chat bubble containing connected nodes and a digital pulse (waveform). Style: Neon Blue and Purple gradient. Background: SOLID BLACK (Hex #000000). No checkerboard. High contrast. Flat vector style."
    
    response = client.models.generate_content(
        model='gemini-3-pro-image-preview',
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
    )
    
    if response.candidates and response.candidates[0].content.parts:
        part = response.candidates[0].content.parts[0]
        if part.inline_data:
            path = os.path.expanduser("~/pob_server/uploads/temp_logo_black.png")
            with open(path, "wb") as f:
                f.write(part.inline_data.data)
            return path
    return None

def make_transparent(input_path, output_path):
    print("✂️ Removing Background...")
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        # 简单的色键抠图：将接近黑色的像素设为透明
        # 阈值设为 15，避免扣掉深色的阴影
        if item[0] < 15 and item[1] < 15 and item[2] < 15:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    
    # 裁剪边缘空白
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    # 调整大小为标准 Icon (256x256)
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    
    img.save(output_path, "PNG")
    print(f"✅ Transparent Icon Saved: {output_path}")

if __name__ == "__main__":
    raw_path = generate_on_black()
    if raw_path:
        final_path = os.path.expanduser("~/pob_server/uploads/infero_icon_transparent.png")
        make_transparent(raw_path, final_path)
    else:
        print("❌ Generation failed.")
