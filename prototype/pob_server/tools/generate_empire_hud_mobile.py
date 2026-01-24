import os
import psutil
from PIL import Image, ImageDraw, ImageFont
import datetime

# 画布设置 (竖屏)
width, height = 600, 1024
bg_color = (10, 15, 20) # 深蓝黑
img = Image.new('RGB', (width, height), color=bg_color)
draw = ImageDraw.Draw(img)

# 字体加载
try:
    font_xl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    font_l = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    font_m = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    font_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
except:
    font_xl = font_l = font_m = font_s = ImageFont.load_default()

# 颜色定义
c_cyan = (0, 255, 255)
c_green = (0, 255, 100)
c_red = (255, 50, 50)
c_dim = (60, 80, 90)
c_white = (220, 220, 220)

# 1. 顶部标题区
draw.rectangle([(20, 20), (width-20, height-20)], outline=c_cyan, width=2)
draw.text((40, 40), "INFERO.NET", font=font_xl, fill=c_cyan)
draw.text((40, 85), "SYSTEM MONITOR", font=font_l, fill=c_dim)

# 时间戳
time_str = datetime.datetime.now().strftime("%H:%M:%S")
draw.text((width-180, 50), time_str, font=font_xl, fill=c_green)

draw.line([(20, 130), (width-20, 130)], fill=c_cyan, width=1)

# 2. 资源监控 (Resource Gauge) - 移到上方
cpu_usage = psutil.cpu_percent()
mem = psutil.virtual_memory()
mem_usage = mem.percent

y_gauge = 160
# CPU
draw.text((40, y_gauge), "CPU LOAD", font=font_s, fill=c_cyan)
draw.rectangle([(160, y_gauge), (width-100, y_gauge+20)], outline=c_dim)
bar_w = (width - 100 - 160)
draw.rectangle([(160, y_gauge), (160 + bar_w * (cpu_usage/100), y_gauge+20)], fill=c_red if cpu_usage > 80 else c_green)
draw.text((width-90, y_gauge), f"{cpu_usage}%", font=font_s, fill=c_cyan)

# MEM
y_gauge += 40
draw.text((40, y_gauge), "MEMORY", font=font_s, fill=c_cyan)
draw.rectangle([(160, y_gauge), (width-100, y_gauge+20)], outline=c_dim)
draw.rectangle([(160, y_gauge), (160 + bar_w * (mem_usage/100), y_gauge+20)], fill=c_red if mem_usage > 80 else c_green)
draw.text((width-90, y_gauge), f"{mem_usage}%", font=font_s, fill=c_cyan)

draw.line([(40, y_gauge+50), (width-40, y_gauge+50)], fill=c_dim, width=1)

# 3. 节点列表 (Nodes) - 垂直堆叠
nodes = [
    {"name": "CORE",    "url": "infero.net",        "role": "BRAIN",   "status": "ONLINE"},
    {"name": "SUMMER",  "url": "summer.infero.net", "role": "HEART",   "status": "ONLINE"},
    {"name": "SANDBOX", "url": "sandbox.infero.net","role": "HAND",    "status": "IDLE"},
    {"name": "DEMO",    "url": "demo.infero.net",   "role": "FACE",    "status": "RESET"},
    {"name": "TOOLS",   "url": "tools.infero.net",  "role": "ARSENAL", "status": "READY"},
]

start_y = 300
card_h = 100
gap = 20

for i, node in enumerate(nodes):
    y = start_y + i * (card_h + gap)
    
    # 卡片背景
    draw.rectangle([(40, y), (width-40, y+card_h)], outline=c_dim, width=1)
    # 左侧高亮条
    status_color = c_green if node["status"] in ["ONLINE", "READY"] else (c_red if node["status"] == "RESET" else c_dim)
    draw.rectangle([(40, y), (50, y+card_h)], fill=status_color)
    
    # 第一行: Name + Status
    draw.text((70, y+15), node["name"], font=font_l, fill=c_white)
    draw.text((width-120, y+20), node["status"], font=font_s, fill=status_color)
    
    # 第二行: Role + URL
    draw.text((70, y+60), f"[{node['role']}]", font=font_s, fill=(255, 200, 0))
    draw.text((180, y+60), node["url"], font=font_s, fill=(150, 150, 150))

# 4. 底部装饰
draw.text((40, height-60), "PROTOCOL: HTTPS", font=font_s, fill=c_dim)
draw.text((width-200, height-60), "OP: KAOS", font=font_s, fill=c_cyan)

# 保存
output_path = os.path.expanduser("~/pob_server/uploads/empire_hud_mobile.png")
img.save(output_path)
print(f"Generated: {output_path}")
