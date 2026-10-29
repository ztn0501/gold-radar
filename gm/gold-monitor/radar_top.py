#!/usr/bin/env python3
"""逃顶雷达（满分 4 分）+ 最近一次 ≥3 分的时间"""
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
piv=[p for p in range(5,N-5) if abs(bars[p]["h"]-max(bars[k]["h"] for k in range(p-5,p+6)))<1e-9]

def red_area(a,b): return abs(sum(x for x in hist[a+1:b+1] if x>0))

def state(i):
    ma20=sum(c[i-19:i+1])/20
    sd=statistics.pstdev(c[i-19:i+1]); upper=ma20+2*sd
    dev20=(c[i]/ma20-1)*100
    lo=max(0,i-119); lows=[x["l"] for x in bars[lo:i+1]]; highs=[x["h"] for x in bars[lo:i+1]]
    mn,mx=min(lows),max(highs); pos120=(c[i]-mn)/(mx-mn)*100 if mx>mn else 0
    # 2026-10 修正：去掉「收盘贴近布林上轨」单独计空间分的分支。
    # 该分支在半山腰反弹里也会成立（8/06 位置仅 20% 却拿到空间分 → 假顶），
    # 全样本实测只贡献 2 次信号、0 次真跌，删掉不影响 1/29 那种真顶（位置 90%）。
    touch_upper = bool(c[i]>=upper*0.995)
    space=bool(pos120>=80 or dev20>=15)
    k=bisect.bisect_left(piv,i)-1
    j=piv[k] if k>=0 else None; j2=piv[k-1] if k>=1 else None
    top_div=False
    if j and j2 and i-j<=5:
        a_now=red_area(j2,j)
        top_div=bars[i]["h"]>bars[j]["h"] and (dif[i]<dif[j] or (a_now and red_area(j,i)<a_now))
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
            "detail":{"pos120":round(pos120,1),"dev20":round(dev20,2),"upper":round(upper,2),
                      "close":b["c"],"ma20":round(ma20,2),"below_ma20":b["c"]<ma20,
                      "touch_upper":touch_upper,
                      "top_div":top_div,"red_shrink":red_shrink,"death":death,
                      "upper_shadow":round(us*100,1),"bear_engulf":bear,
                      "ret3":round(ret3,2),"vr":round(vr,2) if vr else None}}

i=max(k for k in range(N) if bars[k]["d"] in au)
out=state(i); out["date"]=bars[i]["d"]
# 最近一次 >=3 分
last3=None
for k in range(i, max(0,i-60), -1):
    if state(k)["score"]>=3:
        last3={"date":bars[k]["d"],"days_ago":i-k}; break
out["last_top3"]=last3
json.dump(out,open("radar_top.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print(json.dumps(out,ensure_ascii=False,indent=1))
