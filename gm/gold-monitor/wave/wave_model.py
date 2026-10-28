#!/usr/bin/env python3
"""波浪结构模型 v2（独立分支，不做预测）

改了什么（对比 v1）：
  · 拆成两个互斥假设家族：
      A 族：顶部=浪5（浪已走完，现在走 ABC 调整）
      B 族：顶部=浪3（现在走浪4，之后还有浪5 创新高）
  · 加“浪5 不得远长于浪3”的形态约束（v1 缺这条，导致浪5=2.3×浪3 的畸形标注排第一）
  · 每个假设都给：评分、失效价、时间窗

输出：wave_report.txt / wave_candidates.json
"""
import json, os, itertools
from datetime import date, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
os.chdir(ROOT)


def load():
    d = json.load(open("data_full.json", encoding="utf-8"))
    k = d["kline"]
    return ([x["d"] for x in k], [x["c"] for x in k],
            [x["h"] for x in k], [x["l"] for x in k])


def zigzag(H, L, thr):
    piv, dirn, ext_i, ext_p = [], 0, 0, None
    for i in range(1, len(H)):
        if dirn >= 0:
            if ext_p is None or H[i] > ext_p:
                ext_i, ext_p = i, H[i]
            if L[i] <= ext_p * (1 - thr):
                piv.append((ext_i, ext_p, "H"))
                dirn, ext_i, ext_p = -1, i, L[i]
        if dirn <= 0:
            if ext_p is None or L[i] < ext_p:
                ext_i, ext_p = i, L[i]
            if H[i] >= ext_p * (1 + thr):
                piv.append((ext_i, ext_p, "L"))
                dirn, ext_i, ext_p = 1, i, H[i]
    piv.append((ext_i, ext_p, "H" if dirn > 0 else "L"))
    out = []
    for p in piv:
        if out and p[0] == out[-1][0]:
            continue
        out.append(p)
    return out


def fib_score(x, lo, hi, soft=1.2):
    if lo <= x <= hi:
        return 1.0
    d = (lo - x) if x < lo else (x - hi)
    w = (hi - lo) or 0.1
    return max(0.0, 1 - d / (w * soft))


def fam_A(DT, C, H, L, piv, i0, i_top):
    """A 族：顶 = 浪5（5 浪完整）"""
    seg = [p for p in piv if i0 <= p[0] <= i_top]
    Hs = [p for p in seg if p[2] == "H"]
    Ls = [p for p in seg if p[2] == "L"]
    L0 = min([p for p in piv if abs(p[0] - i0) < 90 and p[2] == "L"],
             key=lambda p: p[1], default=(i0, L[i0], "L"))
    out = []
    for h1, h2 in itertools.combinations(Hs, 2):
        for l1, l2 in itertools.combinations(Ls, 2):
            if not (L0[0] < h1[0] < l1[0] < h2[0] < l2[0] < i_top):
                continue
            P0, P1, P2, P3, P4, P5 = L0[1], h1[1], l1[1], h2[1], l2[1], H[i_top]
            if P2 <= P0 or P3 <= P1:
                continue
            # 端点必须是区间极值：浪1 顶 = (起点,浪2底) 最高；浪2 底 = (浪1顶,浪3顶) 最低；
            #                    浪3 顶 = (浪2底,浪4底) 最高
            if P1 != max(H[L0[0]:l1[0] + 1]):
                continue
            if P3 != max(H[l1[0]:l2[0] + 1]):
                continue
            if P2 != min(L[h1[0]:h2[0] + 1]):
                continue
            w1, w3, w5 = P1 - P0, P3 - P2, P5 - P4
            if w3 <= min(w1, w5):                 # 铁律：浪3 不最短
                continue
            r2 = (P1 - P2) / w1
            r4 = (P3 - P4) / (P3 - P2)
            e3, e5 = w3 / w1, w5 / w3
            if e5 > 1.618:                        # 浪5 远长于浪3 → 形态畸形
                continue
            overlap = P4 <= P1
            d2 = max(1, l1[0] - h1[0])
            d4 = max(1, l2[0] - h2[0])
            # 浪4 必须“有实质”：要么够深，要么够久，否则不算一段
            if d4 < 8 and r4 < 0.236:
                continue
            s = (0.18 * fib_score(r2, 0.382, 0.618) +
                 0.16 * fib_score(r4, 0.236, 0.382) +
                 0.22 * fib_score(e3, 1.618, 4.236) +
                 0.16 * fib_score(e5, 0.382, 1.000) +
                 0.08 * min(1.0, abs(r2 - r4) / 0.30) +
                 0.10 * (0.0 if overlap else 1.0) +
                 0.10 * fib_score(d4 / d2, 0.30, 1.50))
            out.append(dict(fam="A", score=round(s, 3),
                            w1=dict(d=DT[h1[0]], p=round(P1, 2)),
                            w2=dict(d=DT[l1[0]], p=round(P2, 2)),
                            w3=dict(d=DT[h2[0]], p=round(P3, 2)),
                            w4=dict(d=DT[l2[0]], p=round(P4, 2)),
                            top=dict(d=DT[i_top], p=round(P5, 2)),
                            r2=round(r2, 3), r4=round(r4, 3),
                            e3=round(e3, 3), e5=round(e5, 3),
                            overlap=overlap,
                            dead_line=round(P5, 2),
                            dead_note="收盘站上 %.0f 即“顶已成立”作废" % P5))
    out.sort(key=lambda x: -x["score"])
    return out


