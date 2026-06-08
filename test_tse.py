import requests

url = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch?market=0&industrialGroup=&paperType=1&symbolState=0&showBonds=false"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://cdn.tsetmc.com/",
    "Accept": "application/json"
}

try:
    res = requests.get(url, headers=headers, timeout=30)
    print(f"Status: {res.status_code}")
    print(f"نتیجه: {str(res.text)[:200]}")
except Exception as e:
    print(f"خطا: {e}")
