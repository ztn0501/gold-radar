#!/usr/bin/env python3
import json, re, urllib.request
import os
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

P = "data.json"
d = json.load(open(P, encoding="utf-8"))
bars = d["kline"]; au = d["au"]

def ema(a, n):
    k = 2/(n+1); out=[]; prev=a[0]
    for i,v in enumerate(a):
        prev = v if i==0 else v*k + prev*(1-k)
        out.append(prev)
    return out

closes=[b["c"] for b in bars]
e12, e26 = ema(closes,12), ema(closes,26)
dif=[a-b for a,b in zip(e12,e26)]
dea=ema(dif,9)
hist=[2*(a-b) for a,b in zip(dif,dea)]

idx={b["d"]:i for i,b in enumerate(bars)}
au_by={a["d"]:a for a in au}
au_dates=sorted(au_by)

def au_at(date):
    cand=[x for x in au_dates if x<=date]
    return au_by[cand[-1]] if cand else None

def au_vol_ratio(date):
    a=au_at(date)
    if not a: return None,None,None
    i=au_dates.index(a["d"])
    win=[au_by[x]["v"] for x in au_dates[max(0,i-19):i+1]]
    avg=sum(win)/len(win)
    return a["v"], a.get("p"), a["v"]/avg

def divergence(i):
    # 前低：i-60 ~ i-5 区间内最低 low 的那天
    lo=max(0,i-60); hi=max(0,i-5)
    if hi<=lo: return None
    j=min(range(lo,hi), key=lambda k: bars[k]["l"])
    lower_low = bars[i]["l"] < bars[j]["l"]
    higher_dif = dif[i] > dif[j]
    return {"prev_date":bars[j]["d"],"prev_low":bars[j]["l"],"prev_dif":dif[j],
            "lower_low":lower_low,"higher_dif":higher_dif,
            "is": bool(lower_low and higher_dif)}

def forward(i, n=3):
    out=[]
    for k in range(1,n+1):
        if i+k < len(bars):
            b=bars[i+k]
            out.append({"d":b["d"],"c":b["c"],
                        "chg%":(b["c"]/bars[i]["c"]-1)*100,
                        "high%":(b["h"]/bars[i]["c"]-1)*100})
    return out

nodes=[("节点1 · 第一波急跌底","2026-02-02",4401.58),
       ("节点2 · 第二波急跌底","2026-03-23",4099.02),
       ("节点3 · 宏观大底","2026-06-24",3959.04),
       ("节点4 · 当前","2026-10-23",3997.79)]

res=[]
for name,date,ref in nodes:
    if date not in idx:
        res.append({"name":name,"date":date,"error":"no bar"}); continue
    i=idx[date]; b=bars[i]
    rng=b["h"]-b["l"]
    lower=min(b["o"],b["c"])-b["l"]
    upper=b["h"]-max(b["o"],b["c"])
    v,p,ratio=au_vol_ratio(date)
    dv=divergence(i)
    res.append({"name":name,"date":date,"ref":ref,
        "o":b["o"],"h":b["h"],"l":b["l"],"c":b["c"],
        "lower_shadow":lower,"lower_shadow_pct":lower/b["c"]*100,
        "lower_share": (lower/rng*100 if rng else 0),
        "dif":dif[i],"dea":dea[i],"hist":hist[i],"div":dv,
        "au_v":v,"au_oi":p,"au_ratio":ratio,
        "fwd":forward(i,3)})

print(json.dumps(res, ensure_ascii=False, indent=1))
json.dump(res, open("signals.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)

# 同日伦敦金实际高低，验证用户给的参考价
for x in res:
    print(x["name"], x["date"], "O/H/L/C", x["o"], x["h"], x["l"], x["c"])
