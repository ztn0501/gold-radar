#!/usr/bin/env python3
"""缠论可测子集：包含处理 → 分型 → 笔 → 中枢 → 第三类买点

只做四件事，不做线段、不做级别递归、不预测：
  1. 用 ATR 做笔（等价于带包含处理的 ZigZag）
  2. 连续三笔重叠算中枢，得到 [下沿 ZD, 上沿 ZG]
  3. 第三类买点：离开中枢后回抽不破上沿
  4. 统计该信号后 T+20 / T+60 的表现，与随机基准、黄灯对比
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)


def load():
    d = json.load(open(os.path.join(ROOT, "data_full.json"), encoding="utf-8"))
    k = d["kline"]
    return ([x["d"] for x in k], [x["c"] for x in k],
            [x["h"] for x in k], [x["l"] for x in k])


def atr(H, L, C, n=14):
    tr = [H[0] - L[0]]
    for i in range(1, len(C)):
        tr.append(max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])))
    out, s = [], sum(tr[:n]) / n
    for i in range(len(C)):
        if i < n:
            out.append(s)
        else:
            s = (s * (n - 1) + tr[i]) / n
            out.append(s)
    return out


def merge_inclusion(H, L, DT):
    """缠论包含处理：方向向上取高高，向下取低低"""
    mh, ml, mi = [H[0]], [L[0]], [[0]]
    dirn = 1
    for i in range(1, len(H)):
        h, l = H[i], L[i]
        if (h <= mh[-1] and l >= ml[-1]) or (h >= mh[-1] and l <= ml[-1]):
            if dirn > 0:                     # 向上：取高的高、低的低里更高的那个
                mh[-1] = max(mh[-1], h)
                ml[-1] = max(ml[-1], l)
            else:
                mh[-1] = min(mh[-1], h)
                ml[-1] = min(ml[-1], l)
            mi[-1].append(i)
        else:
            if h > mh[-1]:
                dirn = 1
            elif l < ml[-1]:
                dirn = -1
            mh.append(h); ml.append(l); mi.append([i])
    return mh, ml, mi


def fractals(mh, ml):
    """顶分型 / 底分型（中间那根，用合并后 K 线）"""
    out = []
    for i in range(1, len(mh) - 1):
        if mh[i] > mh[i - 1] and mh[i] > mh[i + 1] and ml[i] > ml[i - 1] and ml[i] > ml[i + 1]:
            out.append((i, mh[i], "H"))
        elif ml[i] < ml[i - 1] and ml[i] < ml[i + 1] and mh[i] < mh[i - 1] and mh[i] < mh[i + 1]:
            out.append((i, ml[i], "L"))
    return out


def build_bi(fr, mh, ml, min_gap=4, min_pct=0.03):
    """成笔：相邻分型一顶一底，间隔 ≥min_gap 根合并K，且幅度 ≥min_pct"""
    bi, last = [], None
    for f in fr:
        if last is None:
            last = f; continue
        if f[2] == last[2]:                  # 同类型：留更极端的
            if (f[2] == "H" and f[1] > last[1]) or (f[2] == "L" and f[1] < last[1]):
                last = f
            continue
        gap = f[0] - last[0]
        amp = abs(f[1] / last[1] - 1)
        if gap >= min_gap and amp >= min_pct:
            bi.append(dict(a=last, b=f))
            last = f
        else:
            # 幅度不够：如果更极端也替换（避免漏掉真顶底）
            if (f[2] == "H" and f[1] > last[1]) or (f[2] == "L" and f[1] < last[1]):
                pass
    return bi


def zhongshu(bi):
    """连续三笔重叠 → 中枢；随后按“中枢延伸”吞并仍在区间内的笔"""
    out, i = [], 0
    while i + 2 < len(bi):
        seg = bi[i:i + 3]
        highs = [max(x["a"][1], x["b"][1]) for x in seg]
        lows = [min(x["a"][1], x["b"][1]) for x in seg]
        zg, zd = min(highs), max(lows)
        if zg <= zd:
            i += 1
            continue
        j = i + 3
        # 延伸：下一笔仍与区间重叠就并入（区间不变）
        while j < len(bi):
            h = max(bi[j]["a"][1], bi[j]["b"][1])
            l = min(bi[j]["a"][1], bi[j]["b"][1])
            if h >= zd and l <= zg:
                j += 1
            else:
                break
        out.append(dict(i=i, j=j, zg=zg, zd=zd,
                        start=seg[0]["a"][0], end=bi[j - 1]["b"][0],
                        n=j - i))
        i = j
    return out


def third_buy(bi, zs):
    """第三类买点：离开中枢（某笔高点 > ZG）后的下一笔回抽低点 > ZG"""
    sig = []
    for z in zs:
        j = z.get("j", z["i"] + 3)       # 中枢（含延伸）之后的第一笔
        if j + 1 >= len(bi):
            continue
        leave = bi[j]
        hi_leave = max(leave["a"][1], leave["b"][1])
        if hi_leave <= z["zg"]:
            continue
        pull = bi[j + 1]
        lo_pull = min(pull["a"][1], pull["b"][1])
        if lo_pull > z["zg"]:
            sig.append(dict(idx=pull["b"][0], zh=z, leave_hi=hi_leave, pull_low=lo_pull))
    # 去重（同一根）
    out, seen = [], set()
    for s in sig:
        if s["idx"] in seen:
            continue
        seen.add(s["idx"]); out.append(s)
    return out


def main():
    DT, C, H, L = load()
    A = atr(H, L, C)
    mh, ml, mi = merge_inclusion(H, L, DT)
    fr = fractals(mh, ml)
    bi = build_bi(fr, mh, ml)
    zs = zhongshu(bi)
    sig = third_buy(bi, zs)

    def real_idx(mi_idx, kind):
        """合并K线序号 → 原始K线序号（取该合并段的极值那天）"""
        seg = mi[mi_idx]
        if kind == "H":
            return max(seg, key=lambda i: H[i])
        return min(seg, key=lambda i: L[i])

    N = len(C)
    print("=" * 82)
    print("缠论可测子集 · 黄金日线 %s → %s" % (DT[0], DT[-1]))
    print("=" * 82)
    print("  合并后 K 线 %d 根｜分型 %d 个｜笔 %d 个｜中枢 %d 个｜三买信号 %d 个"
          % (len(mh), len(fr), len(bi), len(zs), len(sig)))

    # 基准：全样本任意一天买入的 T+20 / T+60
    def fwd(i, n):
        j = i + n
        return (C[j] / C[i] - 1) * 100 if j < N else None

    base20 = [fwd(i, 20) for i in range(N - 20)]
    base60 = [fwd(i, 60) for i in range(N - 60)]
    m20 = sum(base20) / len(base20)
    m60 = sum(base60) / len(base60)

    rows = []
    for s in sig:
        i = real_idx(s["idx"], "L")
        r20, r60 = fwd(i, 20), fwd(i, 60)
        rows.append((DT[i], C[i], s["zh"]["zd"], s["zh"]["zg"], r20, r60))

    print()
    print("【第三类买点明细】")
    print("  %-12s %-9s %-9s %-9s %-9s %-9s" % ("日期", "收盘", "中枢下沿", "中枢上沿", "T+20", "T+60"))
    for d, c, zd, zg, r20, r60 in rows:
        print("  %-12s %-9.0f %-9.0f %-9.0f %-9s %-9s"
              % (d, c, zd, zg,
                 "%+.1f%%" % r20 if r20 is not None else "—",
                 "%+.1f%%" % r60 if r60 is not None else "—"))

    def stat(vals):
        v = [x for x in vals if x is not None]
        if not v:
            return "—"
        win = sum(1 for x in v if x > 0) / len(v) * 100
        return "%+.2f%%｜胜率 %.0f%%｜n=%d" % (sum(v) / len(v), win, len(v))

    print()
    print("【统计对比】")
    print("  三买信号 T+20：%s" % stat([r[4] for r in rows]))
    print("  三买信号 T+60：%s" % stat([r[5] for r in rows]))
    print("  全样本基准 T+20：%+.2f%%｜胜率 %.0f%%" %
          (m20, sum(1 for x in base20 if x > 0) / len(base20) * 100))
    print("  全样本基准 T+60：%+.2f%%｜胜率 %.0f%%" %
          (m60, sum(1 for x in base60 if x > 0) / len(base60) * 100))

    # 当前是否处在某个中枢附近
    last = zs[-1] if zs else None
    if last:
        print()
        print("【最近一个中枢】%.0f – %.0f（%s 起）" %
              (last["zd"], last["zg"], DT[real_idx(last["start"], "L")]))
        print("  当前 %.2f，位于中枢%s" % (C[-1], "上沿之上" if C[-1] > last["zg"]
                                        else ("下沿之下" if C[-1] < last["zd"] else "内部")))

    out = dict(n_merged=len(mh), n_fractal=len(fr), n_bi=len(bi),
               n_zs=len(zs), n_sig=len(sig),
               signals=[dict(date=r[0], close=r[1], zd=r[2], zg=r[3],
                             r20=r[4], r60=r[5]) for r in rows])
    json.dump(out, open(os.path.join(BASE, "chan_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n已写出 wave/chan_result.json")


if __name__ == "__main__":
    main()
