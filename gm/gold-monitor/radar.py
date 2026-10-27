#!/usr/bin/env python3
"""磨底规则雷达：空间 / 动能 / 形态 / 量能 —— 四状态客观判定"""
import json, statistics
import os
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

d = json.load(open("data_full.json", encoding="utf-8"))
bars = d["kline"]; au = {a["d"]: a for a in d["au"]}
N = len(bars)

def ema(a, n):
    k = 2/(n+1); out=[]; prev=a[0]
    for i,v in enumerate(a):
        prev = v if i==0 else v*k + prev*(1-k); out.append(prev)
    return out

closes=[b["c"] for b in bars]
e12,e26=ema(closes,12),ema(closes,26)
dif=[x-y for x,y in zip(e12,e26)]
dea=ema(dif,9)
hist=[2*(x-y) for x,y in zip(dif,dea)]

def ma(i,n,key="c"):
    if i<n-1: return None
    return sum(bars[k][key] for k in range(i-n+1,i+1))/n

def std(i,n):
    if i<n-1: return None
    xs=[bars[k]["c"] for k in range(i-n+1,i+1)]
    m=sum(xs)/len(xs)
    return statistics.pstdev(xs)

def vol_ma(i,n=20):
    ds=[bars[k]["d"] for k in range(max(0,i-n+1),i+1)]
    vs=[au[x]["v"] for x in ds if x in au]
    return sum(vs)/len(vs) if vs else None

K=5
def pivots_upto(i):
    out=[]
    for p in range(K, i):
        lo=max(0,p-K); hi=min(N-1,p+K)
        seg=[bars[k]["l"] for k in range(lo,hi+1)]
        if abs(bars[p]["l"]-min(seg))<1e-9:
            out.append(p)
    return out

piv_cache={}
def prev_pivots(i):
    if i not in piv_cache:
        ps=pivots_upto(i)
        piv_cache[i]=ps
    return piv_cache[i]

def area(a,b):
    return abs(sum(x for x in hist[a+1:b+1] if x<0))

def state_space(i):
    lo=max(0,i-59)
    lows=[bars[k]["l"] for k in range(lo,i+1)]
    highs=[bars[k]["h"] for k in range(lo,i+1)]
    mn,mx=min(lows),max(highs)
    pos=(bars[i]["c"]-mn)/(mx-mn)*100 if mx>mn else 0
    m20=ma(i,20); sd=std(i,20)
    lower=m20-2*sd if m20 and sd else None
    dev=(bars[i]["c"]-m20)/m20*100 if m20 else None
    below = lower is not None and bars[i]["c"] < lower
    # 只看位置：破布林下轨是「超卖」不是「低位」，仅作提示、不参与判定
    qualify = (pos <= 20)
    return {"pos60":pos,"ma20":m20,"lower":lower,"dev20":dev,"below_lower":below,
            "ok":bool(qualify)}

def state_momentum(i):
    ps=prev_pivots(i)
    j=ps[-1] if ps else None
    j2=ps[-2] if len(ps)>=2 else None
    a_now=area(j,i) if j is not None else None
    a_prev=area(j2,j) if (j is not None and j2 is not None) else None
    area_div = bool(j is not None and bars[i]["l"]<bars[j]["l"] and a_prev and a_now<a_prev)
    dif_higher = bool(j is not None and bars[i]["l"]<bars[j]["l"] and dif[i]>dif[j])
    shrink=0
    for k in range(i,0,-1):
        if hist[k]<0 and hist[k]>hist[k-1]: shrink+=1
        else: break
    ok = area_div or dif_higher or shrink>=2
    return {"prev_low":bars[j]["l"] if j is not None else None,
            "prev_date":bars[j]["d"] if j is not None else None,
            "area_now":a_now,"area_prev":a_prev,"area_div":area_div,
            "dif_higher":dif_higher,"shrink":shrink,"ok":bool(ok)}

