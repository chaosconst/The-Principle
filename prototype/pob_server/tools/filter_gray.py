import os
from PIL import Image

def process():
    input_path = os.path.expanduser("~/pob_server/uploads/infero_icon_final.png")
    output_path = os.path.expanduser("~/pob_server/uploads/infero_icon_cut.png")
    
    if not os.path.exists(input_path):
        print(f"❌ Input not found: {input_path}")
        return

    print(f"🎨 Filtering Dark Gray (<30): {input_path}")
    
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    # 阈值：30
    threshold = 30
    
    for item in datas:
        # item: (r, g, b, a)
        # 如果 RGB 都小于 30，视为背景/深灰色，设为透明
        if item[0] < threshold and item[1] < threshold and item[2] < threshold:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"✅ Saved: {output_path}")

if __name__ == "__main__":
    process()
