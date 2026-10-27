#!/usr/bin/env python3
"""双雷达全历史回测：磨底雷达（4 状态，≥3 触发）+ 暴跌雷达（空间+恐慌+天量）"""
import json, statistics, bisect
import os
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

D = json.load(open("data_full.json", encoding="utf-8"))
bars = D["kline"]; au = D["au"]
N = len(bars)
au_dates = [a["d"] for a in au]; au_map = {a["d"]: a for a in au}

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

def ma_c(i,n):
    return sum(closes[i-n+1:i+1])/n if i>=n-1 else None

def std_c(i,n):
    if i<n-1: return None
    xs=closes[i-n+1:i+1]; m=sum(xs)/n
    return statistics.pstdev(xs)

def au_at(d):
    k=bisect.bisect_right(au_dates, d)-1
    if k<0: return None
    if (bars_i_date_gap(d, au_dates[k]))>10: return None
    return au_map[au_dates[k]]

from datetime import date
def bars_i_date_gap(d1,d2):
    y1,m1,dd1=map(int,d1.split("-")); y2,m2,dd2=map(int,d2.split("-"))
    return abs((date(y1,m1,dd1)-date(y2,m2,dd2)).days)

def vol_ma(i,n=20):
    vs=[]
    for k in range(max(0,i-n+1), i+1):
        a=au_at(bars[k]["d"])
        if a: vs.append(a["v"])
    return sum(vs)/len(vs) if vs else None

# ---------- 指标缓存 ----------
POS=[]; BELOW=[]; DEV=[]; VOLR=[]; RET3=[]; RET5=[]
for i in range(N):
    lo=max(0,i-59); lows=[b["l"] for b in bars[lo:i+1]]; highs=[b["h"] for b in bars[lo:i+1]]
    mn,mx=min(lows),max(highs)
    POS.append((closes[i]-mn)/(mx-mn)*100 if mx>mn else 0)
    m20=ma_c(i,20); sd=std_c(i,20)
    lower=m20-2*sd if (m20 and sd) else None
    BELOW.append(bool(lower and closes[i]<lower))
    DEV.append((closes[i]-m20)/m20*100 if m20 else 0)
    a=au_at(bars[i]["d"]); vm=vol_ma(i,20)
    VOLR.append(a["v"]/vm if (a and vm) else None)
    RET3.append((closes[i]/closes[i-3]-1)*100 if i>=3 else 0)
    RET5.append((closes[i]/closes[i-5]-1)*100 if i>=5 else 0)

# ---------- 摆动低点 ----------
K=5
pivots=[]
for p in range(K, N-K):
    seg=[bars[k]["l"] for k in range(p-K,p+K+1)]
    if abs(bars[p]["l"]-min(seg))<1e-9: pivots.append(p)
piv_set=set(pivots)

def prev_pivots(i):
    k=bisect.bisect_left(pivots,i)-1
    return pivots[max(0,k-1):k+1]  # 最多两个

def neg_area(a,b):
    return abs(sum(x for x in hist[a+1:b+1] if x<0))

# ---------- 磨底雷达 ----------
def mo_di(i):
    ps=prev_pivots(i)
    j=ps[-1] if len(ps)==1 else (ps[-1] if ps else None)
    j2=ps[0] if len(ps)==2 else None
    a_now=neg_area(j,i) if j is not None else None
    a_prev=neg_area(j2,j) if (j is not None and j2 is not None and j2<j) else None
    area_div=bool(j is not None and bars[i]["l"]<bars[j]["l"] and a_prev and a_now<a_prev)
    dif_high=bool(j is not None and bars[i]["l"]<bars[j]["l"] and dif[i]>dif[j])
    shrink=0
    for k in range(i,0,-1):
        if hist[k]<0 and hist[k]>hist[k-1]: shrink+=1
        else: break
    return bool(area_div or dif_high or shrink>=2), {"area_div":area_div,"shrink":shrink,"dif_high":dif_high}

def pat(i):
    b=bars[i]; rng=max(b["h"]-b["l"],1e-9); body=abs(b["c"]-b["o"])
    small=body/rng<=0.35
    no_low = b["l"]>=min(bars[k]["l"] for k in range(max(0,i-3),i)) if i>0 else False
    streak=0
    for k in range(i,-1,-1):
        bb=bars[k]; rr=max(bb["h"]-bb["l"],1e-9)
        if abs(bb["c"]-bb["o"])/rr<=0.35 and (k==0 or bb["l"]>=min(x["l"] for x in bars[max(0,k-3):k])):
            streak+=1
        else: break
    p=bars[i-1] if i>0 else None
    engulf=bool(p and b["c"]>b["o"] and p["c"]<p["o"] and b["c"]>=p["o"] and b["o"]<=p["c"])
    big=bool(b["c"]>b["o"] and body>1.5*(sum(abs(x["c"]-x["o"]) for x in bars[max(0,i-5):i])/max(1,len(bars[max(0,i-5):i]))))
    return bool((small and streak>=2 and no_low) or engulf or (big and no_low)), {"streak":streak,"engulf":engulf,"body":body/rng*100}

