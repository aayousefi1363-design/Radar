import requests
import json
import time
from datetime import datetime
import os

# ─── تنظیمات ───────────────────────────────────────────
SUPABASE_URL = "https://stnhjfodwurnbkzxgnen.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_BPytcImkHwDspdh-vNGrtw_LjdFM1RL")

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

HEADERS_TSE = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# ─── وزن‌های هر تیپ معامله‌گر ──────────────────────────
WEIGHTS = {
    "scalper": {"technical": 0.32, "smart_money": 0.23, "board_reading": 0.20, "trend": 0.12, "fundamental": 0.08, "industry": 0.05},
    "short":   {"technical": 0.28, "smart_money": 0.22, "board_reading": 0.18, "trend": 0.15, "fundamental": 0.12, "industry": 0.05},
    "mid":     {"technical": 0.20, "smart_money": 0.18, "board_reading": 0.12, "trend": 0.15, "fundamental": 0.25, "industry": 0.10},
    "long":    {"technical": 0.10, "smart_money": 0.10, "board_reading": 0.05, "trend": 0.12, "fundamental": 0.38, "industry": 0.25},
    "safe":    {"technical": 0.15, "smart_money": 0.12, "board_reading": 0.10, "trend": 0.18, "fundamental": 0.30, "industry": 0.15},
}

MAX_SCORES = {"technical": 30, "smart_money": 20, "board_reading": 20, "trend": 15, "fundamental": 15, "industry": 10}

# ─── دریافت لیست نمادها از TSETMC ──────────────────────
def get_all_stocks():
    print("دریافت لیست نمادها از TSETMC...")
    try:
        url = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch?market=0&industrialGroup=&paperType=1&symbolState=0&showBonds=false"
        res = requests.get(url, headers=HEADERS_TSE, timeout=30)
        data = res.json()
        stocks = data.get("marketwatch", [])
        print(f"{len(stocks)} نماد دریافت شد")
        return stocks
    except Exception as e:
        print(f"خطا در دریافت لیست: {e}")
        return []

# ─── دریافت داده تکنیکال هر نماد ───────────────────────
def get_stock_detail(ins_code):
    try:
        url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
        res = requests.get(url, headers=HEADERS_TSE, timeout=10)
        return res.json().get("closingPriceInfo", {})
    except:
        return {}

# ─── محاسبه امتیاز تکنیکال ──────────────────────────────
def calc_technical(stock):
    try:
        price = float(stock.get("pClosing", 0) or 0)
        last = float(stock.get("priceMax", 0) or 0)
        low = float(stock.get("priceMin", 0) or 0)
        prev = float(stock.get("prDr", 0) or 0)
        change = float(stock.get("priceChange", 0) or 0)

        score = 0
        if prev > 0 and price > 0:
            pct = (price - prev) / prev * 100
            if pct > 3: score += 10
            elif pct > 1: score += 7
            elif pct > 0: score += 4
            elif pct > -1: score += 2

        if last > 0 and low > 0:
            range_pct = (price - low) / (last - low) * 100 if last != low else 50
            if range_pct > 70: score += 10
            elif range_pct > 40: score += 6
            else: score += 2

        if change > 0: score += 10
        elif change > -2: score += 5

        return min(30, score)
    except:
        return 15

# ─── محاسبه امتیاز پول هوشمند ───────────────────────────
def calc_smart_money(stock):
    try:
        vol = float(stock.get("qTotTran5J", 0) or 0)
        val = float(stock.get("qTotCap", 0) or 0)

        score = 0
        if val > 50_000_000_000: score += 10
        elif val > 10_000_000_000: score += 7
        elif val > 1_000_000_000: score += 4
        else: score += 1

        if vol > 10_000_000: score += 10
        elif vol > 1_000_000: score += 6
        else: score += 2

        return min(20, score)
    except:
        return 10

# ─── محاسبه امتیاز تابلوخوانی ───────────────────────────
def calc_board_reading(stock):
    try:
        buyers = float(stock.get("zTotTranBuy", 0) or 0)
        sellers = float(stock.get("zTotTranSell", 0) or 0)

        score = 10
        if buyers > 0 and sellers > 0:
            ratio = buyers / sellers
            if ratio > 2: score = 20
            elif ratio > 1.5: score = 16
            elif ratio > 1: score = 12
            elif ratio > 0.7: score = 8
            else: score = 4

        return min(20, score)
    except:
        return 10

# ─── محاسبه امتیاز روند ─────────────────────────────────
def calc_trend(stock):
    try:
        change = float(stock.get("priceChange", 0) or 0)
        score = 8
        if change > 3: score = 15
        elif change > 1: score = 12
        elif change > 0: score = 9
        elif change > -1: score = 6
        else: score = 3
        return min(15, score)
    except:
        return 8

