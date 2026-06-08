import requests
import json
import time
from datetime import datetime
import os

SUPABASE_URL = "https://stnhjfodwurnbkzxgnen.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_BPytcImkHwDspdh-vNGrtw_LjdFM1RL")

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

WEIGHTS = {
    "scalper": {"technical":0.32,"smart_money":0.23,"board_reading":0.20,"trend":0.12,"fundamental":0.08,"industry":0.05},
    "short":   {"technical":0.28,"smart_money":0.22,"board_reading":0.18,"trend":0.15,"fundamental":0.12,"industry":0.05},
    "mid":     {"technical":0.20,"smart_money":0.18,"board_reading":0.12,"trend":0.15,"fundamental":0.25,"industry":0.10},
    "long":    {"technical":0.10,"smart_money":0.10,"board_reading":0.05,"trend":0.12,"fundamental":0.38,"industry":0.25},
    "safe":    {"technical":0.15,"smart_money":0.12,"board_reading":0.10,"trend":0.18,"fundamental":0.30,"industry":0.15},
}

def calc_scores(t, sm, br, tr, fu, ind):
    raw = {"technical":t/30,"smart_money":sm/20,"board_reading":br/20,"trend":tr/15,"fundamental":fu/15,"industry":ind/10}
    return {f"score_{k}": round(sum(raw[f]*w for f,w in v.items())*100, 2) for k,v in WEIGHTS.items()}

def build_reason(t, sm, br, tr, fu, symbol):
    r = []
    if t >= 22: r.append("تکنیکال قوی")
    if sm >= 16: r.append("ورود پول هوشمند")
    if br >= 16: r.append("تابلو مثبت")
    if tr >= 12: r.append("روند صعودی")
    if fu >= 12: r.append("بنیادی مناسب")
    return f"نماد {symbol}: {' | '.join(r) if r else 'در محدوده نظارت رادار'}"

def get_stocks_fipiran():
    print("دریافت داده از fipiran.ir ...")
    try:
        url = "https://www.fipiran.ir/DataService/GetSymbolList"
        res = requests.get(url, timeout=30, headers={"User-Agent":"Mozilla/5.0"})
        data = res.json()
        print(f"{len(data)} نماد دریافت شد")
        return data
    except Exception as e:
        print(f"خطا fipiran: {e}")
        return []

def get_stocks_rahavard():
    print("دریافت داده از rahavard365 ...")
    try:
        url = "https://rahavard365.com/api/v2/asset/index-list"
        res = requests.get(url, timeout=30, headers={"User-Agent":"Mozilla/5.0"})
        data = res.json()
        items = data.get("data", data) if isinstance(data, dict) else data
        print(f"{len(items)} نماد دریافت شد")
        return items
    except Exception as e:
        print(f"خطا rahavard: {e}")
        return []

def process_fipiran(stocks):
    records = []
    for s in stocks:
        try:
            symbol = str(s.get("Symbol","") or s.get("symbol","")).strip()
            if not symbol: continue
            name = str(s.get("Name","") or s.get("name","")).strip()
            sector = str(s.get("SectorName","") or s.get("sector","") or "سایر").strip()
            price = float(s.get("LastPrice",0) or s.get("last",0) or 0)
            prev = float(s.get("PreviousPrice",0) or s.get("prev",0) or 0)
            change = round((price-prev)/prev*100,2) if prev>0 else 0
            volume = int(float(s.get("Volume",0) or s.get("volume",0) or 0))
            pe = float(s.get("PE",0) or s.get("pe",0) or 0)
            eps = float(s.get("EPS",0) or s.get("eps",0) or 0)

            t = min(30, 15 + (10 if change>2 else 5 if change>0 else 0) + (5 if volume>1000000 else 2))
            sm = min(20, 10 + (7 if volume>5000000 else 3 if volume>1000000 else 0))
            br = min(20, 10 + (5 if change>1 else 0))
            tr = min(15, 8 + (5 if change>0 else -3 if change<-2 else 0))
            fu = min(15, 8 + (5 if 0<pe<15 else 3 if 0<pe<25 else 0) + (2 if eps>0 else 0))
            ind = 7

            scores = calc_scores(t, sm, br, tr, fu, ind)
            records.append({
                "symbol": symbol, "name": name, "sector": sector,
                "technical": t, "smart_money": sm, "board_reading": br,
                "trend": tr, "fundamental": fu, "industry_score": ind,
                "price": int(price), "change_percent": change, "volume": volume,
                "radar_reason": build_reason(t, sm, br, tr, fu, symbol),
                "updated_at": datetime.utcnow().isoformat(),
                **scores
            })
        except: continue
    return records

def save_to_supabase(records):
    print(f"ذخیره {len(records)} نماد در Supabase...")
    for i in range(0, len(records), 50):
        batch = records[i:i+50]
        try:
            res = requests.post(
                f"{SUPABASE_URL}/rest/v1/stocks",
                headers=HEADERS_SB, json=batch, timeout=30
            )
            status = "✅" if res.status_code in [200,201] else "❌"
            print(f"  {status} دسته {i//50+1} ({len(batch)} نماد) — {res.status_code}")
            if res.status_code not in [200,201]:
                print(f"     {res.text[:150]}")
        except Exception as e:
            print(f"  ❌ خطا: {e}")
        time.sleep(0.3)

def main():
    print(f"\n🚀 رادار — شروع: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    stocks = get_stocks_fipiran()
    if not stocks:
        stocks = get_stocks_rahavard()

    if not stocks:
        print("❌ هیچ منبعی در دسترس نیست")
        return

    records = process_fipiran(stocks)
    if not records:
        print("❌ داده‌ای پردازش نشد")
        return

    records.sort(key=lambda x: x.get("score_scalper",0), reverse=True)
    for i, r in enumerate(records):
        r["radar_rank"] = i + 1

    save_to_supabase(records)
    print(f"\n✅ تمام — {len(records)} نماد ذخیره شد\n")

if __name__ == "__main__":
    main()
