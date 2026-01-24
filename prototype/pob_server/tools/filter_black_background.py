import os
from PIL import Image

def process():
    input_path = os.path.expanduser("~/pob_server/vision/infero_favicon_v4.png")
    output_path = os.path.expanduser("~/pob_server/uploads/infero_icon_keyed.png")
    
    if not os.path.exists(input_path):
        print(f"❌ Input not found: {input_path}")
        return

    print(f"🎨 Filtering Black Background: {input_path}")
    
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    # 阈值设定：RGB 均小于 30 视为背景
    threshold = 30
    
    for item in datas:
        # item: (r, g, b, a)
        if item[0] < threshold and item[1] < threshold and item[2] < threshold:
            new_data.append((0, 0, 0, 0))
        else:
            # 保留原样
            new_data.append(item)
            
    img.putdata(new_data)
    
    # 自动裁剪边缘空白
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    # 缩放至标准尺寸
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    
    img.save(output_path, "PNG")
    print(f"✅ Saved: {output_path}")

if __name__ == "__main__":
    process()
