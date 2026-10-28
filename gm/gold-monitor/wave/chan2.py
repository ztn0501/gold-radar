#!/usr/bin/env python3
"""缠论双级别最小实现：周线中枢 + 日线回抽

流程：
  1. 日线聚合成周线（高取最高、低取最低、收取最后）
  2. 周线上做 包含处理 → 分型 → 笔 → 中枢（沿用 chan.py 的实现）
  3. 价格向上离开周线中枢（突破上沿 ZG）后，在日线上找“回抽不破 ZG”
  4. 统计信号后 T+20 / T+60，与基准对比

判定标准（预注册，不调参）：
  样本 ≥30｜T+20 胜率 ≥55%｜T+60 胜率 ≥58%｜高于全样本基准
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chan as CH

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)


def to_weekly(DT, C, H, L):
    """按 ISO 周聚合"""
    from datetime import date
    weeks = []
    cur_key, cur = None, None
    for i in range(len(DT)):
        d = date.fromisoformat(DT[i])
        key = d.isocalendar()[:2]
        if key != cur_key:
            if cur:
                weeks.append(cur)
            cur_key = key
            cur = dict(h=H[i], l=L[i], c=C[i], last=i, first=i)
        else:
            cur["h"] = max(cur["h"], H[i])
            cur["l"] = min(cur["l"], L[i])
            cur["c"] = C[i]
            cur["last"] = i
    if cur:
        weeks.append(cur)
    return weeks


def main():
    DT, C, H, L = CH.load()
    N = len(C)
    wk = to_weekly(DT, C, H, L)
    nW = len(wk)
    WH = [w["h"] for w in wk]
    WL = [w["l"] for w in wk]
    WD = [DT[w["last"]] for w in wk]

    mh, ml, mi = CH.merge_inclusion(WH, WL, WD)
    fr = CH.fractals(mh, ml)
    bi = CH.build_bi(fr, mh, ml, min_gap=3, min_pct=0.05)
    zs = CH.zhongshu(bi)

    print("=" * 84)
    print("缠论双级别 · 周线中枢 + 日线回抽")
    print("=" * 84)
    print("  日线 %d 根 → 周线 %d 根｜合并 %d｜分型 %d｜笔 %d｜中枢 %d"
          % (N, nW, len(mh), len(fr), len(bi), len(zs)))

    def wi_to_di(w_idx):
        """合并K线序号 → 周线序号 → 日线序号"""
        return wk[w_idx]["last"] if 0 <= w_idx < nW else None

    sigs = []
    for z in zs:
        j = z.get("j", z["i"] + 3)
        if j >= nW:
            continue
        zg, zd = z["zg"], z["zd"]
        leave_di = wi_to_di(wk[j]["last"] if j < nW else None) if False else None
        start_di = wi_to_di(z["end"])          # 中枢最后一个笔端点所在的日线位置
        if start_di is None:
            continue
        # 离开：从 start_di 起，收盘价首次超过 ZG*1.02
        k = start_di
        while k < N and C[k] <= zg * 1.02:
            k += 1
        if k >= N - 25:
            continue
        # 回抽：离开后 60 个交易日内，最低价回落但仍在 ZG 之上，且随后收盘站回 ZG 之上
        end = min(k + 60, N - 1)
        hit = None
        for m in range(k, end):
            if L[m] >= zg and L[m] <= zg * 1.06 and C[m] > zg:
                # 确认：次日收盘仍在 ZG 上方
                if m + 1 < N and C[m + 1] > zg:
                    hit = m + 1
                    break
        if hit is None:
            continue
        if sigs and hit - sigs[-1] < 20:       # 同一次回抽只取一次
            continue
        sigs.append(hit)

    def fwd(i, n):
        j2 = i + n
        return (C[j2] / C[i] - 1) * 100 if j2 < N else None

    rows = [(DT[i], C[i], fwd(i, 20), fwd(i, 60)) for i in sigs]
    print()
    print("【信号明细】")
    print("  %-12s %-9s %-9s %-9s" % ("日期", "收盘", "T+20", "T+60"))
    for d, c, r20, r60 in rows:
        print("  %-12s %-9.0f %-9s %-9s"
              % (d, c,
                 "%+.1f%%" % r20 if r20 is not None else "—",
                 "%+.1f%%" % r60 if r60 is not None else "—"))

    base20 = [fwd(i, 20) for i in range(N - 20)]
    base60 = [fwd(i, 60) for i in range(N - 60)]

    def stat(v):
        v = [x for x in v if x is not None]
        if not v:
            return dict(n=0)
        return dict(n=len(v), avg=sum(v) / len(v),
                    win=sum(1 for x in v if x > 0) / len(v) * 100)

    s20 = stat([r[2] for r in rows])
    s60 = stat([r[3] for r in rows])
    b20 = stat(base20)
    b60 = stat(base60)

    print()
    print("【统计】")
    if s20["n"]:
        print("  信号 T+20：%+.2f%%｜胜率 %.0f%%｜n=%d" % (s20["avg"], s20["win"], s20["n"]))
    if s60["n"]:
        print("  信号 T+60：%+.2f%%｜胜率 %.0f%%｜n=%d" % (s60["avg"], s60["win"], s60["n"]))
    print("  基准 T+20：%+.2f%%｜胜率 %.0f%%" % (b20["avg"], b20["win"]))
    print("  基准 T+60：%+.2f%%｜胜率 %.0f%%" % (b60["avg"], b60["win"]))

    print()
    print("【判定（预注册标准）】")
    checks = [
        ("样本 ≥ 30", s20["n"] >= 30, "%d" % s20["n"]),
        ("T+20 胜率 ≥ 55%", s20["n"] and s20["win"] >= 55,
         "%.0f%%" % s20["win"] if s20["n"] else "—"),
        ("T+60 胜率 ≥ 58%", s60["n"] and s60["win"] >= 58,
         "%.0f%%" % s60["win"] if s60["n"] else "—"),
        ("T+20 均值高于基准", s20["n"] and s20["avg"] > b20["avg"],
         "%+.2f%% vs %+.2f%%" % (s20["avg"], b20["avg"]) if s20["n"] else "—"),
    ]
    allpass = True
    for name, ok, val in checks:
        print("  %-22s %-10s %s" % (name, val, "✅" if ok else "❌"))
        allpass = allpass and bool(ok)
    print()
    print("  总结论：%s" % ("通过，可以考虑接入" if allpass else "不通过，永久停止这条线"))

    json.dump(dict(n_weekly=nW, n_zs=len(zs), n_sig=len(sigs),
                   stat20=s20, stat60=s60, base20=b20, base60=b60,
                   signals=[dict(d=r[0], c=r[1], r20=r[2], r60=r[3]) for r in rows]),
              open(os.path.join(BASE, "chan2_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
