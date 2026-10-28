#!/usr/bin/env python3
"""波浪结构模型 · 可复用库（供敏感性测试 / 多品种验证调用）

与 wave_model.py 的区别：
  · 阈值 thr 可配置
  · 可指定“快照日”（只用当时可见的数据，避免未来函数）
  · 自动识别当前周期（最高点 + 其前方的最低点）
"""
import json, os, itertools

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)


def load_gold():
    d = json.load(open(os.path.join(ROOT, "data_full.json"), encoding="utf-8"))
    k = d["kline"]
    return ([x["d"] for x in k], [x["c"] for x in k], [x["h"] for x in k], [x["l"] for x in k])


def load_sina_index(symbol="sh000001", n=3000):
    """新浪 A 股指数日线"""
    import urllib.request, json as js
    url = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
           "CN_MarketData.getKLineData?symbol=%s&scale=240&ma=no&datalen=%d" % (symbol, n))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Referer": "https://finance.sina.com.cn"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    arr = js.loads(raw)
    return ([x["day"] for x in arr], [float(x["close"]) for x in arr],
            [float(x["high"]) for x in arr], [float(x["low"]) for x in arr])


def load_sina_futures(symbol="CL"):
    """新浪外盘期货日线（CL=WTI 原油, GC=COMEX 黄金）"""
    import urllib.request, re, json as js
    url = ("https://stock.finance.sina.com.cn/futures/api/jsonp.php/var%%20_%s=/"
           "GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=%s" % (symbol, symbol))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Referer": "https://finance.sina.com.cn"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    m = re.search(r"=\((\[.*\])\)", raw, re.S)
    arr = js.loads(m.group(1))
    arr = [x for x in arr if float(x["close"]) > 0]
    return ([x["date"] for x in arr], [float(x["close"]) for x in arr],
            [float(x["high"]) for x in arr], [float(x["low"]) for x in arr])


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
    if ext_i is not None:
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


def detect_cycle(H, L, i_snap, lookback=3000):
    i_top = max(range(i_snap + 1), key=lambda i: H[i])
    i0 = min(range(max(0, i_top - lookback), i_top + 1), key=lambda i: L[i])
    return i0, i_top


def fam_A(DT, C, H, L, i0, i_top, thr):
    piv = zigzag(H[:i_top + 1], L[:i_top + 1], thr)
    seg = [p for p in piv if i0 <= p[0] <= i_top]
    Hs = [p for p in seg if p[2] == "H"]
    Ls = [p for p in seg if p[2] == "L"]
    L0 = (i0, L[i0], "L")
    out = []
    for h1, h2 in itertools.combinations(Hs, 2):
        for l1, l2 in itertools.combinations(Ls, 2):
            if not (i0 < h1[0] < l1[0] < h2[0] < l2[0] < i_top):
                continue
            P0, P1, P2, P3, P4, P5 = L0[1], h1[1], l1[1], h2[1], l2[1], H[i_top]
            if P2 <= P0 or P3 <= P1:
                continue
            if P1 != max(H[i0:l1[0] + 1]) or P3 != max(H[l1[0]:l2[0] + 1]):
                continue
            if P2 != min(L[h1[0]:h2[0] + 1]):
                continue
            w1, w3, w5 = P1 - P0, P3 - P2, P5 - P4
            if w3 <= min(w1, w5):
                continue
            r2, r4 = (P1 - P2) / w1, (P3 - P4) / (P3 - P2)
            e3, e5 = w3 / w1, w5 / w3
            if e5 > 1.618:
                continue
            d2, d4 = max(1, l1[0] - h1[0]), max(1, l2[0] - h2[0])
            if d4 < 8 and r4 < 0.236:
                continue
            overlap = P4 <= P1
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
                            e3=round(e3, 3), e5=round(e5, 3)))
    out.sort(key=lambda x: -x["score"])
    return out


def fam_B(DT, C, H, L, i0, i_top, thr, i_snap):
    piv = zigzag(H[:i_snap + 1], L[:i_snap + 1], thr)
    seg = [p for p in piv if i0 <= p[0] < i_top]
    Hs = [p for p in seg if p[2] == "H"]
    Ls = [p for p in seg if p[2] == "L"]
    L0 = (i0, L[i0], "L")
    low_now = min(L[i_top:i_snap + 1])
    out = []
    for h1 in Hs:
        for l1 in Ls:
            if not (i0 < h1[0] < l1[0] < i_top):
                continue
            P0, P1, P2, P3, P4 = L0[1], h1[1], l1[1], H[i_top], low_now
            if P2 <= P0 or P3 <= P1:
                continue
            if P1 != max(H[i0:l1[0] + 1]) or P2 != min(L[h1[0]:i_top + 1]):
                continue
            w1, w3 = P1 - P0, P3 - P2
            if w3 < w1 or P4 <= P1:
                continue
            r2, r4 = (P1 - P2) / w1, (P3 - P4) / w3
            if not (0.10 <= r4 <= 0.75):
                continue
            e3 = w3 / w1
            s = (0.30 * fib_score(r4, 0.236, 0.500) +
                 0.22 * fib_score(r2, 0.382, 0.618) +
                 0.24 * fib_score(e3, 1.618, 4.236) +
                 0.24 * fib_score(P4 / P1, 1.00, 1.60))
            out.append(dict(fam="B", score=round(s, 3),
                            w1=dict(d=DT[h1[0]], p=round(P1, 2)),
                            w2=dict(d=DT[l1[0]], p=round(P2, 2)),
                            w3=dict(d=DT[i_top], p=round(P3, 2)),
                            w4=dict(d=DT[min(range(i_top, i_snap + 1), key=lambda i: L[i])],
                                    p=round(P4, 2)),
                            r2=round(r2, 3), r4=round(r4, 3), e3=round(e3, 3),
                            w5_target=round(P3 + w1 * 0.618, 0)))
    out.sort(key=lambda x: -x["score"])
    return out


def analyze(DT, C, H, L, i_snap=None, thr=0.08):
    i_snap = len(C) - 1 if i_snap is None else i_snap
    i0, i_top = detect_cycle(H, L, i_snap)
    A = fam_A(DT, C, H, L, i0, i_top, thr)
    B = fam_B(DT, C, H, L, i0, i_top, thr, i_snap)
    sa = A[0]["score"] if A else 0
    sb = B[0]["score"] if B else 0
    tot = sa + sb
    return dict(date=DT[i_snap], close=C[i_snap],
                start=dict(d=DT[i0], p=L[i0]), top=dict(d=DT[i_top], p=H[i_top]),
                nA=len(A), nB=len(B), sa=sa, sb=sb,
                wA=round(sa / tot, 3) if tot else None,
                wB=round(sb / tot, 3) if tot else None,
                A=A[0] if A else None, B=B[0] if B else None,
                low_after=min(L[i_top:i_snap + 1]))