# ─── محاسبه امتیاز بنیادی (ساده‌شده) ───────────────────
def calc_fundamental(stock):
    try:
        eps = float(stock.get("eps", 0) or 0)
        pe = float(stock.get("pe", 0) or 0)
        score = 8
        if eps > 0:
            if pe > 0 and pe < 10: score = 15
            elif pe > 0 and pe < 20: score = 12
            elif pe > 0 and pe < 30: score = 9
            else: score = 6
        return min(15, score)
    except:
        return 8

# ─── محاسبه امتیاز نهایی برای هر تیپ ───────────────────
def calc_scores(technical, smart_money, board_reading, trend, fundamental, industry_score):
    scores = {}
    raw = {
        "technical": technical / MAX_SCORES["technical"],
        "smart_money": smart_money / MAX_SCORES["smart_money"],
        "board_reading": board_reading / MAX_SCORES["board_reading"],
        "trend": trend / MAX_SCORES["trend"],
        "fundamental": fundamental / MAX_SCORES["fundamental"],
        "industry": industry_score / MAX_SCORES["industry"],
    }
    for trader, weights in WEIGHTS.items():
        score = sum(raw[k] * weights[k] * 100 for k in weights)
        scores[f"score_{trader}"] = round(score, 2)
    return scores

# ─── ساخت دلیل انتخاب ───────────────────────────────────
def build_reason(stock_data, symbol):
    reasons = []
    if stock_data["technical"] >= 22: reasons.append("تکنیکال قوی")
    if stock_data["smart_money"] >= 16: reasons.append("ورود پول هوشمند")
    if stock_data["board_reading"] >= 16: reasons.append("تابلو مثبت")
    if stock_data["trend"] >= 12: reasons.append("روند صعودی")
    if stock_data["fundamental"] >= 12: reasons.append("بنیادی مناسب")
    if not reasons: reasons = ["در محدوده نظارت رادار"]
    return f"نماد {symbol}: {' | '.join(reasons)}"

# ─── ذخیره در Supabase ──────────────────────────────────
def save_to_supabase(records):
    print(f"ذخیره {len(records)} نماد در Supabase...")
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            res = requests.post(
                f"{SUPABASE_URL}/rest/v1/stocks",
                headers=HEADERS_SB,
                json=batch,
                timeout=30
            )
            if res.status_code in [200, 201]:
                print(f"  ✅ دسته {i//batch_size + 1} ذخیره شد ({len(batch)} نماد)")
            else:
                print(f"  ❌ خطا در دسته {i//batch_size + 1}: {res.text[:200]}")
        except Exception as e:
            print(f"  ❌ خطا: {e}")
        time.sleep(0.5)

# ─── اجرای اصلی ─────────────────────────────────────────
def main():
    print(f"\n🚀 رادار — شروع دریافت داده: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    stocks = get_all_stocks()
    if not stocks:
        print("❌ داده‌ای دریافت نشد")
        return

    sector_scores = {}
    records = []

    for i, stock in enumerate(stocks):
        try:
            symbol = stock.get("lVal18AFC", "").strip()
            name = stock.get("lVal30", "").strip()
            sector = stock.get("lSecVal", "").strip() or "سایر"

            if not symbol: continue

            technical = calc_technical(stock)
            smart_money = calc_smart_money(stock)
            board_reading = calc_board_reading(stock)
            trend = calc_trend(stock)
            fundamental = calc_fundamental(stock)
            industry_score = 7

            scores = calc_scores(technical, smart_money, board_reading, trend, fundamental, industry_score)

            price = float(stock.get("pClosing", 0) or 0)
            prev = float(stock.get("prDr", 0) or 0)
            change_percent = round((price - prev) / prev * 100, 2) if prev > 0 else 0
            volume = int(float(stock.get("qTotTran5J", 0) or 0))

            stock_data = {
                "technical": technical,
                "smart_money": smart_money,
                "board_reading": board_reading,
                "trend": trend,
                "fundamental": fundamental,
                "industry_score": industry_score
            }

            record = {
                "symbol": symbol,
                "name": name,
                "sector": sector,
                "technical": technical,
                "smart_money": smart_money,
                "board_reading": board_reading,
                "trend": trend,
                "fundamental": fundamental,
                "industry_score": industry_score,
                "price": int(price),
                "change_percent": change_percent,
                "volume": volume,
                "radar_reason": build_reason(stock_data, symbol),
                "updated_at": datetime.utcnow().isoformat(),
                **scores
            }
            records.append(record)

            if (i+1) % 100 == 0:
                print(f"  پردازش {i+1}/{len(stocks)} نماد...")

        except Exception as e:
            continue

    # رتبه‌بندی بر اساس score_scalper
    records.sort(key=lambda x: x.get("score_scalper", 0), reverse=True)
    for i, r in enumerate(records):
        r["radar_rank"] = i + 1

    save_to_supabase(records)
    print(f"\n✅ تمام — {len(records)} نماد آپدیت شد\n")

if __name__ == "__main__":
    main()
