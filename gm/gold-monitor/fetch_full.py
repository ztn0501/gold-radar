#!/usr/bin/env python3
"""抓取全量数据：伦敦金日线 + 沪金量能 + 实时快照（失败时沿用本地旧数据）"""
import json, re, urllib.request, datetime, os, time

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

def fetch(url, headers=None, tries=3):
    h = headers or {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
        except Exception as e:
            last = e; time.sleep(2)
    raise last

def jsonp(text):
    return json.loads(re.search(r"=\((.*)\)", text, re.S).group(1))

try:
    kl = []
    for r in jsonp(fetch("https://stock.finance.sina.com.cn/futures/api/jsonp.php/var%20_XAU=/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=XAU")):
        kl.append({"d": r["date"], "o": float(r["open"]), "h": float(r["high"]),
                   "l": float(r["low"]), "c": float(r["close"])})
    au = []
    for r in jsonp(fetch("https://stock.finance.sina.com.cn/futures/api/jsonp.php/var%20_AU0=/InnerFuturesNewService.getDailyKLine?symbol=AU0")):
        au.append({"d": r["d"], "v": int(float(r["v"])), "p": int(float(r.get("p") or 0)), "c": float(r["c"])})
    json.dump({"kline": kl, "au": au}, open("data_full.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"[fetch] XAU {len(kl)} bars, AU {len(au)} bars, last {kl[-1]['d']}")
except Exception as e:
    print("[warn] 行情抓取失败，沿用本地数据：", e)
    old = json.load(open("data_full.json", encoding="utf-8"))
    kl, au = old["kline"], old["au"]

try:
    f = re.search(r'"(.*)"', fetch("https://hq.sinajs.cn/list=hf_XAU")).group(1).split(",")
    live = {"price": float(f[0]), "prevClose": float(f[1]), "open": float(f[2]),
            "high": float(f[4]), "low": float(f[5]), "time": f[6], "date": f[12]}
except Exception:
    try:
        live = json.load(open("data.json", encoding="utf-8"))["live"]
    except Exception:
        live = {"price": kl[-1]["c"], "prevClose": kl[-2]["c"], "open": kl[-1]["o"],
                "high": kl[-1]["h"], "low": kl[-1]["l"], "time": "", "date": kl[-1]["d"]}

try:
    a = re.search(r'"(.*)"', fetch("https://hq.sinajs.cn/list=nf_AU0")).group(1).split(",")
    au_live = {"price": float(a[8]), "volume": int(float(a[13])), "oi": int(float(a[14]))}
except Exception:
    au_live = None

try:
    fx_s = re.search(r'"(.*)"', fetch("https://hq.sinajs.cn/list=fx_susdcny")).group(1).split(",")
    fx = float(fx_s[1]); fx_time = fx_s[0]
except Exception:
    fx, fx_time = 6.69, ""

json.dump({"kline": kl[-400:], "au": au[-400:], "live": live, "auLive": au_live,
           "fx": fx, "fxTime": fx_time,
           "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
          open("data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("[fetch] done", kl[-1]["d"])
