#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_risk.py —— 风险与政策环境（2026-10-30）

补两个此前标为「没有数据源」的东西：

1) 地缘/恐慌 —— 用 CBOE 的 VIX（标普 500 隐含波动率，1990 起）和
   GVZ（黄金自身隐含波动率，2009 起）。这两个不是「地缘指数」，
   但它们是把地缘事件**实时定价**过的市场产物，且每日更新、无需 key。
   实测比 GPR 之类的学术指数更及时（GPR 站点在本环境完全不通）。

2) 央行购金 —— IMF IFS 的官方储备黄金实物量（百万盎司），月度。
   注意：DBnomics 镜像的 IFS 只更新到 2025-06，滞后一年多，
   **不能用于实时展示**，只用于统计检验（验证它到底有没有预测力）。

输出：
    risk_hist.json  {"d":[...], "vix":[...], "gvz":[...]}
    cb_hist.json    {"d":[月], "oz":[百万盎司]}
"""
import json
import os
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CBOE = "https://cdn.cboe.com/api/global/us_indices/daily_prices/%s_History.csv"
IFS = ("https://api.db.nomics.world/v22/series/IMF/IFS/"
       "M.%s.RAFAGOLDV_OZT?observations=1")


def get(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


def parse_cboe(txt, col):
    """CBOE CSV: DATE,OPEN,HIGH,LOW,CLOSE  或  DATE,GVZ"""
    out = {}
    for line in txt.strip().split("\n")[1:]:
        p = line.strip().split(",")
        if len(p) < 2:
            continue
        d = p[0]
        if "/" in d:                      # MM/DD/YYYY
            m, dd, y = d.split("/")
            d = "%s-%s-%s" % (y, m.zfill(2), dd.zfill(2))
        try:
            v = float(p[col])
        except Exception:
            continue
        if v > 0:
            out[d] = round(v, 2)
    return out


def main():
    # ── 1. VIX / GVZ ────────────────────────────────────────────
    try:
        vix = parse_cboe(get(CBOE % "VIX"), 4)      # CLOSE 在第 5 列
        gvz = parse_cboe(get(CBOE % "GVZ"), 1)      # 只有两列
        if len(vix) < 5000:
            raise ValueError("VIX 样本过少 %d" % len(vix))
        # GVZ 只从 2009-09 开始，允许短
        dates = sorted(set(vix) | set(gvz))
        dates = [d for d in dates if d >= "2009-09-18"]
        json.dump({"d": dates,
                   "vix": [vix.get(d) for d in dates],
                   "gvz": [gvz.get(d) for d in dates]},
                  open("risk_hist.json", "w", encoding="utf-8"),
                  separators=(",", ":"))
        print("[risk] VIX %d 根 / GVZ %d 根，%s → %s，最新 VIX %.2f GVZ %.2f"
              % (len(vix), len(gvz), dates[0], dates[-1], vix[dates[-1]] or 0,
                 gvz.get(dates[-1]) or 0))
    except Exception as e:
        print("[risk] VIX/GVZ 抓取失败：%s（保留旧文件）" % e)

    # ── 2. 央行黄金储备（IMF IFS）────────────────────────────────
    try:
        rows = {}
        for area in ("CN", "RU", "IN", "W0"):
            try:
                j = json.loads(get(IFS % area, 45))
                docs = (j.get("series") or {}).get("docs") or []
                if not docs:
                    print("[cb] %s 无数据" % area)
                    continue
                for p, v in zip(docs[0]["period"], docs[0]["value"]):
                    if v is None:
                        continue
                    rows.setdefault(p, {})[area] = round(float(v), 3)
                print("[cb] %s %d 个月，最新 %s" % (area, len(docs[0]["period"]),
                                                   docs[0]["period"][-1]))
            except Exception as e:
                print("[cb] %s 失败：%s" % (area, e))
        if rows:
            ds = sorted(rows)
            json.dump({"d": ds,
                       "cn": [rows[d].get("CN") for d in ds],
                       "ru": [rows[d].get("RU") for d in ds],
                       "in": [rows[d].get("IN") for d in ds],
                       "w0": [rows[d].get("W0") for d in ds]},
                      open("cb_hist.json", "w", encoding="utf-8"),
                      separators=(",", ":"))
            print("[cb] 合并 %d 个月，%s → %s" % (len(ds), ds[0], ds[-1]))
    except Exception as e:
        print("[cb] 央行储备整体失败：%s" % e)


if __name__ == "__main__":
    main()
