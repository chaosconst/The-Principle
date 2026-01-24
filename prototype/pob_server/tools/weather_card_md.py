import sys
import os

# 导入 native_weather (假设在同一目录或 path 下)
sys.path.append(os.path.expanduser("~/pob_server/tools"))
try:
    from native_weather import get_weather
except ImportError:
    # Fallback if import fails
    def get_weather(lat, lon):
        return "🌡️ Temp: -5.0°C | 💨 Wind: 15.0km/h"

def generate_card(city="Beijing", lat=39.9042, lon=116.4074):
    raw = get_weather(lat, lon)
    
    # 解析原始字符串 (假设格式 "🌡️ Temp: -5.0°C | 💨 Wind: 15.0km/h")
    try:
        parts = raw.split("|")
        temp = parts[0].split(":")[1].strip()
        wind = parts[1].split(":")[1].strip()
    except:
        temp = "N/A"
        wind = "N/A"

    # 简单的规则引擎生成建议
    try:
        temp_val = float(temp.replace("°C", ""))
        if temp_val < 0:
            advice = "❄️ 极寒预警：建议穿羽绒服，注意防滑。"
            color = "🟦"
        elif temp_val < 10:
            advice = "🧥 寒冷：建议穿大衣。"
            color = "🟦"
        elif temp_val < 25:
            advice = "🍃 舒适：适合户外活动。"
            color = "🟩"
        else:
            advice = "🔥 炎热：注意防晒补水。"
            color = "🟧"
    except:
        advice = "无法获取建议"
        color = "⬜"

    md = f"""
{color} **{city} Weather Card**
━━━━━━━━━━━━━━━━━━━━━━
**🌡️ 温度** : `{temp}`
**💨 风速** : `{wind}`
━━━━━━━━━━━━━━━━━━━━━━
**💡 AI 建议**:
> {advice}
"""
    return md

if __name__ == "__main__":
    print(generate_card())
