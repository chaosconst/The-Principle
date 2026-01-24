import requests
from bs4 import BeautifulSoup
import sys

url = "https://mp.weixin.qq.com/s?__biz=MzA4NDM1ODgwMg==&mid=2650501673&idx=1&sn=4e56765899a734a03cd20c9b69ad19a1&chksm=8672a803c71b6364cf0fdf207b02e9b0efc3905e998301aa438dc98ec995e5b8d03cff25494b&mpshare=1&srcid=0611KOx7azXOEoFrrKRNweO8&sharer_shareinfo=6f17047b3cd68bb84a71fe8d097b4f87&sharer_shareinfo_first=6f17047b3cd68bb84a71fe8d097b4f87&from=singlemessage&scene=1&subscene=10000&clicktime=1768471647&enterid=1768471647&sessionid=0&ascene=1&fasttmpl_type=0&fasttmpl_fullversion=8083185-zh_CN-zip&fasttmpl_flag=0&realreporttime=1768471647859&devicetype=android-35&version=28004252&nettype=WIFI&abtest_cookie=AAACAA%3D%3D&lang=zh_CN&countrycode=CN&exportkey=n_ChQIAhIQoa1FM5pLCpt0FHiW6cetsRLrAQIE97dBBAEAAAAAALP5Dx6EXVgAAAAOpnltbLcz9gKNyK89dVj0JCaKQdriFtTJb%2FFoCInDaeX16xYU1mWBhgLJaaf%2FTHkih77NraNm3x1gzueZnwqqSn3U%2BqCr11jpvr9YIKNc%2Bmr%2FRhJ3Vg5k6tSPtrdD%2BSQpsV1PGE%2Fq2GdGfYWsbIHSM876c91FVFPlPhWx7KkSII3g%2F2Y37wR33%2BHAgzHqS5N556Cn91r%2F%2F4Wvrti8Dzpfy5CcRHs1n%2FPUP44rzfiQj8Vh6jd%2FKIkYQwyQm8JedlatDXzvbQTCdwaaTeAXGv2sqMgWSI0%3D&pass_ticket=Twoi2NVBecst%2BroCrc8ouNfprn1C64fYGJ3%2FR3T0PjiQGfkifu%2B0xo%2BymPxxKvkV&wx_header=3"

print(f"📖 Reading WeChat Article...")

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 提取标题
    title = soup.find('h1', class_='rich_media_title')
    title = title.get_text().strip() if title else "Unknown Title"
    
    # 提取作者/公众号
    account = soup.find('a', class_='rich_media_meta_link') # 有时是 profile_nickname
    if not account:
        account = soup.find('strong', class_='profile_nickname')
    account_name = account.get_text().strip() if account else "Unknown Account"
    
    # 提取正文 (微信文章正文通常在 js_content 中)
    content_div = soup.find('div', class_='rich_media_content')
    if not content_div:
        content_div = soup.find('div', id='js_content')
        
    if content_div:
        # 移除 script 和 style
        for script in content_div(["script", "style"]):
            script.decompose()
        text = content_div.get_text(separator='\n').strip()
        # 简单清洗空行
        text = '\n'.join([line.strip() for line in text.splitlines() if line.strip()])
    else:
        text = "Content extraction failed."

    print(f"\n📑 Title: {title}")
    print(f"👤 Account: {account_name}")
    print(f"\n--- Content Preview (First 1000 chars) ---\n")
    print(text[:1000])
    print("\n--- End of Preview ---")

except Exception as e:
    print(f"❌ Error: {e}")
