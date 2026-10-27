#!/usr/bin/env python3
"""两种实战背离口径：MACD 绿柱面积法 + 摆动低点法"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

d = json.load(open("data.json", encoding="utf-8"))
bars = d["kline"]

def ema(a, n):
    k = 2/(n+1); out=[]; prev=a[0]
    for i,v in enumerate(a):
        prev = v if i == 0 else v*k + prev*(1-k)
        out.append(prev)
    return out

closes=[b["c"] for b in bars]
e12,e26=ema(closes,12),ema(closes,26)
dif=[x-y for x,y in zip(e12,e26)]
dea=ema(dif,9)
hist=[2*(x-y) for x,y in zip(dif,dea)]

N=len(bars)
K=5  # 左右各 5 根确认

def is_pivot_low(i, k=K):
    lo=max(0,i-k); hi=min(N-1,i+k)
    if bars[i]["l"] > min(b["l"] for b in bars[lo:hi+1]):
        return False
    # 左侧也必须是低点（避免平台）
    left=min(b["l"] for b in bars[lo:i+1])
    return abs(bars[i]["l"]-left) < 1e-9

pivots=[i for i in range(K, N-K) if is_pivot_low(i)]
# 最新一根允许“右侧未确认”
if is_pivot_low(N-1, K) and (not pivots or pivots[-1]!=N-1):
    pivots.append(N-1)

def neg_area(a, b):
    """a→b 区间内（不含 a，含 b）绿柱面积绝对值之和"""
    return abs(sum(x for x in hist[a+1:b+1] if x < 0))

def analyze(i):
    """以 i 为当前低点，找它前一个摆动低点"""
    prev=[p for p in pivots if p < i]
    if not prev:
        return None
    j=prev[-1]
    # 前一个摆动低点之前的再前一个，用来算“上一波面积”
    prev2=[p for p in pivots if p < j]
    j2=prev2[-1] if prev2 else None

    area_now=neg_area(j, i)
    area_prev=neg_area(j2, j) if j2 is not None else None

    swing = {
        "prev_date": bars[j]["d"], "prev_low": bars[j]["l"], "prev_dif": dif[j],
        "lower_low": bars[i]["l"] < bars[j]["l"],
        "higher_dif": dif[i] > dif[j],
    }
    swing["is"] = bool(swing["lower_low"] and swing["higher_dif"])

    area={
        "prev2_date": bars[j2]["d"] if j2 is not None else None,
        "area_now": area_now, "area_prev": area_prev,
        "lower_low": bars[i]["l"] < bars[j]["l"],
        "smaller_area": (area_prev is not None and area_now < area_prev),
    }
    area["is"] = bool(area["lower_low"] and area["smaller_area"])

    return {"swing":swing, "area":area,
            "confirmed": i < N-K, "prev_pivot": bars[j]["d"]}

nodes=["2026-02-02","2026-03-23","2026-06-24","2026-10-23"]
idx={b["d"]:k for k,b in enumerate(bars)}
out=[]
for dt in nodes:
    i=idx[dt]
    r=analyze(i)
    out.append({"date":dt, "low":bars[i]["l"], "dif":dif[i], **(r or {})})

print(json.dumps(out, ensure_ascii=False, indent=1))
print("\n摆动低点列表（最近12个）:")
for p in pivots[-12:]:
    print(bars[p]["d"], bars[p]["l"], round(dif[p],2))

json.dump(out, open("divergence2.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
