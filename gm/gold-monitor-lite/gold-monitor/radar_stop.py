#!/usr/bin/env python3
"""动态回撤追踪（Chandelier + 棘轮 + 三重修正）
1) 起点 = 最近一次「创 60 日新高」的交易日；反弹次高不重置
2) 止盈线 = 段内 max(近20日最高 − 3×ATR14)，只上移不下移
3) 仅收盘确认；跌破止盈线且同时跌破 MA10 → 触发；仍在 MA10 上方 → 视为震荡带暂停
4) MA60 已破 → 本模块失效，只显示、不再报警（交给清仓线）
"""
import json, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open("data_full.json", encoding="utf-8"))
bars = D["kline"]
au = {a["d"] for a in D["au"]}
N = len(bars)
c = [x["c"] for x in bars]
i = max(k for k in range(N) if bars[k]["d"] in au)   # 最近一个已完成收盘日


def tr(k):
    if k == 0:
        return bars[k]["h"] - bars[k]["l"]
    pc = bars[k - 1]["c"]
    return max(bars[k]["h"] - bars[k]["l"], abs(bars[k]["h"] - pc), abs(bars[k]["l"] - pc))


def raw_at(k):
    hh = max(x["h"] for x in bars[k - 19:k + 1])
    atr = sum(tr(j) for j in range(k - 13, k + 1)) / 14
    return hh - 3 * atr


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
    """当日最高价是否创近 60 日新高"""
    if k < 59:
        return False
    return bars[k]["h"] >= max(x["h"] for x in bars[k - 59:k + 1])


def seg_start(k):
    j = k
    while j >= 59:
        if is_new_high(j):
            return j
        j -= 1
    return 59


s = seg_start(i)
trail = max(raw_at(k) for k in range(s, i + 1))
atr14 = sum(tr(k) for k in range(i - 13, i + 1)) / 14
hh20 = max(x["h"] for x in bars[i - 19:i + 1])
raw = raw_at(i)
drop = c[i - 1] - c[i]
dev20 = (c[i] / ma20[i] - 1) * 100
dev10 = (c[i] / ma10[i] - 1) * 100
below = c[i] < trail
below_ma10 = c[i] < ma10[i]
paused = bool(below and not below_ma10)          # 跌破止盈线但仍在 MA10 上方 = 震荡带
ma60_broken = bool(ma60[i] and c[i] < ma60[i])
trigger = bool(below and below_ma10 and not ma60_broken)

if ma60_broken:
    action = "已失效（MA60 破位）→ 看清仓线"
elif trigger:
    action = "减仓一半（高位动态回撤）"
elif below:
    action = "跌破但暂停（仍在 MA10 上方 %.2f%%）" % dev10
else:
    action = "持有，止盈线可继续上移"

out = {
    "date": bars[i]["d"], "close": round(c[i], 2),
    "atr14": round(atr14, 2), "hh20": round(hh20, 2),
    "chandelier_raw": round(raw, 2), "trail": round(trail, 2),
    "gap_trail": round((c[i] / trail - 1) * 100, 2), "below_trail": bool(below),
    "ma10": round(ma10[i], 2), "dev10": round(dev10, 2), "below_ma10": bool(below_ma10),
    "ma20": round(ma20[i], 2), "dev20": round(dev20, 2), "paused": bool(paused),
    "day_drop": round(drop, 2),
    "ma60": round(ma60[i], 2), "ma60_broken": ma60_broken,
    "trigger": trigger, "fail": ma60_broken,
    "seg_start": bars[s]["d"], "seg_days": i - s, "seg_price": round(bars[s]["h"], 2),
    "action": action,
}
json.dump(out, open("radar_stop.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
