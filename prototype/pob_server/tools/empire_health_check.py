import requests
import sys

domains = [
    "https://infero.net",
    "https://summer.infero.net",
    "https://sandbox.infero.net",
    "https://demo.infero.net",
    "https://tools.infero.net"
]

print("--- EMPIRE HEALTH CHECK ---")
for url in domains:
    try:
        # 设置超时，忽略证书错误(以防万一)
        resp = requests.get(url, timeout=5, verify=False)
        status = resp.status_code
        # 401 (Auth) 和 200 (OK) 都是正常状态
        if status in [200, 401]:
            state = "🟢 ONLINE"
        else:
            state = f"🔴 ERROR ({status})"
    except Exception as e:
        state = f"🔴 DOWN ({str(e)[:20]}...)"
    
    print(f"{url:<30} : {state}")
