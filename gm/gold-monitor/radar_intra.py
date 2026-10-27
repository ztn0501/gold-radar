#!/usr/bin/env python3
"""1H / 4H 小周期雷达（满分 3 分）：空间 / 动能 / 形态
注意：数据源为沪金主力 AU0 60 分钟（内盘时段），作为伦敦金短线的跨市场代理。
"""
import json, os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

data = json.load(open("intraday.json", encoding="utf-8"))
h1 = data["bars"]

def ema(a, n):
    k = 2/(n+1); out=[]; p=a[0]
    for i,v in enumerate(a):
        p = v if i==0 else v*k + p*(1-k); out.append(p)
    return out

# 4H 合成：按 日期 + 4 小时时段 分组
groups = {}
for b in h1:
    dt = datetime.strptime(b["d"], "%Y-%m-%d %H:%M:%S")
    key = (dt.date(), dt.hour // 4)
    groups.setdefault(key, []).append(b)
h4 = []
for key in sorted(groups):
    g = groups[key]
    h4.append({"d": g[-1]["d"], "o": g[0]["o"], "h": max(x["h"] for x in g),
               "l": min(x["l"] for x in g), "c": g[-1]["c"], "v": sum(x["v"] for x in g)})

def analyze(bars, window):
    closes=[b["c"] for b in bars]
    if len(closes) < 30:
        return {"score":0,"space":False,"momentum":False,"pattern":False,
                "detail":"数据不足"}
    e12,e26=ema(closes,12),ema(closes,26)
    dif=[x-y for x,y in zip(e12,e26)]
    dea=ema(dif,9)
    hist=[2*(x-y) for x,y in zip(dif,dea)]

    view=bars[-window:]
    mn=min(b["l"] for b in view); mx=max(b["h"] for b in view)
    i=len(bars)-1
    pos=(closes[i]-mn)/(mx-mn)*100 if mx>mn else 0
    space = pos<=20

    # 动能：近 3 根内金叉，或价格新低但 DIF/绿柱面积不新低
    cross = any(dif[k]>dea[k] and dif[k-1]<=dea[k-1] for k in range(max(1,i-2), i+1))
    seg=view[:-1]
    j=min(range(len(seg)), key=lambda k: seg[k]["l"]) + (len(bars)-len(view))
    lower_low = bars[i]["l"] < bars[j]["l"]
    area_now = abs(sum(x for x in hist[max(0,j+1):i+1] if x<0))
    area_prev = abs(sum(x for x in hist[max(0,j-24):j+1] if x<0))
    diverge = bool(lower_low and (dif[i] > dif[j] or area_now < area_prev))
    momentum = bool(cross or diverge)

    b=bars[i]; rng=max(b["h"]-b["l"],1e-9)
    shadow=(min(b["o"],b["c"])-b["l"])/rng
    p=bars[i-1]
    engulf = bool(b["c"]>b["o"] and p["c"]<p["o"] and b["c"]>=p["o"] and b["o"]<=p["c"])
    pattern = bool(shadow>0.5 or engulf)

    return {"score":int(space)+int(momentum)+int(pattern),
            "space":bool(space),"momentum":bool(momentum),"pattern":bool(pattern),
            "detail":{"pos":round(pos,1),"shadow":round(shadow*100,1),"cross":cross,
                      "diverge":diverge,"engulf":engulf,"close":b["c"],"time":b["d"]}}

# ---------- 日线趋势闸门：只有多头才允许做T ----------
days = {}
for b in h1:
    days[b["d"][:10]] = b["c"]          # 每日最后一根收盘 = 日线收盘
dd = sorted(days); dc = [days[d] for d in dd]
nd = len(dc)
ma20d = [sum(dc[i-19:i+1])/20 if i >= 19 else None for i in range(nd)]
ma60d = [sum(dc[i-59:i+1])/60 if i >= 59 else None for i in range(nd)]
lastc, m20d, m60d = dc[-1], ma20d[-1], ma60d[-1]
if m20d is None or m60d is None:
    trend, label = "unknown", "日线数据不足，做T信号已关闭"
elif lastc > m20d and m20d > m60d:
    trend, label = "up", "牛市回调做T专用"
elif lastc < m60d:
    trend, label = "down", "趋势向下，做T信号已关闭"
else:
    trend, label = "range", "趋势不明（震荡），做T信号已关闭"
gate = {"trend": trend, "allow": trend == "up", "label": label,
        "close": round(lastc, 2),
        "ma20d": round(m20d, 2) if m20d else None,
        "ma60d": round(m60d, 2) if m60d else None,
        "gap60": round((lastc/m60d-1)*100, 2) if m60d else None,
        "bars": nd}

out={"h1":analyze(h1,24),"h4":analyze(h4,30),"gate":gate,
     "generated":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
     "source":"沪金主力 AU0 60m（内盘时段，跨市场代理）"}
json.dump(out, open("radar_intra.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
