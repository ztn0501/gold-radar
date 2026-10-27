#!/usr/bin/env python3
"""抓取沪金主力 AU0 60 分钟线（跨市场代理），供 1H / 4H 雷达使用"""
import json, re, urllib.request, os, time

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")

url = ("https://stock.finance.sina.com.cn/futures/api/jsonp.php/var%20_A=/"
       "InnerFuturesNewService.getFewMinLine?symbol=AU0&type=60&datalen=600")
try:
    s = fetch(url)
    rows = json.loads(re.search(r"=\((.*)\)", s, re.S).group(1))
    bars = []
    for r in rows:
        try:
            bars.append({"d": r["d"], "o": float(r["o"]), "h": float(r["h"]),
                         "l": float(r["l"]), "c": float(r["c"]), "v": int(float(r.get("v") or 0))})
        except Exception:
            pass
    if len(bars) < 50: raise ValueError("bars too few")
except Exception as e:
    print("[warn] 小时线抓取失败，沿用本地数据：", e)
    bars = json.load(open("intraday.json", encoding="utf-8"))["bars"]

json.dump({"bars": bars, "source": "沪金主力 AU0 60分钟（新浪）"},
          open("intraday.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"[intra] {len(bars)} bars, {bars[0]['d']} → {bars[-1]['d']}")
