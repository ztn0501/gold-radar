#!/usr/bin/env python3
"""2026 四个高点：逃顶雷达逐日复盘"""
import json, os, statistics, bisect

os.chdir(os.path.dirname(os.path.abspath(__file__)))
D=json.load(open("data_full.json",encoding="utf-8"))
bars=D["kline"]; au={a["d"]:a for a in D["au"]}; N=len(bars)
c=[b["c"] for b in bars]

def ema(a,n):
    k=2/(n+1); out=[]; p=a[0]
    for i,v in enumerate(a): p=v if i==0 else v*k+p*(1-k); out.append(p)
    return out

e12,e26=ema(c,12),ema(c,26)
dif=[x-y for x,y in zip(e12,e26)]
dea=ema(dif,9)
hist=[2*(x-y) for x,y in zip(dif,dea)]

piv=[]
for p in range(5,N-5):
    seg=[bars[k]["h"] for k in range(p-5,p+6)]
    if abs(bars[p]["h"]-max(seg))<1e-9: piv.append(p)

def red_area(a,b): return abs(sum(x for x in hist[a+1:b+1] if x>0))

def state(i):
    ma20=sum(c[i-19:i+1])/20
    sd=statistics.pstdev(c[i-19:i+1])
    upper=ma20+2*sd
    dev20=(c[i]/ma20-1)*100
    lo=max(0,i-119); lows=[x["l"] for x in bars[lo:i+1]]; highs=[x["h"] for x in bars[lo:i+1]]
    mn,mx=min(lows),max(highs); pos120=(c[i]-mn)/(mx-mn)*100 if mx>mn else 0
    space = bool(pos120>=80 or dev20>=15 or c[i]>=upper*0.995)

    k=bisect.bisect_left(piv,i)-1
    j=piv[k] if k>=0 else None
    j2=piv[k-1] if k>=1 else None
    top_div=False
    if j and j2 and i-j<=5:
        a_now=red_area(j2,j) if j2<j else 0
        top_div = bars[i]["h"]>bars[j]["h"] and (dif[i]<dif[j] or (a_now and red_area(j,i)<a_now))
    red_shrink=bool(hist[i]>0 and hist[i]<hist[i-1]<hist[i-2])
    death=any(dif[k2]<dea[k2] and dif[k2-1]>=dea[k2-1] for k2 in range(max(1,i-3),i+1)) and pos120>=70
    momentum=bool(top_div or red_shrink or death)

    b=bars[i]; rng=max(b["h"]-b["l"],1e-9)
    us=(b["h"]-max(b["o"],b["c"]))/rng
    pv=bars[i-1]
    bear=bool(b["c"]<b["o"] and pv["c"]>pv["o"] and b["c"]<=pv["o"] and b["o"]>=pv["c"])
    ret3=(c[i]/c[i-3]-1)*100 if i>=3 else 0
    pattern=bool(us>0.5 or bear or ret3>=6)

    a=au.get(b["d"]); vs=[au[x["d"]]["v"] for x in bars[max(0,i-20):i] if x["d"] in au]
    vr=a["v"]/(sum(vs)/len(vs)) if (a and vs) else None
    vol=bool(vr and vr>=2.0 and (b["c"]<b["o"] or us>0.4))
    return {"score":int(space)+int(momentum)+int(pattern)+int(vol),
            "space":space,"momentum":momentum,"pattern":pattern,"volume":vol,
            "pos120":pos120,"dev20":dev20,"c":c[i],"ma20":ma20,"below":c[i]<ma20,
            "us":us*100,"ret3":ret3,"vr":vr,"top_div":top_div,"red_shrink":red_shrink,
            "death":death,"bear":bear,"dif":dif[i],"dea":dea[i],"hist":hist[i]}

idx={b["d"]:k for k,b in enumerate(bars)}
peaks=[("2026-01-29",5596.33),("2026-02-24",5249.29),("2026-04-17",4889.24),("2026-08-25",4696.59)]
out=[]
for dt,ph in peaks:
    i=idx[dt]
    win=[]
    for k in range(i-2,i+3):
        s=state(k); win.append({"d":bars[k]["d"],"score":s["score"],"below":s["below"],"c":s["c"],"s":s})
    # 首次 >=3 分
    first=None
    for k in range(i,min(i+11,N)):
        if state(k)["score"]>=3: first=(bars[k]["d"],k-i); break
    # 首次跌破 MA20
    brk=None
    for k in range(i,min(i+61,N)):
        if state(k)["below"]: brk=(bars[k]["d"],k-i,state(k)["score"]); break
    # 见顶后 60 日最大回撤
    dd=min(bars[k]["l"] for k in range(i,min(i+61,N)))/c[i]-1
    out.append({"date":dt,"peak":ph,"window":win,"first_alert":first,"break_ma20":brk,
                "dd60":dd*100,"day":state(i)})

for o in out:
    print("==",o["date"],"peak",o["peak"],"score",o["day"]["score"],"| window",[(w["d"][5:],w["score"]) for w in o["window"]])
    print("   first>=3",o["first_alert"],"break MA20",o["break_ma20"],"DD60",round(o["dd60"],2))
json.dump(out,open("top_review.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
