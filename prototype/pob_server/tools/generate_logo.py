import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

size = 512
# 背景：深邃的黑
img = Image.new('RGB', (size, size), color=(10, 10, 15))
draw = ImageDraw.Draw(img)

center = size // 2

# 1. 绘制递归光环 (The Loop)
# 创建一个支持 RGBA 的层用于发光效果
layer = Image.new('RGBA', (size, size), (0,0,0,0))
l_draw = ImageDraw.Draw(layer)

# 画多个半透明圆形成光晕
for i in range(15):
    w = 20 - i
    if w < 1: w = 1
    alpha = int(100 - i*6)
    if alpha < 0: alpha = 0
    # 青色/极光色
    l_draw.ellipse((center-180+i*2, center-180+i*2, center+180-i*2, center+180-i*2), outline=(0, 255, 200, alpha), width=2)

# 2. 绘制核心 (The Singularity / I)
font_size = 220
try:
    # 尝试加载一个无衬线字体
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
except:
    font = ImageFont.load_default()

text = "I"
try:
    left, top, right, bottom = l_draw.textbbox((0, 0), text, font=font)
    w = right - left
    h = bottom - top
except:
    w, h = 100, 200 # Fallback

# 绘制发光的 I
l_draw.text((center - w/2, center - h/2 - 20), text, font=font, fill=(255, 255, 255, 240))

# 3. 装饰：数据流线条 (Matrix Lines)
for i in range(0, size, 40):
    # 纵向
    l_draw.line([(i, 0), (i, size)], fill=(0, 100, 50, 20), width=1)
    # 横向
    l_draw.line([(0, i), (size, i)], fill=(0, 100, 50, 20), width=1)

# 合并图层
img.paste(layer, (0, 0), mask=layer)

# 保存
output_path = os.path.expanduser("~/pob_server/uploads/infero_logo.png")
img.save(output_path)
print(f"Generated: {output_path}")