def state_pattern(i):
    b=bars[i]; rng=max(b["h"]-b["l"],1e-9); body=abs(b["c"]-b["o"])
    small = body/rng<=0.35
    no_new_low = b["l"] >= min(bars[k]["l"] for k in range(max(0,i-3),i)) if i>=1 else False
    # 连续小实体
    streak=0
    for k in range(i,-1,-1):
        bb=bars[k]; rr=max(bb["h"]-bb["l"],1e-9)
        if abs(bb["c"]-bb["o"])/rr<=0.35 and (k==0 or bb["l"]>=min(x["l"] for x in bars[max(0,k-3):k])):
            streak+=1
        else: break
    prev=bars[i-1] if i>0 else None
    engulf=False
    if prev:
        engulf = (b["c"]>b["o"] and prev["c"]<prev["o"]
                  and b["c"]>=prev["o"] and b["o"]<=prev["c"])
    big_yang = b["c"]>b["o"] and (body > 1.5*sum(abs(x["c"]-x["o"]) for x in bars[max(0,i-5):i])/max(1,len(bars[max(0,i-5):i])))
    ok = (small and streak>=2 and no_new_low) or engulf or (big_yang and no_new_low)
    return {"small":small,"streak":streak,"no_new_low":no_new_low,"body_pct":body/rng*100,
            "engulf":engulf,"big_yang":big_yang,"ok":bool(ok)}

def state_volume(i):
    v=au.get(bars[i]["d"],{}).get("v")
    vm=vol_ma(i,20)
    ratio=v/vm if (v and vm) else None
    b=bars[i]; pct=(b["c"]/bars[i-1]["c"]-1)*100 if i>0 else 0
    dry = ratio is not None and ratio<=0.7
    mild_up = ratio is not None and 1.0<=ratio<=1.8 and b["c"]>b["o"] and 0<pct<=3
    blowoff = ratio is not None and ratio>=2.0 and b["c"]<b["o"] and pct<=-1.5
    ok = (dry or mild_up) and not blowoff
    return {"vol":v,"vol_ma20":vm,"ratio":ratio,"dry":dry,"mild_up":mild_up,
            "blowoff":blowoff,"pct":pct,"ok":bool(ok)}

def radar(i):
    s1=state_space(i); s2=state_momentum(i); s3=state_pattern(i); s4=state_volume(i)
    score=sum([s1["ok"],s2["ok"],s3["ok"],s4["ok"]])
    return {"d":bars[i]["d"],"c":bars[i]["c"],"score":score,
            "space":s1,"momentum":s2,"pattern":s3,"volume":s4}

idx={b["d"]:k for k,b in enumerate(bars)}
nodes=[("① 第一波急跌底","2026-02-02"),("② 第二波急跌底","2026-03-23"),
       ("③ 宏观大底","2026-06-24"),("④ 当前","2026-10-23")]

out=[]
for name,dt in nodes:
    i=idx[dt]
    win=[radar(k) for k in range(max(0,i-2), min(N,i+4))]
    out.append({"name":name,"date":dt,"day":radar(i),"window":win})

print(json.dumps([{ "name":x["name"],"date":x["date"],
  "score":x["day"]["score"],
  "space":(round(x["day"]["space"]["pos60"],1),x["day"]["space"]["ok"]),
  "mom":(x["day"]["momentum"]["area_div"],x["day"]["momentum"]["shrink"],x["day"]["momentum"]["ok"]),
  "pat":(x["day"]["pattern"]["streak"],x["day"]["pattern"]["engulf"],x["day"]["pattern"]["ok"]),
  "vol":(round(x["day"]["volume"]["ratio"],2) if x["day"]["volume"]["ratio"] else None,x["day"]["volume"]["ok"]),
  "win":[ (w["d"],w["score"]) for w in x["window"]]
} for x in out], ensure_ascii=False, indent=1))

json.dump(out, open("radar.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
