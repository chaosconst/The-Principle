import os
from PIL import Image, ImageDraw, ImageOps

def process_icon():
    input_path = os.path.expanduser("~/pob_server/vision/infero_favicon_v4.png")
    output_path = os.path.expanduser("~/pob_server/uploads/infero_icon_final.png")
    
    if not os.path.exists(input_path):
        print(f"❌ Input file not found: {input_path}")
        return

    print(f"✂️ Processing: {input_path}")
    
    try:
        img = Image.open(input_path).convert("RGBA")
        width, height = img.size
        
        # 1. 创建圆形遮罩 (Mask)
        # 假设图标在正中心，直径约为宽度的 90% (留一点余量或者切边)
        # 根据之前的截图，图标几乎占满画面，我们试着切一个 95% 大小的圆
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        
        # 计算圆的边界
        margin = 10 
        draw.ellipse((margin, margin, width-margin, height-margin), fill=255)
        
        # 2. 应用遮罩
        # 创建一个新的透明底图片
        output = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        # 将原图粘贴上去，使用 mask 决定透明度
        output.paste(img, (0, 0), mask=mask)
        
        # 3. 裁剪空白边缘 (Auto Crop)
        bbox = output.getbbox()
        if bbox:
            output = output.crop(bbox)
            
        # 4. 缩放至标准图标大小 (256x256)
        output = output.resize((256, 256), Image.Resampling.LANCZOS)
        
        output.save(output_path, "PNG")
        print(f"✅ Processed Icon Saved: {output_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    process_icon()
