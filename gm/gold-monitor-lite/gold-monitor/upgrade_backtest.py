#!/usr/bin/env python3
"""升级回测：雷达触发 + 右侧确认（MACD金叉 或 站上MA5且MA5拐头）+ 位置过滤"""
import json, statistics, bisect
from datetime import date
import os
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

D=json.load(open("data_full.json",encoding="utf-8"))
bars=D["kline"]; au=D["au"]; N=len(bars)
ad=[a["d"] for a in au]; am={a["d"]:a for a in au}

def au_at(d):
    k=bisect.bisect_right(ad,d)-1
    if k<0: return None
    y1,m1,x1=map(int,d.split("-")); y2,m2,x2=map(int,ad[k].split("-"))
    if (date(y1,m1,x1)-date(y2,m2,x2)).days>10: return None
    return am[ad[k]]

def ema(a,n):
    k=2/(n+1); out=[]; p=a[0]
    for i,v in enumerate(a): p = v if i==0 else v*k+p*(1-k); out.append(p)
    return out

c=[b["c"] for b in bars]
e12,e26=ema(c,12),ema(c,26)
dif=[x-y for x,y in zip(e12,e26)]
dea=ema(dif,9); hist=[2*(x-y) for x,y in zip(dif,dea)]
ma5=[sum(c[max(0,i-4):i+1])/len(c[max(0,i-4):i+1]) if i>=4 else None for i in range(N)]
ma60=[sum(c[i-59:i+1])/60 if i>=59 else None for i in range(N)]
ma120=[sum(c[i-119:i+1])/120 if i>=119 else None for i in range(N)]

POS60=[];BELOW=[];RET3=[];RET5=[];VOLR=[];POS250=[];DEV120=[]
for i in range(N):
    lo=max(0,i-59); lows=[b["l"] for b in bars[lo:i+1]]; highs=[b["h"] for b in bars[lo:i+1]]
    mn,mx=min(lows),max(highs); POS60.append((c[i]-mn)/(mx-mn)*100 if mx>mn else 0)
    m20=sum(c[i-19:i+1])/20 if i>=19 else None
    sd=statistics.pstdev(c[i-19:i+1]) if i>=19 else None
    BELOW.append(bool(m20 and sd and c[i] < m20-2*sd))
    RET3.append((c[i]/c[i-3]-1)*100 if i>=3 else 0)
    RET5.append((c[i]/c[i-5]-1)*100 if i>=5 else 0)
    a=au_at(bars[i]["d"])
    vs=[au_at(bars[k]["d"])["v"] for k in range(max(0,i-19),i+1) if au_at(bars[k]["d"])]
    VOLR.append(a["v"]/(sum(vs)/len(vs)) if (a and vs) else None)
    lo2=max(0,i-249); l2=[b["l"] for b in bars[lo2:i+1]]; h2=[b["h"] for b in bars[lo2:i+1]]
    mn2,mx2=min(l2),max(h2); POS250.append((c[i]-mn2)/(mx2-mn2)*100 if mx2>mn2 else 0)
    DEV120.append((c[i]/ma120[i]-1)*100 if ma120[i] else 0)

# 摆动低点
K=5; pivots=[]
for p in range(K,N-K):
    seg=[bars[k]["l"] for k in range(p-K,p+K+1)]
    if abs(bars[p]["l"]-min(seg))<1e-9: pivots.append(p)

def prev_piv(i):
    k=bisect.bisect_left(pivots,i)-1
    return pivots[max(0,k-1):k+1]

def area(a,b): return abs(sum(x for x in hist[a+1:b+1] if x<0))

def mo_state(i):
    ps=prev_piv(i); j=ps[-1] if ps else None; j2=ps[0] if len(ps)==2 else None
    a_now=area(j,i) if j is not None else None
    a_prev=area(j2,j) if (j is not None and j2 is not None and j2<j) else None
    area_div=bool(j is not None and bars[i]["l"]<bars[j]["l"] and a_prev and a_now<a_prev)
    dif_high=bool(j is not None and bars[i]["l"]<bars[j]["l"] and dif[i]>dif[j])
    shrink=0
    for k in range(i,0,-1):
        if hist[k]<0 and hist[k]>hist[k-1]: shrink+=1
        else: break
    sp = POS60[i]<=20 or BELOW[i]
    b=bars[i]; rng=max(b["h"]-b["l"],1e-9); body=abs(b["c"]-b["o"])
    small=body/rng<=0.35
    no_low=b["l"]>=min(bars[k]["l"] for k in range(max(0,i-3),i)) if i>0 else False
    streak=0
    for k in range(i,-1,-1):
        bb=bars[k]; rr=max(bb["h"]-bb["l"],1e-9)
        if abs(bb["c"]-bb["o"])/rr<=0.35 and (k==0 or bb["l"]>=min(x["l"] for x in bars[max(0,k-3):k])): streak+=1
        else: break
    p=bars[i-1] if i>0 else None
    engulf=bool(p and b["c"]>b["o"] and p["c"]<p["o"] and b["c"]>=p["o"] and b["o"]<=p["c"])
    big=bool(b["c"]>b["o"] and body>1.5*(sum(abs(x["c"]-x["o"]) for x in bars[max(0,i-5):i])/max(1,len(bars[max(0,i-5):i]))))
    pat=bool((small and streak>=2 and no_low) or engulf or (big and no_low))
    r=VOLR[i]; pct=(b["c"]/bars[i-1]["c"]-1)*100 if i>0 else 0
    dry=bool(r is not None and r<=0.7)
    mild=bool(r is not None and 1.0<=r<=1.8 and b["c"]>b["o"] and 0<pct<=3)
    blow=bool(r is not None and r>=2.0 and b["c"]<b["o"] and pct<=-1.5)
    vol=bool((dry or mild) and not blow)
    return sum([sp,bool(area_div or dif_high or shrink>=2),pat,vol])

