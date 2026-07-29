import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*"
}

test_urls = [
    "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.600519&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&beg=20250101&end=20260722",
    "https://www.eastmoney.com"
]

for url in test_urls:
    try:
        print(f"测试: {url[:60]}...")
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"  状态码: {resp.status_code}")
        if resp.status_code == 200:
            if len(resp.text) > 100:
                print(f"  响应长度: {len(resp.text)} 字符")
                print(f"  前100字符: {resp.text[:100]}")
    except Exception as e:
        print(f"  失败: {str(e)[:80]}")