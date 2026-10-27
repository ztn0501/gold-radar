#!/usr/bin/env python3
"""动态回撤追踪 · 2026 五高点复盘（三重修正版）
起点 = 最近一次创 60 日新高日；止盈线 = 段内 max(HH20−3ATR14)
触发需收盘跌破止盈线且同时跌破 MA10；仍在 MA10 上方 = 震荡带暂停
MA60 已破 → 模块失效
"""
import json, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open("data_full.json", encoding="utf-8"))
bars = D["kline"]
N = len(bars)
c = [x["c"] for x in bars]
idx = {x["d"]: i for i, x in enumerate(bars)}


def tr(k):
    if k == 0:
        return bars[k]["h"] - bars[k]["l"]
    pc = bars[k - 1]["c"]
    return max(bars[k]["h"] - bars[k]["l"], abs(bars[k]["h"] - pc), abs(bars[k]["l"] - pc))


def raw_at(k):
    return max(x["h"] for x in bars[k - 19:k + 1]) - 3 * sum(tr(j) for j in range(k - 13, k + 1)) / 14


ma10 = [None] * N
ma20 = [None] * N
ma60 = [None] * N
for k in range(9, N):
    ma10[k] = sum(c[k - 9:k + 1]) / 10
for k in range(19, N):
    ma20[k] = sum(c[k - 19:k + 1]) / 20
for k in range(59, N):
    ma60[k] = sum(c[k - 59:k + 1]) / 60


def is_new_high(k):
    return k >= 59 and bars[k]["h"] >= max(x["h"] for x in bars[k - 59:k + 1])


def seg_start(k):
    j = k
    while j >= 59:
        if is_new_high(j):
            return j
        j -= 1
    return 59


peaks = [
    ("2025-10-20", 4381.29),
    ("2026-01-29", 5596.33),
    ("2026-02-24", 5249.29),
    ("2026-04-17", 4889.24),
    ("2026-08-25", 4696.59),
]

out = []
for dt, ph in peaks:
    p = idx[dt]
    s = seg_start(p)
    trail = max(raw_at(k) for k in range(s, p + 1))

    # 顶点后逐日判定
    hit = None
    for k in range(p + 1, min(p + 90, N)):
        if c[k] >= trail:
            continue
        atr = sum(tr(j) for j in range(k - 13, k + 1)) / 14
        drop = c[k - 1] - c[k]
        dev = (c[k] / ma20[k] - 1) * 100
        dev10 = (c[k] / ma10[k] - 1) * 100
        below10 = c[k] < ma10[k]
        hit = {"k": k, "atr": atr, "drop": drop, "below_ma10": bool(below10),
               "dev20": round(dev, 2), "dev10": round(dev10, 2), "paused": bool(not below10),
               "effective": bool(below10),
               "ma60_gap": round((c[k] / ma60[k] - 1) * 100, 2) if ma60[k] else None}
        if hit["effective"]:
            break

    m60brk = None
    for k in range(p + 1, min(p + 120, N)):
        if ma60[k] and c[k] < ma60[k]:
            m60brk = k
            break

    row = {
        "date": dt, "high": ph, "close": round(c[p], 2),
        "seg_start": bars[s]["d"], "seg_days": p - s, "seg_price": round(bars[s]["h"], 2),
        "trail": round(trail, 2),
        "gap_peak": round((c[p] / trail - 1) * 100, 2),
        "is_new_high": bool(is_new_high(p)),
        "ma60_at_peak": round((c[p] / ma60[p] - 1) * 100, 2) if ma60[p] else None,
    }
    if hit:
        k = hit["k"]
        row.update({
            "break_date": bars[k]["d"], "break_days": k - p, "break_close": round(c[k], 2),
            "break_gap": round((c[k] / trail - 1) * 100, 2),
            "dev20": hit["dev20"], "dev10": hit["dev10"], "paused": hit["paused"],
            "below_ma10": hit["below_ma10"], "atr": round(hit["atr"], 2), "drop": round(hit["drop"], 2),
            "ma60_gap": hit["ma60_gap"],
            "ma60_broken": bool(hit["ma60_gap"] is not None and hit["ma60_gap"] < 0),
        })
        # 首次跌破日（无论是否暂停）
        first = None
        for k2 in range(p + 1, min(p + 90, N)):
            if c[k2] < trail:
                d2 = (c[k2] / ma20[k2] - 1) * 100
                first = {"date": bars[k2]["d"], "days": k2 - p, "dev20": round(d2, 2)}
                break
        row["first_break"] = first
    else:
        row.update({"break_date": None, "break_days": None})

    if m60brk:
        row["ma60_break_date"] = bars[m60brk]["d"]
        row["ma60_break_days"] = m60brk - p
    else:
        row["ma60_break_date"] = None

    if row.get("break_date") and m60brk:
        row["who_first"] = "止盈线" if hit["k"] <= m60brk else "MA60"
    elif row.get("break_date"):
        row["who_first"] = "止盈线"
    elif m60brk:
        row["who_first"] = "MA60"
    else:
        row["who_first"] = "-"

    out.append(row)

json.dump(out, open("trail_review.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

for r in out:
    print(f"== {r['date']} 高{r['high']} 收{r['close']} 新高={r['is_new_high']}")
    print(f"   起点 {r['seg_start']}({r['seg_days']}天, 高{r['seg_price']}) 线 {r['trail']} 顶点距线 {r['gap_peak']}%")
    if r["break_date"]:
        print(f"   跌破 {r['break_date']} T+{r['break_days']} 收{r['break_close']} 距线{r['break_gap']}% | dev10 {r['dev10']}% 破MA10={r['below_ma10']} 暂停={r['paused']}")
        print(f"   首次跌破 {r['first_break']['date']} T+{r['first_break']['days']} | MA60 {r['ma60_gap']}% | 谁先 {r['who_first']}")
    else:
        print("   90日内未触发")
    print(f"   MA60 首破 {r['ma60_break_date']}")