def crash_state(i):
    b=bars[i]; rng=max(b["h"]-b["l"],1e-9)
    ls=(min(b["o"],b["c"])-b["l"])/rng
    sp=(RET3[i]<=-3.0) or (BELOW[i] and RET5[i]<=-4.0)
    p=bars[i-1] if i>0 else None
    prev_pct=(p["c"]/bars[i-2]["c"]-1)*100 if (p and i>=2) else 0
    engulf=bool(p and b["c"]>b["o"] and p["c"]<p["o"] and b["c"]>=p["o"] and b["o"]<=p["c"] and prev_pct<=-1.5)
    panic=bool(ls>0.5 or engulf)
    a=au_at(b["d"]); vs=[au_at(bars[k]["d"])["v"] for k in range(max(0,i-20),i) if au_at(bars[k]["d"])]
    newhigh=bool(a and vs and a["v"]>=max(vs))
    vol=bool(VOLR[i] is not None and VOLR[i]>=1.5 and newhigh)
    return bool(sp and panic and vol)

def confirm(i):
    A = i>0 and dif[i]>dea[i] and dif[i-1]<=dea[i-1]
    B = i>=5 and ma5[i] is not None and ma5[i-1] is not None and c[i]>ma5[i] and ma5[i]>ma5[i-1]
    return A or B

def confirm_type(i):
    A = i>0 and dif[i]>dea[i] and dif[i-1]<=dea[i-1]
    B = i>=5 and ma5[i] is not None and ma5[i-1] is not None and c[i]>ma5[i] and ma5[i]>ma5[i-1]
    return "MACD金叉" if A else ("站上MA5" if B else None)

def pos_ok(i):
    return (DEV120[i] <= -15) or (POS250[i] <= 20)

def fwd(i,n):
    if i+n>=N: return None
    c0=c[i]
    return {"ret":(c[i+n]/c0-1)*100,
            "up":(max(bars[k]["h"] for k in range(i+1,i+n+1))/c0-1)*100,
            "dn":(min(bars[k]["l"] for k in range(i+1,i+n+1))/c0-1)*100}

START=next(k for k,b in enumerate(bars) if b["d"]>="2011-01-01")
END=N-21

def build(trigger_fn,label):
    """返回 触发→确认→位置 的各级样本"""
    raw=[]; conf=[]; confpos=[]; confpos2=[]
    for i in range(max(START,60), END+1):
        if not trigger_fn(i): continue
        raw.append(i)
        e=None
        for t in range(i, min(i+11, END+1)):
            if confirm(t): e=t; break
        if e is not None:
            conf.append((i,e,confirm_type(e)))
            if pos_ok(e): confpos.append((i,e,confirm_type(e)))
            if pos_ok(i): confpos2.append((i,e,confirm_type(e)))
    def st(entries):
        if not entries: return {"n":0}
        idxs=[e[1] if isinstance(e,tuple) else e for e in entries]
        # 去重（10 日）
        uniq=[]; last=-999
        for x in idxs:
            if x-last>=10: uniq.append(x); last=x
        out={"n":len(uniq)}
        for n in (5,10,20):
            rs=[];ups=[];dns=[]
            for x in uniq:
                f=fwd(x,n)
                if f: rs.append(f["ret"]);ups.append(f["up"]);dns.append(f["dn"])
            if not rs: continue
            wins=[x for x in rs if x>0]; losses=[x for x in rs if x<=0]
            aw=sum(wins)/len(wins) if wins else 0
            al=sum(losses)/len(losses) if losses else 0
            out[n]={"win":len(wins)/len(rs)*100,"avg":sum(rs)/len(rs),
                    "maxup":sum(ups)/len(ups),"maxdn":sum(dns)/len(dns),
                    "avgwin":aw,"avgloss":al,
                    "payoff": (aw/abs(al)) if al else None,
                    "exp":sum(rs)/len(rs)}
        return out
    return {"label":label,"raw":st(raw),"conf":st(conf),"confpos":st(confpos),"confpos_trig":st(confpos2),
            "counts":{"raw":len(raw),"conf":len(conf),"confpos":len(confpos),"confpos_trig":len(confpos2)}}

cr=build(crash_state,"暴跌雷达")
mo=build(lambda i: mo_state(i)>=3,"磨底雷达≥3")

# 磨底 4 分也跑一版对照
mo4=build(lambda i: mo_state(i)==4,"磨底雷达4分")

def show(b):
    print("\n===",b["label"],b["counts"])
    for key,tag in (("raw","原始触发"),("conf","+右侧确认"),("confpos","+确认+位置(入场日)"),("confpos_trig","+确认+位置(触发日)")):
        s=b[key]
        if not s.get("n"): print(f"  {tag}: n=0"); continue
        print(f"  {tag}: n={s['n']}")
        for n in (5,10,20):
            x=s[n]
            pf = "∞" if x['payoff'] is None else f"{x['payoff']:.2f}"
            print(f"    {n}日 胜率{x['win']:.1f}% 均值{x['avg']:+.2f}% 盈亏比{pf} 均盈{x['avgwin']:+.2f}% 均亏{x['avgloss']:+.2f}% 最大反弹{x['maxup']:+.2f}% 最大回撤{x['maxdn']:+.2f}%")

show(cr); show(mo); show(mo4)
json.dump({"crash":cr,"mo":mo,"mo4":mo4}, open("upgrade.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