def fam_B(DT, C, H, L, piv, i0, i_top):
    """B 族：顶 = 浪3（浪4 进行中，之后还有浪5 创新高）

    约束：浪3 必须终止于最高点（否则顶部之后又创新高，浪3 就被证伪）
    """
    seg = [p for p in piv if i0 <= p[0] < i_top]
    Hs = [p for p in seg if p[2] == "H"]
    Ls = [p for p in seg if p[2] == "L"]
    L0 = min([p for p in piv if abs(p[0] - i0) < 90 and p[2] == "L"],
             key=lambda p: p[1], default=(i0, L[i0], "L"))
    low_now = min(L[i_top:])
    out = []
    for h1 in Hs:
        for l1 in Ls:
            if not (L0[0] < h1[0] < l1[0] < i_top):
                continue
            P0, P1, P2, P3, P4 = L0[1], h1[1], l1[1], H[i_top], low_now
            if P2 <= P0 or P3 <= P1:
                continue
            if P1 != max(H[L0[0]:l1[0] + 1]):
                continue
            if P2 != min(L[h1[0]:i_top + 1]):
                continue
            w1, w3 = P1 - P0, P3 - P2
            if w3 < w1:                       # 浪3 应长于浪1
                continue
            if P4 <= P1:                      # 浪4 重叠浪1 → 不成立
                continue
            r2 = (P1 - P2) / w1
            r4 = (P3 - P4) / w3
            if not (0.10 <= r4 <= 0.75):      # 浪4 回撤区间
                continue
            e3 = w3 / w1
            s_ = (0.30 * fib_score(r4, 0.236, 0.500) +
                  0.22 * fib_score(r2, 0.382, 0.618) +
                  0.24 * fib_score(e3, 1.618, 4.236) +
                  0.24 * fib_score(P4 / P1, 1.00, 1.60))
            out.append(dict(fam="B", score=round(s_, 3),
                            w1=dict(d=DT[h1[0]], p=round(P1, 2)),
                            w2=dict(d=DT[l1[0]], p=round(P2, 2)),
                            w3=dict(d=DT[i_top], p=round(P3, 2)),
                            w4=dict(d=DT[min(range(i_top, len(L)), key=lambda i: L[i])],
                                    p=round(P4, 2)),
                            r2=round(r2, 3), r4=round(r4, 3), e3=round(e3, 3),
                            dead_line=round(P1, 2),
                            w5_target=round(P3 + w1 * 0.618, 0),
                            dead_note="收盘跌破 %.0f（浪1 顶）即浪4 作废" % P1))
    out.sort(key=lambda x: -x["score"])
    return out


def post_top(DT, C, H, L, i_top):
    ia = min(range(i_top, len(C)), key=lambda i: L[i])
    ib = max(range(ia, len(C)), key=lambda i: H[i])
    Ptop, Pa, Pb, cur = H[i_top], L[ia], H[ib], C[-1]
    retr_b = (Pb - Pa) / (Ptop - Pa)
    a_drop = Ptop - Pa
    return dict(top=dict(d=DT[i_top], p=round(Ptop, 2)),
                A=dict(d=DT[ia], p=round(Pa, 2)),
                B=dict(d=DT[ib], p=round(Pb, 2)),
                retr_B=round(retr_b, 3),
                C_over_A=round((Pb - cur) / a_drop, 3),
                c_targets={str(k): round(Pb - a_drop * k, 1)
                           for k in (0.618, 1.0, 1.272, 1.618)},
                cur=round(cur, 2))


