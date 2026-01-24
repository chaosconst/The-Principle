import os
from PIL import Image, ImageDraw

def create_favicon():
    input_path = os.path.expanduser("~/pob_server/vision/infero_favicon_v4.png")
    output_png = os.path.expanduser("~/pob_server/uploads/favicon_fixed.png")
    
    if not os.path.exists(input_path):
        print("Input not found")
        return

    print(f"✂️ Processing Favicon (Fixed): {input_path}")
    
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size
    
    # 1. 居中裁剪为正方形
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    right = left + min_side
    bottom = top + min_side
    
    img = img.crop((left, top, right, bottom))
    print(f"  Cropped to square: {min_side}x{min_side}")
    
    # 2. 创建圆形遮罩
    mask = Image.new('L', (min_side, min_side), 0)
    draw = ImageDraw.Draw(mask)
    
    # 稍微收缩，切掉边缘黑边
    margin = int(min_side * 0.02)
    draw.ellipse((margin, margin, min_side-margin, min_side-margin), fill=255)
    
    # 3. 应用遮罩
    output = Image.new('RGBA', (min_side, min_side), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask=mask)
    
    # 4. 缩放
    icon_final = output.resize((256, 256), Image.Resampling.LANCZOS)
    icon_final.save(output_png)
    print(f"✅ Saved PNG: {output_png}")

if __name__ == "__main__":
    create_favicon()