def vol_state(i):
    r=VOLR[i]; b=bars[i]; pct=(b["c"]/bars[i-1]["c"]-1)*100 if i>0 else 0
    dry=bool(r is not None and r<=0.7)
    mild=bool(r is not None and 1.0<=r<=1.8 and b["c"]>b["o"] and 0<pct<=3)
    blow=bool(r is not None and r>=2.0 and b["c"]<b["o"] and pct<=-1.5)
    return bool((dry or mild) and not blow), {"ratio":r,"dry":dry,"mild":mild,"blow":blow}

def base(i):
    sp = POS[i]<=20 or BELOW[i]
    m,md = mo_di(i)
    p,pd = pat(i)
    v,vd = vol_state(i)
    return sum([sp,m,p,v]), {"space":sp,"momentum":m,"pattern":p,"volume":v}, md, pd, vd

# ---------- 暴跌雷达 ----------
def crash_state(i):
    b=bars[i]; rng=max(b["h"]-b["l"],1e-9)
    lower_shadow=(min(b["o"],b["c"])-b["l"])/rng
    space = (RET3[i] <= -3.0) or (BELOW[i] and RET5[i] <= -4.0)
    p=bars[i-1] if i>0 else None
    prev_pct=(p["c"]/bars[i-2]["c"]-1)*100 if (p and i>=2) else 0
    engulf=bool(p and b["c"]>b["o"] and p["c"]<p["o"] and b["c"]>=p["o"] and b["o"]<=p["c"] and prev_pct<=-1.5)
    panic = bool(lower_shadow>0.5 or engulf)
    # 天量：量比≥1.5 且 成交量创前 20 日新高（绝对值意义上的天量）
    a=au_at(bars[i]["d"]); prev=[au_at(bars[k]["d"])["v"] for k in range(max(0,i-20),i) if au_at(bars[k]["d"])]
    new_high = bool(a and prev and a["v"]>=max(prev))
    vol = bool(VOLR[i] is not None and VOLR[i]>=1.5 and new_high)
    mom = bool(hist[i]<0 and hist[i]>hist[i-1])
    score=sum([space,panic,vol,mom])
    trigger = bool(space and panic and vol)
    return trigger, score, {"space":space,"panic":panic,"vol":vol,"mom":mom,"ls":lower_shadow*100,"ratio":VOLR[i],"engulf":engulf,"newhigh":new_high}

# ---------- 前瞻 ----------
def forward(i, n):
    if i+n>=N: return None
    c0=closes[i]
    r=closes[i+n]/c0-1
    mx=max(bars[k]["h"] for k in range(i+1,i+n+1))/c0-1
    mn=min(bars[k]["l"] for k in range(i+1,i+n+1))/c0-1
    return {"ret":r*100,"maxup":mx*100,"maxdown":mn*100}

def dedupe(idxs, cool=10):
    out=[]; last=-999
    for i in idxs:
        if i-last>=cool: out.append(i); last=i
    return out

START=next(k for k,b in enumerate(bars) if b["d"]>="2011-01-01")
END=N-21

crash_trig=[]; crash_novol=[]; mo_trig=[]; mo4=[]
crash_detail={}; mo_detail={}
for i in range(max(START,60), END+1):
    c,s,cd = crash_state(i)
    if c: crash_trig.append(i); crash_detail[i]=(s,cd)
    if cd["space"] and cd["panic"]: crash_novol.append(i)
    sc,st,md,pd,vd = base(i)
    if sc>=3: mo_trig.append(i); mo_detail[i]=(sc,st,md,pd,vd)
    if sc==4: mo4.append(i)

crash_u=dedupe(crash_trig); mo_u=dedupe(mo_trig)
novol_u=dedupe(crash_novol); mo4_u=dedupe(mo4)
mo3_space=[i for i in mo_u if (POS[i]<=20 or BELOW[i])]

