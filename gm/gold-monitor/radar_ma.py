#!/usr/bin/env python3
"""均线防守线：MA20 / MA60 状态 + 牛市模式所需的"破位天数/收回"字段"""
import json, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open("data_full.json", encoding="utf-8"))
bars = D["kline"]
au = {a["d"]: a for a in D["au"]}
c = [b["c"] for b in bars]
N = len(bars)
# 只用伦敦金价格，不必等沪金当日数据；取最后一根 bar（盘中则取当前价）
i = N - 1

ma20 = [None] * N
ma60 = [None] * N
for k in range(19, N):
    ma20[k] = sum(c[k - 19:k + 1]) / 20
for k in range(59, N):
    ma60[k] = sum(c[k - 59:k + 1]) / 60

close = c[i]


def below_days(ma):
    """当前连续收盘低于该均线的交易日数（0 = 今天在上方）"""
    if not ma[i] or close >= ma[i]:
        return 0
    k = i
    while k > 0 and ma[k] and c[k] < ma[k]:
        k -= 1
    return i - k


def last_break(ma):
    """最近一次从上方跌破的索引（找不到返回 None）"""
    for k in range(i, 60, -1):
        if ma[k] and ma[k - 1] and c[k - 1] >= ma[k - 1] and c[k] < ma[k]:
            return k
    return None


def last_reclaim(ma):
    """最近一次从下方收回的索引"""
    for k in range(i, 20, -1):
        if ma[k] and ma[k - 1] and c[k - 1] <= ma[k - 1] and c[k] > ma[k]:
            return k
    return None


b20 = below_days(ma20)
b60 = below_days(ma60)
lb20 = last_break(ma20)
lb60 = last_break(ma60)
lr20 = last_reclaim(ma20)

gap20 = (close / ma20[i] - 1) * 100 if ma20[i] else None
gap60 = (close / ma60[i] - 1) * 100 if ma60[i] else None

# 120 日区间位置：MA20 减仓的高位过滤（≥70% 才提示）
lo = max(0, i - 119)
lows = [b["l"] for b in bars[lo:i + 1]]
highs = [b["h"] for b in bars[lo:i + 1]]
mn, mx = min(lows), max(highs)
pos120 = (close - mn) / (mx - mn) * 100 if mx > mn else 0
HIGH_POS = 70.0
high_pos = bool(pos120 >= HIGH_POS)

# 牛市回补：今天在 MA20 上方，且最近一次跌破发生在 10 个交易日内
reclaim20 = bool(
    b20 == 0 and lb20 is not None and (i - lb20) <= 10 and gap60 is not None and gap60 > -1.5
)
# 牛市浅破：今天在 MA60 下方，但幅度 <1.5%
shallow60 = bool(b60 > 0 and gap60 is not None and abs(gap60) < 1.5)

# ---------- 破位分层：环境（MA200）× 位置（距 250 日高） ----------
ma200 = [None] * N
for k in range(199, N):
    ma200[k] = sum(c[k - 199:k + 1]) / 200
_slope200 = (ma200[i] / ma200[i - 20] - 1) * 100 if (ma200[i] and i - 20 >= 199 and ma200[i - 20]) else None
if _slope200 is None or ma200[i] is None:
    env = "过渡"
elif close > ma200[i] and _slope200 > 0:
    env = "牛"
elif close < ma200[i] and _slope200 < 0:
    env = "熊"
else:
    env = "过渡"

hi250 = max(b["h"] for b in bars[max(0, i - 249):i + 1])
pos250 = (close / hi250 - 1) * 100 if hi250 else None
if pos250 is None:
    zone = "中"
elif pos250 > -10:
    zone = "高"
elif pos250 > -25:
    zone = "中"
else:
    zone = "低"

# 逃顶阈值：从 250 日高回撤 8%（2006-2026 五个大顶平均回撤 8-10% 才该动，只展示不推送）
DD8 = 8.0
dd8 = bool(pos250 is not None and pos250 <= -DD8)
dd8_days = 0
if dd8:
    k = i
    while k > 0 and i - k < 250:
        hh = max(b["h"] for b in bars[max(0, k - 249):k + 1])
        if (c[k] / hh - 1) * 100 <= -DD8:
            k -= 1
        else:
            break
    dd8_days = i - k

# 破位动作：牛+高=不动（洗盘）｜过渡=清仓（反转确认）｜其余=减半
if not (ma60[i] and close < ma60[i]):
    ma60_action = "守住"
elif env == "牛" and zone == "高":
    ma60_action = "不动"
elif env == "过渡":
    ma60_action = "清仓"
else:
    ma60_action = "减半"

try:
    top = json.load(open("radar_top.json", encoding="utf-8"))
except Exception:
    top = {}
lt = top.get("last_top3") or {}
recent_top = bool(lt.get("days_ago") is not None and lt["days_ago"] <= 10)

out = {
    "date": bars[i]["d"], "close": round(close, 2),
    "ma20": round(ma20[i], 2), "ma60": round(ma60[i], 2),
    "below20": bool(close < ma20[i]), "below60": bool(close < ma60[i]),
    "pos120": round(pos120, 1), "highPos": high_pos, "highPosThr": HIGH_POS,
    # 高位破 MA20 才是减仓信号；低位破 MA20 只记录、不报警
    "high20break": bool(close < ma20[i] and high_pos),
    "low20break": bool(close < ma20[i] and not high_pos),
    "gap20": round(gap20, 2) if gap20 is not None else None,
    "gap60": round(gap60, 2) if gap60 is not None else None,
    "below20_days": b20, "below60_days": b60,
    "last_break20": bars[lb20]["d"] if lb20 else None,
    "last_break60": bars[lb60]["d"] if lb60 else None,
    "days_since_break20": (i - lb20) if lb20 else None,
    "reclaim20": reclaim20,
    "reclaim20_date": bars[lb20]["d"] if reclaim20 and lb20 else None,
    "shallow60": shallow60,
    "ma200": round(ma200[i], 2) if ma200[i] else None,
    "ma200_slope20": round(_slope200, 2) if _slope200 is not None else None,
    "hi250": round(hi250, 2) if hi250 else None,
    "pos250": round(pos250, 1) if pos250 is not None else None,
    "dd8": dd8, "dd8_days": dd8_days, "dd8_thr": DD8,
    "env": env, "zone": zone, "ma60_action": ma60_action,
    "last_top3": lt, "recent_top3": recent_top,
    "ultimate": bool(recent_top and close < ma20[i]),
}
json.dump(out, open("radar_ma.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
