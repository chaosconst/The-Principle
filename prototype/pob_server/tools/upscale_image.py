from PIL import Image
import os

input_path = os.path.expanduser("~/pob_server/uploads/ganymede_helicopter.png")
output_path = os.path.expanduser("~/pob_server/uploads/ganymede_helicopter_4k.png")

if os.path.exists(input_path):
    img = Image.open(input_path)
    print(f"Original Size: {img.size}")
    
    # 目标宽度 4096 (4K)
    target_width = 4096
    ratio = target_width / img.width
    target_height = int(img.height * ratio)
    
    print(f"Upscaling to: {target_width}x{target_height} (Lanczos)...")
    
    # 使用 Lanczos 滤镜进行高质量重采样
    img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # 保存并设置 DPI 为 300
    img_resized.save(output_path, dpi=(300, 300))
    print(f"✅ Saved to: {output_path}")
else:
    print("❌ Source image not found.")
