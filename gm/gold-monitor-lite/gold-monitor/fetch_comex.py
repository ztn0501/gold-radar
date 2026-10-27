#!/usr/bin/env python3
"""COMEX 基差：GC（纽约黄金期货）− XAU（伦敦金现货）
用途：只展示，不参与判定。升水扩大＝期货偏紧/投机偏多，贴水＝现货偏紧。
数据源：新浪（GC 日线 2016 起；实时 hf_GC / hf_XAU）。失败静默。
"""
import json, os, re, urllib.request, time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}


def get(url, tries=3):
    last = None
    for _ in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "ignore")
        except Exception as e:
            last = e
            time.sleep(2)
    raise last


def jsonp(t):
    m = re.search(r"=\((.*)\)", t, re.S)
    if not m:
        m = re.search(r"=\s*(\[.*\])", t, re.S)
    return json.loads(m.group(1))


def main():
    try:
        gc_raw = jsonp(get("https://stock.finance.sina.com.cn/futures/api/jsonp.php/var%20_GC=/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=GC"))
        gc = {r["date"]: float(r["close"]) for r in gc_raw if r.get("close")}
    except Exception as e:
        print("[comex] GC 日线失败：", e)
        gc = {}

    try:
        xau = {b["d"]: b["c"] for b in json.load(open("data_full.json", encoding="utf-8"))["kline"]}
    except Exception:
        xau = {}

    hist = []
    for d in sorted(set(gc) & set(xau)):
        hist.append([d, round(gc[d], 2), round(xau[d], 2), round(gc[d] - xau[d], 2)])
    hist = hist[-260:]

    # 实时
    live = {}
    try:
        txt = get("https://hq.sinajs.cn/list=hf_GC,hf_XAU")
        for line in txt.strip().split("\n"):
            m = re.search(r'hq_str_(hf_\w+)="([^"]*)"', line)
            if not m:
                continue
            f = m.group(2).split(",")
            live[m.group(1)] = float(f[0]) if f and f[0] else None
    except Exception:
        pass

    out = {"updated": time.strftime("%Y-%m-%d %H:%M")}
    if hist:
        cur = hist[-1][3]
        out.update({
            "date": hist[-1][0], "gc": hist[-1][1], "xau": hist[-1][2], "basis": cur,
            "pct": round(cur / hist[-1][2] * 100, 3) if hist[-1][2] else None,
            "avg20": round(sum(x[3] for x in hist[-20:]) / min(20, len(hist)), 2),
            "avg60": round(sum(x[3] for x in hist[-60:]) / min(60, len(hist)), 2),
            "hi250": max(x[3] for x in hist), "lo250": min(x[3] for x in hist),
            "hist": hist[-120:],
        })
    if live.get("hf_GC") and live.get("hf_XAU"):
        out["live_gc"] = round(live["hf_GC"], 2)
        out["live_xau"] = round(live["hf_XAU"], 2)
        out["live_basis"] = round(live["hf_GC"] - live["hf_XAU"], 2)

    json.dump(out, open("comex_basis.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[comex] {out.get('date')} GC {out.get('gc')} · XAU {out.get('xau')} · 基差 {out.get('basis')} ({out.get('pct')}%)")


if __name__ == "__main__":
    main()
