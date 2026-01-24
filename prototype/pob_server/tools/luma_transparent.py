import os
from PIL import Image, ImageOps

def process():
    input_path = os.path.expanduser("~/pob_server/vision/infero_favicon_v4.png")
    output_path = os.path.expanduser("~/pob_server/uploads/infero_icon_luma.png")
    
    if not os.path.exists(input_path):
        print("Input not found")
        return

    print(f"🧪 Processing Luminance to Alpha: {input_path}")
    
    img = Image.open(input_path).convert("RGB")
    
    # 1. 自动裁剪黑边
    # 先转灰度找边界
    gray = ImageOps.grayscale(img)
    bbox = gray.getbbox()
    if bbox:
        img = img.crop(bbox)
        # 稍微外扩一点以免切断光晕
        # (这里简化处理，直接用 crop 后的图)
    
    # 2. 生成 Alpha 通道
    # 使用图像的亮度作为基础 Alpha
    # 越亮越不透明，越黑越透明
    # 为了让主体更实，我们可以对亮度进行增强
    # 比如：Alpha = (Luminance * 1.5) clamped to 255
    
    r, g, b = img.split()
    
    # 使用 Max(R, G, B) 作为亮度基础，这样纯色也能保留
    # 逐像素处理比较慢，使用 point 函数加速
    # 这里我们简单用 grayscale 作为 alpha 基础
    alpha = ImageOps.grayscale(img)
    
    # 增强 Alpha：让暗部更透，亮部更实
    # x < 20 -> 0 (去除极暗噪点)
    # x > 20 -> 放大
    alpha = alpha.point(lambda x: 0 if x < 15 else min(255, int(x * 1.5)))
    
    # 3. 合成 RGBA
    img.putalpha(alpha)
    
    # 4. 缩放
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    
    img.save(output_path, "PNG")
    print(f"✅ Saved: {output_path}")

if __name__ == "__main__":
    process()
