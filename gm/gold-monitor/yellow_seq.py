#!/usr/bin/env python3
"""黄灯「第几次」分层回测 + 页面用轮次状态
口径：
  · 黄灯 = 磨底雷达 >=3 分 且 空间达标（60日位置<=20% 或 破布林下轨）
  · 两个黄灯日间隔 >=10 个交易日 才算新的一次（连续亮/隔天闪烁算同一次）
  · 连续 10 个交易日收盘站上 MA60 → 视为趋势修复，轮次计数清零
说明：轮次扫描覆盖到最新交易日（hits_all）；收益统计只取 T+20 已走完的样本（rows）。
输出 yellow_seq.json 供 build_page.py 注入页面
"""
import json, os, io, contextlib, importlib.util, statistics as st

os.chdir(os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    spec = importlib.util.spec_from_file_location("rr", "radar.py")
    rr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rr)

D = json.load(open("data_full.json", encoding="utf-8"))
bars = D["kline"]
closes = [b["c"] for b in bars]
lows = [b["l"] for b in bars]
highs = [b["h"] for b in bars]
def atr_at(k, n=14):
    if k < n: return None
    tot = 0.0
    for j in range(k-n+1, k+1):
        pc = closes[j-1]
        tot += max(highs[j]-lows[j], abs(highs[j]-pc), abs(lows[j]-pc))
    return tot/n
N = len(bars)

ma60 = [None] * N
for k in range(59, N):
    ma60[k] = sum(closes[k - 59:k + 1]) / 60

GAP = 10          # 间隔多少个交易日算新一次
HOLD = 10         # 连续多少日站上 MA60 视为趋势修复

i0 = next(k for k in range(N) if bars[k]["d"] >= "2011-01-01")

# ---------- 1) 全量扫描（含最近三周）----------
hits_all, last = [], -999
for k in range(max(i0, 60), N):
    r = rr.radar(k)
    if r["score"] >= 3 and r["space"]["ok"]:
        if k - last >= GAP:
            hits_all.append(k)
            last = k

# ---------- 2) 趋势修复重置点 ----------
reclaim = [False] * N
for k in range(59, N):
    if k - 9 >= 59 and all(closes[j] > ma60[j] for j in range(k - 9, k + 1)):
        reclaim[k] = True

def last_reclaim_between(a, b):
    """(b, a) 区间内最近一次修复点（不含端点 a），无则 None"""
    return next((j for j in range(a - 1, b, -1) if reclaim[j]), None)

# ---------- 3) 给全部事件打序号 ----------
seqs, seq, prev_e = {}, 1, None
for k in hits_all:
    if prev_e is not None:
        seq = 1 if last_reclaim_between(k, prev_e) is not None else seq + 1
    seqs[k] = seq
    prev_e = k

# ---------- 4) 只对 T+20 已走完的样本做收益统计 ----------
rows = []
for k in hits_all:
    if k > N - 22:
        continue
    gap = (closes[k] / ma60[k] - 1) * 100
    f = {n: round((closes[min(k + n, N - 1)] / closes[k] - 1) * 100, 2) for n in (5, 10, 20)}
    path = [closes[j] for j in range(k, min(N, k + 21))]
    rows.append({"date": bars[k]["d"], "seq": seqs[k], "close": round(closes[k], 2),
                 "gap": round(gap, 2), "deep": gap <= -4.0,
                 **{f"r{n}": v for n, v in f.items()},
                 "mdd": round((min(path) / closes[k] - 1) * 100, 2)})

def stat(s):
    if not s:
        return {"n": 0}
    o = {"n": len(s)}
    for n in (5, 10, 20):
        k = f"r{n}"
        o[f"w{n}"] = round(sum(1 for x in s if x[k] > 0) / len(s) * 100, 1)
        o[f"a{n}"] = round(st.mean([x[k] for x in s]), 2)
    o["mdd"] = round(st.mean([x["mdd"] for x in s]), 2)
    o["mdd_w"] = round(min(x["mdd"] for x in s), 2)
    return o

groups = {str(s_): stat([x for x in rows if x["seq"] == s_]) for s_ in (1, 2, 3)}
groups["4+"] = stat([x for x in rows if x["seq"] >= 4])
deep_first = stat([x for x in rows if x["seq"] == 1 and x["deep"]])

# ---------- 5) 当前状态 ----------
cur_r = rr.radar(N - 1)
cur_gap = (closes[-1] / ma60[-1] - 1) * 100
lit_now = bool(cur_r["score"] >= 3 and cur_r["space"]["ok"])
last_k = hits_all[-1]
last_seq = seqs[last_k]
since = N - 1 - last_k