def main():
    DT, C, H, L = load()
    i_now = len(C) - 1
    s = next(i for i, d in enumerate(DT) if d >= "2015-10-01")
    e = next(i for i, d in enumerate(DT) if d >= "2026-02-15")
    i0 = min(range(s, e), key=lambda i: L[i])
    i_top = max(range(s, i_now), key=lambda i: H[i])
    thr = 0.08
    piv = zigzag(H, L, thr)
    lines = []

    def P(x=""):
        lines.append(x)
        print(x)

    P("=" * 80)
    P("波浪结构模型 v2 · %s · 收盘 %.2f" % (DT[-1], C[-1]))
    P("=" * 80)
    P("本轮起点 %s %.2f｜本轮顶 %s %.2f｜当前距顶 %.1f%%"
      % (DT[i0], L[i0], DT[i_top], H[i_top], (C[-1] / H[i_top] - 1) * 100))
    P("摆动点 %d 个（阈值 %.0f%%）" % (len(piv), thr * 100))
    P()

    A = fam_A(DT, C, H, L, piv, i0, i_top)
    B = fam_B(DT, C, H, L, piv, i0, i_top)
    P("A 族（顶=浪5，已走完）合法标注 %d 个｜B 族（顶=浪3，浪4 进行中）%d 个" % (len(A), len(B)))
    P()

    for name, lst in (("A 族 · 顶 = 浪5，现在走 ABC", A), ("B 族 · 顶 = 浪3，现在走浪4", B)):
        P("-" * 80)
        P(name)
        P("-" * 80)
        if not lst:
            P("  无合法标注")
            P()
            continue
        for i, c in enumerate(lst[:3], 1):
            if c["fam"] == "A":
                P("  #%d 评分 %.3f  %s 起点 → ①%.0f(%s) → ②%.0f(%s) → ③%.0f(%s) → ④%.0f(%s) → ⑤%.0f(%s)"
                  % (i, c["score"], "%.0f" % L[i0],
                     c["w1"]["p"], c["w1"]["d"][2:], c["w2"]["p"], c["w2"]["d"][2:],
                     c["w3"]["p"], c["w3"]["d"][2:], c["w4"]["p"], c["w4"]["d"][2:],
                     c["top"]["p"], c["top"]["d"][2:]))
                P("      ②回撤 %.0f%% ④回撤 %.0f%%｜浪3 = %.2f×浪1｜浪5 = %.2f×浪3｜④重叠①:%s"
                  % (c["r2"] * 100, c["r4"] * 100, c["e3"], c["e5"],
                     "是" if c["overlap"] else "否"))
            else:
                P("  #%d 评分 %.3f  %s 起点 → ①%.0f(%s) → ②%.0f(%s) → ③%.0f(%s) → ④进行中 %.0f"
                  % (i, c["score"], "%.0f" % L[i0],
                     c["w1"]["p"], c["w1"]["d"][2:], c["w2"]["p"], c["w2"]["d"][2:],
                     c["w3"]["p"], c["w3"]["d"][2:], c["w4"]["p"]))
                P("      ②回撤 %.0f%% ④回撤 %.0f%%｜浪3 = %.2f×浪1｜浪4 距浪1顶 %.0f%%｜浪5 目标 ≈%.0f"
                  % (c["r2"] * 100, c["r4"] * 100, c["e3"],
                     (c["w4"]["p"] / c["w1"]["p"] - 1) * 100, c["w5_target"]))
        P("  失效条件：%s" % lst[0]["dead_note"])
        P()

    pt = post_top(DT, C, H, L, i_top)
    P("-" * 80)
    P("顶部之后（ABC）")
    P("-" * 80)
    P("  顶 %s %.0f → A %s %.0f → B %s %.0f"
      % (pt["top"]["d"], pt["top"]["p"], pt["A"]["d"], pt["A"]["p"], pt["B"]["d"], pt["B"]["p"]))
    P("  B 回撤 A 的 %.1f%%（理想 38-62%%）｜当前 C/A = %.2f" % (pt["retr_B"] * 100, pt["C_over_A"]))
    P("  C = k×A 目标：" + "｜".join("%s→%.0f" % (k, v) for k, v in pt["c_targets"].items()))
    P()

    # 归一化概率
    sa = A[0]["score"] if A else 0
    sb = B[0]["score"] if B else 0
    tot = sa + sb or 1
    P("-" * 80)
    P("两个假设的相对权重")
    P("-" * 80)
    P("  A（顶已成立，现在 ABC）  %.1f%%" % (sa / tot * 100))
    P("  B（顶只是浪3，还有浪5）  %.1f%%" % (sb / tot * 100))
    P()

    D = i_top - i0
    P("-" * 80)
    P("时间窗（起点→顶 %d 个交易日 = %.1f 年）" % (D, D / 252))
    P("-" * 80)
    for k in (0.382, 0.5, 0.618, 1.0):
        j = i_top + int(D * k)
        if j <= i_now:
            P("  %.3f× → %s（已过）" % (k, DT[j]))
        else:
            ed = date.fromisoformat(DT[-1]) + timedelta(days=int((j - i_now) * 1.45))
            P("  %.3f× → 约 %s（还有 %d 个交易日）" % (k, ed.isoformat(), j - i_now))
    P()

    P("-" * 80)
    P("结论")
    P("-" * 80)
    if A:
        P("  A 族最可能标注：⑤ = %.0f（%s），失效价 %.0f"
          % (A[0]["top"]["p"], A[0]["top"]["d"], A[0]["dead_line"]))
    if B:
        P("  B 族最可能标注：④ 底 = %.0f，失效价 %.0f（跌破即否），浪5 目标 ≈%.0f"
          % (B[0]["w4"]["p"], B[0]["dead_line"], B[0]["w5_target"]))
    P("  两条路的分水岭：%.0f。站上 → A 族作废；跌破 %.0f → B 族作废"
      % (A[0]["dead_line"] if A else 0, B[0]["dead_line"] if B else 0))
    P()
    P("-" * 80)
    P("关键价位（分级失效）")
    P("-" * 80)
    if B:
        p2, p3, p1 = B[0]["w2"]["p"], B[0]["w3"]["p"], B[0]["w1"]["p"]
        lv50 = p3 - (p3 - p2) * 0.5
        lv618 = p3 - (p3 - p2) * 0.618
        P("  B 族（浪4 进行中）")
        P("    跌破 %.0f（浪3 的 50%% 回撤）→ 开始吃力，浪4 偏深" % lv50)
        P("    跌破 %.0f（61.8%% 回撤）→ 基本否掉，改按 A 族处理" % lv618)
        P("    跌破 %.0f（浪1 顶）→ 彻底作废" % p1)
    if A:
        P("  A 族（顶已成立，走 ABC）")
        P("    站上 %.0f（B 浪顶）→ ABC 结构需重估，可能还有一段上冲" % pt["B"]["p"])
        P("    站上 %.0f（历史顶）→ A 族彻底作废" % A[0]["dead_line"])

    json.dump(dict(date=DT[-1], close=C[-1], weight_A=round(sa / tot, 3),
                   weight_B=round(sb / tot, 3),
                   fam_A=A[:5], fam_B=B[:5], post_top=pt),
              open(os.path.join(BASE, "wave_candidates.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(os.path.join(BASE, "wave_report.txt"), "w", encoding="utf-8").write("\n".join(lines))
    # 每日留痕（用于日后检验模型给过的候选）
    import csv
    log = os.path.join(BASE, "wave_log.csv")
    new_file = not os.path.exists(log)
    with open(log, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["date", "close", "wA", "wB", "A_score", "B_score",
                        "A_dead", "B_dead", "C_tgt_0618", "C_tgt_100", "w5_target"])
        w.writerow([DT[-1], round(C[-1], 2), round(sa / tot, 3), round(sb / tot, 3),
                    A[0]["score"] if A else "", B[0]["score"] if B else "",
                    A[0]["dead_line"] if A else "", B[0]["dead_line"] if B else "",
                    pt["c_targets"]["0.618"], pt["c_targets"]["1.0"],
                    B[0]["w5_target"] if B else ""])
    print("\n已写出 wave/wave_candidates.json、wave/wave_report.txt、wave/wave_log.csv")


if __name__ == "__main__":
    main()
