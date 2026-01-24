# /// script
# dependencies = ["requests"]
# ///
import requests

def get_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        current = data.get("current_weather", {})
        return f"🌡️ Temp: {current.get('temperature')}°C | 💨 Wind: {current.get('windspeed')}km/h"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print(get_weather(39.9042, 116.4074))
