import os
from PIL import Image, ImageDraw

def create_favicon():
    input_path = os.path.expanduser("~/pob_server/vision/infero_favicon_v4.png")
    output_png = os.path.expanduser("~/pob_server/uploads/favicon.png")
    output_ico = os.path.expanduser("~/pob_server/uploads/favicon.ico")
    
    if not os.path.exists(input_path):
        print("Input not found")
        return

    print(f"✂️ Processing Favicon: {input_path}")
    
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    
    # 1. 创建圆形遮罩
    # 假设 logo 居中，我们取宽度的 95% 作为直径，留一点呼吸空间
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    # 稍微收缩一点边界，切掉可能的黑边
    margin = int(width * 0.02) 
    draw.ellipse((margin, margin, width-margin, height-margin), fill=255)
    
    # 2. 应用遮罩
    output = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask=mask)
    
    # 3. 裁剪空白
    bbox = output.getbbox()
    if bbox:
        output = output.crop(bbox)
        
    # 4. 生成 PNG (256x256)
    icon_large = output.resize((256, 256), Image.Resampling.LANCZOS)
    icon_large.save(output_png)
    print(f"✅ Saved PNG: {output_png}")
    
    # 5. 生成 ICO (包含多尺寸)
    # ICO 格式通常包含 16, 32, 48, 64, 128, 256
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icon_large.save(output_ico, format='ICO', sizes=sizes)
    print(f"✅ Saved ICO: {output_ico}")

if __name__ == "__main__":
    create_favicon()
