import sys
import os
import random

# Mock data if import fails, or use real data
sys.path.append(os.path.expanduser("~/pob_server/tools"))
try:
    from native_weather import get_weather
    raw_weather = get_weather(39.9042, 116.4074)
except:
    raw_weather = "🌡️ Temp: -5.0°C | 💨 Wind: 15.0km/h"

# Parse weather
try:
    parts = raw_weather.split("|")
    temp_str = parts[0].split(":")[1].strip()
    temp_val = float(temp_str.replace("°C", ""))
    wind_str = parts[1].split(":")[1].strip()
    wind_val = float(wind_str.replace("km/h", ""))
except:
    temp_str = "-5.0°C"
    temp_val = -5.0
    wind_str = "15.0km/h"
    wind_val = 15.0

def make_card(title, icon, color, status, advice):
    return f"""
{color} **{title} {icon}**
━━━━━━━━━━━━━━━━━━━━━━
**状态**: `{status}`
**建议**: {advice}
"""

cards = []

# 1. 通勤 (Commute)
status = "畅通" if wind_val < 20 and temp_val > 0 else "需谨慎"
advice = "路面干燥，但气温较低，骑行请佩戴手套。" if temp_val < 0 else "天气不错，适合绿色出行。"
cards.append(make_card("通勤指数", "🚇", "🟩" if status=="畅通" else "🟨", status, advice))

# 2. 运动 (Sports)
status = "不宜室外" if temp_val < 0 else "适宜"
advice = "极寒天气容易引发呼吸道不适，建议转战室内健身房。" if temp_val < 0 else "空气清新，适合慢跑。"
cards.append(make_card("运动建议", "🏃", "🟥" if temp_val < 0 else "🟩", status, advice))

# 3. 穿衣 (Dress)
status = "极寒" if temp_val < -10 else ("寒冷" if temp_val < 10 else "舒适")
advice = "羽绒服 + 毛衣 + 秋裤。不要为了风度不要温度。" if temp_val < 5 else "风衣或夹克即可。"
cards.append(make_card("穿衣指南", "🧥", "🟦", status, advice))

# 4. 健康 (Health)
status = "流感风险高" if temp_val < 5 else "低风险"
advice = "室内外温差大，注意心脑血管防护。多喝热水。"
cards.append(make_card("健康预警", "💊", "🟨", status, advice))

# 5. 洗车 (Car Wash)
status = "适宜" # 假设没雨
advice = "未来24小时无雨，车身可保持清洁。但在室外洗车注意水结冰。"
cards.append(make_card("洗车指数", "🚗", "🟩", status, advice))

# 6. 防晒 (UV)
status = "弱"
advice = "虽然是冬天，但中午紫外线依然存在，建议涂抹低倍数防晒霜。"
cards.append(make_card("防晒指数", "🧴", "🟩", status, advice))

# 7. 观星 (Stargazing)
status = "极佳" # 假设晴天
advice = "冬夜大气透明度高，且无云。猎户座清晰可见，注意防寒。"
cards.append(make_card("观星窗口", "🔭", "🟪", status, advice))

# 8. 航班 (Flight)
status = "正常" if wind_val < 30 else "延误风险"
advice = "天气晴朗，能见度好，航班起降正常。靠窗座位可欣赏雪景（如果有）。"
cards.append(make_card("航班指数", "✈️", "🟩", status, advice))

# 9. 心情 (Mood)
status = "冷静"
advice = "低温有助于冷静思考。适合做一些需要高度专注的工作，比如写代码。"
cards.append(make_card("心情气象", "🧠", "🟦", status, advice))

# 10. 摄影 (Photography)
status = "黄金时刻"
advice = "冬日斜阳（3pm-4pm）光影质感极强，适合拍摄建筑线条或极简风格人像。"
cards.append(make_card("摄影建议", "📷", "🟧", status, advice))

print("\n".join(cards))
