#!/usr/bin/env python3
"""五高点 · 三模块联合复盘
模块：逃顶雷达(≥3紫灯) / 动态止盈线(ATR+MA10) / MA60防守
判定首个报警模块，并统计后续跌幅与"避开幅度"
"""
import json, os, bisect

os.chdir(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open("data_full.json", encoding="utf-8"))
bars = D["kline"]
au = {a["d"]: a for a in D["au"]}
N = len(bars)
c = [x["c"] for x in bars]
idx = {x["d"]: i for i, x in enumerate(bars)}


def tr(k):
    if k == 0:
        return bars[k]["h"] - bars[k]["l"]
    pc = bars[k - 1]["c"]
    return max(bars[k]["h"] - bars[k]["l"], abs(bars[k]["h"] - pc), abs(bars[k]["l"] - pc))


def raw_at(k):
    hh = max(x["h"] for x in bars[k - 19:k + 1])
    return hh - 3 * sum(tr(j) for j in range(k - 13, k + 1)) / 14


def ema(a, n):
    k = 2 / (n + 1); out = []; p = a[0]
    for i, v in enumerate(a):
        p = v if i == 0 else v * k + p * (1 - k)
        out.append(p)
    return out


e12, e26 = ema(c, 12), ema(c, 26)
dif = [x - y for x, y in zip(e12, e26)]
dea = ema(dif, 9)
hist = [2 * (x - y) for x, y in zip(dif, dea)]

ma10 = [None] * N
ma20 = [None] * N
ma60 = [None] * N
for k in range(9, N):
    ma10[k] = sum(c[k - 9:k + 1]) / 10
for k in range(19, N):
    ma20[k] = sum(c[k - 19:k + 1]) / 20
for k in range(59, N):
    ma60[k] = sum(c[k - 59:k + 1]) / 60

piv = [p for p in range(5, N - 5) if abs(bars[p]["h"] - max(bars[k]["h"] for k in range(p - 5, p + 6))) < 1e-9]


def red_area(a, b):
    return abs(sum(x for x in hist[a + 1:b + 1] if x > 0))


def top_state(i):
    """逃顶雷达 4 分"""
    lo = max(0, i - 119)
    lows = [x["l"] for x in bars[lo:i + 1]]
    highs = [x["h"] for x in bars[lo:i + 1]]
    mn, mx = min(lows), max(highs)
    pos120 = (c[i] - mn) / (mx - mn) * 100 if mx > mn else 0
    dev20 = (c[i] / ma20[i] - 1) * 100 if ma20[i] else 0
    upper = ma20[i] + 2 * (sum((x - ma20[i]) ** 2 for x in c[i - 19:i + 1]) / 20) ** 0.5 if ma20[i] else 1e9
    space = bool(pos120 >= 80 or dev20 >= 15 or c[i] >= upper * 0.995)

    k = bisect.bisect_left(piv, i) - 1
    j = piv[k] if k >= 0 else None
    j2 = piv[k - 1] if k >= 1 else None
    top_div = False
    if j and j2 and i - j <= 5:
        a_now = red_area(j2, j)
        top_div = bars[i]["h"] > bars[j]["h"] and (dif[i] < dif[j] or (a_now and red_area(j, i) < a_now))
    red_shrink = bool(hist[i] > 0 and hist[i] < hist[i - 1] < hist[i - 2])
    death = any(dif[k2] < dea[k2] and dif[k2 - 1] >= dea[k2 - 1] for k2 in range(max(1, i - 3), i + 1)) and pos120 >= 70
    mom = bool(top_div or red_shrink or death)

    b = bars[i]
    rng = max(b["h"] - b["l"], 1e-9)
    us = (b["h"] - max(b["o"], b["c"])) / rng
    pv = bars[i - 1]
    bear = bool(b["c"] < b["o"] and pv["c"] > pv["o"] and b["c"] <= pv["o"] and b["o"] >= pv["c"])
    ret3 = (c[i] / c[i - 3] - 1) * 100 if i >= 3 else 0
    pat = bool(us > 0.5 or bear or ret3 >= 6)

    a = au.get(b["d"])
    vs = [au[x["d"]]["v"] for x in bars[max(0, i - 20):i] if x["d"] in au]
    vr = a["v"] / (sum(vs) / len(vs)) if (a and vs) else None
    vol = bool(vr and vr >= 2.0 and (b["c"] < b["o"] or us > 0.4))

    sc = sum([space, mom, pat, vol])
    return sc, {"space": space, "mom": mom, "pat": pat, "vol": vol,
                "pos120": round(pos120, 1), "dev20": round(dev20, 2),
                "us": round(us * 100, 1), "vr": round(vr, 2) if vr else None}


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
    ("2026-01-29", 5596.33, "绝对大顶"),
    ("2026-03-02", 5419.01, "第一波诱多反弹顶"),
    ("2026-04-17", 4889.24, "次高反弹"),
    ("2026-05-12", 4773.37, "破MA60后反弹次高"),
    ("2026-08-25", 4696.59, "W浪高点"),
]

