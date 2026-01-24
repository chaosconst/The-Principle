import os
from PIL import Image, ImageOps

def process():
    input_path = os.path.expanduser("~/pob_server/vision/infero_favicon_v4.png")
    output_png = os.path.expanduser("~/pob_server/uploads/favicon_ultimate.png")
    output_ico = os.path.expanduser("~/pob_server/uploads/favicon.ico")
    
    if not os.path.exists(input_path):
        print("Input not found")
        return

    print(f"💎 Processing Ultimate Favicon: {input_path}")
    
    img = Image.open(input_path).convert("RGB")
    w, h = img.size
    
    # 1. 居中裁剪为正方形 (Center Crop)
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    right = left + min_side
    bottom = top + min_side
    img = img.crop((left, top, right, bottom))
    
    # 2. 亮度转透明 (Luminance to Alpha)
    # 使用灰度值作为基础透明度
    alpha = ImageOps.grayscale(img)
    
    # 增强对比度：让暗部更透，亮部更实
    # 阈值 15 以下完全透明，以上线性映射
    alpha = alpha.point(lambda x: 0 if x < 15 else min(255, int(x * 1.5)))
    
    # 3. 合成
    img = img.convert("RGBA")
    img.putalpha(alpha)
    
    # 4. 缩放
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    
    # 保存 PNG
    img.save(output_png)
    print(f"✅ Saved PNG: {output_png}")
    
    # 保存 ICO (覆盖旧的)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(output_ico, format='ICO', sizes=sizes)
    print(f"✅ Saved ICO: {output_ico}")

if __name__ == "__main__":
    process()
