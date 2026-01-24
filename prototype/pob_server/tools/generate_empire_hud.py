import os
import psutil
from PIL import Image, ImageDraw, ImageFont
import datetime

# 画布设置
width, height = 1024, 600
bg_color = (10, 15, 20) # 深蓝黑
img = Image.new('RGB', (width, height), color=bg_color)
draw = ImageDraw.Draw(img)

# 字体加载
try:
    # 稍微调小一点标题字体，留出空间
    font_l = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    font_m = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    font_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
except:
    font_l = font_m = font_s = ImageFont.load_default()

# 颜色定义
c_cyan = (0, 255, 255)
c_green = (0, 255, 100)
c_red = (255, 50, 50)
c_dim = (60, 80, 90)
c_white = (220, 220, 220)

# 1. 绘制框架 (HUD Frame)
draw.rectangle([(20, 20), (width-20, height-20)], outline=c_cyan, width=2)
draw.line([(20, 80), (width-20, 80)], fill=c_cyan, width=1)

# 标题
title = "INFERO.NET // SYSTEM MONITOR"
draw.text((40, 35), title, font=font_l, fill=c_cyan)

# 时间戳 (动态右对齐)
time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
try:
    bbox = draw.textbbox((0, 0), time_str, font=font_m)
    time_w = bbox[2] - bbox[0]
except:
    time_w = 250
draw.text((width - time_w - 40, 45), time_str, font=font_m, fill=c_green)

# 2. 获取系统数据
cpu_usage = psutil.cpu_percent()
mem = psutil.virtual_memory()
mem_usage = mem.percent

# 3. 绘制节点 (Nodes)
nodes = [
    {"name": "CORE",    "url": "infero.net",        "port": 8000, "role": "BRAIN",   "status": "ONLINE"},
    {"name": "SUMMER",  "url": "summer.infero.net", "port": 8001, "role": "HEART",   "status": "ONLINE"},
    {"name": "SANDBOX", "url": "sandbox.infero.net","port": 8002, "role": "HAND",    "status": "IDLE"},
    {"name": "DEMO",    "url": "demo.infero.net",   "port": 8003, "role": "FACE",    "status": "RESET"},
    {"name": "TOOLS",   "url": "tools.infero.net",  "port": 8004, "role": "ARSENAL", "status": "READY"},
]

start_y = 110
row_h = 70

for i, node in enumerate(nodes):
    y = start_y + i * row_h
    # 节点框
    draw.rectangle([(40, y), (620, y+50)], outline=c_dim, width=1)
    
    # 装饰线
    draw.line([(40, y), (40, y+50)], fill=c_cyan, width=4)
    
    # 名字
    draw.text((60, y+15), node["name"], font=font_m, fill=c_white)
    
    # URL (固定坐标对齐)
    draw.text((200, y+18), node["url"], font=font_s, fill=(150, 150, 150))
    
    # 角色
    draw.text((450, y+18), f"[{node['role']}]", font=font_s, fill=(255, 200, 0))
    
    # 状态灯
    status_color = c_green if node["status"] == "ONLINE" or node["status"] == "READY" else c_dim
    if node["status"] == "RESET": status_color = c_red
    
    draw.ellipse((580, y+18, 594, y+32), fill=status_color)
    draw.text((630, y+18), node["status"], font=font_s, fill=status_color)

# 4. 绘制资源监控 (Resource Gauge)
gauge_x = 750
# CPU
draw.text((gauge_x, 120), "CPU LOAD", font=font_s, fill=c_cyan)
draw.rectangle([(gauge_x, 150), (width-50, 170)], outline=c_dim)
bar_w = (width - 50 - gauge_x)
draw.rectangle([(gauge_x, 150), (gauge_x + bar_w * (cpu_usage/100), 170)], fill=c_red if cpu_usage > 80 else c_green)
draw.text((width-90, 120), f"{cpu_usage}%", font=font_s, fill=c_cyan)

# MEM
draw.text((gauge_x, 220), "MEMORY", font=font_s, fill=c_cyan)
draw.rectangle([(gauge_x, 250), (width-50, 270)], outline=c_dim)
draw.rectangle([(gauge_x, 250), (gauge_x + bar_w * (mem_usage/100), 270)], fill=c_red if mem_usage > 80 else c_green)
draw.text((width-90, 220), f"{mem_usage}%", font=font_s, fill=c_cyan)

# 装饰性数据流
draw.text((gauge_x, 320), "NETWORK TRAFFIC", font=font_s, fill=c_dim)
draw.line([(gauge_x, 350), (width-50, 350)], fill=c_dim, width=1)
# 模拟波形
import random
prev_y = 350
for x in range(gauge_x, width-50, 10):
    next_y = 350 + random.randint(-20, 20)
    draw.line([(x, prev_y), (x+10, next_y)], fill=c_cyan, width=1)
    prev_y = next_y

# 5. 底部装饰
draw.text((40, height-40), "PROTOCOL: HTTPS/SSL SECURED", font=font_s, fill=c_dim)
draw.text((width-200, height-40), "OPERATOR: KAOS", font=font_s, fill=c_cyan)

# 保存
output_path = os.path.expanduser("~/pob_server/uploads/empire_hud_v2.png")
img.save(output_path)
print(f"Generated: {output_path}")