def stats(idxs, label):
    rows=[]
    for i in idxs:
        f={n:forward(i,n) for n in (5,10,20)}
        rows.append({"i":i,"d":bars[i]["d"],"c":bars[i]["c"],**{f"r{n}":(f[n]["ret"] if f[n] else None) for n in (5,10,20)},
                     **{f"u{n}":(f[n]["maxup"] if f[n] else None) for n in (5,10,20)},
                     **{f"d{n}":(f[n]["maxdown"] if f[n] else None) for n in (5,10,20)}})
    out={"label":label,"n":len(rows)}
    for n in (5,10,20):
        rs=[r[f"r{n}"] for r in rows if r[f"r{n}"] is not None]
        us=[r[f"u{n}"] for r in rows if r[f"u{n}"] is not None]
        ds=[r[f"d{n}"] for r in rows if r[f"d{n}"] is not None]
        out[n]={"win":sum(1 for x in rs if x>0)/len(rs)*100 if rs else None,
                "avg":sum(rs)/len(rs) if rs else None,
                "med":statistics.median(rs) if rs else None,
                "maxup":sum(us)/len(us) if us else None,
                "maxdown":sum(ds)/len(ds) if ds else None,
                "best":max(rs) if rs else None,"worst":min(rs) if rs else None}
    return out, rows

crash_stats, crash_rows = stats(crash_u, "暴跌雷达（空间+恐慌+天量）")
mo_stats, mo_rows = stats(mo_u, "磨底雷达（≥3 分）")
novol_stats, _ = stats(novol_u, "暴跌雷达（不含天量）")
mo4_stats, _ = stats(mo4_u, "磨底雷达（4 分满分）")
mo3s_stats, _ = stats(mo3_space, "磨底雷达（≥3 分且空间达标）")

# 分类
def classify(r):
    if r["r20"] is None: return "未验证"
    if r["r20"]>=5 and r["d20"]>-4: return "真底"
    if r["r20"]<=-3: return "假底"
    return "中性"

for r in crash_rows:
    r["cls"]=classify(r); r["type"]="暴跌"; r["score"]=crash_detail[r["i"]][0]
for r in mo_rows:
    r["cls"]=classify(r); r["type"]="磨底"; r["score"]=mo_detail[r["i"]][0]

print("=== 触发次数（原始/去重） ===")
print("暴跌", len(crash_trig), len(crash_u), "| 暴跌无量能", len(crash_novol), len(novol_u))
print("磨底≥3", len(mo_trig), len(mo_u), "| 磨底4分", len(mo4), len(mo4_u), "| 磨底≥3+空间", len(mo3_space))
for s in (crash_stats, mo_stats, novol_stats, mo4_stats, mo3s_stats):
    print("\n===", s["label"], "n=", s["n"])
    for n in (5,10,20):
        x=s[n]; print(f" {n}日: 胜率 {x['win']:.1f}%  均值 {x['avg']:+.2f}%  中位 {x['med']:+.2f}%  最大反弹均值 {x['maxup']:+.2f}%  最大回撤均值 {x['maxdown']:+.2f}%  最好 {x['best']:+.2f}%  最差 {x['worst']:+.2f}%")

print("\n=== 暴跌事件 ===")
for r in crash_rows:
    print(r["d"], f"{r['r20']:+.1f}%" if r["r20"] is not None else "", r["cls"])
print("\n=== 磨底事件(≥3) ===")
for r in mo_rows:
    print(r["d"], f"{r['r20']:+.1f}%" if r["r20"] is not None else "", r["cls"])

LAST = next(k for k,b in enumerate(bars) if b["d"]=="2026-10-23")
tr, lsc, lcd = crash_state(LAST)
def _conf(i):
    A = i>0 and dif[i]>dea[i] and dif[i-1]<=dea[i-1]
    B = i>=5 and ma_c(i,5) and ma_c(i-1,5) and bars[i]["c"]>ma_c(i,5) and ma_c(i,5)>ma_c(i-1,5)
    return bool(A), bool(B)

cA, cB = _conf(LAST)
latest_crash = {"date":bars[LAST]["d"], "score":lsc, "trigger":tr, "confirmA":cA, "confirmB":cB, "confirm":(cA or cB),
                "ret3":RET3[LAST], "ret5":RET5[LAST], "below":BELOW[LAST],
                "hist":hist[LAST], "hist_prev":hist[LAST-1], **lcd}

json.dump({"latest_crash":latest_crash, "crash":crash_stats,"mo":mo_stats,"novol":novol_stats,"mo4":mo4_stats,"mo3s":mo3s_stats,
           "crash_rows":crash_rows,"mo_rows":mo_rows,
           "counts":{"crash_raw":len(crash_trig),"crash":len(crash_u),"mo_raw":len(mo_trig),"mo":len(mo_u),
                     "novol":len(novol_u),"mo4":len(mo4_u),"mo3s":len(mo3_space)},
           "crash_detail":{str(k):v for k,v in crash_detail.items()},
           "mo_detail":{str(k):v for k,v in mo_detail.items()}},
          open("backtest.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