out = []
for dt, ph, tag in peaks:
    p = idx[dt]
    s = seg_start(p)
    trail = max(raw_at(k) for k in range(s, p + 1))

    # 逃顶：顶点前 2 天 ~ 后 10 天首次 >=3
    top_hit = None
    for k in range(max(60, p - 2), min(p + 11, N)):
        sc, d = top_state(k)
        if sc >= 3:
            top_hit = {"date": bars[k]["d"], "days": k - p, "score": sc, "close": round(c[k], 2), **d}
            break

    # 动态止盈线：顶点后首次 收盘<线 且 收盘<MA10
    trail_hit = None
    first_below = None
    for k in range(p + 1, min(p + 90, N)):
        if c[k] < trail and first_below is None:
            first_below = {"date": bars[k]["d"], "days": k - p}
        if c[k] < trail and ma10[k] and c[k] < ma10[k]:
            trail_hit = {"date": bars[k]["d"], "days": k - p, "close": round(c[k], 2),
                         "dev10": round((c[k] / ma10[k] - 1) * 100, 2)}
            break

    # MA60：顶点时是否已破 / 之后首次跌破
    ma60_before = bool(ma60[p] and c[p] < ma60[p])
    ma60_hit = None
    if ma60_before:
        k = p
        while k > 60 and ma60[k] and c[k] < ma60[k]:
            k -= 1
        ma60_hit = {"date": bars[k + 1]["d"], "days": (k + 1) - p, "close": round(c[k + 1], 2), "before": True}
    else:
        for k in range(p + 1, min(p + 120, N)):
            if ma60[k] and c[k] < ma60[k]:
                ma60_hit = {"date": bars[k]["d"], "days": k - p, "close": round(c[k], 2), "before": False}
                break

    # 首个报警模块
    cands = []
    if top_hit:
        cands.append((top_hit["date"], "逃顶紫灯", top_hit["close"]))
    if trail_hit:
        cands.append((trail_hit["date"], "止盈线+MA10", trail_hit["close"]))
    if ma60_hit and not ma60_hit.get("before"):
        cands.append((ma60_hit["date"], "MA60破位", ma60_hit["close"]))
    cands.sort(key=lambda x: x[0])
    first = {"module": cands[0][1], "date": cands[0][0], "price": cands[0][2]} if cands else None
    if ma60_before:
        first = {"module": "顶点前已破MA60", "date": ma60_hit["date"], "price": ma60_hit["close"]}

    # 后续跌幅
    win = bars[p:min(p + 61, N)]
    low = min(x["l"] for x in win)
    low_day = [x for x in win if x["l"] == low][0]["d"]
    drop = (low / c[p] - 1) * 100
    avoid = (first["price"] / low - 1) * 100 if first else None

    out.append({
        "date": dt, "high": ph, "close": round(c[p], 2), "tag": tag,
        "seg_start": bars[s]["d"], "trail": round(trail, 2),
        "top": top_hit, "trail_hit": trail_hit, "first_below": first_below,
        "ma60": ma60_hit, "ma60_before": ma60_before,
        "first": first, "low": round(low, 2), "low_day": low_day,
        "drop": round(drop, 2), "avoid": round(avoid, 2) if avoid is not None else None,
    })

json.dump(out, open("triple_review.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

for r in out:
    print(f"== {r['date']} ({r['tag']}) 高{r['high']} 收{r['close']} 线{r['trail']} 起点{r['seg_start']}")
    t = r["top"]
    print(f"   逃顶: {t['date']} T+{t['days']} {t['score']}/4 收{t['close']} (空间{t['space']} 动能{t['mom']} 形态{t['pat']} 量能{t['vol']})" if t else "   逃顶: 无")
    th = r["trail_hit"]
    print(f"   止盈线: {th['date']} T+{th['days']} 收{th['close']} dev10 {th['dev10']}%" if th else "   止盈线: 无")
    m = r["ma60"]
    print(f"   MA60: {m['date']} T+{m['days']} 收{m['close']} 顶点前已破={m.get('before')}" if m else "   MA60: 未破")
    f = r["first"]
    print(f"   首个报警: {f['module']} @ {f['date']} {f['price']}")
    print(f"   60日最低 {r['low']} ({r['low_day']}) 跌幅 {r['drop']}% | 信号价高于最低 {r['avoid']}%")
