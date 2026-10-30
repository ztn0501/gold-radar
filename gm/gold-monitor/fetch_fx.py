#!/usr/bin/env python3
"""抓 USD/CNY 即期日线（1994 至今），供「人民币视角」使用

数据源：新浪外汇 NewForexService.getDayKLine?symbol=fx_susdcny
字段：date,open,close,high,low
用途：换算人民币金价（元/克）、拆分「美元金价涨跌」与「汇率贡献」
"""
import json, re, urllib.request, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def fetch(url, tries=3):
    import time
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"})
            return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
        except Exception as e:
            last = e; time.sleep(2)
    raise last

def main():
    try:
        t = fetch("https://vip.stock.finance.sina.com.cn/forex/api/jsonp.php/"
                  "var%20_fx=/NewForexService.getDayKLine?symbol=fx_susdcny")
        body = re.search(r"=\((.*)\)", t, re.S).group(1)
        rows = []
        for seg in body.split("|"):
            p = seg.strip().strip('"').split(",")
            if len(p) < 5:
                continue
            try:
                rows.append({"d": p[0], "o": float(p[1]), "c": float(p[2]),
                             "h": float(p[3]), "l": float(p[4])})
            except Exception:
                pass
        rows.sort(key=lambda x: x["d"])
        # 简单校验：汇率不可能落在 3~15 之外
        rows = [r for r in rows if 3 < r["c"] < 15]
        if len(rows) < 1000:
            raise ValueError("样本过少 %d" % len(rows))
        # 只存日期 + 收盘，压缩体积（页面只需要这两个字段）
        json.dump({"d": [r["d"] for r in rows], "c": [round(r["c"], 4) for r in rows]},
                  open("fx_hist.json", "w", encoding="utf-8"), separators=(",", ":"))
        print("[fx] %d bars, %s → %s, last %.4f" % (len(rows), rows[0]["d"], rows[-1]["d"], rows[-1]["c"]))
    except Exception as e:
        print("[warn] 汇率抓取失败，沿用旧文件：", e)

if __name__ == "__main__":
    main()
