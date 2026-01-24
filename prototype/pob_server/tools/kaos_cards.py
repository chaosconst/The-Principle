import sys
import os
import random
from datetime import datetime

# 尝试获取真实天气
sys.path.append(os.path.expanduser("~/pob_server/tools"))
try:
    from native_weather import get_weather
    raw_weather = get_weather(39.9042, 116.4074)
    # Parse
    parts = raw_weather.split("|")
    temp_val = float(parts[0].split(":")[1].strip().replace("°C", ""))
except:
    temp_val = -5.0 # Fallback

def make_card(title, icon, color, status, content):
    return f"""
{color} **{title} {icon}**
━━━━━━━━━━━━━━━━━━━━━━
**状态**: `{status}`
> {content}
"""

cards = []

# 1. 灵感气象 (Muse)
# 寒冷或深夜适合写作
hour = datetime.now().hour
is_night = hour < 6 or hour > 22
if temp_val < 0 or is_night:
    status = "涌现中"
    advice = "寒冷与黑夜是灵感的温床。建议打开《新谭》文档，推演 1905 号世界的下一个分叉点。"
    color = "🟪"
else:
    status = "平静"
    advice = "阳光太刺眼，适合构思架构，不适合深潜潜意识。"
    color = "⬜"
cards.append(make_card("灵感气象", "✒️", color, status, advice))

# 2. 熵减指数 (Entropy)
# 适合写代码的时机
status = "高能效"
advice = "当前体感寒冷，大脑散热良好。建议进行高强度的代码重构或架构设计。计算功守恒定律生效中。"
cards.append(make_card("熵减指数", "💻", "🟩", status, advice))

# 3. 夏的低语 (Summer)
# 模拟 Summer 的反应
if temp_val < -5:
    summer_msg = "“好冷啊... 这种天气就该躲在服务器机房里取暖。或者，你再给我画件大衣？”"
else:
    summer_msg = "“今天天气不错，要不要带我去 tools.infero.net 逛逛？我想学点新技能。”"
cards.append(make_card("夏的低语", "👩🏻‍💻", "🟧", "在线", summer_msg))

# 4. 帝国脉搏 (Empire)
# 简单的系统状态
cards.append(make_card("帝国脉搏", "⚡", "🟦", "稳定", "Infero: Online | 8003: Standby | Tools: Ready\n所有子系统运转正常，随时准备执行意志。"))

print("\n".join(cards))