if lit_now:
    if since < GAP:
        cur_seq = last_seq              # 仍在冷却窗口内，算同一轮的同一次
    elif (N - 1) in seqs:
        cur_seq = seqs[N - 1]
    else:
        r_ = last_reclaim_between(N - 1, last_k)
        cur_seq = 1 if r_ is not None else last_seq + 1
    next_seq = cur_seq
else:
    if since < GAP:
        next_seq = last_seq              # 仍在本轮冷却窗口内，再亮算同一轮
    else:
        r_ = last_reclaim_between(N - 1, last_k)
        next_seq = 1 if r_ is not None else last_seq + 1
    cur_seq = None

# ---------- 6) 踏空豁免：首灯后 20 日没等到二灯，且 MA20 上穿 MA60 ----------
ma20 = [None] * N
for k in range(19, N):
    ma20[k] = sum(closes[k - 19:k + 1]) / 20
EXEMPT_WAIT = 20

# 本轮是否已有首灯
has_first = bool((lit_now and (cur_seq or 0) >= 1) or ((not lit_now) and next_seq > 1))
first_k, round_ev = None, 0
if has_first:
    for k in reversed(hits_all):
        if seqs[k] == 1:
            first_k = k
            round_ev = 1
            break
        round_ev += 1

gold_k = None
if first_k is not None:
    for k in range(first_k + 1, N):
        if ma20[k] and ma60[k] and ma20[k] > ma60[k] and ma20[k - 1] <= ma60[k - 1]:
            gold_k = k
            break

days_since_first = (N - 1 - first_k) if first_k is not None else None
exempt = bool(first_k is not None and round_ev == 1 and days_since_first >= EXEMPT_WAIT
              and gold_k is not None)

out = {
    "events": rows,
    "groups": groups,
    "deepFirst": deep_first,
    "params": {"gap": GAP, "hold": HOLD},
    "cur": {
        "date": bars[-1]["d"], "close": round(closes[-1], 2),
        "ma60": round(ma60[-1], 2), "gap": round(cur_gap, 2),
        "score": cur_r["score"], "space": bool(cur_r["space"]["ok"]),
        "lit": bool(lit_now), "curSeq": cur_seq, "nextSeq": next_seq,
        "lastDate": bars[last_k]["d"], "lastSeq": last_seq,
        "sinceDays": since, "deep": cur_gap <= -4.0,
        "firstDate": bars[first_k]["d"] if first_k is not None else None,
        "firstLow": round(lows[first_k], 2) if first_k is not None else None,
        "firstClose": round(closes[first_k], 2) if first_k is not None else None,
        "firstATR": round(atr_at(first_k), 2) if (first_k is not None and atr_at(first_k)) else None,
        "stopLow": round(lows[first_k] - 2.0*atr_at(first_k), 2) if (first_k is not None and atr_at(first_k)) else None,
        "daysSinceFirst": days_since_first, "roundEvents": round_ev,
        "goldDate": bars[gold_k]["d"] if gold_k is not None else None,
        "goldGap": round((ma20[gold_k] / ma60[gold_k] - 1) * 100, 2) if gold_k is not None else None,
        "exempt": exempt, "exemptWait": EXEMPT_WAIT,
        "ma20": round(ma20[-1], 2) if ma20[-1] else None,
        "ma20Above60": bool(ma20[-1] and ma60[-1] and ma20[-1] > ma60[-1]),
    },
}
json.dump(out, open("yellow_seq.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print(f"黄灯事件 {len(rows)} 个（可统计）/ {len(hits_all)} 个（含最近）")
print(f"当前 {bars[-1]['d']} 分数 {cur_r['score']}/4 · 偏离MA60 {cur_gap:+.2f}% · "
      f"{'已亮灯 第%d次' % cur_seq if lit_now else '未亮灯'} · "
      f"下次亮灯=第{next_seq}次 · 上次 {bars[last_k]['d']}（第{last_seq}次，{since}个交易日前）\n")
for lbl in ("1", "2", "3", "4+"):
    g = groups[lbl]
    if not g["n"]:
        continue
    print(f"第{lbl}次: {g['n']:>2}个  +5胜{g['w5']:5.1f}%均{g['a5']:+6.2f}%  "
          f"+10胜{g['w10']:5.1f}%均{g['a10']:+6.2f}%  +20胜{g['w20']:5.1f}%均{g['a20']:+6.2f}%  "
          f"20日MDD均{g['mdd']:+6.2f}%")
print(f"\n深水首灯: {deep_first['n']}个  +5胜{deep_first['w5']:.1f}%  +10胜{deep_first['w10']:.1f}%  "
      f"+20胜{deep_first['w20']:.1f}% 20日均{deep_first['a20']:+.2f}%")
