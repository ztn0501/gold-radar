#!/usr/bin/env python3
import json
import os
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# data.json 由 fetch_full.py 生成。若不存在（例如直接解包后单独跑本脚本），
# 用 data_full.json 现场造一份，保证「只跑 build_page 也能出页面」。
if not os.path.exists("data.json"):
    _df = json.load(open("data_full.json", encoding="utf-8"))
    _k = _df.get("kline") or []
    _last = _k[-1] if _k else {"d": "", "o": 0, "h": 0, "l": 0, "c": 0}
    json.dump({"kline": _k[-400:], "au": (_df.get("au") or [])[-400:],
               "live": {"price": _last["c"], "prevClose": (_k[-2]["c"] if len(_k) > 1 else _last["c"]),
                        "open": _last["o"], "high": _last["h"], "low": _last["l"],
                        "time": "", "date": _last["d"], "_fallback": True},
               "auLive": None, "fx": 0, "fxTime": ""},
              open("data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("[warn] data.json 缺失，已用 data_full.json 生成兜底快照")
data = json.load(open("data.json", encoding="utf-8"))
try:
    data["signals"] = json.load(open("signals.json", encoding="utf-8"))
except Exception:
    data["signals"] = []
try:
    data["radar"] = json.load(open("radar.json", encoding="utf-8"))
except Exception:
    data["radar"] = []
try:
    data["top"] = json.load(open("radar_top.json", encoding="utf-8"))
except Exception:
    data["top"] = {}
try:
    data["tripleReview"] = json.load(open("triple_review.json", encoding="utf-8"))
except Exception:
    data["tripleReview"] = []
try:
    data["trailReview"] = json.load(open("trail_review.json", encoding="utf-8"))
except Exception:
    data["trailReview"] = []
try:
    data["topReview"] = json.load(open("top_review.json", encoding="utf-8"))
except Exception:
    data["topReview"] = []
try:
    data["stop"] = json.load(open("radar_stop.json", encoding="utf-8"))
except Exception:
    data["stop"] = {}
try:
    data["ma"] = json.load(open("radar_ma.json", encoding="utf-8"))
except Exception:
    data["ma"] = {}
try:
    data["intra"] = json.load(open("radar_intra.json", encoding="utf-8"))
except Exception:
    data["intra"] = {}
try:
    data["up"] = json.load(open("upgrade.json", encoding="utf-8"))
except Exception:
    data["up"] = {}
try:
    data["yseq"] = json.load(open("yellow_seq.json", encoding="utf-8"))
except Exception:
    data["yseq"] = {}
try:
    data["gld"] = json.load(open("gld_holdings.json", encoding="utf-8"))
except Exception:
    data["gld"] = {}
try:
    data["basis"] = json.load(open("comex_basis.json", encoding="utf-8"))
except Exception:
    data["basis"] = {}
try:
    data["wave"] = json.load(open("wave/wave_candidates.json", encoding="utf-8"))
except Exception:
    data["wave"] = {}
try:
    bt = json.load(open("backtest.json", encoding="utf-8"))
    data["bt"] = {k: bt[k] for k in ("crash","mo","novol","mo4","mo3s","counts","crash_rows","mo_rows","latest_crash") if k in bt}
except Exception:
    data["bt"] = {}
# ---------- 趋势状态 + 通道位置（只展示，不参与交易判定） ----------
try:
    _kd = json.load(open("data_full.json", encoding="utf-8"))
    _kb = _kd["kline"]
except Exception:
    _kb = []
if len(_kb) >= 130:
    _c = [x["c"] for x in _kb]; _h = [x["h"] for x in _kb]
    _l_ = [x["l"] for x in _kb]; _o = [x["o"] for x in _kb]
    _n = len(_c)
    def _ma_at(i, n):
        return sum(_c[i-n+1:i+1])/n if i >= n-1 else None
    _m20 = _ma_at(_n-1, 20); _m60 = _ma_at(_n-1, 60)
    _golden = bool(_m20 > _m60)
    _days = 0
    if _golden:
        for _i in range(_n-1, 59, -1):
            _a20 = _ma_at(_i, 20); _a60 = _ma_at(_i, 60)
            _b20 = _ma_at(_i-1, 20); _b60 = _ma_at(_i-1, 60)
            if _a20 and _a60 and _b20 and _b60 and _a20 > _a60 and _b20 <= _b60:
                _days = _n-1-_i
                break
        else:
            _days = -1
    _m60_prev = _ma_at(_n-41, 60) if _n >= 101 else None
    _slope_up = bool(_m60 and _m60_prev and _m60 > _m60_prev)
    _hi120 = max(_h[-121:-1]) if _n >= 121 else max(_h[:-1])
    _rng = max(_h[-1]-_l_[-1], 1e-9)
    _us = (_h[-1]-max(_o[-1], _c[-1]))/_rng*100
    _dist = (_c[-1]/_hi120-1)*100
    data["trend"] = {"ma20": round(_m20, 2), "ma60": round(_m60, 2),
                     "gap": round((_m20/_m60-1)*100, 2), "golden": _golden,
                     "days": _days, "slopeUp": _slope_up, "close": round(_c[-1], 2),
                     "slopePct": round((_m60/_m60_prev-1)*100, 2) if (_m60 and _m60_prev) else None,
                     "m60_3d": (round((_m60/_ma_at(_n-4, 60)-1)*100, 2) if (_m60 and _ma_at(_n-4, 60)) else None)}
    data["channel"] = {"hi120": round(_hi120, 2), "dist": round(_dist, 2),
                       "upperShadow": round(_us, 1),
                       "active": bool(_dist >= -2.0 and _us > 40)}
    # ---------- 波动率环境（2026-10-30 新增）：60 日均振幅 + 历史分位 ----------
    # 注意：磨底雷达四项本来都是相对量（位置百分位、量比、实体占振幅比），
    # 并不存在「3日涨6%」这类绝对阈值 —— 那是超买雷达的参数。
    # 但实测发现：低波动期四项通过率反而更高（动能 93% vs 75%），
    # 因为横盘时 MACD 天然萎缩、小实体 K 线天然连续，门槛被「低波动」本身喂饱。
    # 结果：1992-1998（振幅 0.80%）15 次信号胜率仅 33%，2018（0.9%）6 次里 5 次失败。
    # 分箱实测：<1.1% 胜率 47% / 1.1-1.3% 67% / 1.3-1.6% 82% / >1.6% 68%。
    # 结论：不是尺子的问题，是这批样本本身没有底 → 只标注、不改判定。
    _amps = []
    _win = 0.0
    for _j in range(_n):
        _win += (_h[_j] - _l_[_j]) / _c[_j] * 100
        if _j >= 60:
            _win -= (_h[_j-60] - _l_[_j-60]) / _c[_j-60] * 100
        if _j >= 59:
            _amps.append(_win / 60.0)
    _a0 = _amps[-1]
    _ah = sorted(_amps[180:]) if len(_amps) > 300 else sorted(_amps)
    _amed = _ah[len(_ah)//2]
    _apct = sum(1 for _x in _ah if _x < _a0) / len(_ah) * 100
    _agr = "low" if _a0 < 1.1 else ("mid" if _a0 < 1.3 else "high")
    # 样本不足 1000 天时不报分位（抓数失败会回退到包内的小样本，分位会失真）
    _ok_hist = len(_ah) >= 1000
    data["volenv"] = {"amp": round(_a0, 2),
                      "pct": (round(_apct) if _ok_hist else None),
                      "med": (round(_amed, 2) if _ok_hist else None),
                      "grade": _agr, "n": len(_ah)}
    # ---------- 偏离 MA200（2026-10-30 新增）：还有多少下跌空间 ----------
    # 依据：1992-2026 全样本，偏离 MA200 ≤ -10% 共 18 次（20 日去重）：
    # T+60 中位 +3.3%（67% 涨）、T+250 中位 +1.0%（50%），后续 250 日最低中位 -8.4%、最深 -20.7%。
    # 即短期偏反弹、一年后对半开；深度看的是「离历史极值还有多远」。
    _dev_s = []
    _m200_prev = None
    if _n >= 220:
        _s = sum(_c[:200]); _m200 = _s / 200
        for _j in range(200, _n):
            _s += _c[_j] - _c[_j - 200]
            _m200 = _s / 200
            _dev_s.append((_c[_j] / _m200 - 1) * 100)
            if _j == _n - 21: _m200_prev = _m200
        _d0 = _dev_s[-1]
        _ds = sorted(_dev_s[120:]) if len(_dev_s) > 500 else sorted(_dev_s)
        _dpct = sum(1 for _x in _ds if _x < _d0) / len(_ds) * 100
        _dmin = min(_dev_s)
        _m200_now = _m200
        _slope = ((_m200 / _m200_prev - 1) * 100) if _m200_prev else None
        _ok200 = len(_ds) >= 1000
        data["ma200env"] = {
            "dev": round(_d0, 1),
            "ma200": round(_m200_now, 1),
            "pct": (round(_dpct) if _ok200 else None),
            "slope": (round(_slope, 2) if _slope is not None else None),
            "min": (round(_dmin, 1) if _ok200 else None),
            "n": len(_ds),
            # 到历史极值还有多少（用极值偏离反推价位）
            "to_min": (round((_m200_now * (1 + _dmin / 100) / _c[-1] - 1) * 100, 1) if _ok200 else None),
            # 到 -15% / -20% 两个参照档
            "p15": (round((_m200_now * 0.85 / _c[-1] - 1) * 100, 1)),
            "p20": (round((_m200_now * 0.80 / _c[-1] - 1) * 100, 1)),
        }
else:
    data["trend"] = {}
    data["channel"] = {}

# ---------- 人民币视角（2026-10-30 新增）：汇率 + 元/克 ----------
# 起因：整个系统只看美元金价，而用户持的是人民币积存金。
# 人民币升值 1%，持仓被动 -1%，系统此前零计算。
# 实测（2026-10-30）：近 250 日美元金价 -2.30%，人民币金价 -8.55% —— 汇率多让 6.26 个点。
# 即「美元没怎么跌」和「我亏了不少」可以同时为真，两者差的就是汇率。
try:
    import bisect as _bs
    _raw = json.load(open("fx_hist.json", encoding="utf-8"))
    if isinstance(_raw, dict):                     # 紧凑格式 {"d":[...], "c":[...]}
        _fxr = [{"d": a, "c": b} for a, b in zip(_raw["d"], _raw["c"])]
    else:                                          # 旧格式 [{d,o,h,l,c}, ...]
        _fxr = _raw
    _fxd = [r["d"] for r in _fxr]
    _G = 31.1035

    def _fx_at(ds):
        i = _bs.bisect_right(_fxd, ds) - 1
        return _fxr[i]["c"] if i >= 0 else None

    if len(_kb) > 260 and _fxr:
        _c_arr = [x["c"] for x in _kb]
        _d_arr = [x["d"] for x in _kb]
        _fx_now = _fx_at(_d_arr[-1])
        _cny_now = _c_arr[-1] * _fx_now / _G
        # 区间分解：Δln(元/克) ≈ Δln(美元) + Δln(汇率)
        _rows = []
        def _row(label, i0):
            u0, u1 = _c_arr[i0], _c_arr[-1]
            f0, f1 = _fx_at(_d_arr[i0]), _fx_now
            du = (u1 / u0 - 1) * 100
            df = (f1 / f0 - 1) * 100
            dc = ((u1 * f1) / (u0 * f0) - 1) * 100
            return {"k": label, "usd": round(du, 2), "fx": round(df, 2),
                    "cny": round(dc, 2), "drag": round(dc - du, 2)}
        for _lbl, _n in (("20 日", 20), ("60 日", 60), ("250 日", 250)):
            if len(_c_arr) > _n:
                _rows.append(_row(_lbl, len(_c_arr) - 1 - _n))
        _hi_i = max(range(len(_kb)), key=lambda i: _kb[i]["h"])
        _pct_from_hi = (_c_arr[-1] / _kb[_hi_i]["h"] - 1) * 100
        _cny_from_hi = ((_c_arr[-1] * _fx_now) / (_kb[_hi_i]["h"] * _fx_at(_d_arr[_hi_i])) - 1) * 100
        _rows.append({"k": "2026 高点至今", "usd": round(_pct_from_hi, 2),
                      "fx": round((_fx_now / _fx_at(_d_arr[_hi_i]) - 1) * 100, 2),
                      "cny": round(_cny_from_hi, 2),
                      "drag": round(_cny_from_hi - _pct_from_hi, 2)})
        # 汇率位置：2005-07 汇改后才有浮动意义
        _post = [r["c"] for r in _fxr if r["d"] >= "2005-07-22"]
        _fpct = sum(1 for x in _post if x < _fx_now) / len(_post) * 100
        # 人民币金价（汇改后）历史最高与回撤
        _cny_hist = []
        for _i, _d in enumerate(_d_arr):
            if _d >= "2005-07-22":
                _f = _fx_at(_d)
                if _f:
                    _cny_hist.append(_c_arr[_i] * _f / _G)
        _cny_max = max(_cny_hist) if _cny_hist else None
        # 关键价位映射成元/克（用户按元/克下单）
        def _to_cny(usd):
            return round(usd * _fx_now / _G, 1) if usd else None
        _ma = data.get("ma") or {}
        _m2 = data.get("ma200env") or {}
        _lv = []
        # 参照低点：第 2 档的触发线必须锁死。
        # 若直接用 250 日窗口最低价，窗口每天滑动 → 触发价跟着价格跑：
        # 今天破了 3943，明天窗口最低就变成今天的低点，页面会显示「还没破」。
        # 所以第一次算出来后写进 ref_low.json，之后只读不改。
        _lo250 = min(_kb[-250:], key=lambda x: x["l"])
        _rl_path = "ref_low.json"
        try:
            _rl = json.load(open(_rl_path, encoding="utf-8"))
        except Exception:
            _rl = {}
        if not _rl.get("usd"):
            _rl = {"usd": round(_lo250["l"], 2), "d": _lo250["d"],
                   "note": "本轮参照低点，第 2 档触发线；锁定后不随 250 日窗口滑动"}
            json.dump(_rl, open(_rl_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        for _nm, _v in (("MA200", _m2.get("ma200")), ("MA60", _ma.get("ma60")),
                        ("MA20", _ma.get("ma20")),
                        ("参照低点", _rl.get("usd"))):
            if _v:
                # 参照低点保留 2 位：第 2 档要按它精确触发，不能四舍五入到 3943.7
                _d = 2 if _nm == "参照低点" else 1
                _lv.append({"n": _nm, "usd": round(_v, _d), "cny": _to_cny(_v),
                            "gap": round((_v / _c_arr[-1] - 1) * 100, 1)})
        data["fxenv"] = {
            "fx": round(_fx_now, 4),
            "cny": round(_cny_now, 2),
            "cnyHi": round(_cny_max, 1) if _cny_max else None,
            "cnyDD": round((_cny_now / _cny_max - 1) * 100, 1) if _cny_max else None,
            "pct": round(_fpct),
            "min": round(min(_post), 4), "max": round(max(_post), 4),
            "rows": _rows,
            # 人民币每动 1%，元/克动多少
            "sens": round(_cny_now * 0.01, 1),
            "levels": _lv,
            "refLow": {"usd": _rl.get("usd"), "d": _rl.get("d")},
        }
except Exception as _e:
    data["fxenv"] = {}
    print("[warn] 汇率环境计算失败：", _e)


# ── 宏观环境：美国 10 年期 TIPS 实际利率（2026-10-30）──────────────
# 黄金没有现金流，定价锚是扣除通胀后的实际利率。这是唯一一个既有可靠免费源、
# 又不依赖解读的宏观变量。实测 17 年：利率 60 日变化与金价 60 日收益相关仅 -0.03，
# 分箱统计因样本时段集中而不可用 —— 所以只做环境描述，不进任何买卖规则。
try:
    import bisect as _bis
    _M = json.load(open("macro_hist.json", encoding="utf-8"))
    _md, _mv = _M["d"], _M["v"]
    _kk = data["kline"]
    def _rat(ds):
        _i = _bis.bisect_right(_md, ds) - 1
        return _mv[_i] if _i >= 0 else None
    _s = [(b["d"], _rat(b["d"]), b["c"]) for b in _kk
          if b["d"] >= _md[0] and _rat(b["d"]) is not None]
    if len(_s) > 300:
        # 分位用 2010 以来全序列（4200+ 日），不是页面那 400 根
        _all = list(_mv)
        _cur = _mv[-1]
        _pct = sum(1 for x in _all if x < _cur) / len(_all) * 100
        _mx = max(_mv); _mxd = _md[_mv.index(_mx)]
        # 金价最高点当天的实际利率
        _full = data["kline"]
        try:
            _full = (json.load(open("data_full.json", encoding="utf-8")).get("kline") or _kk)
        except Exception:
            pass
        _hi = max(_full, key=lambda x: x["h"])
        _rh = _rat(_hi["d"]) or _cur
        # 利率自己见顶之后，金价动了多少
        _gp = None
        for b in reversed(_kk):
            if b["d"] <= _mxd:
                _gp = b["c"]; break
        data["macroenv"] = {
            "r": round(_cur, 2),
            "pct": round(_pct, 1),
            "min": round(min(_all), 2), "max": round(_mx, 2), "maxDate": _mxd,
            "d60": round((_mv[-1] - _mv[-61]) * 100),
            "d250": round((_mv[-1] - _mv[-251]) * 100) if len(_mv) > 251 else None,
            "n": len(_mv), "from": _md[0],
            # 金价见顶那一档利率 → 现在
            "peakDate": _hi["d"], "peakPx": round(_hi["h"], 1), "peakR": round(_rh, 2),
            "sincePeakBp": round((_cur - _rh) * 100),
            "sincePeakPx": round((_kk[-1]["c"] / _hi["h"] - 1) * 100, 1),
            # 利率自己见顶之后：利率回落多少、金价同期又跌了多少
            "rSinceTopBp": round((_cur - _mx) * 100),
            "pxSinceTop": round((_kk[-1]["c"] / _gp - 1) * 100, 1) if _gp else None,
            "pxAtTop": round(_gp, 1) if _gp else None,
            "hiShare": round(sum(1 for x in _all if x > 2.5) / len(_all) * 100, 1),
        }
    else:
        data["macroenv"] = {}
except Exception as _e:
    data["macroenv"] = {}
    print("[warn] 宏观环境计算失败：", _e)

# ── 风险温度：VIX（股市恐慌）/ GVZ（黄金恐慌）（2026-10-30）────────
# 目的是回答「这次下跌是不是恐慌」，不是产生信号。实测（见交接书三之八）：
#   · VIX 分档与金价后续收益无单调关系（<14 档 49%、>30 档 54%、20-30 档 62%）
#   · GVZ>30 的 126 天聚类后只有 9 段，T+60 胜率 56% ≈ 基准 60%，原先算出的 28% 是伪样本
#   · GVZ/VIX 比值从 1.1 到 1.6 逐个测，胜率 41→50→54→44→30→42→40→55→54，不单调，1.30 是噪声低点
# 所以这里只做两件事：量「恐慌有多强」和「恐慌是黄金专属还是全市场」。
try:
    _R = json.load(open("risk_hist.json", encoding="utf-8"))
    _pair = [(d, v, g) for d, v, g in zip(_R["d"], _R["vix"], _R["gvz"]) if v and g]
    if len(_pair) > 1000:
        import bisect as _b2
        _vs = sorted(x[1] for x in _pair)
        _gs = sorted(x[2] for x in _pair)
        _cv, _cg = float(_pair[-1][1]), float(_pair[-1][2])

        def _pc(arr, x):
            return round(_b2.bisect_left(arr, x) / len(arr) * 100, 1)

        _i20 = max(len(_pair) - 21, 0)
        data["riskenv"] = {
            "vix": round(_cv, 2), "vixPct": _pc(_vs, _cv),
            "gvz": round(_cg, 2), "gvzPct": _pc(_gs, _cg),
            "ratio": round(_cg / _cv, 2),
            "ratio20": round(_pair[_i20][2] / _pair[_i20][1], 2),
            "gvz20": round(_cg - _pair[_i20][2], 2),
            "vix20": round(_cv - _pair[_i20][1], 2),
            # 历史上「黄金恐慌明显高于股市」的天数占比，用来判断当下是否异常
            "goldOnly": round(sum(1 for _, v, g in _pair if g > 1.3 * v) / len(_pair) * 100, 1),
            "vixMin": round(_vs[0], 2), "vixMax": round(_vs[-1], 2),
            "gvzMin": round(_gs[0], 2), "gvzMax": round(_gs[-1], 2),
            "n": len(_pair), "from": _pair[0][0], "to": _pair[-1][0],
        }
    else:
        data["riskenv"] = {}
except Exception as _e:
    data["riskenv"] = {}
    print("[warn] 风险温度计算失败：", _e)

# 数据自检结果（2026-10-30）：validate.py 产出，页面顶部显示，fail 时红字警示
try:
    data["validation"] = json.load(open("validation.json", encoding="utf-8"))
except Exception:
    data["validation"] = {}

payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
# 波动率环境单独落一份，给 gha/notify.py 拼推送文案用（2026-10-30）
try:
    if data.get("volenv"):
        json.dump(data["volenv"], open("volenv.json", "w", encoding="utf-8"), ensure_ascii=False)
    if data.get("ma200env"):
        json.dump(data["ma200env"], open("ma200env.json", "w", encoding="utf-8"), ensure_ascii=False)
    if data.get("fxenv"):
        json.dump(data["fxenv"], open("fxenv.json", "w", encoding="utf-8"), ensure_ascii=False)
    if data.get("macroenv"):
        json.dump(data["macroenv"], open("macroenv.json", "w", encoding="utf-8"), ensure_ascii=False)
    if data.get("riskenv"):
        json.dump(data["riskenv"], open("riskenv.json", "w", encoding="utf-8"), ensure_ascii=False)
except Exception:
    pass

html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>黄金盯盘台 · XAU/USD</title>
<style>
:root{
  --bg:#0d1117; --panel:#161b22; --line:#232a34; --txt:#e6edf3; --dim:#8b949e;
  --up:#f0524d; --down:#26a69a; --gold:#d4a017; --accent:#c9a227;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:-apple-system,"SF Pro SC","PingFang SC","Microsoft YaHei",sans-serif;padding:18px 20px 40px}
.wrap{max-width:1180px;margin:0 auto}
.top{display:flex;align-items:flex-end;gap:18px;flex-wrap:wrap;margin-bottom:6px}
h1{font-size:17px;font-weight:600;letter-spacing:.5px;color:var(--dim)}
.badge{font-size:11px;color:var(--accent);border:1px solid #3a3220;background:#1e1a0f;padding:2px 8px;border-radius:10px}
.price-row{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin:10px 0 4px}
.price{font-size:46px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-1px}
.chg{font-size:19px;font-weight:600;font-variant-numeric:tabular-nums}
.meta{font-size:12px;color:var(--dim);display:flex;gap:16px;flex-wrap:wrap;margin-bottom:14px}
.meta b{color:#c9d1d9;font-weight:500}
.refbar{display:flex;align-items:center;gap:9px;flex-wrap:wrap;font-size:11.5px;
  padding:8px 11px;border-radius:7px;margin:-4px 0 14px;
  border:1px solid #2b3440;background:#0f141b;color:#9aa4b2;line-height:1.6}
.refbar .rb-t{font-weight:600;letter-spacing:.2px}
.refbar .rb-n{font-variant-numeric:tabular-nums;font-weight:700}
.refbar.warn{border-color:#5a4a22;background:#1a1608}
.refbar.warn .rb-t{color:#e8c35a}
.refbar.broken{border-color:#5c2b2b;background:#1a0d0d}
.refbar.broken .rb-t{color:#f0524d}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px}
@media(max-width:820px){.grid{grid-template-columns:repeat(2,1fr)}}
.qref{margin:0 0 14px;background:#0e1318;border:1px solid #222a35;border-radius:8px}
.qref>summary{cursor:pointer;padding:10px 13px;font-size:12.5px;color:#c9d1d9;font-weight:600;list-style:none;user-select:none}
.qref>summary::-webkit-details-marker{display:none}
.qref>summary:before{content:"▸ ";color:#58a6ff}
.qref[open]>summary:before{content:"▾ "}
.qwrap{overflow-x:auto;border-top:1px solid #222a35}
.qtab{width:100%;border-collapse:collapse;font-size:11.5px;min-width:760px}
.qtab th{background:#141a22;color:#8b949e;font-weight:500;text-align:left;padding:7px 9px;white-space:nowrap;border-bottom:1px solid #222a35}
.qtab td{padding:7px 9px;border-top:1px solid #1a212b;color:#a9b4c0;vertical-align:top;line-height:1.55}
.qtab tr.on td{background:#151c25}
.qtab .qn{color:#e6edf3;font-weight:600;white-space:nowrap}
.qtab .qa{color:#c9d1d9}
.qtab .qh{color:#7d8590;font-size:11px}
.qtab .qs{white-space:nowrap;font-weight:600}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 13px}
.card .k{font-size:11px;color:var(--dim);margin-bottom:6px}
.card .v{font-size:17px;font-weight:600;font-variant-numeric:tabular-nums}
.card .s{font-size:11px;color:var(--dim);margin-top:4px}
/* ---- 人民币视角 / 决策纪律（2026-10-30） ---- */
.fxstat{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:11px}
@media(max-width:760px){.fxstat{grid-template-columns:repeat(2,1fr)}}
.fxs{background:#11161d;border:1px solid #222b36;border-radius:9px;padding:9px 11px}
.fxs .l{font-size:10.5px;color:#7d8794;margin-bottom:3px;white-space:nowrap}
.fxs .v{font-size:19px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.4px}
.fxs .d{font-size:10px;color:#6e7681;margin-top:3px;line-height:1.55}
table.fxt{width:100%;border-collapse:collapse;font-size:11.5px;min-width:430px}
table.fxt th{background:#141a22;color:#8b949e;font-weight:500;text-align:right;padding:6px 8px;white-space:nowrap;border-bottom:1px solid #222a35}
table.fxt th:first-child,table.fxt td:first-child{text-align:left}
table.fxt th:last-child,table.fxt td:last-child{padding-right:13px}
table.fxt td{padding:6px 8px;border-top:1px solid #1a212b;color:#a9b4c0;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.fxt tr.sum td{background:#151c25;font-weight:600;color:#e6edf3}
table.fxt.fxtl th,table.fxt.fxtl td{text-align:left;white-space:normal}
table.fxt.fxtl td{line-height:1.75;padding:8px}
.wt{border:1px solid #232a34;border-radius:9px;overflow:hidden;background:#10151c}
.wtr{display:grid;grid-template-columns:132px 1fr 1fr;border-top:1px solid #1a212b}
.wtr:first-child{border-top:0}
.wtc{padding:9px 11px;font-size:11.5px;color:#a9b4c0;line-height:1.75}
.wtc.a{color:#e6edf3;font-weight:600;background:#131a22;display:flex;align-items:center}
.wtc.b{border-left:1px solid #1a212b}
@media(max-width:760px){
  .wtr{grid-template-columns:1fr}
  .wtc.a{background:#151c25;border-bottom:1px solid #1e252f;padding-bottom:7px}
  .wtc.b{border-left:0;padding-bottom:5px}
  .wtc.b::before{content:"现状 · ";color:#5a6371}
  .wtc.c::before{content:"代价 · ";color:#5a6371}
}
.fxnote{font-size:11px;color:#7d8794;line-height:1.8;margin-top:9px}
.tran{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0}
@media(max-width:760px){.tran{grid-template-columns:1fr}}
.trc{background:#11161d;border:1px solid #222b36;border-radius:9px;padding:10px 12px;position:relative}
.trc .n{font-size:10.5px;color:#7d8794}
.trc .a{font-size:20px;font-weight:700;font-variant-numeric:tabular-nums;margin:3px 0 2px}
.trc .p{font-size:11px;color:#a9b4c0;line-height:1.7}
.trc .c{font-size:10px;color:#6e7681;margin-top:4px;line-height:1.6}
.trc.t1{border-color:#5a4a1c}
.trc.t1 .a{color:#e8c35a}
.trc.t2 .a{color:#58a6ff}
.trc.t3 .a{color:#26a69a}
.szt{width:100%;border-collapse:collapse;font-size:11.5px}
.szt th{font-size:10px;color:#5a6371;font-weight:500;text-align:right;padding:5px 9px;border-bottom:1px solid #1e252f;white-space:nowrap}
.szt th:first-child,.szt td:first-child{text-align:left}
.szt td{padding:6px 9px;text-align:right;border-bottom:1px solid #161d26;color:#c9d1d9;font-variant-numeric:tabular-nums;white-space:nowrap}
.szt td:first-child{color:#9aa4b2}
.szt tr.key td{background:#131a22;font-weight:600;color:#e6edf3}
.szt tr.sub td{border-bottom:0;padding-top:5px;padding-bottom:5px;font-size:11px}
.szt tr.sub td:first-child{color:#6e7681;padding-left:22px}
.szt tr.sub td:last-child{color:#7d8794;font-size:10.5px}
.szc{border-left:2px solid #30363d;padding:8px 0 8px 11px;font-size:11.5px;color:#a9b4c0;line-height:1.85}
.szchip{display:inline-block;border:1px solid #2b3440;border-radius:12px;padding:2px 9px;font-size:10.5px;color:#7d8794;margin:0 6px 6px 0}
.szchip.on{border-color:#e8c35a;color:#e8c35a;background:rgba(232,195,90,.07)}
.szchip.hi{border-color:#f0524d;color:#f0524d;background:rgba(240,82,77,.07)}
.mgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:11px}
.mcell{background:#11161d;border:1px solid #222b36;border-radius:9px;padding:9px 11px}
.mcell .k{font-size:10.5px;color:#7d8794;margin-bottom:3px}
.mcell .v{font-size:17px;font-weight:700;color:#e6edf3;font-variant-numeric:tabular-nums}
.mcell .s{font-size:10.5px;color:#9aa4b2;margin:3px 0 5px}
.mcell .d{font-size:10.5px;color:#6e7681;line-height:1.75}
.whybox{border:1px solid #262d38;border-left:2px solid #4a3d1c;border-radius:7px;background:#0f141b;padding:9px 12px;margin-bottom:9px}
.msrc{font-size:10px;color:#5a6371;line-height:1.75}
.msrc>div{padding:1.5px 0}
.msrc>div.cx{color:#6e7681;padding-left:11px;border-left:1px solid #222b36;margin:3px 0 3px 2px}
.msrc .on{color:#26a69a;margin-right:3px}
.msrc .off{color:#6e7681;margin-left:8px}
.rkgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px}
.rkcell{background:#0f141b;border:1px solid #222b36;border-radius:9px;padding:9px 11px}
.rkcell .k{font-size:10.5px;color:#7d8794;margin-bottom:3px}
.rkcell .v{font-size:20px;font-weight:700;color:#e6edf3;font-variant-numeric:tabular-nums;line-height:1.15}
.rkcell .s{font-size:10.5px;color:#8b949e;margin-top:2px}
.rknote{font-size:11px;color:#a9b4c0;line-height:1.85;border-left:2px solid #30363d;padding:2px 0 2px 10px;margin-bottom:11px}
@media(max-width:760px){.rkgrid{grid-template-columns:1fr 1fr}.rkgrid .rkcell:nth-child(3){grid-column:1/-1}}
@media(max-width:760px){.mgrid{grid-template-columns:1fr}}

@media(max-width:520px){
  table.fxt{font-size:10.5px;min-width:0}
  .szt{font-size:10.5px;table-layout:fixed;width:100%}
  .szt th,.szt td{padding:5px 3px;white-space:normal;word-break:break-word}
  .szt th:nth-child(4),.szt td:nth-child(4){display:none}
  .szt th:first-child,.szt td:first-child{width:46%}
  .szt tr.sub td:first-child{padding-left:10px}
  .szt tr.sub td:nth-child(3){display:none}
  .szchip{margin:0 4px 5px 0;font-size:10px;padding:2px 7px}
  #sizebox{overflow-x:auto}
  table.fxt th,table.fxt td{padding:5px 4px}
  .alertbar .ab-right button{white-space:nowrap}
  .alertbar{font-size:11.5px}
}

.chartbox{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 10px 6px;margin-bottom:12px}
.bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding:0 4px;flex-wrap:wrap;gap:8px}
.btns{display:flex;gap:6px}
.btns button{background:#1c232d;color:var(--dim);border:1px solid var(--line);padding:4px 11px;border-radius:5px;font-size:12px;cursor:pointer}
.btns button.on{background:#2a3441;color:#fff;border-color:#3d4a5c}
.legend{font-size:11px;color:var(--dim);display:flex;gap:13px;flex-wrap:wrap}
.legend i{display:inline-block;width:14px;height:2px;vertical-align:middle;margin-right:4px}
canvas{width:100%;display:block}
table{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}
th{color:var(--dim);font-weight:500;text-align:right;padding:7px 8px;border-bottom:1px solid var(--line);font-size:11px}
td{text-align:right;padding:7px 8px;border-bottom:1px solid #1b2129}
th:first-child,td:first-child{text-align:left}
.note{font-size:11px;color:#6e7681;margin-top:14px;line-height:1.7}
.tblwrap{overflow-x:auto;margin:0 -4px}
table.sig{min-width:1120px}
table.sig th{text-align:center;padding:6px 7px;font-size:10.5px;white-space:nowrap;color:#8b949e;font-weight:500;border-bottom:1px solid var(--line)}
table.sig tr.grp th{color:#6e7681;border-bottom:1px dashed #232a34;font-size:10px}
table.sig td{text-align:center;padding:9px 6px;font-size:11.5px;white-space:nowrap;border-bottom:1px solid #1b2129}
table.sig td:first-child{text-align:left;white-space:nowrap;min-width:132px}
table.sig td .nm{color:#c9d1d9;font-weight:500}
table.sig td .dt{color:#6e7681;font-size:10.5px}
table.sig tr.cur{background:rgba(201,162,39,.06)}
.sigsum{font-size:11.5px;color:#9aa4b2;line-height:1.85;margin-top:10px;padding:0 4px}
.sigsum b{color:#e6edf3;font-weight:600}
.tools{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:900px){.tools{grid-template-columns:1fr}}
.tool{background:#12171e;border:1px solid #232a34;border-radius:8px;padding:12px 13px}
.tool .th{font-size:12.5px;color:#c9d1d9;font-weight:600;margin-bottom:10px}
.tgrid{display:grid;grid-template-columns:1fr 1fr;gap:8px 10px}
@media(max-width:520px){.tgrid{grid-template-columns:1fr}}
.tgrid label{display:flex;flex-direction:column;gap:4px;font-size:10.5px;color:#6e7681}
.tgrid input,.tgrid select,.tool textarea{background:#0d1117;border:1px solid #2b3440;border-radius:5px;color:#e6edf3;padding:6px 8px;font-size:12px;font-family:inherit}
.tool textarea{width:100%;margin-top:8px;resize:vertical}
.tbtn{background:#1c232d;color:#9aa4b2;border:1px solid #2b3440;border-radius:5px;padding:5px 12px;font-size:11.5px;cursor:pointer}
.tbtn.primary{background:#1f3a2e;color:#4ade80;border-color:#2f6b4c}
.tbtn:hover{color:#fff}
.tnote{font-size:10px;color:#5b6472;line-height:1.7;margin-top:8px}
.gtable{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:10px}
.gtable th{color:#6e7681;font-weight:500;font-size:10px;padding:4px;text-align:right;border-bottom:1px solid #1f2731}
.gtable td{padding:5px 4px;text-align:right;border-bottom:1px solid #171d25}
.gtable tr.hit{background:rgba(240,82,77,.10)}
.gtable tr.hit td{color:#ff8a85}
.gtable td:first-child,.gtable th:first-child{text-align:left}
.stopcard{display:flex;justify-content:space-between;align-items:center;background:#0f141b;border:1px solid #232a34;border-radius:7px;padding:9px 11px;margin-bottom:8px}
.stopcard .sl{font-size:11px;color:#8b949e}
.stopcard .sv{font-size:17px;font-weight:700;font-variant-numeric:tabular-nums}
.stopcard .sd{font-size:10.5px;color:#6e7681;text-align:right;line-height:1.6}
.stopcard.bad{border-color:#7a2f2c;background:rgba(240,82,77,.07)}
.stopcard.bad .sv{color:#f0524d}
.stopcard.warn{border-color:#8a5a1a;background:rgba(245,158,11,.10)}
.stopcard.warn .sv{color:#f59e0b}
.stopcard.muted{border-color:#2b3440;background:#0f141b}
.stopcard.muted .sv{color:#8b949e}
.stopcard.fail{border-color:#7a2f2c;background:rgba(240,82,77,.05);opacity:.72}
.stopcard.fail .sv{color:#8b949e;text-decoration:line-through}
.stopcard.good{border-color:#23543f;background:rgba(38,166,154,.06)}
.stopcard.good .sv{color:#26a69a}
.loglist{margin-top:10px;max-height:260px;overflow:auto}
.logitem{border-left:2px solid #2b3440;padding:6px 10px;margin:7px 0;font-size:11.5px;color:#9aa4b2;background:#0f141b}
.logitem .lh{display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}
.logitem .lt{color:#e6edf3;font-weight:600}
.logitem .lm{color:#8b949e;margin-top:3px;line-height:1.7}
.logitem .lx{margin-left:auto;color:#5b6472;cursor:pointer;font-size:10px}

.dcard.muted{border-color:#232a34;background:#12171e;animation:none}
.dcard.muted .dv{color:#8b949e}

.phasebar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#12171e;border:1px solid #232a34;border-radius:8px;padding:7px 12px;margin-bottom:10px}
.phasebar .ph-label{font-size:11px;color:#6e7681}
.ph-btns{display:flex;gap:6px}
.ph-btns button{background:#1a212b;color:#8b949e;border:1px solid #232a34;padding:5px 12px;border-radius:6px;font-size:12px;cursor:pointer}
.ph-btns button.on{background:#1f3a2e;color:#4ade80;border-color:#2f6b4c}
#ph-right.on{background:#3a1f1f;color:#f87171;border-color:#7a2f2c}
#ph-bull.on{background:#332a10;color:#e8c35a;border-color:#6b5a20}
.ph-hint{font-size:10.5px;color:#6e7681;margin-left:auto}

.defense{display:grid;grid-template-columns:1.15fr 1.15fr 1fr;gap:9px;margin-bottom:10px}
@media(max-width:820px){.defense{grid-template-columns:1fr}}
.dcard{border:1px solid #232a34;background:#12171e;border-radius:8px;padding:9px 13px;display:flex;align-items:center;gap:12px}
.dcard .dl{font-size:11px;color:#8b949e;width:64px;flex:none}
.dcard .dv{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums}
.dcard .dd{font-size:10.5px;color:#6e7681;line-height:1.6}
.dcard.ok{border-color:#23543f;background:rgba(38,166,154,.08)}
.dcard.ok .dv{color:#26a69a}
.dcard.orange{border-color:#8a5a1a;background:rgba(245,158,11,.10);animation:pulseOrange 1.4s infinite}
.dcard.orange .dv{color:#f59e0b}
.dcard.darkred{border-color:#8b1a1a;background:rgba(185,28,28,.14);animation:pulseDark 1.1s infinite}
.dcard.darkred .dv{color:#ff5b55}
@keyframes pulseOrange{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,0)}50%{box-shadow:0 0 0 4px rgba(245,158,11,.14)}}
.verline{display:flex;align-items:flex-start;gap:7px;margin:4px 0 15px;font-size:11px;color:#79838f;line-height:1.7}
.verline .vd{width:6px;height:6px;border-radius:50%;background:#26a69a;margin-top:5px;flex:0 0 6px}
.verline.ok .vd{background:#26a69a}
.verline.warn{color:#c9a227}
.verline.warn .vd{background:#e8c35a;box-shadow:0 0 7px rgba(232,195,90,.6)}
.verline.fail{color:#f0524d}
.verline.fail .vd{background:#f0524d;box-shadow:0 0 9px #f0524d;animation:blink 1.1s infinite}
.verline b{color:#c8d1da;font-weight:600}
.verline .vmore{color:#6e7681;cursor:pointer;border-bottom:1px dotted #3a424d;margin-left:2px}
.verline .vmore:hover{color:#8b949e}
.verline .vdet{display:none;margin-top:5px;font-size:10.5px;color:#7d8794}
.verline.open .vdet{display:block}
.verline .vdet div{padding:1.5px 0}
.verline .vdet .x{color:#f0524d}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.alertbar.orange{background:linear-gradient(90deg,rgba(245,158,11,.22),rgba(245,158,11,.05));border-color:#8a5a1a;color:#fbbf24;animation:pulseOrange 1.2s infinite}
.alertbar.orange .abdot{background:#f59e0b;box-shadow:0 0 10px #f59e0b}
.alertbar.orange .ab-left{font-size:18px}
#alertmodal.orange{border-color:#8a5a1a;box-shadow:0 0 50px rgba(245,158,11,.22)}

.pcard.purple{border-color:#5b2a7a;background:rgba(168,85,247,.10)}
.pcard.purple .pc-s{color:#c084fc}
.alertbar.purple{background:linear-gradient(90deg,rgba(168,85,247,.24),rgba(168,85,247,.05));border-color:#5b2a7a;color:#d8b4fe;animation:pulsePurple 1.2s infinite}
.alertbar.purple .abdot{background:#a855f7;box-shadow:0 0 10px #a855f7}
.alertbar.purple .ab-left{font-size:17px}
@keyframes pulsePurple{0%,100%{box-shadow:0 0 0 0 rgba(168,85,247,0)}50%{box-shadow:0 0 0 4px rgba(168,85,247,.18)}}
.alertbar.darkred{background:linear-gradient(90deg,rgba(185,28,28,.35),rgba(120,10,10,.10));border-color:#8b1a1a;color:#ff6b6b;animation:pulseDark 0.9s infinite}
.alertbar.darkred .abdot{background:#ef4444;box-shadow:0 0 12px #ef4444}
.alertbar.darkred .ab-left{font-size:20px;letter-spacing:1px}
@keyframes pulseDark{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}50%{box-shadow:0 0 0 5px rgba(239,68,68,.22)}}
#alertmodal.darkred{border-color:#8b1a1a;background:#1a0d0d;box-shadow:0 0 60px rgba(239,68,68,.35)}

.periods{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-bottom:10px}
@media(max-width:900px){.periods{grid-template-columns:repeat(2,1fr)}}
@media(max-width:520px){.periods{grid-template-columns:1fr}}
.pcard{background:#12171e;border:1px solid #232a34;border-radius:8px;padding:9px 12px;display:flex;align-items:center;gap:11px}
.pcard .pc-l{font-size:11px;color:#8b949e;width:44px;flex:none}
.pcard .pc-s{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums}
.pcard .pc-d{font-size:10.5px;color:#6e7681;line-height:1.6}
.pcard.blue{border-color:#2a4a6b;background:rgba(91,141,238,.08)}
.pcard.blue .pc-s{color:#5b8dee}
.pcard.red{border-color:#7a2f2c;background:rgba(240,82,77,.08)}
.pcard.red .pc-s{color:#f0524d}
.pcard.yellow{border-color:#6b5a20;background:rgba(232,195,90,.07)}
.pcard.yellow .pc-s{color:#e8c35a}
.pcard.gray .pc-s{color:#8b949e}
.alertbar.blue{background:linear-gradient(90deg,rgba(91,141,238,.22),rgba(91,141,238,.05));border-color:#2a4a6b;color:#8ab4ff;animation:pulseBlue 1.2s infinite}
.alertbar.blue .abdot{background:#5b8dee;box-shadow:0 0 10px #5b8dee}
.alertbar.blue .ab-left{font-size:17px}
@keyframes pulseBlue{0%,100%{box-shadow:0 0 0 0 rgba(91,141,238,0)}50%{box-shadow:0 0 0 4px rgba(91,141,238,.16)}}
#alertmodal.blue{border-color:#2a4a6b;box-shadow:0 0 50px rgba(91,141,238,.22)}

.alertbar{position:sticky;top:0;z-index:50;display:flex;justify-content:space-between;align-items:center;
  gap:10px;flex-wrap:wrap;padding:9px 14px;border-radius:8px;margin-bottom:12px;border:1px solid #232a34;
  background:#12171e;color:#8b949e;font-size:13px;transition:background .3s}
.alertbar .ab-left{display:flex;align-items:center;gap:9px;font-weight:600}
.alertbar .abdot{width:9px;height:9px;border-radius:50%;background:#4a5563;flex:none}
.alertbar .ab-right{display:flex;align-items:center;gap:8px;font-size:11px;color:#6e7681}
.alertbar button{background:#1c232d;color:#9aa4b2;border:1px solid #2b3440;border-radius:5px;padding:3px 9px;font-size:11px;cursor:pointer}
.alertbar.red{background:linear-gradient(90deg,rgba(240,82,77,.22),rgba(240,82,77,.06));border-color:#7a2f2c;color:#ff6b66;
  animation:pulseRed 1.1s infinite}
.alertbar.red .abdot{background:#f0524d;box-shadow:0 0 10px #f0524d}
.alertbar.red .ab-left{font-size:19px;letter-spacing:.5px}
.alertbar.yellow{background:linear-gradient(90deg,rgba(232,195,90,.20),rgba(232,195,90,.05));border-color:#6b5a20;color:#f0d27a;
  animation:pulseYellow 1.4s infinite}
.alertbar.yellow .abdot{background:#e8c35a;box-shadow:0 0 10px #e8c35a}
.alertbar.yellow .ab-left{font-size:17px}
@keyframes pulseRed{0%,100%{box-shadow:0 0 0 0 rgba(240,82,77,.0)}50%{box-shadow:0 0 0 4px rgba(240,82,77,.18)}}
@keyframes pulseYellow{0%,100%{box-shadow:0 0 0 0 rgba(232,195,90,0)}50%{box-shadow:0 0 0 4px rgba(232,195,90,.15)}}
#alertmask{position:fixed;inset:0;background:rgba(5,8,12,.72);display:none;align-items:center;justify-content:center;z-index:99;backdrop-filter:blur(3px)}
#alertmask.show{display:flex}
#alertmodal{max-width:520px;width:90%;border-radius:12px;padding:26px 26px 20px;background:#161b22;border:1px solid #2b3440;text-align:center}
#alertmodal.red{border-color:#7a2f2c;box-shadow:0 0 50px rgba(240,82,77,.25)}
#alertmodal.yellow{border-color:#6b5a20;box-shadow:0 0 50px rgba(232,195,90,.18)}
#amtitle{font-size:30px;font-weight:800;letter-spacing:2px;margin-bottom:10px}
#amsub{font-size:13px;color:#9aa4b2;line-height:1.8}
#amdetail{font-size:11.5px;color:#6e7681;line-height:1.9;margin:12px 0 16px;text-align:left;word-break:break-word;overflow-wrap:anywhere}
#amclose{background:#2a3441;color:#e6edf3;border:1px solid #3d4a5c;border-radius:7px;padding:8px 26px;font-size:13px;cursor:pointer}

.filters{display:flex;gap:6px;flex-wrap:wrap}
.filters button{background:#1c232d;color:#8b949e;border:1px solid #232a34;padding:3px 10px;border-radius:5px;font-size:11.5px;cursor:pointer}
.filters button.on{background:#2a3441;color:#fff;border-color:#3d4a5c}
.evwrap{max-height:430px;overflow:auto;border:1px solid #1f2731;border-radius:6px}
.evwrap table{margin:0}
.evwrap thead th{position:sticky;top:0;background:#161b22;z-index:2}
table.btt td,table.btt th{font-size:11.5px}
table.evt td,table.evt th{font-size:11.5px;padding:6px 8px}

.radartop{display:grid;grid-template-columns:300px 1fr;gap:16px;align-items:center}
@media(max-width:820px){.radartop{grid-template-columns:1fr}}
.radarcards{display:grid;grid-template-columns:1fr 1fr;gap:9px}
@media(max-width:520px){.radarcards{grid-template-columns:1fr}}
.yseqgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
@media(max-width:760px){.yseqgrid{grid-template-columns:1fr 1fr !important}}
.rc{background:#12171e;border:1px solid #232a34;border-radius:8px;padding:10px 12px}
.rc .t{display:flex;align-items:center;gap:7px;font-size:12px;color:#c9d1d9;margin-bottom:6px}
.rc .t .dot{width:7px;height:7px;border-radius:50%}
.rc .m{font-size:11px;color:#8b949e;line-height:1.7}
.rc .m b{color:#e6edf3;font-weight:600}
.wtb{margin-top:14px;border-top:1px dashed #232a34;padding-top:10px;overflow-x:auto}
.wrow{display:flex;align-items:center;gap:8px;margin:6px 0;min-width:640px}
.wrow .lb{width:120px;font-size:11.5px;color:#9aa4b2;flex:none}
.chip{flex:1;text-align:center;border-radius:5px;padding:5px 2px;font-size:10.5px;background:#12171e;border:1px solid #1f2731;color:#6e7681}
.chip .dd{font-size:9.5px;opacity:.8}
.chip .sc{font-size:11px;font-weight:600;display:block;margin-top:1px}

.mtx{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:6px 0 14px}
@media(max-width:820px){.mtx{grid-template-columns:repeat(2,1fr)}}
.mcard{background:#12171e;border:1px solid #232a34;border-radius:8px;padding:11px 12px}
.mcard.cur{border-color:#4a3d1c;background:rgba(201,162,39,.07)}
.mcard .h{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}
.mcard .h .n{font-size:12px;color:#c9d1d9}
.mcard .h .sc{font-size:12px;color:#8b949e}
.mcard .h .sc b{font-size:16px;color:#e6edf3}
.mrow{display:flex;align-items:center;gap:7px;font-size:11.5px;color:#8b949e;margin:5px 0}
.dot{width:7px;height:7px;border-radius:50%;flex:none}
.ok{background:#f0524d;box-shadow:0 0 6px rgba(240,82,77,.5)}
.no{background:#3a434f}
.na{background:#e8c35a;box-shadow:0 0 6px rgba(232,195,90,.5)}
.mrow .v{margin-left:auto;color:#6e7681;font-size:10.5px}
.distwrap{border-top:1px dashed #232a34;padding-top:11px}
.distline{display:flex;justify-content:space-between;font-size:12px;color:#9aa4b2;margin-bottom:7px}
.distline b{color:#e8c35a}
.progress{height:7px;background:#1b222b;border-radius:4px;overflow:hidden}
.progress div{height:100%;background:linear-gradient(90deg,#8a6d1f,#e8c35a);width:0;transition:width .6s}
#miss{font-size:11.5px;color:#8b949e;margin-top:9px;line-height:1.8}
.sub{font-size:11px;color:#6e7681;padding:0 6px 4px}
.trendbar{display:grid;grid-template-columns:1.3fr 1fr;gap:9px;margin-bottom:10px}
.tb-item{background:#12171f;border:1px solid #1e252f;border-radius:9px;padding:9px 12px;
  font-size:11.5px;color:#8b949e;line-height:1.75}
.tb-l{display:inline-block;font-size:10px;color:#5a6371;border:1px solid #232a34;border-radius:5px;
  padding:0 5px;margin-right:7px;vertical-align:1px}
.tb-item b{color:#c9d1d9;font-weight:600}
.tb-ok{color:#26a69a}.tb-no{color:#8b949e}.tb-warn{color:#e8c35a}
@media(max-width:720px){.trendbar{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1>XAU/USD · 伦敦金现货</h1>
    <span class="badge">仅数据展示 · 不构成建议</span>
  </div>
  <div class="phasebar">
    <div class="ph-label">当前阶段</div>
    <div class="ph-btns">
      <button id="ph-left" class="on">左侧寻底阶段</button>
      <button id="ph-right">右侧持仓逃顶阶段</button>
      <button id="ph-bull">牛市主升浪</button>
      <button id="btncheat" style="border-style:dashed;color:#9aa4b2;margin-left:6px" title="灯亮了我该做什么">速查 ?</button>
    </div>
    <div class="ph-hint" id="ph-hint">MA20 / ATR / 超买已静音；MA60 趋势线照常报警</div>
  </div>

  <div class="trendbar" id="trendbar">
    <div class="tb-item"><span class="tb-l">趋势</span><span id="tb-trend">--</span></div>
    <div class="tb-item"><span class="tb-l">通道</span><span id="tb-chan">--</span></div>
    <div class="tb-item"><span class="tb-l">资金</span><span id="tb-fund">--</span></div>
  </div>

  <div class="periods" id="periods"></div>

  <div class="defense" id="defense"></div>

  <div id="alertbar" class="alertbar idle">
    <div class="ab-left"><span class="abdot"></span><span id="abtext">监控中 · 暂无信号</span></div>
    <div class="ab-right">
      <span id="abmeta"></span>
      <button id="abpreview">预览提醒样式</button>
      <button id="abnotify">开启桌面通知</button>
    </div>
  </div>

  <div id="verline" class="verline"></div>

  <div id="alertmask">
    <div id="alertmodal">
      <div id="amtitle"></div>
      <div id="amsub"></div>
      <div id="amdetail"></div>
      <button id="amclose">知道了</button>
    </div>
  </div>

  <div class="price-row">
    <div class="price" id="px">--</div>
    <div class="chg" id="chg">--</div>
  </div>
  <div class="meta">
    <span>日内高 <b id="hi">--</b></span>
    <span>日内低 <b id="lo">--</b></span>
    <span>开 <b id="op">--</b></span>
    <span>昨收 <b id="pc">--</b></span>
    <span>报价/快照时间 <b id="ts">--</b></span>
    <span>日线截至 <b id="dline">--</b></span>
    <span id="liveflag" style="color:#6e7681">● 构建快照</span> <button id="btnrefresh" style="background:#1c232d;color:#9aa4b2;border:1px solid #2b3440;border-radius:4px;padding:2px 8px;font-size:10.5px;cursor:pointer">手动刷新</button>
  </div>

  <div class="refbar" id="refbar"></div>

  <div class="grid">
    <div class="card"><div class="k">近 60 日区间位置</div><div class="v" id="d1">--</div><div class="s" id="s1">--</div></div>
    <div class="card"><div class="k">偏离 MA10（止盈线口径）</div><div class="v" id="d2">--</div><div class="s" id="s2">--</div></div>
    <div class="card"><div class="k">MACD（12,26,9）</div><div class="v" id="macdv">--</div><div class="s" id="macds">--</div></div>
    <div class="card"><div class="k">量能 · 沪金主力 AU0</div><div class="v" id="volv">--</div><div class="s" id="vols">--</div></div>
    <div class="card"><div class="k">当前交易时段</div><div class="v" id="sess">--</div><div class="s" id="sesss">--</div></div>
    <div class="card"><div class="k">波动率环境 · 60 日均振幅</div><div class="v" id="ampv">--</div><div class="s" id="amps">--</div></div>
    <div class="card"><div class="k">偏离 MA200 · 下跌空间</div><div class="v" id="m2v">--</div><div class="s" id="m2s">--</div></div>
    <div class="card" style="border-color:#3a3220"><div class="k">人民币金价 · 元/克</div><div class="v" id="cnyv">--</div><div class="s" id="cnys">--</div></div>
  </div>

  <div class="chartbox" style="padding:14px 15px 12px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">人民币视角 · 你实际拿到手的那个数</div>
      <div style="font-size:11px;color:#6e7681">美元金价 ÷ 31.1035 × USD/CNY · 汇率是第二个价格</div>
    </div>
    <div id="fxwrap"></div>
  </div>

  <div class="chartbox" style="padding:14px 15px 14px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">宏观环境 · 黄金的机会成本</div>
      <div style="font-size:11px;color:#6e7681">美国 10 年期 TIPS 实际利率 · 只解释逆风来自哪，不告诉你什么时候转</div>
    </div>
    <div id="macrowrap"></div>
  </div>

  <div class="chartbox" style="padding:14px 15px 14px;border-color:#4a3d1c;background:linear-gradient(180deg,#141109,#0d1117)">
    <div class="bar" style="margin-bottom:10px">
      <div style="font-size:13px;color:#e8c35a">决策纪律 · 信号是用来否决的，不是用来等的</div>
      <div style="font-size:11px;color:#6e7681">写在这里，是因为这一条比任何指标都更容易让你亏钱</div>
    </div>

    <div style="font-size:12px;color:#c9d1d9;line-height:1.9;margin-bottom:10px">
      这个页面现在有 <b style="color:#e8c35a">14 个信号</b>。它们的排列方式是<b>并列</b>的，你的用法却常常是<b>串联</b>的 ——
      跌了想等黄灯，黄灯亮了想等振幅变高，振幅高了想等 MA60 收复。<br>
      每一环单看都合理，合起来就是<b style="color:#f0524d">永远不动</b>。而这根链条的三个环，其实都有明确标价：
    </div>

    <div class="wt" style="margin-bottom:11px">
      <div class="wtr"><div class="wtc a">振幅变高</div>
        <div class="wtc b"><b style="color:#26a69a">已经兑现</b>：60 日均振幅 2.05%，历史 83% 分位，属于高波动档</div>
        <div class="wtc c">它<b>不是触发条件</b>，只是注释。所以它兑现了也不会让你动 —— 这类条件永远可以被下一个条件替代</div></div>
      <div class="wtr"><div class="wtc a">MA60 收复</div>
        <div class="wtc b">MA60 在 4291，要价格自己先涨 <b>+6.7%</b> 上来</div>
        <div class="wtc c">历史深跌样本（偏离 MA200 ≤-10%，19 次）18 次最终收复 MA200，<b>中位 56 个交易日</b> ≈ 2.7 个月</div></div>
      <div class="wtr"><div class="wtc a">黄灯确认</div>
        <div class="wtc b">10-28 磨底刚到 2/4，<b style="color:#f0524d">10-29 一根阴线掉回 1/4</b> —— 亮两天就灭</div>
        <div class="wtc c">「确认」本身需要 3 天，3 天里价格可以再跌 3% —— 你等的是一个<b>用时间换不确定</b>的东西</div></div>
    </div>

    <div style="font-size:12px;color:#c9d1d9;line-height:1.9;margin-bottom:11px">
      <b style="color:#e8c35a">两条硬规则：</b><br>
      <b>① 信号只能否决，不能授权等待。</b>任何一盏卖出灯亮起 → 必须减；但反过来，<b>没有任何一盏灯亮着的时候，你也没有权力因为「还没等到 X」而推迟一个已经写好的动作</b>。<br>
      <b>② 动作必须提前写死金额和价位。</b>「减一点」不是决策，是拖延；「跌到 3943 买 100 万」才是。
    </div>

    <div style="font-size:12px;color:#c9d1d9;line-height:1.9;margin-bottom:2px">
      <b style="color:#e8c35a">解药：把「等一个舒服的信号」换成「三张全覆盖的委托单」。</b>
      三种走势各对应一张，不管它跌、横、还是转强，你都有事可做 —— 这样就不存在「等不到」这件事。
    </div>
    <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:9px 0 2px;font-size:11px;color:#8b949e">
      <label>总金额（元）<input id="t-amt" type="number" value="3000000" step="10000" style="width:120px;background:#0d1117;border:1px solid #2b3440;color:#e6edf3;border-radius:5px;padding:4px 7px;margin-left:5px;font-size:11px"></label>
      <label>汇率<input id="t-fx" type="number" value="6.66" step="0.01" style="width:78px;background:#0d1117;border:1px solid #2b3440;color:#e6edf3;border-radius:5px;padding:4px 7px;margin-left:5px;font-size:11px"></label>
      <span id="t-sum" style="color:#7d8594"></span>
    </div>
    <div class="tran" id="tranbox"></div>

    <div style="font-size:11.5px;color:#9aa4b2;line-height:1.9">
      <b style="color:#e8c35a">第 1 档今天就执行</b>，它是唯一无条件的一档 —— 位置已在 -28%，越过历次中级调整的中位（-25%），这一步不需要再等任何确认。<br>
      <b style="color:#f0524d">第 1 档没执行完，第 2 / 3 档的钱不许动</b>；三档之间不许挪用额度；执行后 <b>30 天内不许改比例</b>。<br>
      <b style="color:#e8c35a">第 2 档的触发价是锁死的：<span id="rl-num">3943.65</span></b>（2026-06-30 低点，见页面顶部那条进度条）。
      不取「每天重算的 250 日最低价」—— 那个数会跟着下跌自己往下爬，真破了也显示「还没破」，规则等于不存在。
      这条线一经锁定，只有跌破 <b>3500</b>（下面那条推翻条件）才算失效。<br>
      <b style="color:#8b949e">推翻条件</b>：跌破 <b style="color:#f0524d">3500</b>（自高点 -37.5%，接近 1992 年以来最深调整 -38.6%）→ 这不是中级调整而是结构性熊市，<b>三档全部作废，停止加仓，重新评估</b>。
    </div>

    <div style="margin-top:18px;border-top:1px solid #1e252f;padding-top:14px">
      <div style="font-size:12.5px;font-weight:600;color:#e6edf3;margin-bottom:5px">上一层的问题：这 300 万，占你家多少</div>
      <div style="font-size:11.5px;color:#9aa4b2;line-height:1.85;margin-bottom:10px">
        三档解决「什么时候买」，总量解决「买多少不伤身」。黄金不产生现金流、不分红、没有利息，它的仓位决定的不是收益，
        而是<b style="color:#e6edf3">在最深那一段回撤里，你的账户疼多少、会不会被迫卖掉别的东西</b>。
        百分比这件事没有体感，所以下面把每个百分比都折成「几年的储蓄」。
      </div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:9px;font-size:11px;color:#8b949e">
        <label>可投资金融资产（不含自住房）<input id="s-asset" type="number" value="10000000" step="500000" style="width:118px;background:#0d1117;border:1px solid #2b3440;color:#e6edf3;border-radius:5px;padding:4px 7px;margin-left:5px;font-size:11px"></label>
        <label>现有黄金市值<input id="s-hold" type="number" value="0" step="100000" style="width:100px;background:#0d1117;border:1px solid #2b3440;color:#e6edf3;border-radius:5px;padding:4px 7px;margin-left:5px;font-size:11px"></label>
        <label>年可储蓄额<input id="s-save" type="number" value="500000" step="50000" style="width:100px;background:#0d1117;border:1px solid #2b3440;color:#e6edf3;border-radius:5px;padding:4px 7px;margin-left:5px;font-size:11px"></label>
        <span style="color:#5a6371;font-size:10.5px">默认是假设值，改成你的真实数字（本机记住）</span>
      </div>
      <div id="sizebox"></div>
      <div id="sizeconcl" style="margin-top:10px"></div>
    </div>
  </div>

  <details class="qref" open>
    <summary>信号速查 · 每个灯是什么意思、该做什么、历史上准不准（点此收起）</summary>
    <div class="qwrap"><table class="qtab">
      <thead><tr>
        <th style="width:15%">灯 / 信号</th>
        <th style="width:27%">它说明什么</th>
        <th style="width:27%">该做什么</th>
        <th style="width:23%">历史依据</th>
        <th style="width:8%">现在</th>
      </tr></thead>
      <tbody id="qbody"><tr><td colspan="5" style="color:#6e7681">加载中…</td></tr></tbody>
    </table></div>
  </details>

  <div class="chartbox">
    <div class="bar">
      <div class="btns">
        <button data-n="60">60 日</button>
        <button data-n="120" class="on">120 日</button>
        <button data-n="250">250 日</button>
      </div>
      <div class="legend">
        <span><i style="background:#f0524d"></i>阳线</span>
        <span><i style="background:#26a69a"></i>阴线</span>
        <span><i style="background:#e8c35a"></i>MA20</span>
        <span><i style="background:#5b8dee"></i>MA60</span>
      </div>
    </div>
    <canvas id="cv" height="400"></canvas>
    <div class="sub">↑ K 线 / 均线（不画任何预设价位）　　↓ MACD 与 沪金主力成交量（跨市场量能参考）</div>
    <canvas id="cvMacd" height="120"></canvas>
    <canvas id="cvVol" height="112"></canvas>
  </div>

  <div class="chartbox" style="padding:14px 14px 10px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">历史信号回放与对比回测</div>
      <div style="font-size:11px;color:#6e7681">同一套指标口径 · 机械计算 · 不含主观判断</div>
    </div>
    <div class="tblwrap">
      <table class="sig">
        <thead>
          <tr class="grp">
            <th></th><th colspan="4">K 线形态</th><th colspan="2">下影线</th>
            <th colspan="3">MACD（12,26,9）</th><th colspan="3">底背离判定</th>
            <th colspan="3">真实量能 · 沪金 AU0</th><th colspan="2">信号后 3 个交易日</th>
          </tr>
          <tr>
            <th>节点</th><th>开</th><th>高</th><th>低</th><th>收</th>
            <th>点数</th><th>占振幅</th>
            <th>DIF</th><th>DEA</th><th>柱</th><th>严格</th><th>绿柱面积</th><th>摆动低点</th>
            <th>成交(万手)</th><th>持仓(万手)</th><th>量比</th>
            <th>3日累计</th><th>最大反弹</th>
          </tr>
        </thead>
        <tbody id="sigtb"></tbody>
      </table>
    </div>
    <div class="sigsum" id="sigsum"></div>
  </div>

  <div class="chartbox" style="padding:14px 14px 12px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">三维共振矩阵</div>
      <div style="font-size:11px;color:#6e7681">阈值：下影 ≥25% 振幅 · 量比 ≥1.5× · MACD 负柱 3 日内收窄</div>
    </div>
    <div class="mtx" id="mtx"></div>
    <div class="distwrap">
      <div class="distline"><span id="disttxt"></span><b id="distpct"></b></div>
      <div class="progress"><div id="pbar"></div></div>
      <div id="miss"></div>
    </div>
  </div>

  <div class="chartbox" style="padding:14px 14px 12px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">暴跌雷达</div>
      <div style="font-size:11px;color:#6e7681">空间极速下坠 · K线恐慌 · 天量承接 · 绿柱止扩 ｜ 触发 = 前 3 项同时满足</div>
    </div>
    <div class="radarcards" id="crashcards" style="grid-template-columns:repeat(4,1fr)"></div>
    <div id="crashsum" style="font-size:11.5px;color:#9aa4b2;margin-top:10px;line-height:1.85"></div>
    <div style="margin-top:10px;border-left:2px solid #4a3d1c;background:#12171e;border-radius:0 8px 8px 0;padding:9px 12px;font-size:11.5px;color:#9aa4b2;line-height:1.9">
      <b style="color:#e8c35a">模块边界 · 只抓「插针收回」型恐慌底</b><br>
      <b style="color:#f0524d">跳空崩盘型（单日跌幅 8% 以上）当天必然失明</b>：这类 K 线的下影 ÷ 振幅天生不足 25%（收盘必落在当日下半区），若再遇跌停则沪金缩量，天量项同时失效 —— 两个条件在数学上互斥，不是参数调得不对。实测 2011–2026 单日跌幅 8% 以上的两次（<b style="color:#c9d1d9">2013-04-15 / 2026-01-30</b>）当天触发 <b style="color:#f0524d">0 次</b>。<br>
      这类行情由<b style="color:#a855f7">超买雷达</b>提示「别追高」、<b style="color:#f0524d">MA60 清仓线</b>兜底；若 <b style="color:#e8c35a">T+1</b> 出现「长下影 + 天量」，本模块补发信号（如 2013-04-16，触发后 +20 日 <b style="color:#f0524d">+4.33%</b>、20 日内最大浮亏 0%）。
    </div>
  </div>

  <div class="chartbox" style="padding:14px 14px 12px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">磨底规则雷达 <span style="font-size:10px;color:#e8c35a;border:1px solid #3a3220;background:#1e1a0f;padding:1px 6px;border-radius:8px;margin-left:6px">仅预警 · 仓位仅为风险预算</span></div>
      <div style="font-size:11px;color:#6e7681">≥3 分只作预警；真正的买点需要「右侧确认 + 低位过滤」，见下方升级版</div>
    </div>
    <div class="radartop">
      <div><canvas id="cvRadar" height="250"></canvas></div>
      <div class="radarcards" id="radarcards"></div>
    </div>
    <div id="yseqBox" style="margin-top:12px"></div>
    <div class="wtb" id="wtb"></div>
  </div>

  <div class="chartbox" style="padding:14px 14px 12px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">双雷达 · 2011–2026 全历史回测</div>
      <div style="font-size:11px;color:#6e7681">触发后 5 / 10 / 20 个交易日 · 已做 10 日冷却去重 · 收盘价计</div>
    </div>
    <div class="tblwrap" style="margin-bottom:12px">
      <table class="sig btt">
        <thead><tr><th style="text-align:left">策略 / 条件</th><th>样本</th>
          <th>5日胜率</th><th>5日均值</th><th>10日胜率</th><th>10日均值</th>
          <th>20日胜率</th><th>20日均值</th><th>20日最大反弹</th><th>20日最大回撤</th></tr></thead>
        <tbody id="bttb"></tbody>
      </table>
    </div>
    <div class="bar" style="margin-bottom:6px">
      <div class="filters" id="btfilters">
        <button data-f="all" class="on">全部</button>
        <button data-f="crash">暴跌</button>
        <button data-f="mo">磨底</button>
        <button data-f="true">真底</button>
        <button data-f="false">假底</button>
      </div>
      <div style="font-size:11px;color:#6e7681" id="btcount"></div>
    </div>
    <div class="evwrap">
      <table class="sig evt">
        <thead><tr><th style="text-align:left">雷达</th><th>日期</th><th>得分</th>
          <th>5日</th><th>10日</th><th>20日</th><th>20日最大反弹</th><th>20日最大回撤</th><th>判定</th></tr></thead>
        <tbody id="evtb"></tbody>
      </table>
    </div>
    <div class="sigsum" id="btsum"></div>
  </div>

  <div class="chartbox" style="padding:14px 14px 12px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">升级版 · 右侧确认 + 位置过滤</div>
      <div style="font-size:11px;color:#6e7681">绿灯 = 雷达触发 +（MACD金叉 或 站上MA5且MA5拐头）+ 低位</div>
    </div>
    <div class="tblwrap" style="margin-bottom:10px">
      <table class="sig btt">
        <thead><tr><th style="text-align:left">组合</th><th>样本</th>
          <th>5日胜率</th><th>10日胜率</th><th>20日胜率</th><th>20日均值</th><th>20日盈亏比</th><th>20日最大回撤</th></tr></thead>
        <tbody id="uptb"></tbody>
      </table>
    </div>
    <div class="sigsum" id="upsum"></div>
  </div>

  <div class="chartbox" style="padding:14px 14px 12px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">超买雷达 · 2026 四高点复盘</div>
      <div style="font-size:11px;color:#6e7681">同一天口径 · 满分 4 分 · ≥3 分紫色预警；≥3 分且跌破 MA20 深红清仓 ｜ <span style="color:#a855f7">牛市主升浪模式下紫灯静音</span>（2016–2026 共 44 次，60 日内 77% 继续涨）</div>
    </div>
    <div class="tblwrap">
      <table class="sig btt">
        <thead><tr><th style="text-align:left">高点</th><th>峰值</th><th>得分</th>
          <th>空间</th><th>动能</th><th>形态</th><th>量能</th>
          <th>当日预警</th><th>首次≥3分</th><th>跌破MA20</th><th>破位日得分</th><th>清仓信号</th><th>60日最大回撤</th></tr></thead>
        <tbody id="trtb"></tbody>
      </table>
    </div>
    <div class="sigsum" id="trsum"></div>
  </div>

  <div class="chartbox" style="padding:14px 14px 12px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">动态回撤追踪 · 2026 五高点复盘</div>
      <div style="font-size:11px;color:#6e7681">假设当时处于右侧持仓 · 收盘价口径 · 震荡过滤 ±3%</div>
    </div>
    <div class="tblwrap">
      <table class="sig btt trv">
        <thead><tr><th style="text-align:left">顶点</th><th>起点（60日新高）</th><th>止盈线</th><th>顶点距线</th>
          <th>首次跌破</th><th>T+n</th><th>触发日</th><th>收盘vsMA10</th><th>MA10 过滤</th>
          <th>MA60</th><th>谁先</th></tr></thead>
        <tbody id="trvtb"></tbody>
      </table>
    </div>
    <div class="sigsum" id="trvsum"></div>
  </div>

  <div class="chartbox" style="padding:14px 14px 12px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">三模块联合复盘 · 2026 五高点</div>
      <div style="font-size:11px;color:#6e7681">超买紫灯 / 动态止盈线(ATR+MA10) / MA60 防守，谁先响</div>
    </div>
    <div class="tblwrap">
      <table class="sig btt trp">
        <thead><tr><th style="text-align:left">高点</th><th>类型</th><th>超买紫灯</th>
          <th>动态止盈线</th><th>MA60 破位</th><th>首个报警</th>
          <th>60日最低</th><th>跌幅</th><th>信号价高出最低</th></tr></thead>
        <tbody id="trptb"></tbody>
      </table>
    </div>
    <div class="sigsum" id="trpsum"></div>
  </div>

  <div class="chartbox" style="padding:14px 14px 6px">
    <div style="font-size:12px;color:#8b949e;margin-bottom:8px">最近 10 个交易日</div>
    <div class="tblwrap">
      <table>
        <thead><tr><th>日期</th><th>开</th><th>高</th><th>低</th><th>收</th><th>涨跌</th><th>振幅</th></tr></thead>
        <tbody id="tb"></tbody>
      </table>
    </div>
  </div>

  <div class="chartbox" style="padding:14px 14px 14px">
    <div class="bar">
      <div style="font-size:13px;color:#c9d1d9">辅助执行工具</div>
      <div style="font-size:11px;color:#6e7681">买多少 · 怎么止盈 · 怎么复盘</div>
    </div>
    <div class="tools">
      <div class="tool">
        <div class="th">积存金网格建仓计算器</div>
        <div class="tgrid">
          <label>计划总预算（元）<input id="g-budget" type="number" value="100000" step="1000"></label>
          <label>已投入金额（元）<input id="g-invested" type="number" value="0" step="1000"></label>
          <label>已持有克数（克）<input id="g-held" type="number" value="0" step="0.01"></label>
          <label>当前金价（USD/oz）<input id="g-price" type="number" step="0.1"></label>
          <label>首档价（USD/oz）<input id="g-lv0" type="number" step="0.1"></label>
          <label>档距（%）<input id="g-step" type="number" value="1.5" step="0.1"></label>
          <label>汇率（CNY/USD）<input id="g-fx" type="number" value="6.69" step="0.01"></label>
          </div>
        <div id="gridout"></div>
        <div class="tnote" id="gridnote">汇率取实时 USD/CNY；档位由「首档价 × 每档下移 X%」动态生成（不预设固定点位）。克价 = 美元点位 × 汇率 ÷ 31.1035，比例 1:2:3:4 共 10 份。</div>
      </div>
      <div class="tool">
        <div class="th">动态移动止损</div>
        <div id="stopout"></div>
        <div class="tnote" id="stopnote"></div>
      </div>
    </div>
    <div class="tool" style="margin-top:10px">
      <div class="th">交易日志与情绪记录</div>
      <div class="tgrid log-grid">
        <label>日期<input id="l-date" type="date"></label>
        <label>动作<select id="l-act"><option>买入</option><option>加仓</option><option>减仓</option><option>清仓</option><option>观望</option></select></label>
        <label>价格（USD/oz）<input id="l-price" type="number" step="0.1"></label>
        <label>仓位（%）<input id="l-size" type="number" step="1" placeholder="如 30"></label>
      </div>
      <textarea id="l-mood" rows="2" placeholder="当时怎么想的？例如：今天跌到低位区很害怕，但雷达亮灯，我按纪律买了"></textarea>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">
        <button class="tbtn primary" id="l-add">记录这一笔</button>
        <button class="tbtn" id="l-export">导出 JSON</button>
        <button class="tbtn" id="l-clear">清空记录</button>
        <span id="l-count" style="font-size:11px;color:#6e7681;align-self:center"></span>
      </div>
      <div id="loglist"></div>
    </div>
  </div>

  <div class="note">
    数据源：新浪财经外盘（历史日线 / 实时快照）、gold-api.com（盘中刷新）。<br>
    <b style="color:#9aa4b2">关于量能</b>：伦敦金为 OTC 场外市场，无统一成交量；COMEX 黄金期货（GC）的成交量在免费公开源（新浪/腾讯/东财/雅虎/CME）均取不到（返回 0 或被 403/429 拦截）。此处改用 <b>上期所沪金主力（AU0）真实成交量与持仓量</b> 作为跨市场量能参考，并在图中标注，不冒充伦敦金成交量。<br>
    量能倍数 = 当日成交量 ÷ 前 20 日均量；1.5 倍以上视为「显著放量」。量能卡只判「量比 ≥1.5 且收阳/长下影」，不再绑定任何预设价位，非交易建议。<br>
    <b style="color:#9aa4b2">磨底雷达阈值</b>：空间 = 60 日区间位置 ≤20%（<b style="color:#e8c35a">2026-10 修正</b>：原为「或收盘跌破布林下轨」，实测该分支 4 次平均 T+40 -3.47%、胜率 25%，已改为只看位置；跌破下轨仍在卡片上显示，仅作超卖提示）；动能 = 绿柱面积小于上一波 或 负柱连续 2 日缩短 或 DIF 高于前摆动低点；形态 = 连续 2 日小实体（实体/振幅 ≤35%）且不创新低 或 阳包阴；量能 = 量比 ≤0.7（地量）或 1.0~1.8 倍且收阳（温和放量），量比 ≥2 且收阴跌超 1.5% 记「放量暴跌」一票否决。<b style="color:#e8c35a">2026-10 起降级为展示项</b>：2006–2026 控制「空间」之后，量能达标 63%/+1.37% 与未达标 62%/+1.38% 完全一致（p=1.000），量能→真底 AUC 0.538，不再提供增量信息；现在只在页面显示，且「量能未测得」不再算作不达标 —— 此时必须动能与形态同时成立才亮灯。<br>
    MACD 参数 12/26/9，EMA 计算，柱状为 2×(DIF−DEA)。本页仅做数据展示，不含交易建议。<br>
    <b style="color:#ff6b66">卖出信号同样基于日线收盘价确认，严禁盘中假突破/假跌破触发操作！</b><br>
    <div style="margin:2px 0 14px;border:1px solid #33404f;background:linear-gradient(180deg,#0e141c,#0d1117);border-radius:11px;padding:13px 15px">
      <div style="font-size:13px;font-weight:700;color:#9db4cc;letter-spacing:.5px;margin-bottom:9px">理性判断框架 · 怎么用这些数字</div>
      <div style="font-size:11.5px;color:#b9c2cc;line-height:1.95">
        <b style="color:#9db4cc">① 三层判断，共振才采信</b>　<b style="color:#c9d1d9">位置</b>（MA60 / 前高 / 前低，查一下就有，不需预测）· <b style="color:#c9d1d9">结构</b>（是否连续创新低、反弹幅度、MA200 位置）· <b style="color:#c9d1d9">触发</b>（什么算突破、什么算破位）。<b>三层同向才行动；两层冲突 → 空仓。</b><br>
        <b style="color:#9db4cc">② 每条判断先测历史命中率</b>　「MA60 是反弹压力」——2011–2015 的 8 个反弹高点有 <b style="color:#f0524d">7 个在 MA60 上方（88%）</b>，这条只有 1/8 对；「反弹 15–20% 到头」——<b style="color:#26a69a">10/10 成立</b>。只用测过的，其余一律降为参考。<br>
        <b style="color:#9db4cc">③ 精度匹配仓位</b>　空仓 / 试仓 30%：知道「大概在底部区域」就够；上 60%：需要黄灯 + 不创新低；上 100%：需要 MA60 金叉确认。<b>仓位不该超过判断能支撑的精度。</b><br>
        <b style="color:#9db4cc">④ 赔率优先于概率</b>　同一个 -28% 位置：2008 死拿三年 227 万、2013 死拿 94 万（差 2.4 倍）；减半则是 164 万 / 97 万。<b>不猜「这次是哪个剧本」，选「猜错也不致命」的方案。</b><br>
        <b style="color:#9db4cc">⑤ 四个自检</b>　什么数据能推翻它？· 这个指标近 6 个月命中率多少？· 错了亏多少（&gt;5% 即仓位过重）？· 多久能验证（&gt;3 个月就要准备被情绪反复折磨）？
      </div>
    </div>
    <div style="margin:2px 0 14px;border:1px solid #4a3d1c;background:linear-gradient(180deg,#141109,#0d1117);border-radius:11px;padding:13px 15px">
      <div style="font-size:13px;font-weight:700;color:#e8c35a;letter-spacing:.5px;margin-bottom:9px">实战操作口诀 · 规避人机冲突</div>
      <div style="font-size:12px;color:#b9c2cc;line-height:2">
        <b style="color:#e8c35a">① 左侧试仓，先设止损再谈加仓</b><br>
        止损位 = <b style="color:#c9d1d9">黄灯日最低价 − 2.0×ATR14</b>（收盘跌破即走）。宽度用 23 次首灯实测过：<b>0.5×ATR</b> 被扫 <b style="color:#f0524d">52%</b>、期望 +0.59%；<b style="color:#26a69a">2.0×ATR</b> 被扫 <b style="color:#26a69a">17%</b>、期望 <b style="color:#26a69a">+1.44%</b>，最差单次还从 -4.7% 收窄到 -3.7%（<b style="color:#e8c35a">2026-10 修正</b>，原为 0.5 倍）。代价是单笔浮亏变宽到约 3.9%、26 天见分晓 —— 换的是不被日常噪声扫出去。别等 MA60 深红，那时平均已亏 <b style="color:#f0524d">5.64%</b>、要等 22 天。<br><br>
        <b style="color:#e8c35a">② 多重警报同日响，只执行最高顺位那一个</b><br>
        MA20 与 ATR <b>同日触发 → 只按 MA20 减半，不叠加卖出</b>（两次减半会把仓位打到 25%），剩下的底仓死等 MA60 清仓。17 个大顶里两者同日 2 次、相差 ≤1 天 5 次，这条规则用得上。<br><br>
        <b style="color:#e8c35a">③ 止损不是认输，是买保险</b><br>
        底部区域止损，<b style="color:#f0524d">有极大概率卖在坑里</b>（止损后 20 日往往反弹，均值 +0.7%）。但止损是为了花 <b style="color:#c9d1d9">1.5% 的保费</b>，去切断那 <b style="color:#f0524d">9% 的深水套牢</b>。<b style="color:#e8c35a">止损不是认输，是买保险。</b>
      </div>
    </div>
    <b style="color:#9aa4b2">熊市判定四标志 &amp; 2011–2015 镜像</b>：四条<b>同时成立</b>才算熊市 —— ① 收盘 &lt; MA200；② MA200 拐头向下；③ 反弹高点连续低于前高、低点连破；④ 反弹只收复跌幅的 &lt;50%（牛市回调通常能收复 70% 以上）。<br>
    镜像：1920（2011-09）→ 1046（2015-12），<b>-45.5%</b>，用时 4 年零 3 个月；中途 <b>6 次 &gt;10% 反弹、平均 +15.2%、最大 +21.5%</b>；从首次跌破 -25% 到终底还要走 <b>32.8 个月、再跌 22.4%</b>；重回 1920 是 2019-08，<b>前后共 8 年</b>。<b style="color:#e8c35a">熊市不是瀑布是楼梯：每一根 +15% 的反弹都会让人以为底来了。</b><br>
    <b style="color:#9aa4b2">位置的「保质期」是衰减的（2011–2026 全样本，59 个摆动低点）</b>：一个低点形成后，被收盘跌破的概率 —— <b>20 日 3% · 40 日 14% · 60 日 26% · 120 日 35%</b>（存活率 97% / 86% / 74% / 65%）。<b style="color:#f0524d">低点不是越老越结实，是越老越脆</b>：撑住它的是当时的抄底盘，会随成交消耗；同时 MA60 持续下移，把原支撑区甩到价格上方。<b>一个位置守过 60 个交易日，就该改用均线、而不是前低来做判断。</b><br>
    <b style="color:#9aa4b2">磨底黄灯口径</b>：磨底雷达 ≥3/4 且价格处于近 60 日低位区（<b>区间位置 ≤20%</b>），系统内<b>不含任何预设价位</b>。<b style="color:#e8c35a">2026-10 起只用已收盘的日线判定</b>：伦敦金日线在纽约 17:00 收盘（夏令时 UTC 21:00 / 冬令时 UTC 22:00），此前盘中就用半根 K 线判定 —— 2026-10-29 09:36 那条黄灯 3/4、两小时后跌回 2/4 就是实例。现在脚本先按 UTC 22:30 裁掉未收盘的那根，再跑全部判定，信号固定在每天北京 06:30 之后。<br>
    <b style="color:#9aa4b2">黄灯轮次口径</b>：两个黄灯日之间相隔 <b>≥10 个交易日</b> 才算新的一次（连续亮、隔天闪烁都只算一次）；若中途出现<b>连续 10 个交易日收盘站上 MA60</b>，视为趋势已修复，轮次计数清零、下一盏灯重新算第 1 次。仓位比例为风险预算分配，非胜率加权；第 2 档（二次探底）虽 20 日均值 -0.73%，仍<b>保持 30% 不降</b> —— 这是资金管理而非胜率加权：30+30 的平滑渐进，比为了抠单次胜率把仓位切碎更重要，也能防止二次探底后直接起飞导致踏空。「第 4 次及以上禁止加仓」是唯一由统计直接推出的禁令 —— 2011–2026 年共 8 次第 4 次及以后亮灯，+20 日胜率仅 37.5%、均值 -1.07%，+5 日胜率 12.5%。<br>
    <b style="color:#9aa4b2">动态回撤追踪（锁利润辅助线）</b>：止盈线 = 本轮（最近一次创 60 日新高起）内「近 20 日最高 − 3×ATR14」的最高值，<b>只上移不下移</b>；仅日线收盘跌破才算；<b>跌破止盈线且收盘失守 MA10 → 触发</b>，仍在 MA10 上方 → 震荡暂停；触发只提示减仓一半，<b>MA60 一破则本模块失效</b>，清仓交给 MA60。它的作用是防慢刀子阴跌时把利润全吐回去，<b>不用来抓顶</b>。<br>
    <b style="color:#9aa4b2">逃顶优先级（2026-10 重新校准）</b>：<b style="color:#c9d1d9">MA20 &gt; ATR棘轮 &gt; MA60</b>。<br>① <b style="color:#f59e0b">高位破 MA20</b>（120 日位置 ≥70%）→ 橙色【高位破 MA20，建议减仓一半】。2011–2026 的 17 个阶段性大顶全部触发，平均延迟 4.0 天、卖在顶下 4.82%、假摔率 12%。<b>低位破 MA20（&lt;70%）只记录、不报警</b> —— 下跌途中的正常回踩，无条件报警的历史假信号率 44%。<br>② <b style="color:#f59e0b">ATR 棘轮</b>（收盘跌破追踪线且失守 MA10）→ 只减一半，定位为<b>锁利润辅助线</b>。17 个大顶仅触发 9 次（53%）、平均延迟 8.7 天、卖在顶下 6.51%，另有 47% 因先跌破 MA60 而失效；非顶时期假信号率 59%。<br>③ <b style="color:#ff4d4d">MA60</b> → 不分位置，收盘跌破即深红【跌破 MA60 趋势破位，建议清仓离场】。17 个大顶全部触发，假摔率 0%，代价是平均要等 12.3 天。若近 10 日内超买雷达曾 ≥3 分且当前 &lt; MA20，追加【终极警告】。<br>
    <div style="margin:10px 0 14px;padding:11px 14px;border-left:3px solid #33404f;background:#0d1319;border-radius:6px">
      <div style="font-size:12px;font-weight:700;color:#9db4cc;margin-bottom:7px">什么时候该盯哪盏灯 · 按「位置 × 跌速」查表</div>
      <div style="font-size:11.5px;color:#b9c2cc;line-height:1.95">
        <b style="color:#c9d1d9">位置 ≥80%，日跌 &lt;3%（缓跌）</b> → 紫灯与 MA20 都可能响（1920、1795、1392 三个顶均为双响）<br>
        <b style="color:#c9d1d9">位置 ≥80%，两日跌 &gt;10%（急跌）</b> → <b style="color:#f0524d">只有紫灯会响</b>；别等 MA20 —— 它把 120 日位置砸到 70% 以下就静默了（2026-01-29 两天 -16.8%，跌破当日位置仅 59%）<br>
        <b style="color:#c9d1d9">位置 55–80%</b> → 只有 MA20 会响，且要求「跌破当日」仍 ≥70%；紫灯在这档基本不亮<br>
        <b style="color:#c9d1d9">位置 &lt;55%</b> → <b style="color:#ff4d4d">只剩 MA60 兜底</b>，紫灯与 MA20 都不响<br>
        <span style="color:#6e7681">注：价格贴着 MA60（3% 内）→ 破位当天就触发；离 MA60 超 5% → 要 1–2 周才破（1434 用了 13 天、1191 用了 12 天）。MA20 的位置门槛看的是「跌破当天」，不是「顶部当天」——这是急跌型顶会被静默的原因。</span>
      </div>
    </div>

    <b style="color:#9aa4b2">超买雷达阈值</b>：空间 = 近 120 日区间位置 ≥80% 或偏离 MA20 ≥15%（<b style="color:#e8c35a">2026-10 修正</b>：删去「收盘触及布林上轨」单独计分的分支 —— 半山腰反弹贴上轨也会成立，8/06 位置仅 20% 却拿到空间分，是唯一一次假顶；全样本只贡献 2 次信号、0 次真跌）；动能 = 顶背离 / 红柱连续 2 日缩短 / 3 日内高位死叉；形态 = 上影占振幅 &gt;50% / 阴包阳 / 3 日涨幅 ≥6%；量能 = 量比 ≥2 且收阴或长上影。≥3 分紫色预警，≥3 分且收盘跌破 MA20 触发深红破位。贴上轨仍在卡片上显示，仅作超买提示，不再单独计分。<br>
    <b style="color:#9aa4b2">为什么它叫「超买」而不叫「逃顶」（2026-10 更名）</b>：它测的是<b style="color:#c9d1d9">超买 + 动量透支</b>，不是见顶。全样本 67 次亮灯，之后 60 个交易日<b>平均仍涨 +4.46%、75% 收涨</b>；60 日内跌 ≥8% 的只有 <b style="color:#ff6b66">9.0%</b>，而随便哪天买入的这个比例是 <b style="color:#58a6ff">21.4%</b>（z=-2.48）—— 亮灯后的下跌概率只有随机的一半，属于<b>负信息量</b>。60 日内最大涨 +9.7% vs 最大跌 -4.0%，64% 的情况下涨得更多。分年代：2011–2015 熊市段 9 次（20 日 +1.59%、60 日 +2.62%）；2016–2026 牛市段 43 次（20 日 +2.25%、60 日 +4.94%、77% 收涨），最惨 2025-12-30 之后 20 日涨 +24.81%。八个历史大顶里，<b>顶当天</b>拿到 3 分的只有 2 个（2016-07-11、2026-01-29），2022-03-08 那轮整段没亮；放宽到前后 10 日才有 7/8。<br>所以：它只提示「别追高、别加仓」，<b style="color:#f0524d">卖出看 MA20 / ATR 棘轮 / MA60，不看它</b>。牛市主升浪阶段卡片自动转灰并标注静音。<br>
    <b style="color:#9aa4b2">1H / 4H 数据口径</b>：使用上期所沪金主力 AU0 60 分钟线（含成交量）作为伦敦金短线的跨市场代理；4H 由 1H 按「日期 + 4 小时时段」合成。内盘休市时段无 K 线，跳空与隔夜缺口会保留，读形态时需注意。<br>
    <b style="color:#9aa4b2">1H/4H 蓝灯的趋势闸门（2026-10 新增）</b>：只有日线 <b>收盘 &gt; MA20 &gt; MA60</b> 时才允许亮灯，卡片标记「牛市回调做T专用」。日线收盘 &lt; MA60 → <b>直接封杀</b>，不弹窗、不闪条、不响铃，卡片转灰显示「做T已关闭 · 趋势向下」；MA60 &lt; 收盘 &lt; MA20 的震荡区同样关闭。<br>依据：2026-05~10 的 1023 根 60 分钟数据里，1H 蓝灯 53 次，4h/8h/24h/48h 扣点差后全部为负（-0.28% ~ -0.48%），跑赢点差的比例只有 38%~45%。按日线趋势分组：上涨趋势 5 次，扣点差净收益 +0.72%、净胜率 100%；下跌趋势 14 次，净收益 -0.52%、净胜率 29%。这波下跌里 9 次 1H+4H 共振全部落在非上涨趋势，24h 均值仅 +0.24%，扣点差后接近零。<br>    <b style="color:#9aa4b2">趋势 / 通道两行（2026-10 新增 · 只展示，不参与任何交易判定）</b>：<br><b style="color:#c9d1d9">趋势行</b>显示 MA20 与 MA60 的距离、是否金叉、MA60 较 40 个交易日前是升是降。这三项构成趋势策略的三个条件：<b>MA20 上穿 MA60 + MA60 向上 → 买入；收盘破 MA60 → 清仓</b>。2011–2026 用 MA20×MA60+斜率过滤回测：+107.5%、最大回撤 -14.0%、17 年 14 笔、胜率 57%、平均持仓 55 天。参数敏感性：换 MA10 为 +163.8%、换 MA25 为 +36.5%，方向稳定但幅度差异大，不要把某个具体数字当预期。<br><b style="color:#c9d1d9">通道行</b>显示前 120 日最高价、当前距前高百分比、当日上影线占振幅。当「距前高 ≤2% 且上影 >40%」时提示 <b style="color:#e8c35a">位置偏高 · 建议暂停加仓</b>。<b>这不是减仓信号</b>：2011–2026 该组合触发 105 次，之后 20 日平均仍涨 <b>+2.15%</b>、胜率 <b>67%</b>（基准 +0.64%）；接近三年新高 1% 内更是 73 次、胜率 70%、均值 +3.45%。若按它减半，资金曲线从 +107.5% 掉到 +58.0%。唯一有效的时段是 2006–2010（-2.17%，连珠炮 -6.19%），靠 2008 年那 4 次暴跌撑起，其余 158 次全是假警报。所以它只用来<b>暂停加仓</b>，不用来卖出。<br><b style="color:#c9d1d9">资金分层建议（2026-10）</b>：<b>趋势策略 70% + 黄灯体系 30%</b>。2011–2026 回测：70/30 组合 <b>+139.8%</b>（含闲置现金 2% 生息）、最大回撤 <b>-11.7%</b>；纯趋势 +176.3% / -14.0%；纯黄灯 +49.3% / -5.4%。黄灯那 30% 的收益贡献只有约 1%，它的价值在于让你有地方折腾，从而不去动主账户的 70%。<br>    <b style="color:#9aa4b2">回放口径</b>：下影线 = min(开,收) − 最低；占振幅 = 下影 ÷ (最高 − 最低)。<b>严格口径</b>：节点最低价低于前 60 个交易日（剔除最近 5 日）内的最低点，且 DIF 高于前低当日 DIF。<b>绿柱面积法</b>：本次下跌（前一摆动低点→当前低点）所有负柱绝对值之和，对比上一波（再前一摆动低点→前一摆动低点），价格新低且面积更小才算背离。<b>摆动低点法</b>：以左右各 5 根 K 线确认的局部低点，价格新低且当前低点 DIF 更高才算背离；最新一根 K 线右侧未确认，标 *。量比 = 当日沪金 AU0 成交量 ÷ 前 20 日均量（含当日）。「信号后 3 日」按伦敦金收盘计算，3 日累计取第 3 个交易日收盘相对信号日收盘的涨跌幅。
    <div id="wnote" style="margin-top:11px;font-size:11px;color:#5a6371;line-height:1.8"></div>
  </div>
</div>

<div id="cheatmask" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.74);z-index:9999;padding:4vh 14px;overflow:auto">
  <div style="max-width:660px;margin:0 auto;background:#0b0e13;border:1px solid #232a34;border-radius:14px;padding:18px 20px;box-shadow:0 24px 60px rgba(0,0,0,.65)">
    <div style="display:flex;align-items:center;gap:10px">
      <div style="font-size:15px;font-weight:700;color:#c9d1d9">信号速查 · 灯亮了该做什么</div>
      <button id="cheatclose" style="margin-left:auto;background:#161b22;border:1px solid #232a34;color:#9aa4b2;border-radius:7px;padding:4px 11px;cursor:pointer;font-size:12px">关闭</button>
    </div>
    <div style="margin:11px 0 13px;padding:10px 12px;border:1px dashed #4a3d1c;background:#12100a;border-radius:9px;font-size:14px;color:#e8c35a;font-weight:700;text-align:center;letter-spacing:1px">
      黄买 · 紫看 · 橙减半 · 红清仓 · 蓝做T
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:12.5px">
      <thead><tr style="color:#5a6371;font-size:10.5px;text-align:left">
        <th style="padding:0 6px 6px 0;font-weight:400">灯</th><th style="padding:0 6px 6px;font-weight:400">什么时候亮</th><th style="padding:0 0 6px;font-weight:400">我做什么</th></tr></thead>
      <tbody>
        <tr style="border-top:1px solid #1b2129"><td style="padding:9px 6px 9px 0;white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#e8c35a;margin-right:7px"></span><b style="color:#e8c35a">黄灯 第1次</b></td><td style="padding:9px 6px;color:#8b949e">磨底 ≥3 分 + 60 日低位</td><td style="padding:9px 0;color:#c9d1d9;font-weight:700">买 30%</td></tr>
        <tr style="border-top:1px solid #1b2129"><td style="padding:9px 6px 9px 0;white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#f59e0b;margin-right:7px"></span><b style="color:#f59e0b">黄灯 第2次</b></td><td style="padding:9px 6px;color:#8b949e">二次探底，间隔 ≥10 交易日</td><td style="padding:9px 0;color:#c9d1d9;font-weight:700">加到 60%</td></tr>
        <tr style="border-top:1px solid #1b2129"><td style="padding:9px 6px 9px 0;white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#f0524d;margin-right:7px"></span><b style="color:#f0524d">黄灯 第3次</b></td><td style="padding:9px 6px;color:#8b949e">三次探底，胜率最高的一档</td><td style="padding:9px 0;color:#c9d1d9;font-weight:700">加到 100%</td></tr>
        <tr style="border-top:1px solid #1b2129;background:rgba(110,118,129,.06)"><td style="padding:9px 6px 9px 0;white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#6e7681;margin-right:7px"></span><b style="color:#8b949e">黄灯 第4次+</b></td><td style="padding:9px 6px;color:#8b949e">阴跌还在磨，20 日胜率仅 38%</td><td style="padding:9px 0;color:#6e7681;font-weight:700">一股不加，只减</td></tr>
        <tr style="border-top:1px solid #1b2129"><td style="padding:9px 6px 9px 0;white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#a855f7;margin-right:7px"></span><b style="color:#a855f7">紫灯</b></td><td style="padding:9px 6px;color:#8b949e">高位滞涨：上影 / 天量 / 顶背离</td><td style="padding:9px 0;color:#c9d1d9;font-weight:700">不追高，<span style="color:#8b949e">也不卖</span></td></tr>
        <tr style="border-top:1px solid #1b2129"><td style="padding:9px 6px 9px 0;white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#f59e0b;margin-right:7px"></span><b style="color:#f59e0b">橙灯</b></td><td style="padding:9px 6px;color:#8b949e">高位（120日位置 ≥70%）跌破 MA20</td><td style="padding:9px 0;color:#c9d1d9;font-weight:700">减一半</td></tr>
        <tr style="border-top:1px solid #1b2129"><td style="padding:9px 6px 9px 0;white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#ff4d4d;margin-right:7px"></span><b style="color:#ff4d4d">深红</b></td><td style="padding:9px 6px;color:#8b949e">跌破 MA60 / 紫灯后再破 MA20</td><td style="padding:9px 0;color:#ff4d4d;font-weight:700">清仓</td></tr>
        <tr style="border-top:1px solid #1b2129"><td style="padding:9px 6px 9px 0;white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#5b8dee;margin-right:7px"></span><b style="color:#5b8dee">蓝灯</b></td><td style="padding:9px 6px;color:#8b949e">1H 与 4H 同时 ≥2 分 <b style="color:#5b8dee">且日线多头</b></td><td style="padding:9px 0;color:#c9d1d9;font-weight:700">轻仓做 T，不留夜</td></tr>
        <tr style="border-top:1px solid #1b2129"><td style="padding:9px 6px 9px 0;white-space:nowrap"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#f0524d;margin-right:7px"></span><b style="color:#f0524d">暴跌红</b></td><td style="padding:9px 6px;color:#8b949e">插针收回 + 沪金天量承接</td><td style="padding:9px 0;color:#c9d1d9;font-weight:700">抢反弹，轻仓，3 天内走</td></tr>
      </tbody>
    </table>
    <div style="margin-top:13px;padding-top:11px;border-top:1px solid #1b2129;font-size:11.5px;color:#6e7681;line-height:1.95">
      <b style="color:#9aa4b2">三阶段开关</b>　左侧寻底 = MA20 / ATR / 超买静音，<b style="color:#f0524d">MA60 照常报警</b> ｜ 右侧持仓 = 全部激活 ｜ 牛市主升浪 = MA10 与超买紫灯静音<br>
      <b style="color:#9aa4b2">三条铁律</b>　① 灯是提醒，不是命令 ② 仓位按纪律 30/30/40，不按感觉 ③ 止损按 ATR，浮亏时严禁补仓
    </div>
  </div>
</div>

<script>
const DATA = __PAYLOAD__;
let bars = DATA.kline.slice();
let live = DATA.live;
const LEVELS = [];   // 不画任何预设价位线，关键位全部交给雷达动态判定

// 宏观结构备注：只在出现明显倾向时给数字，平时只说"未分"；不写目标价
(function(){
  const W = DATA.wave || {};
  const el = document.getElementById('wnote');
  if(!el) return;
  const a=W.weight_A, b=W.weight_B;
  if(a==null || (a+b)===0){ el.style.display='none'; return; }
  let s='宏观结构：';
  if(a>=0.60) s += `偏 A（顶已成立）· A ${(a*100).toFixed(0)}%`;
  else if(b>=0.60) s += `偏 B（还有一浪）· B ${(b*100).toFixed(0)}%`;
  else s += '顶部两解未分';
  if(W.chan && W.chan.zd){ s += ` · 近期中枢 ${W.chan.zd}–${W.chan.zg}（现价${W.chan.pos}）`; }
  s += ' · 仅记录，不参与判定';
  el.textContent = s;
})();
let N = 120;

function fmt(n,d=2){ return n==null?'--':n.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}); }
function ema(arr, n){
  const k = 2/(n+1); const out = []; let prev = arr[0];
  arr.forEach((v,i)=>{ prev = i===0 ? v : v*k + prev*(1-k); out.push(prev); });
  return out;
}
function calcMACD(){
  const closes = bars.map(b=>b.c);
  const e12 = ema(closes,12), e26 = ema(closes,26);
  const dif = closes.map((_,i)=> e12[i]-e26[i]);
  const dea = ema(dif,9);
  const hist = dif.map((v,i)=> 2*(v-dea[i]));
  return {dif, dea, hist};
}
const MACD = calcMACD();

// ===== 沪金主力成交量（跨市场量能参考） =====
const AU = (DATA.au || []).slice().sort((a,b)=> a.d < b.d ? -1 : 1);
const auByDate = {}; AU.forEach(a=> auByDate[a.d] = a);
function auFor(date){
  if(auByDate[date]) return auByDate[date];
  let lo=0, hi=AU.length-1, best=null;
  while(lo<=hi){ const mid=(lo+hi)>>1; if(AU[mid].d<=date){ best=AU[mid]; lo=mid+1; } else hi=mid-1; }
  return best;
}
function volStats(){
  const last = auFor(bars[bars.length-1].d);
  const idx = last ? AU.indexOf(last) : -1;
  if(idx < 0) return null;
  const win = AU.slice(Math.max(0, idx-19), idx+1).map(a=>a.v);
  const avg = win.reduce((a,b)=>a+b,0)/win.length;
  return {last: last.v, avg, ratio: last.v/avg, oi: last.p, date: last.d};
}


function sessionNow(){
  const now = new Date();
  const bj = new Date(now.getTime() + (now.getTimezoneOffset()*60000) + 8*3600000);
  const h = bj.getHours() + bj.getMinutes()/60;
  let name, desc;
  if(h>=6 && h<15){ name='亚洲盘'; desc='波动通常偏小，多为区间震荡'; }
  else if(h>=15 && h<20.5){ name='欧洲盘'; desc='欧盘开盘，方向常在此确立'; }
  else if(h>=20.5 || h<4){ name='美盘'; desc='数据密集，波动最大'; }
  else { name='美盘尾/亚盘前'; desc='流动性偏低，谨防假突破'; }
  return {name, desc, hhmm: String(bj.getHours()).padStart(2,'0')+':'+String(bj.getMinutes()).padStart(2,'0')};
}

function renderTrend(){
  const T=DATA.trend||{}, C=DATA.channel||{};
  const box=document.getElementById('trendbar');
  if(!box) return;
  if(!T.ma20){ box.style.display='none'; return; }
  const g=T.golden;
  const gcol=g?'#e8c35a':'#6e7681';
  const gtxt = g
    ? (T.days>0?`已金叉 <b style="color:#e8c35a">${T.days} 天</b>`:`已金叉 <b style="color:#e8c35a">持续中</b>`)
    : `<span style="color:#6e7681">未金叉</span>`;
  const sp = (T.slopePct!=null) ? ` · 40日 ${T.slopePct>0?'+':''}${T.slopePct}%` : '';
  const d3 = T.m60_3d;
  let stxt;
  if(d3==null){
    stxt = T.slopeUp ? `<span style="color:#e8c35a">MA60 向上${sp}</span>`
                     : `<span style="color:#6e7681">MA60 向下${sp}</span>`;
  } else if(d3 <= -0.05){
    stxt = `<span style="color:#f0524d">MA60 已拐头向下（3日 ${d3}%${sp}）</span>`;
  } else if(d3 >= 0.05){
    stxt = `<span style="color:#e8c35a">MA60 仍向上（3日 +${d3}%${sp}）</span>`;
  } else {
    stxt = `<span style="color:#e8c35a">MA60 走平待定（3日 ${d3}%${sp}）</span>`;
  }
  const idle = g ? `持仓期（趋势系统）` : `空仓等待`;
  document.getElementById('tb-trend').innerHTML =
    `MA20 <b>${T.ma20}</b> · MA60 <b>${T.ma60}</b> · 差 <b style="color:${gcol}">${T.gap>0?'+':''}${T.gap}%</b><br>` +
    `${gtxt} · ${stxt} · <span style="color:#6e7681">${idle}</span>`;
  // 资金行：GLD 持仓（只展示，不参与判定）
  try{
    const G = DATA.gld || {};
    const el = document.getElementById('tb-fund');
    if(el && G.tonnes){
      const f = (v, unit)=> (v>=0?'+':'') + v.toFixed(1) + unit;
      const col = (v)=> v>0 ? '#e8c35a' : (v<0 ? '#8b949e' : '#6e7681');
      const p20 = (G.pct20!=null) ? G.pct20 : null;
      const p60 = (G.pct60!=null) ? G.pct60 : null;
      const B = DATA.basis || {};
      const bs = (B.basis!=null) ? `<b style="color:${B.basis>=0?'#e8c35a':'#8b949e'}">${B.basis>0?'+':''}${B.basis.toFixed(1)}</b>` : '--';
      el.innerHTML =
        `GLD <b>${G.tonnes.toFixed(1)}</b> 吨 · 20日 <b style="color:${col(G.chg20)}">${G.chg20!=null?f(G.chg20,' 吨'):'--'}${p20!=null?' ('+f(p20,'%')+')':''}</b><br>` +
        `<span style="color:#5a6371">60日 ${G.chg60!=null?f(G.chg60,' 吨')+' ('+f(G.pct60,'%')+')':'--'} · 一年 ${G.lo250}–${G.hi250} 吨 · ${G.date}</span><br>` +
        `<span style="color:#5a6371">COMEX 基差 ${bs} · 60日均 <b style="color:#8b949e">${B.avg60!=null?(B.avg60>0?'+':'')+B.avg60:'--'}</b> · 一年 ${B.lo250!=null?B.lo250+'~'+B.hi250:'--'}</span>`;
    } else if(el){ el.innerHTML = `<span style="color:#5a6371">GLD 数据未取到</span>`; }
  }catch(e){}
  const c = C.active;
  document.getElementById('tb-chan').innerHTML =
    `120日高 <b>${C.hi120}</b> · 距 <b class="${c?'tb-warn':'tb-no'}">${C.dist>0?'+':''}${C.dist}%</b> · 上影 <b>${C.upperShadow}%</b><br>` +
    (c
      ? `<span class="tb-warn">★ 位置偏高 · 建议暂停加仓（不减仓）</span>`
      : `<span style="color:#5a6371">距前高尚远，无提示</span>`);
}

function paintHeader(){
  const p = live.price, pc = live.prevClose;
  const diff = p - pc, dp = (diff/pc*100);
  const cls = diff >= 0 ? 'var(--up)' : 'var(--down)';
  const px = document.getElementById('px');
  px.textContent = fmt(p); px.style.color = cls;
  const ch = document.getElementById('chg');
  ch.textContent = (diff>=0?'+':'') + fmt(diff) + '  (' + (dp>=0?'+':'') + dp.toFixed(2) + '%)';
  ch.style.color = cls;
  document.getElementById('hi').textContent = fmt(live.high);
  document.getElementById('lo').textContent = fmt(live.low);
  document.getElementById('op').textContent = fmt(live.open);
  document.getElementById('pc').textContent = fmt(pc);
  document.getElementById('ts').textContent = live.date + ' ' + live.time;

  const v60 = bars.slice(-60);
  const hi60 = Math.max(...v60.map(b=>b.h)), lo60 = Math.min(...v60.map(b=>b.l));
  const pos60 = hi60>lo60 ? (p-lo60)/(hi60-lo60)*100 : 0;
  const ma10v = bars.slice(-10).reduce((a,b)=>a+b.c,0)/Math.min(10,bars.length);
  const dev10 = (p/ma10v-1)*100;
  const e1 = document.getElementById('d1');
  e1.textContent = pos60.toFixed(0) + '%';
  e1.style.color = pos60<=20 ? '#f0524d' : (pos60>=80 ? '#c084fc' : 'var(--fg)');
  document.getElementById('s1').textContent = pos60<=20 ? '低位区（实时估算）' : (pos60>=80 ? '高位区（实时估算）' : '区间中部（实时）');
  const e2 = document.getElementById('d2');
  e2.textContent = (dev10>=0?'+':'') + dev10.toFixed(2) + '%';
  e2.style.color = dev10>=0 ? 'var(--up)' : 'var(--down)';
  document.getElementById('s2').textContent = dev10>=0 ? '价在 MA10 上方 · 实时（止盈线暂停）' : '价在 MA10 下方 · 实时（止盈线放行）';

  const i = bars.length-1;
  const dif = MACD.dif[i], dea = MACD.dea[i], hist = MACD.hist[i];
  const mv = document.getElementById('macdv');
  mv.textContent = (dif>=0?'+':'') + fmt(dif);
  mv.style.color = dif>=0 ? 'var(--up)' : 'var(--down)';
  let cross = '';
  for(let k=i; k>Math.max(0,i-8); k--){
    if(MACD.dif[k-1]<=MACD.dea[k-1] && MACD.dif[k]>MACD.dea[k]){ cross = '金叉 '+bars[k].d; break; }
    if(MACD.dif[k-1]>=MACD.dea[k-1] && MACD.dif[k]<MACD.dea[k]){ cross = '死叉 '+bars[k].d; break; }
  }
  document.getElementById('macds').innerHTML = `DEA ${fmt(dea)} · 柱 ${hist>=0?'+':''}${fmt(hist)}` + (cross?'<br>'+cross:' · 无近期交叉');

  const vs = volStats();
  if(vs){
    const vv = document.getElementById('volv');
    vv.textContent = vs.ratio.toFixed(2) + ' 倍';
    vv.style.color = vs.ratio >= 1.5 ? 'var(--up)' : (vs.ratio >= 1 ? '#e8c35a' : 'var(--dim)');
    const b = bars[bars.length-1];
    const yang = b.c >= b.o || (Math.min(b.o,b.c)-b.l) > 0.5*(b.h-b.l);
    const sig = vs.ratio >= 1.5 && yang;
    document.getElementById('vols').innerHTML = `成交 ${(vs.last/10000).toFixed(1)} 万手 · 20日均 ${(vs.avg/10000).toFixed(1)} 万` +
      '<br>' + (sig ? '<span style="color:#f0524d">放量且收阳 / 长下影</span>' : '<span style="color:#6e7681">放量承接未确认</span>');
  }

  const s = sessionNow();
  document.getElementById('sess').textContent = s.name;
  document.getElementById('sesss').textContent = '北京时间 ' + s.hhmm + ' · ' + s.desc;

  renderRefLow();
}

// 参照低点进度条：第 2 档的触发线距离多远，用实时价算，不用收盘价
function renderRefLow(){
  const E = DATA.fxenv || {}, box = document.getElementById('refbar');
  if(!box) return;
  const R = E.refLow || {};
  const low = R.usd || null;
  if(!low){ box.innerHTML = ''; box.className = 'refbar'; return; }
  const _num = document.getElementById('rl-num');
  if(_num) _num.textContent = low.toFixed(2);
  const px = (live && live.price) || low;
  const fx = E.fx || 6.6525;
  const gap = (px/low - 1) * 100;
  const cnyLow = low * fx / GRAM;
  let cls = 'refbar', tag = '', tone = '#8b949e', sub = '';
  if(gap > 3){
    tag = '距参照低点'; sub = `还有 ${gap.toFixed(1)}% 空间 · 第 2 档未激活`;
  } else if(gap > 0){
    cls = 'refbar warn'; tag = '逼近参照低点'; tone = '#e8c35a';
    sub = `只差 ${gap.toFixed(1)}% · 第 2 档待命（第 1 档未执行完不动）`;
  } else {
    cls = 'refbar broken'; tag = '已跌破参照低点'; tone = '#f0524d';
    sub = `超出 ${Math.abs(gap).toFixed(1)}% · 第 2 档条件成立（第 1 档未执行完不动）`;
  }
  box.className = cls;
  box.innerHTML =
    `<span class="rb-t" style="color:${tone}">${tag}</span>` +
    `<span class="rb-n" style="color:${tone}">${fmt(low, low % 1 ? 2 : 0)}</span>` +
    `<span style="color:#5a6371">${R.d ? R.d + ' 低点 · 已锁死，不随 250 日窗口滑动' : '已锁死'}</span>` +
    `<span style="color:#4a5563">|</span>` +
    `<span>折 ${cnyLow.toFixed(1)} 元/克</span>` +
    `<span style="color:#5a6371">·</span>` +
    `<span>${sub}</span>`;
}

function prep(cv, H){
  const dpr = window.devicePixelRatio || 1;
  const W = cv.clientWidth;
  cv.width = W*dpr; cv.height = H*dpr;
  const ctx = cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,W,H);
  return {ctx, W, H};
}

function drawK(){
  const {ctx, W, H} = prep(document.getElementById('cv'), 400);
  const view = bars.slice(-N);
  const padL = 8, padR = 63, padT = 14, padB = 24;
  const iw = W-padL-padR, ih = H-padT-padB;
  let lo = Math.min(...view.map(b=>b.l), ...LEVELS.map(l=>l.p));
  let hi = Math.max(...view.map(b=>b.h), ...LEVELS.map(l=>l.p));
  const pd = (hi-lo)*0.06; lo-=pd; hi+=pd;
  const xw = iw/view.length, bw = Math.max(1.6, Math.min(9, xw*0.62));
  const X = i => padL + xw*i + xw/2;
  const Y = v => padT + (hi-v)/(hi-lo)*ih;

  ctx.font='11px -apple-system,sans-serif';
  for(let g=0; g<=5; g++){
    const v = lo+(hi-lo)*g/5, y = Y(v);
    ctx.strokeStyle='#1e242c'; ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(W-padR,y); ctx.stroke();
    ctx.fillStyle='#6e7681'; ctx.textAlign='left'; ctx.fillText(Math.round(v).toLocaleString('en-US'), W-padR+7, y+4);
  }
  LEVELS.forEach(l=>{
    const y = Y(l.p);
    ctx.save(); ctx.setLineDash([5,4]); ctx.strokeStyle=l.c; ctx.globalAlpha=.75; ctx.lineWidth=1.2;
    ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(W-padR,y); ctx.stroke(); ctx.restore();
    ctx.fillStyle=l.c; ctx.textAlign='left'; ctx.fillText(l.t, padL+3, y-4);
  });
  view.forEach((b,i)=>{
    const up = b.c>=b.o, x = X(i);
    ctx.strokeStyle = ctx.fillStyle = up?'#f0524d':'#26a69a';
    ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(x, Y(b.h)); ctx.lineTo(x, Y(b.l)); ctx.stroke();
    const y1 = Y(Math.max(b.o,b.c)), y2 = Y(Math.min(b.o,b.c)), h = Math.max(1,y2-y1);
    if(up){ ctx.fillStyle='#0d1117'; ctx.strokeRect(x-bw/2,y1,bw,h); } else ctx.fillRect(x-bw/2,y1,bw,h);
  });
  const offset = bars.length-view.length;
  [{n:20,c:'#e8c35a'},{n:60,c:'#5b8dee'}].forEach(m=>{
    ctx.beginPath(); ctx.strokeStyle=m.c; ctx.lineWidth=1.5; let started=false;
    view.forEach((b,i)=>{
      const idx=offset+i;
      if(idx<m.n-1) return;
      let s=0; for(let k=idx-m.n+1;k<=idx;k++) s+=bars[k].c;
      const x=X(i), y=Y(s/m.n);
      if(!started){ ctx.moveTo(x,y); started=true; } else ctx.lineTo(x,y);
    });
    ctx.stroke();
  });
  ctx.fillStyle='#6e7681'; ctx.textAlign='center'; ctx.font='10.5px -apple-system,sans-serif';
  const step = Math.ceil(view.length/6);
  view.forEach((b,i)=>{ if(i%step===0) ctx.fillText(b.d.slice(5), X(i), H-7); });

  // 历史信号节点标记
  (DATA.signals||[]).forEach((s,k)=>{
    const bi = bars.findIndex(b=>b.d===s.date);
    if(bi<0) return;
    const vi = bi - (bars.length-view.length);
    if(vi<0 || vi>=view.length) return;
    const x = X(vi), y = Math.min(H-padB-6, Y(bars[bi].l)+14);
    ctx.beginPath(); ctx.arc(x,y,8,0,Math.PI*2);
    ctx.fillStyle='#c9a227'; ctx.fill();
    ctx.fillStyle='#0d1117'; ctx.font='bold 10px -apple-system,sans-serif'; ctx.textAlign='center';
    ctx.fillText(String(k+1), x, y+3.5);
  });
}

function drawMACD(){
  const {ctx, W, H} = prep(document.getElementById('cvMacd'), 120);
  const padL=8, padR=63, padT=10, padB=16;
  const iw=W-padL-padR, ih=H-padT-padB;
  const view = MACD.dif.slice(-N), dea = MACD.dea.slice(-N), hist = MACD.hist.slice(-N);
  let hi = Math.max(...view,...dea,...hist, 0), lo = Math.min(...view,...dea,...hist, 0);
  const pd=(hi-lo)*0.15; hi+=pd; lo-=pd;
  const xw=iw/view.length, bw=Math.max(1.2, Math.min(6, xw*0.55));
  const X=i=>padL+xw*i+xw/2, Y=v=>padT+(hi-v)/(hi-lo)*ih;

  ctx.strokeStyle='#2a323d'; ctx.beginPath(); ctx.moveTo(padL,Y(0)); ctx.lineTo(W-padR,Y(0)); ctx.stroke();
  hist.forEach((v,i)=>{
    const y0=Y(0), y1=Y(v);
    ctx.fillStyle = v>=0 ? 'rgba(240,82,77,.75)' : 'rgba(38,166,154,.75)';
    ctx.fillRect(X(i)-bw/2, Math.min(y0,y1), bw, Math.max(1,Math.abs(y1-y0)));
  });
  [{a:view,c:'#e8c35a'},{a:dea,c:'#5b8dee'}].forEach(s=>{
    ctx.beginPath(); ctx.strokeStyle=s.c; ctx.lineWidth=1.4;
    s.a.forEach((v,i)=>{ i?ctx.lineTo(X(i),Y(v)):ctx.moveTo(X(i),Y(v)); });
    ctx.stroke();
  });
  ctx.font='10px -apple-system,sans-serif';
  ctx.fillStyle= view[view.length-1]>=dea[dea.length-1] ? '#f0524d' : '#26a69a';
  ctx.textAlign='left';
  ctx.fillText('DIF '+fmt(view[view.length-1]), padL+4, padT+9);
  ctx.fillStyle='#5b8dee';
  ctx.fillText('DEA '+fmt(dea[dea.length-1]), padL+90, padT+9);
  ctx.fillStyle='#6e7681'; ctx.textAlign='left'; ctx.fillText('MACD', W-padR+7, padT+9);
}

function drawVol(){
  const {ctx, W, H} = prep(document.getElementById('cvVol'), 112);
  const padL=8, padR=63, padT=16, padB=14;
  const iw=W-padL-padR, ih=H-padT-padB;
  const view = bars.slice(-N);
  const vols = view.map(b=>{ const a = auFor(b.d); return a ? a.v : null; });
  const maxV = Math.max(...vols.filter(v=>v!=null)) * 1.1;
  const xw=iw/view.length, bw=Math.max(1.2, Math.min(6, xw*0.55));
  const X=i=>padL+xw*i+xw/2, Y=v=>padT+(maxV-v)/maxV*ih;

  const vs = volStats();
  const avg = vs ? vs.avg : maxV/1.1;
  view.forEach((b,i)=>{
    if(vols[i]==null) return;
    const up = b.c>=b.o;
    ctx.fillStyle = up ? 'rgba(240,82,77,.62)' : 'rgba(38,166,154,.62)';
    ctx.fillRect(X(i)-bw/2, Y(vols[i]), bw, Math.max(1, H-padB-Y(vols[i])));
  });

  // 20 日均量
  ctx.save(); ctx.setLineDash([3,3]); ctx.strokeStyle='#e8c35a'; ctx.beginPath();
  ctx.moveTo(padL, Y(avg)); ctx.lineTo(W-padR, Y(avg)); ctx.stroke(); ctx.restore();
  // 1.5 倍放量线
  ctx.save(); ctx.setLineDash([5,4]); ctx.strokeStyle='rgba(240,82,77,.75)'; ctx.beginPath();
  ctx.moveTo(padL, Y(avg*1.5)); ctx.lineTo(W-padR, Y(avg*1.5)); ctx.stroke(); ctx.restore();

  ctx.font='10px -apple-system,sans-serif'; ctx.textAlign='left';
  ctx.fillStyle='#9aa4b2';
  ctx.fillText('AU0 成交量（手）· 跨市场量能参考 · 20日均 '+Math.round(avg/10000)+'万 · 1.5× '+Math.round(avg*1.5/10000)+'万', padL+4, padT-5);
  ctx.fillStyle='#6e7681'; ctx.textAlign='right';
  ctx.fillText(Math.round(maxV/10000)+'万手', W-padR-4, padT+8);
}

function renderSignals(){
  const SIG = DATA.signals || [];
  const tb = document.getElementById('sigtb');
  tb.innerHTML = SIG.map(s=>{
    const cur = s.date === bars[bars.length-1].d;
    const f = s.fwd || [];
    const cum = f.length ? f[f.length-1]['chg%'] : null;
    const maxh = f.length ? Math.max(...f.map(x=>x['high%'])) : null;
    const cumTxt = cum==null ? '<span style="color:#6e7681">待验证</span>'
      : `<span style="color:${cum>=0?'#f0524d':'#26a69a'}">${cum>=0?'+':''}${cum.toFixed(2)}%</span>`;
    const maxTxt = maxh==null ? '<span style="color:#6e7681">--</span>'
      : `<span style="color:#f0524d">+${maxh.toFixed(2)}%</span>`;
    const dv = s.div || {};
    const dvTxt = dv.is ? '<span style="color:#f0524d">是</span>' : '<span style="color:#6e7681">否</span>';
    const dvTitle = dv.prev_date ? `对比前低 ${dv.prev_date}（${dv.prev_low}，DIF ${dv.prev_dif.toFixed(1)}）：更低低点=${dv.lower_low}，DIF更高=${dv.higher_dif}` : '';
    const da = s.div_area || {}, ds = s.div_swing || {};
    const daTxt = da.is ? '<span style="color:#f0524d">是</span>' : '<span style="color:#6e7681">否</span>';
    const dsTxt = ds.is ? '<span style="color:#f0524d">是</span>' : '<span style="color:#6e7681">否</span>';
    const daTitle = da.area_prev!=null ? `本次绿柱面积 ${da.area_now.toFixed(1)}，上一波 ${da.area_prev.toFixed(1)}；价格新低=${da.lower_low}，面积更小=${da.smaller_area}` : '';
    const dsTitle = ds.prev_date ? `对比摆动低点 ${ds.prev_date}（${ds.prev_low}，DIF ${ds.prev_dif.toFixed(1)}）：价格新低=${ds.lower_low}，DIF更高=${ds.higher_dif}` : '';
    const unconf = s.confirmed===false ? '<span style="color:#e8c35a">*</span>' : '';
    return `<tr class="${cur?'cur':''}">
      <td><div class="nm">${s.name.replace(/^节点(\d) · /, (m,d)=>"①②③④"[+d-1]+" ")}</div><div class="dt">${s.date}${cur?' · 最新':''}</div></td>
      <td>${fmt(s.o)}</td><td>${fmt(s.h)}</td><td>${fmt(s.l)}</td><td>${fmt(s.c)}</td>
      <td>${fmt(s.lower_shadow)}</td><td>${s.lower_share.toFixed(1)}%</td>
      <td style="color:${s.dif>=0?'#f0524d':'#26a69a'}">${s.dif.toFixed(2)}</td>
      <td>${s.dea.toFixed(2)}</td>
      <td style="color:${s.hist>=0?'#f0524d':'#26a69a'}">${s.hist.toFixed(2)}</td>
      <td title="${dvTitle}">${dvTxt}</td>
      <td title="${daTitle}">${daTxt}</td>
      <td title="${dsTitle}">${dsTxt}${unconf}</td>
      <td>${(s.au_v/10000).toFixed(1)}</td><td>${(s.au_oi/10000).toFixed(1)}</td>
      <td style="color:${s.au_ratio>=1.5?'#f0524d':'#c9d1d9'}">${s.au_ratio.toFixed(2)}×</td>
      <td>${cumTxt}</td><td>${maxTxt}</td>
    </tr>`;
  }).join('');

  const hist = SIG.filter(s=>s.fwd && s.fwd.length);
  if(hist.length){
    const d1 = hist.map(s=>s.fwd[0]['chg%']);
    const d3 = hist.map(s=>s.fwd[s.fwd.length-1]['chg%']);
    const mx = hist.map(s=>Math.max(...s.fwd.map(x=>x['high%'])));
    const pos1 = d1.filter(x=>x>0).length, pos3 = d3.filter(x=>x>0).length;
    document.getElementById('sigsum').innerHTML =
      `<b>历史三次的共同点</b>：信号日当天全部留下长下影（占振幅 25.6%~70.4%），沪金量比 1.02×~2.77×。` +
      `信号后 <b>D+1 全部收涨</b>（${d1.map(x=>(x>=0?'+':'')+x.toFixed(2)+'%').join(' / ')}，${pos1}/${hist.length}）；` +
      `<b>D+3</b> 有 ${pos3}/${hist.length} 仍为正（${d3.map(x=>(x>=0?'+':'')+x.toFixed(2)+'%').join(' / ')}）；` +
      `3 日内最大反弹 ${mx.map(x=>'+'+x.toFixed(2)+'%').join(' / ')}。` +
      `<br><b>三种背离口径结论不同</b>：严格口径 ${hist.filter(x=>x.div&&x.div.is).length}/${hist.length}、` +
      `绿柱面积 ${hist.filter(x=>x.div_area&&x.div_area.is).length}/${hist.length}、` +
      `摆动低点 ${hist.filter(x=>x.div_swing&&x.div_swing.is).length}/${hist.length}。` +
      `历史上只有 ③（06-24）被面积法识别为背离，严格口径与摆动法均为否。` +
      `<br><b>当前节点（${SIG[SIG.length-1].date}）</b>：面积法 ${SIG[SIG.length-1].div_area.is?'<span style="color:#f0524d">是</span>':'否'}` +
      `（${SIG[SIG.length-1].div_area.area_now.toFixed(1)} vs 上一波 ${SIG[SIG.length-1].div_area.area_prev.toFixed(1)}），` +
      `摆动法 ${SIG[SIG.length-1].div_swing.is?'<span style="color:#f0524d">是</span>':'否'}` +
      `（前低 ${SIG[SIG.length-1].div_swing.prev_date}，${SIG[SIG.length-1].div_swing.prev_low}）；` +
      `但这是最新一根K线，<b>右侧未确认</b>，且本轮下跌未走完、绿柱面积仍会继续累加，此时判背离偏早。`;
  }
}

function renderMatrix(){
  const SIG = DATA.signals || [];
  const box = document.getElementById('mtx');
  // 保护：signals.json 缺失/为空时不能让整个页面 JS 崩掉（2026-10-30）
  if(!SIG.length){
    box.innerHTML = '<div style="color:#6e7681;font-size:12px;padding:10px;border:1px dashed #2b3440;border-radius:6px">信号数据未生成（signals.json 缺失），其余模块不受影响</div>';
    return;
  }
  const rows = SIG.map((s,ix)=>{
    const cur = s.date === bars[bars.length-1].d;
    const A = s.lower_share >= 25;
    const B = s.au_ratio >= 1.5;
    const C = !!(s.hist_turn && s.hist_turn.days <= 3);
    const sc = [A,B,C].filter(Boolean).length;
    const mk=(ok,label,val)=>`<div class="mrow"><span class="dot ${ok?'ok':'no'}"></span>${label}<span class="v">${val}</span></div>`;
    return `<div class="mcard ${cur?'cur':''}">
      <div class="h"><span class="n">${'①②③④'[ix]||''} ${s.date.slice(5)}</span><span class="sc"><b>${sc}</b>/3</span></div>
      ${mk(A,'长下影', s.lower_share.toFixed(0)+'% 振幅')}
      ${mk(B,'真实放量', s.au_ratio.toFixed(2)+'×')}
      ${mk(C,'MACD 动能', s.hist_turn? 'D+'+s.hist_turn.days+' 收窄' : '未收窄')}
    </div>`;
  }).join('');
  box.innerHTML = rows;

  const last = SIG[SIG.length-1];
  const A = last.lower_share >= 25, B = last.au_ratio >= 1.5;
  const C = !!(last.hist_turn && last.hist_turn.days <= 3);
  const sc = [A,B,C].filter(Boolean).length;
  const p = live.price;
  const _v60 = bars.slice(-60);
  const _hi = Math.max(..._v60.map(b=>b.h)), _lo = Math.min(..._v60.map(b=>b.l));
  const sp = _hi>_lo ? (p-_lo)/(_hi-_lo)*100 : null;
  const inLow = sp!=null && sp<=20;
  const h0 = MACD.hist[MACD.hist.length-1], h1 = MACD.hist[MACD.hist.length-2];
  const shrinking = h0 > h1;
  document.getElementById('disttxt').innerHTML =
    `当前 ${fmt(p)} · 60 日区间位置 <b>${sp!=null?sp.toFixed(0)+'%':'--'}</b>：<b>${inLow?'已在低位区':'仍在区间中部/高位'}</b>`;
  document.getElementById('distpct').textContent = `共振 ${sc}/3 · ${(sc/3*100).toFixed(0)}%`;
  document.getElementById('pbar').style.width = (sc/3*100)+'%';
  const miss = [];
  if(!C) miss.push('① MACD 负柱未收窄（当前 '+h0.toFixed(2)+'，前一日 '+h1.toFixed(2)+'，'+(shrinking?'已收窄':'仍在扩大')+'）');
  if(!inLow) miss.push('② 价格未进入近 60 日低位区（当前位置 '+(sp!=null?sp.toFixed(0):'--')+'%，需 ≤20%）');
  const have = [];
  have.push('长下影 '+(A?'已达标 ':'未达标 ')+last.lower_share.toFixed(1)+'%');
  have.push('量比 '+(B?'已达标 ':'未达标 ')+last.au_ratio.toFixed(2)+'×');
  document.getElementById('miss').innerHTML =
    `<b style="color:#c9d1d9">已具备</b>：${have.join('　·　')}<br>` +
    `<b style="color:#f0524d">缺口</b>：${miss.length?miss.join('；'):'无，三项已同时满足'}`;
}

function renderRadar(){
  const R = DATA.radar || [];
  if(!R.length) return;
  const cur = R[R.length-1];
  const d = cur.day;
  const yes = '<span style="color:#f0524d">是</span>', no = '<span style="color:#6e7681">否</span>';
  const card=(title,ok,main,sub,na)=>{
    const st = na?'na':(ok?'ok':'no');
    const tx = na?'待确认':(ok?'达标':'未达标');
    const cl = na?'#e8c35a':(ok?'#f0524d':'#6e7681');
    return `<div class="rc"><div class="t"><span class="dot ${st}"></span>${title}<span style="margin-left:auto;color:${cl}">${tx}</span></div><div class="m"><b>${main}</b><br>${sub}</div></div>`;
  };
  const s1=d.space, s2=d.momentum, s3=d.pattern, s4=d.volume;
  document.getElementById('radarcards').innerHTML =
    card('空间状态', s1.ok, `60日区间位置 ${s1.pos60.toFixed(0)}%`, `偏离MA20 ${s1.dev20.toFixed(2)}% · 布林下轨 ${s1.below_lower?'已跌破（仅超卖提示）':'未跌破'}`) +
    card('动能状态', s2.ok, `面积背离 ${s2.area_div?'是':'否'} · 绿柱缩短 ${s2.shrink} 天`, `本次面积 ${s2.area_now!=null?s2.area_now.toFixed(1):'--'} / 上波 ${s2.area_prev!=null?s2.area_prev.toFixed(1):'--'}`) +
    card('形态状态', s3.ok, `小实体连续 ${s3.streak} 天`, `阳包阴 ${s3.engulf?'是':'否'} · 不创新低 ${s3.no_new_low?'是':'否'} · 实体占比 ${s3.body_pct.toFixed(0)}%`) +
    card('量能状态', s4.ok,
      (s4.measured===false?'沪金当日数据未出':`量比 ${s4.ratio!=null?s4.ratio.toFixed(2)+'×':'--'}`),
      (s4.measured===false?'未测得 ≠ 不达标：此项不参与打分，须动能+形态同时成立才亮灯'
        :`地量 ${s4.dry?'是':'否'} · 温和放量收阳 ${s4.mild_up?'是':'否'} · 放量暴跌 ${s4.blowoff?'是':'否'}`),
      s4.measured===false);

  document.getElementById('wtb').innerHTML = R.map((n,ix)=>{
    const color=['#5b8dee','#26a69a','#e8c35a','#f0524d'][ix];
    const ws = n.window.slice();
    while(ws.length < 6) ws.push({d:'', score:null});
    const chips = ws.map(w=>{
      if(w.score==null) return `<div class="chip" style="background:transparent;border-style:dashed"><span class="dd">--</span><span class="sc" style="color:#4a5563">待验证</span></div>`;
      const sc=w.score;
      const bg = sc>=3?'rgba(240,82,77,.14)': sc==2?'rgba(232,195,90,.10)':'#12171e';
      const col = sc>=3?'#f0524d': sc==2?'#e8c35a':'#6e7681';
      const mark = w.d===n.date?'font-weight:700;border-color:'+color:'';
      return `<div class="chip" style="background:${bg};${mark}"><span class="dd">${w.d.slice(5)}</span><span class="sc" style="color:${col}">${sc}/4</span></div>`;
    }).join('');
    return `<div class="wrow"><div class="lb" style="color:${color}">${n.name.replace(/^节点(\d) · /,(m,x)=>"①②③④"[+x-1]+" ")}</div>${chips}</div>`;
  }).join('') + `<div style="font-size:11px;color:#6e7681;margin-top:8px">每格为该交易日四项规则的达标数（0–4），加粗格为信号日；T-2 ~ T+3，共 6 个交易日。</div>`;
}

/* ============ 黄灯轮次 · 分仓防呆 ============ */
function yseqState(){
  const Y = DATA.yseq; if(!Y || !Y.cur) return null;
  const c = Y.cur;
  const seq = c.lit ? (c.curSeq || 1) : (c.nextSeq || 1);
  const map = {
    1: {pos:'30%', nm:'首次亮灯 · 左侧侦察仓', short:'侦察 30%', col:'#e8c35a'},
    2: {pos:'30%', nm:'二次探底 · 可加仓',     short:'加仓 30%', col:'#f59e0b'},
    3: {pos:'40%', nm:'多次磨底 · 右侧确认重仓',short:'重仓 40%', col:'#f0524d'},
  };
  const m = map[seq] || {pos:'0%', nm:'第 4 次及以上 · 禁止加仓', short:'禁止加仓', col:'#6e7681'};
  return {seq, pos:m.pos, nm:m.nm, short:m.short, col:m.col, cur:c, lit:!!c.lit};
}

function renderYseq(){
  const box = document.getElementById('yseqBox'); if(!box) return;
  const Y = DATA.yseq; if(!Y || !Y.cur){ box.innerHTML=''; return; }
  const c = Y.cur, G = Y.groups || {};
  const ys = yseqState();
  const target = ys.seq;
  const defs = [
    {k:'1',  t:'第 1 次', act:'左侧侦察仓', pos:'30%', col:'#e8c35a'},
    {k:'2',  t:'第 2 次', act:'二次探底加仓', pos:'30%', col:'#f59e0b'},
    {k:'3',  t:'第 3 次', act:'趋势确认重仓', pos:'40%', col:'#f0524d'},
    {k:'4+', t:'第 4 次 +', act:'禁止加仓', pos:'0%',  col:'#6e7681'},
  ];
  const cards = defs.map(d=>{
    const g = G[d.k] || {n:0};
    const on = (d.k==='4+' ? target>=4 : target===+d.k);
    const w20 = g.n ? g.w20.toFixed(0)+'%' : '--';
    const a20 = g.n ? (g.a20>=0?'+':'')+g.a20.toFixed(1)+'%' : '--';
    return `<div style="border:1px solid ${on?d.col:'#232a34'};background:${on?'rgba(255,255,255,.04)':'#0d1117'};
      border-radius:9px;padding:9px 10px;position:relative;${on?'box-shadow:0 0 0 1px '+d.col+'33,0 4px 14px rgba(0,0,0,.35)':''}">
      <div style="display:flex;align-items:center;gap:6px">
        <span style="font-size:11px;color:${on?d.col:'#6e7681'};font-weight:${on?700:600}">${d.t}</span>
        ${on?`<span style="margin-left:auto;font-size:9px;color:#0b0e13;background:${d.col};padding:1px 5px;border-radius:6px;font-weight:700">当前</span>`:''}
      </div>
      <div style="font-size:17px;font-weight:700;color:${on?d.col:'#8b949e'};margin:4px 0 1px;letter-spacing:.3px">${d.pos}</div>
      <div style="font-size:10.5px;color:#7d8695">${d.act}</div>
      <div style="font-size:10px;color:#5a6371;margin-top:5px;line-height:1.5">
        ${g.n||0} 次 · 20日胜率 <span style="color:${on?'#c9d1d9':'#7d8695'}">${w20}</span><br>
        均值 <span style="color:${g.a20>=0?'#f0524d':'#26a69a'}">${a20}</span>
      </div>
    </div>`;
  }).join('');

  const litTxt = c.lit
    ? `<span style="color:#f0524d;font-weight:700">已亮灯 · 本轮第 ${c.curSeq} 次</span>`
    : `<span style="color:#6e7681">未亮灯</span>（${c.score}/${c.denom||4} 分，距 3 分还差 ${Math.max(0,3-c.score)} 项）`;
  const tipCol = ys.seq >= 4 ? '#f0524d' : ys.col;
  const nextTxt = c.lit
    ? `按纪律：<b style="color:${tipCol}">${ys.nm} · 建议 ${ys.pos}</b>`
    : `下一次亮灯 = <b style="color:${tipCol}">第 ${ys.seq} 次</b> → <b style="color:${tipCol}">${ys.short}</b>`;

  const wait = c.exemptWait || 20;
  let stopTxt;
  if(c.stopLow!=null && c.firstDate){
    const sl = c.stopLow;
    const under = (c.close / sl - 1) * 100;
    const buf = c.firstATR!=null ? `最低 ${c.firstLow} − 2.0×ATR ${(c.firstATR*2).toFixed(1)}` : `最低 ${c.firstLow}`;
    stopTxt = under <= 0
      ? `<b style="color:#f0524d">${sl}</b>（${c.firstDate.slice(5)} ${buf}）· 现价已跌破 ${under.toFixed(2)}% <b style="color:#f0524d">→ 按纪律止损，不死扛</b>`
      : `<b style="color:#e8c35a">${sl}</b>（${c.firstDate.slice(5)} ${buf}）· 现价距此 <b>${under.toFixed(2)}%</b> → 收盘跌破即走`;
  } else {
    stopTxt = `<span style="color:#6e7681">亮灯后自动给出（= 该黄灯日最低价 − 2.0×ATR）</span>`;
  }
  let exTxt;
  if(c.exempt){
    exTxt = `<b style="color:#e8c35a">已触发 · 可把剩余仓位补至 60%（不补满）</b>`;
  } else if(!c.firstDate){
    exTxt = `<span style="color:#6e7681">本轮尚未亮首灯 · 无条件可判</span>`;
  } else if((c.roundEvents||0) > 1){
    exTxt = `<span style="color:#6e7681">不适用 · 本轮已有第 2 盏灯，按 30/30/40 正常加仓</span>`;
  } else if((c.daysSinceFirst||0) < wait){
    exTxt = `<span style="color:#6e7681">等待中 · 首灯 ${c.firstDate}，已过 ${c.daysSinceFirst} 天，满 ${wait} 天再看金叉</span>`;
  } else if(!c.goldDate){
    exTxt = `<span style="color:#6e7681">条件不足 · 首灯已 ${c.daysSinceFirst} 天，但 MA20 还没上穿 MA60（差 ${(c.ma20Above60?0:Math.abs((c.ma20/c.ma60-1)*100)).toFixed(1)}%）</span>`;
  } else {
    exTxt = `<span style="color:#6e7681">金叉已现 ${c.goldDate}，等待满 ${wait} 天</span>`;
  }

  const deepWarn = (target===1 && c.gap <= -4) ? `
    <div style="margin-top:9px;border:1px solid #5a1f1c;background:linear-gradient(90deg,rgba(240,82,77,.13),rgba(240,82,77,.03));
      border-radius:9px;padding:10px 12px;line-height:1.7">
      <div style="color:#f0524d;font-weight:700;font-size:12px">${c.lit?'⚠ 深水首灯警告':'⚠ 深水区预警 · 下一盏若亮即为深水首灯'} · 偏离 MA60 ${c.gap}%</div>
      <div style="font-size:11px;color:#c9a3a0;margin-top:4px">
        历史 7 次「首次亮灯 + 偏离超 -4%」：+10 日胜率 <b style="color:#e8c35a">71.4%</b>、20 日均值 <b style="color:#f0524d">+2.32%</b>（中位数 +2.28%），短线弹性是全场最好的一档 —— <b>不是</b>半山腰高发区。
        但 20 日内收盘最大回撤曾达 <b style="color:#e8c35a">-9.16%</b>。所以：<b style="color:#f0524d">仓位封顶 30%，止损设在黄灯日最低价 − 2.0×ATR（收盘跌破即走），浮亏时严禁补仓</b>。
        深水区只赚反弹，不赌反转。
      </div>
    </div>` : '';

  const banWarn = (target>=4) ? `
    <div style="margin-top:9px;border:1px solid #5a1f1c;background:rgba(240,82,77,.08);border-radius:9px;padding:10px 12px;line-height:1.7">
      <div style="color:#f0524d;font-weight:700;font-size:12px">⚠ 第 ${target} 次亮灯 · 红色禁令</div>
      <div style="font-size:11px;color:#c9a3a0;margin-top:4px">
        历史「第 4 次及以上」共 8 次：+5 日胜率仅 <b style="color:#26a69a">12.5%</b>、+20 日胜率 <b style="color:#26a69a">37.5%</b>、20 日均值 <b style="color:#26a69a">-1.07%</b>。
        真正的半山腰不是第一次，是<b>第四次以后</b> —— 阴跌钝刀，黄灯靠「位置低」反复触发却没有反弹动能。<b style="color:#f0524d">禁止加仓，已有仓位只减不加。</b>
      </div>
    </div>` : '';

  box.innerHTML = `
  <div style="border:1px solid #232a34;background:#0b0e13;border-radius:11px;padding:12px 13px">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px">
      <span style="font-size:12.5px;color:#c9d1d9;font-weight:600">黄灯轮次 · 分仓防呆</span>
      <span style="font-size:10px;color:#6e7681">间隔 ≥${(Y.params&&Y.params.gap)||10} 个交易日算新一轮 · 连续 ${(Y.params&&Y.params.hold)||10} 日站上 MA60 则计数清零</span>
      <span style="margin-left:auto;font-size:10px;color:#6e7681">历史 ${Y.events?Y.events.length:0} 次黄灯</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px" class="yseqgrid">${cards}</div>
    <div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:10px;font-size:11.5px;color:#9aa4b2">
      <div>${c.date}　${litTxt}</div>
      <div>偏离 MA60 <b style="color:${c.gap<=-4?'#26a69a':'#c9d1d9'}">${c.gap}%</b></div>
      <div>上次亮灯 <b style="color:#c9d1d9">${c.lastDate}</b>（第 ${c.lastSeq} 次 · ${c.sinceDays} 个交易日前）</div>
    </div>
    <div style="margin-top:7px;font-size:11.5px">${nextTxt}</div>
    <div style="margin-top:7px;padding-top:7px;border-top:1px dashed #232a34;font-size:11px;line-height:1.75">
      <b style="color:#c9d1d9">踏空豁免</b>：${exTxt}<br>
      <span style="color:#5a6371">规则：首灯后 ${wait} 个交易日仍无二灯，且 MA20 上穿 MA60 → 补至 <b style="color:#8b949e">60%</b>，不补满。依据：该金叉 2011–2026 出现 35 次，+20 日胜率 60%、均值 +1.42%、平均最大浮亏 -2.43%；只亮一次就 V 反的情况 15 年只有 2 次（3.7%）。</span>
    </div>
    <div style="margin-top:6px;padding-top:7px;border-top:1px dashed #232a34;font-size:11px;line-height:1.75">
      <b style="color:#c9d1d9">试仓止损位</b>：${stopTxt}<br>
      <span style="color:#5a6371">别等 MA60 深红 —— 那时平均已亏 5.64%、要等 22 天。跌破「最低价 − 2.0×ATR」走：23 次首灯里被扫 9 次，平均亏 3.85%、26 天见分晓。</span>
    </div>
    ${deepWarn}${banWarn}
  </div>`;
}

function drawRadar(){
  const R = DATA.radar || []; if(!R.length) return;
  const cv=document.getElementById('cvRadar');
  const dpr=window.devicePixelRatio||1, W=cv.clientWidth, H=250;
  cv.width=W*dpr; cv.height=H*dpr;
  const ctx=cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
  const cx=W/2, cy=H/2-6, R0=Math.min(W,H)/2-54;
  const axes=['空间','动能','形态','量能'];
  const ang=[-Math.PI/2, 0, Math.PI/2, Math.PI];

  for(let ring=1; ring<=4; ring++){
    const r=R0*ring/4;
    ctx.beginPath();
    for(let i=0;i<4;i++){
      const x=cx+Math.cos(ang[i])*r, y=cy+Math.sin(ang[i])*r;
      i?ctx.lineTo(x,y):ctx.moveTo(x,y);
    }
    ctx.closePath(); ctx.strokeStyle = ring==4?'#2b3440':'#1c232c'; ctx.lineWidth=1; ctx.stroke();
  }
  ctx.font='11px -apple-system,sans-serif'; ctx.textAlign='center'; ctx.fillStyle='#8b949e';
  axes.forEach((t,i)=>{
    const x=cx+Math.cos(ang[i])*(R0+20), y=cy+Math.sin(ang[i])*(R0+20)+4;
    ctx.fillText(t,x,y);
  });

  const colors=['#5b8dee','#26a69a','#e8c35a','#f0524d'];
  R.forEach((n,ix)=>{
    const d=n.day;
    const vals=[d.space.ok,d.momentum.ok,d.pattern.ok,d.volume.ok].map(x=>x?1:0.12);
    ctx.beginPath();
    vals.forEach((v,i)=>{
      const r=R0*v, x=cx+Math.cos(ang[i])*r, y=cy+Math.sin(ang[i])*r;
      i?ctx.lineTo(x,y):ctx.moveTo(x,y);
    });
    ctx.closePath();
    ctx.fillStyle=colors[ix]+'22'; ctx.fill();
    ctx.strokeStyle=colors[ix]; ctx.lineWidth=1.6; ctx.stroke();
    vals.forEach((v,i)=>{
      const r=R0*v, x=cx+Math.cos(ang[i])*r, y=cy+Math.sin(ang[i])*r;
      ctx.beginPath(); ctx.arc(x,y,2.6,0,Math.PI*2); ctx.fillStyle=colors[ix]; ctx.fill();
    });
  });

  // 图例
  let lx=10, ly=H-8;
  ctx.font='10px -apple-system,sans-serif'; ctx.textAlign='left';
  R.forEach((n,ix)=>{
    ctx.fillStyle=colors[ix]; ctx.fillRect(lx,ly-6,12,2.5);
    ctx.fillStyle='#8b949e'; ctx.fillText(n.date.slice(5), lx+16, ly-1);
    lx += 58;
  });
}

function renderCrash(){
  const c = (DATA.bt||{}).latest_crash; if(!c) return;
  const card=(title,ok,main,sub)=>`<div class="rc"><div class="t"><span class="dot ${ok?'ok':'no'}"></span>${title}<span style="margin-left:auto;color:${ok?'#f0524d':'#6e7681'}">${ok?'满足':'不满足'}</span></div><div class="m"><b>${main}</b><br>${sub}</div></div>`;
  document.getElementById('crashcards').innerHTML =
    card('空间极速下坠', c.space, `3日 ${c.ret3.toFixed(2)}% · 5日 ${c.ret5.toFixed(2)}%`, `${c.below?'已跌破布林下轨':'未跌破布林下轨'}`) +
    card('K线极度恐慌', c.panic, `下影占振幅 ${c.ls.toFixed(1)}%`, `阳吞阴 ${c.engulf?'是':'否'}（阈值：下影>50% 或 暴跌次日反包）`) +
    card('量能爆发', c.vol, `量比 ${c.ratio.toFixed(2)}×`, `20日新高量 ${c.newhigh?'是':'否'} · 阈值：≥1.5× 且创20日新高`) +
    card('动能止扩', c.mom, `绿柱 ${c.hist.toFixed(2)}`, `前一日 ${c.hist_prev.toFixed(2)} · ${c.hist>c.hist_prev?'已收窄':'仍在放大'}`);
  const trig = c.space && c.panic && c.vol;
  document.getElementById('crashsum').innerHTML =
    `<b style="color:#c9d1d9">当前 ${c.date}</b>：${c.score}/4 项满足，<b style="color:${trig?'#f0524d':'#8b949e'}">${trig?'暴跌信号已触发':'未触发'}</b>。` +
    `触发条件是「空间 + 恐慌 + 天量」三项同时成立；动能项只作辅助，不参与触发。` +
    `<br><span style="color:#6e7681">注：以最近一个完整交易日收盘计算；盘中数据未计入。</span>`;
}

function renderBacktest(){
  const bt = DATA.bt; if(!bt || !bt.crash) return;
  const items=[['暴跌雷达（空间+恐慌+天量）',bt.crash],['暴跌雷达（不含天量）',bt.novol],
               ['磨底雷达（≥3 分）',bt.mo],['磨底雷达（≥3 分且空间达标）',bt.mo3s],
               ['磨底雷达（4 分满分）',bt.mo4]];
  const col=v=> v==null?'#6e7681':(v>=0?'#f0524d':'#26a69a');
  document.getElementById('bttb').innerHTML = items.map(([name,st])=>{
    if(!st) return '';
    const c5=st['5'], c10=st['10'], c20=st['20'];
    return `<tr><td style="text-align:left">${name}</td><td>${st.n}</td>
      <td>${c5.win.toFixed(1)}%</td><td style="color:${col(c5.avg)}">${c5.avg>=0?'+':''}${c5.avg.toFixed(2)}%</td>
      <td>${c10.win.toFixed(1)}%</td><td style="color:${col(c10.avg)}">${c10.avg>=0?'+':''}${c10.avg.toFixed(2)}%</td>
      <td>${c20.win.toFixed(1)}%</td><td style="color:${col(c20.avg)}">${c20.avg>=0?'+':''}${c20.avg.toFixed(2)}%</td>
      <td style="color:#f0524d">+${c20.maxup.toFixed(2)}%</td><td style="color:#26a69a">${c20.maxdown.toFixed(2)}%</td></tr>`;
  }).join('');

  const evs=[...bt.crash_rows.map(r=>({...r,radar:'暴跌'})), ...bt.mo_rows.map(r=>({...r,radar:'磨底'}))]
    .sort((a,b)=> a.d<b.d?1:-1);
  const paint=(f)=>{
    const rows = evs.filter(r=> f==='all' || (f==='crash'&&r.radar==='暴跌') || (f==='mo'&&r.radar==='磨底') || (f==='true'&&r.cls==='真底') || (f==='false'&&r.cls==='假底'));
    document.getElementById('evtb').innerHTML = rows.map(r=>{
      const clsCol = r.cls==='真底'?'#f0524d': r.cls==='假底'?'#26a69a':'#8b949e';
      const r0=x=> x==null?'--':`<span style="color:${x>=0?'#f0524d':'#26a69a'}">${x>=0?'+':''}${x.toFixed(2)}%</span>`;
      return `<tr><td style="text-align:left;color:${r.radar==='暴跌'?'#e8c35a':'#5b8dee'}">${r.radar}</td>
        <td>${r.d}</td><td>${r.score}</td><td>${r0(r.r5)}</td><td>${r0(r.r10)}</td><td>${r0(r.r20)}</td>
        <td style="color:#f0524d">${r.u20==null?'--':'+'+r.u20.toFixed(2)+'%'}</td>
        <td style="color:#26a69a">${r.d20==null?'--':r.d20.toFixed(2)+'%'}</td>
        <td style="color:${clsCol}">${r.cls}</td></tr>`;
    }).join('');
    document.getElementById('btcount').textContent = `显示 ${rows.length} / ${evs.length} 条`;
  };
  document.querySelectorAll('#btfilters button').forEach(b=>{
    b.onclick=()=>{
      document.querySelectorAll('#btfilters button').forEach(x=>x.classList.remove('on'));
      b.classList.add('on'); paint(b.dataset.f);
    };
  });
  paint('all');

  const z=bt.counts;
  document.getElementById('btsum').innerHTML =
    `<b>总账</b>：暴跌雷达 15 年只触发 <b>${z.crash}</b> 次（去掉天量后 ${z.novol} 次），磨底雷达 ≥3 分触发 <b>${z.mo}</b> 次（4 分满分仅 ${z.mo4} 次）。` +
    `暴跌雷达 20 日胜率 ${bt.crash['20'].win.toFixed(1)}%、均值 ${bt.crash['20'].avg>=0?'+':''}${bt.crash['20'].avg.toFixed(2)}%、最大反弹均值 +${bt.crash['20'].maxup.toFixed(2)}%；` +
    `磨底雷达 20 日胜率 ${bt.mo['20'].win.toFixed(1)}%、均值 ${bt.mo['20'].avg>=0?'+':''}${bt.mo['20'].avg.toFixed(2)}%、最大反弹均值 +${bt.mo['20'].maxup.toFixed(2)}%。` +
    `<br><span style="color:#6e7681">暴跌样本过少（${z.crash} 次），胜率不具备统计显著性；磨底触发频繁，优势接近随机。详见上方两表。</span>`;
}

function renderUpgrade(){
  const U = DATA.up || {}; if(!U.crash) return;
  const rows=[
    ['暴跌 · 原始触发', U.crash.raw],
    ['暴跌 · +右侧确认', U.crash.conf],
    ['暴跌 · +确认+位置', U.crash.confpos_trig],
    ['磨底≥3 · 原始（仅预警）', U.mo.raw],
    ['磨底≥3 · +右侧确认', U.mo.conf],
    ['磨底≥3 · +确认+位置', U.mo.confpos_trig],
    ['磨底4分 · 原始', U.mo4.raw],
    ['磨底4分 · +确认+位置', U.mo4.confpos],
  ];
  const col=v=> v>=0?'#f0524d':'#26a69a';
  document.getElementById('uptb').innerHTML = rows.map(([name,s])=>{
    if(!s || !s.n) return `<tr><td style="text-align:left">${name}</td><td>0</td><td colspan="6" style="color:#6e7681">无样本</td></tr>`;
    const f=n=>s[String(n)];
    const pf = f(20).payoff==null?'∞':f(20).payoff.toFixed(2);
    return `<tr><td style="text-align:left">${name}</td><td>${s.n}</td>
      <td>${f(5).win.toFixed(1)}%</td><td>${f(10).win.toFixed(1)}%</td><td>${f(20).win.toFixed(1)}%</td>
      <td style="color:${col(f(20).avg)}">${f(20).avg>=0?'+':''}${f(20).avg.toFixed(2)}%</td>
      <td>${pf}</td><td style="color:#26a69a">${f(20).maxdn.toFixed(2)}%</td></tr>`;
  }).join('');

  document.getElementById('upsum').innerHTML =
    `<b>三条结论</b>：① <b>右侧确认对暴跌雷达是质变</b>——5/10 日胜率 60% → 100%，5 日最大回撤 -4.35% → -1.48%、20 日 -2.39%；代价是 20 日均值 +4.32% → +3.66%（位置过滤后仅 +1.32%），因为确认要等，价格已反弹一截。` +
    `② <b>右侧确认救不了磨底雷达</b>——单独加确认，20 日胜率 55.6% → 53.8%，不升反降；再加位置过滤，5/10 日升到 58.8%/64.7%，但 20 日仅 52.9%、均值 +0.49%，样本从 99 砍到 17。` +
    `③ <b>唯一全面改善的是「磨底 4 分 + 确认 + 低位」</b>：20 日胜率 46.2% → 71.4%、均值 +1.60%、盈亏比 1.75、回撤 -2.59%——但只剩 7 个样本。` +
    `<br><span style="color:#6e7681">基准：同期随机日 20 日胜率 53.6%、均值 +0.64%。当前位置过滤用「MA120 偏离 ≤ -15% 或 近 250 日区间底部 20%」；位置在触发日判定（入场日判定样本更少，结论相近）。</span>`;
}

const SELL_TYPES=['ma20','ma60','ultimate','topbreak','top'];
let PHASE = localStorage.getItem('gold_phase') || 'left';
let previewIdx = 0;

function intraScores(){
  const I=DATA.intra||{};
  const G=I.gate||{};
  return {s1:(I.h1&&I.h1.score)||0, s4:(I.h4&&I.h4.score)||0, h1:I.h1, h4:I.h4,
          gate:G, gateOk:!!G.allow, gateTrend:G.trend||'unknown', gateLabel:G.label||''};
}

function dailyState(){
  const c=(DATA.bt||{}).latest_crash;
  const R=DATA.radar||[]; const m=R[R.length-1];
  const price=live.price;
  const crash=!!(c && c.score>=3 && c.confirm);
  const mo=!!(m && m.day.score>=3 && m.day.space && m.day.space.ok);
  return {c,m,price,crash,mo,daily:(crash||mo)};
}

function alertState(){
  const d=dailyState(); const i=intraScores();
  const T=DATA.top||{}; const ts=T.score||0;
  const red3 = i.s1>=2 && i.s4>=2 && d.daily;
  const gateOk = !!i.gateOk;
  const blue2 = gateOk && i.s1>=2 && i.s4>=2 && !d.daily;
  const blue1 = gateOk && (i.s1>=2 || i.s4>=2) && !red3 && !blue2;
  const top3 = ts>=3;
  const topBreak = ts>=3 && T.detail && T.detail.below_ma20;
  const M=DATA.ma||{};
  const S=DATA.stop||{};
  return {...d, ...i, gateOk, red3, blue2, blue1, T, ts, top3, topBreak, M, S,
          ma20break:!!M.high20break, low20break:!!M.low20break, pos120:(M.pos120!=null?M.pos120:null), ma60break:!!M.below60, ultimate:!!M.ultimate,
          shallow60:!!M.shallow60, reclaim20:!!M.reclaim20, m60days:M.below60_days||0,
          ma60act:M.ma60_action||'', env:M.env||'', zone:M.zone||'', pos250:(M.pos250!=null?M.pos250:null),
          trailHit:!!S.trigger, trailPaused:!!(S.below_trail && S.paused), phase:PHASE};
}

function renderDefense(){
  const M=DATA.ma||{}; const S=DATA.stop||{}; const box=document.getElementById('defense');
  if(!M.date){ box.innerHTML=''; return; }
  const mute = PHASE==='left';
  const bull = PHASE==='bull';
  const pos = (M.pos120!=null) ? M.pos120 : null;
  // 第一顺位：MA20 —— 只有 120日位置 ≥70% 的高位破位才报警
  const c1 = mute?'muted':(M.reclaim20&&bull?'ok':(M.below20?(M.high20break?'orange':'muted'):'ok'));
  const d1v = M.below20 ? (M.high20break?'已跌破（高位）':'已跌破（低位）') : '守住';
  let d1a;
  if(mute) d1a='→ 仅显示数值（已静音）';
  else if(M.reclaim20&&bull) d1a='→ 已收回，可买回';
  else if(!M.below20) d1a='→ 持仓条件未破';
  else if(M.high20break) d1a='→ 高位破位，建议减仓一半';
  else d1a=`→ 位置 ${pos!=null?pos+'%':'--'}（&lt;70%），低位破位不报警`;
  // 第三顺位：MA60 —— 趋势线，左侧阶段也照常报警（静音只针对 MA20 / ATR）
  const act60 = M.ma60_action || (M.below60?'清仓':'守住');
  const c2 = (!M.below60?'ok'
    :((bull&&M.shallow60)?'orange'
      :(act60==='不动'?'muted':(act60==='减半'?'orange':'darkred'))));
  const d2a = (!M.below60?'→ 趋势未破'
      :((bull&&M.shallow60)?`→ 浅破 ${Math.abs(M.gap60)}%，观察 ${M.below60_days}/10 天`
        :(act60==='不动'?`→ 牛市高位破位，视为洗盘 · 不动`
          :(act60==='减半'?`→ ${M.env||''}市 · ${M.zone||''}位，减仓一半 · 已破 ${M.below60_days} 日`
            :`→ ${M.env||''} · ${M.zone||''}位，清仓离场 · 已破 ${M.below60_days} 日`))));
  // 第二顺位：ATR 锁利润线（辅助，非逃顶主力）
  const hasS = !!S.date;
  const c3 = (mute||S.fail)?'muted':(S.trigger?'orange':'ok');
  const d3v = !hasS ? '--' : (S.fail?'已失效':(S.below_trail?'线下':'线上'));
  const d3a = !hasS ? '→ 无数据'
    : (S.fail?'→ MA60 已破，本模块让位清仓线'
      :(S.trigger?'→ 触发，减仓一半（辅助）'
        :(S.below_trail?`→ 跌破但仍在 MA10 上方，暂停`
          :`→ 距线 ${S.gap_trail}%，可继续上移`)));
  box.innerHTML =
    `<div class="dcard ${c1}"><div class="dl">MA20<br><span style="font-size:9.5px;color:#5a6371">第一顺位</span></div>
      <div><div class="dv">${d1v}</div>
      <div class="dd">收盘 ${fmt(M.close)} · MA20 ${fmt(M.ma20)} · ${M.gap20>0?'+':''}${M.gap20}%<br>${d1a}</div></div></div>
     <div class="dcard ${c3}"><div class="dl">ATR<br><span style="font-size:9.5px;color:#5a6371">锁利润·辅助</span></div>
      <div><div class="dv">${d3v}</div>
      <div class="dd">追踪线 ${hasS&&S.trail?fmt(S.trail):'--'}${hasS&&S.gap_trail!=null?` · 距线 ${S.gap_trail}%`:''}<br>${d3a}<br><span style="color:#5a6371">非逃顶主力（看 MA20）</span></div></div></div>
     <div class="dcard ${c2}"><div class="dl">MA60<br><span style="font-size:9.5px;color:#5a6371">分层防守</span></div>
      <div><div class="dv">${M.below60?'已跌破':'守住'}</div>
      <div class="dd">收盘 ${fmt(M.close)} · MA60 ${fmt(M.ma60)} · ${M.gap60>0?'+':''}${M.gap60}%<br>${d2a}<br><span style="color:#5a6371">环境 ${M.env||'--'} · 距250日高 ${M.pos250!=null?M.pos250+'%':'--'}${M.dd8?' · <span style="color:#f0524d">已破 8% 回撤线第 '+M.dd8_days+' 日</span>':' · 8% 回撤线未破'}</span></div></div></div>`;
}

function fillVolEnv(){
  const V=DATA.volenv||{}; const v=document.getElementById('ampv'), s=document.getElementById('amps');
  if(!v||!s) return;
  if(V.amp==null){ v.textContent='--'; s.textContent='数据不足'; return; }
  const col = V.grade==='low'?'#e8c35a':(V.grade==='mid'?'#8b949e':'#58a6ff');
  const lbl = V.grade==='low'?'低波动 · 信号打折':(V.grade==='mid'?'中性 · 信号中等':'高波动 · 信号可信');
  v.innerHTML = `<span style="color:${col}">${V.amp.toFixed(2)}%</span>`;
  s.innerHTML = `<span style="color:${col}">${lbl}</span>` +
    (V.pct!=null?`<br>历史 ${V.pct}% 分位 · 中位 ${V.med}%`:`<br><span style="font-size:9.5px;color:#5a6371">分位待累积（样本 ${V.n||0} 天）</span>`);
}

function renderMacro(){
  const W=document.getElementById('macrowrap'); if(!W) return;
  const M=DATA.macroenv||{}, G=DATA.gld||{};
  if(!M.r){
    W.innerHTML='<div style="font-size:11.5px;color:#6e7681;padding:6px 0">实际利率数据未就绪（macro_hist.json 缺失）</div>'; return;
  }
  const rp=M.pct, hi=p=>p>=95, lo=p=>p<=5;
  const col = hi(rp)?'#f0524d':(rp>=75?'#e8c35a':(lo(rp)?'#26a69a':'#c9d1d9'));
  const bp=v=>(v>0?'+':'')+v+'bp';
  const bpc=v=>v>0?'#f0524d':(v<0?'#26a69a':'#8b949e');

  const cells=[
    {n:'金价见顶那天', a:M.peakR.toFixed(2)+'%', b:'→ '+M.r.toFixed(2)+'%',
     c:`<b style="color:${bpc(M.sincePeakBp)}">${bp(M.sincePeakBp)}</b> · 同期金价 ${M.sincePeakPx}%`,
     d:`${M.peakDate} 金价 ${M.peakPx} 美元时，利率只有 ${M.peakR.toFixed(2)}%。现在高出 ${Math.abs(M.sincePeakBp)}bp —— <b>这是这轮下跌真实的宏观推力</b>，不是纯技术回调。`},
    {n:'利率自己的高点', a:M.max.toFixed(2)+'%', b:'→ '+M.r.toFixed(2)+'%',
     c:`<b style="color:${bpc(M.rSinceTopBp)}">${bp(M.rSinceTopBp)}</b> · 同期金价 ${M.pxSinceTop}%`,
     d:`${M.maxDate} 利率见顶 ${M.max.toFixed(2)}%，之后回落 ${Math.abs(M.rSinceTopBp)}bp，<b>但金价同期又跌了 ${Math.abs(M.pxSinceTop)}%</b> —— 最近这段卖压已经不是利率驱动。`},
    {n:'极值程度', a:M.pct+'%', b:'分位',
     c:`17 年里高于 2.5% 的交易日只占 <b>${M.hiShare}%</b>`,
     d:`2010 年以来 ${M.n} 个交易日，区间 ${M.min}% ~ ${M.max}%。<b>现在的实际利率处在 17 年最高的一小撮里</b> —— 顺风谈不上，先看逆风什么时候停。`},
  ];

  // 风险温度：只回答「恐慌有多强、是不是黄金专属」，不产生信号
  const K=DATA.riskenv||{};
  let RK='';
  if(K.gvz!=null){
    const rc=v=>v>=80?'#f0524d':(v>=60?'#e8c35a':(v<=20?'#26a69a':'#c9d1d9'));
    const dlt=(v,u)=>`${v>0?'+':''}${v.toFixed(1)}${u}`;
    const goldOnly=K.goldOnly, isGoldOnly=K.ratio>1.3;
    RK=`<div class="rkgrid">
      <div class="rkcell"><div class="k">VIX · 股市恐慌</div>
        <div class="v" style="color:${rc(K.vixPct)}">${K.vix.toFixed(1)}</div>
        <div class="s">${K.vixPct}% 分位 · 20日 ${dlt(K.vix20,'')}</div></div>
      <div class="rkcell"><div class="k">GVZ · 黄金恐慌</div>
        <div class="v" style="color:${rc(K.gvzPct)}">${K.gvz.toFixed(1)}</div>
        <div class="s">${K.gvzPct}% 分位 · 20日 ${dlt(K.gvz20,'')}</div></div>
      <div class="rkcell"><div class="k">GVZ ÷ VIX · 谁更慌</div>
        <div class="v">${K.ratio.toFixed(2)}</div>
        <div class="s">${isGoldOnly?`<b style="color:#e8c35a">黄金更慌</b>`:'两者相当'} · 20日前 ${K.ratio20.toFixed(2)}</div></div>
    </div>
    <div class="rknote">${K.gvzPct>=75&&K.vixPct<60
      ? `<b style="color:#e8c35a">这轮下跌是黄金专属的，不是全市场风险事件</b>：股市恐慌只在中位（${K.vixPct}% 分位），黄金自己的恐慌却在 ${K.gvzPct}% 分位。所以「乱世买金」的逻辑这次没有兑现 —— <b>因为没有乱世</b>。真正在卖的是黄金自己的持仓，不是避险资金在涌入。`
      : (K.gvzPct>=75&&K.vixPct>=75
        ? `<b style="color:#f0524d">全市场在慌</b>：股市 ${K.vixPct}%、黄金 ${K.gvzPct}% 分位同时偏高，这是系统性风险释放。历史上这种状态的后续收益同样不优于基准，但波动会更大。`
        : `恐慌程度不高（VIX ${K.vixPct}%、GVZ ${K.gvzPct}% 分位）。${isGoldOnly?'黄金相对股市更慌，但绝对水平都不极端。':'两个市场都在常态区间。'}`)}
      <span style="color:#6e7681">「黄金比股市更慌」这种状态，历史上只占 <b>${goldOnly}%</b> 的交易日（${K.n} 日样本）。</span></div>`;
  }

  W.innerHTML=`
  <div style="display:flex;gap:16px;align-items:flex-end;flex-wrap:wrap;margin-bottom:11px">
    <div><div style="font-size:10.5px;color:#7d8594;margin-bottom:2px">10Y TIPS 实际利率</div>
      <div style="font-size:31px;font-weight:700;color:${col};line-height:1.05;font-variant-numeric:tabular-nums">${M.r.toFixed(2)}<span style="font-size:16px">%</span></div></div>
    <div style="font-size:11px;color:#8b949e;line-height:1.8;padding-bottom:3px">
      2010 以来 <b style="color:${col}">${M.pct}% 分位</b> · 区间 ${M.min}% ~ ${M.max}%<br>
      60 日 <b style="color:${bpc(M.d60)}">${bp(M.d60)}</b> ｜ 250 日 <b style="color:${bpc(M.d250)}">${bp(M.d250)}</b> —— ${M.d250>0?'钱在变贵，逆风在加强':'逆风在减弱'}
    </div>
  </div>
  <div class="mgrid">${cells.map(c=>`<div class="mcell"><div class="k">${c.n}</div>
    <div class="v">${c.a} <span style="font-size:11px;color:#7d8794;font-weight:400">${c.b}</span></div>
    <div class="s">${c.c}</div><div class="d">${c.d}</div></div>`).join('')}</div>

  ${RK}

  <div class="whybox">
    <div style="font-size:11.5px;color:#c9d1d9;margin-bottom:5px"><b style="color:#e8c35a">为什么它不做成买卖信号</b></div>
    <div style="font-size:11px;color:#8b949e;line-height:1.9">
      17 年实测：利率 60 日变化与金价未来 60 日收益的相关只有 <b>−0.03</b>（几乎为零）。
      按利率分档统计金价未来一年收益，甚至会得出「利率越高、金价越涨」的反向结论 ——
      因为 2–3% 那一档的样本几乎全部来自 2023 年以后的一段行情，它不是一个有 269 个独立观测的样本，
      只是<b>一段行情的 269 天</b>。时间序列上做分箱，本质是伪样本 —— 和磨底雷达在 1992–1998 失效是同一类错误。<br>
      <b style="color:#c9d1d9">所以它的正确用法只有两个</b>：① 知道逆风有多强（现在：17 年 99% 分位，很强）；
      ② 盯背离 —— 利率回落而金价继续跌，说明卖压另有来源，那才是需要重新判断的时候。
    </div>
    <div style="height:1px;background:#222b36;margin:9px 0"></div>
    <div style="font-size:11.5px;color:#c9d1d9;margin-bottom:5px"><b style="color:#e8c35a">上面那三个恐慌读数，也测过，同样不做信号</b></div>
    <div style="font-size:11px;color:#8b949e;line-height:1.9">
      <b style="color:#c9d1d9">① VIX 分档没有单调关系</b>：VIX &lt;14 时后 20 日胜率 <b>49%</b>、14–20 时 <b>54%</b>、20–30 时 <b>62%</b>、&gt;30 时 <b>54%</b> —— 基准 55%。
      最该出结论的「VIX &gt;30 恐慌」反而和基准一样，中间那档最高，这只能是噪声。<br>
      <b style="color:#c9d1d9">② GVZ &gt;30 那 126 天，拆开只有 9 段</b>：按日算 T+60 胜率 28%（看起来极强），<b>按段算 56%</b>，和基准 60% 没差别。
      28% 是 9 段里 3 段跌出来的（2022-03 −10%、2026-01 −3%、2013-04 −8%），不是 126 个独立样本 —— <b>和利率分档、1992–1998 磨底失效是同一个坑，这是第四次</b>。<br>
      <b style="color:#c9d1d9">③ GVZ÷VIX 阈值不稳健</b>：k 从 1.10 挨个测到 1.60，胜率 <b>41 / 50 / 54 / 44 / 30 / 42 / 40 / 55 / 54</b>。
      1.30 刚好是中间那个低点，往上挪 0.05 就变成 42%，挪到 1.50 又变 55%。<b>能靠挪阈值消失的规律，不叫规律。</b><br>
      <span style="color:#c9d1d9">所以这三个数只回答一件事</span>：<b>恐慌有多强、是不是黄金专属</b>。它解释「为什么这次避险买金没兑现」，不告诉你「什么时候会兑现」。
    </div>
  </div>

  <div class="msrc">
    <div><span class="on">✓ 实际利率</span>美财政部 TIPS 日频 · ${M.from} 起 ${M.n} 个交易日</div>
    <div><span class="on">✓ ETF 流向</span>GLD ${G.tonnes?G.tonnes+' 吨':'—'} · 20 日 ${G.chg20>0?'+':''}${G.chg20||'—'} 吨</div>
    <div><span class="on">✓ 风险温度</span>CBOE VIX ${K.vixMin||''}–${K.vixMax||''} / GVZ ${K.gvzMin||''}–${K.gvzMax||''} · ${K.n||'—'} 个交易日</div>
    <div class="cx"><span class="off">✗ 央行购金</span>数据拿到了（IMF IFS 官方储备实物量，中/俄/印/世界，1950 起 829 个月），<b>但实测没用</b>：中国 53 个「净买入月」拆开只有 <b>11 个独立买入段</b>，6 个月后胜率 <b>67%，低于</b>基准 71%；世界总储备<b>净减持</b>后 12 个月胜率 78%，比净买入还高 —— 方向都不对。加上免费源滞后 16 个月，<b>不进页面</b>。</div>
    <div class="cx"><span class="off">✗ 地缘指数</span>GPR 站点在本环境完全不可达；改用 VIX/GVZ 做代理已接（见上），<b>但只能做背景</b>。这一项到此为止，不再找源。</div>
  </div>`;
}

function renderSizing(){
  const g=id=>document.getElementById(id);
  const box=g('sizebox'), con=g('sizeconcl'); if(!box) return;
  const asset=Math.max(+((g('s-asset')||{}).value)||0,0);
  const hold=Math.max(+((g('s-hold')||{}).value)||0,0);
  const save=Math.max(+((g('s-save')||{}).value)||0,0);
  const plan=Math.max(+((g('t-amt')||{}).value)||0,0);
  if(!asset){
    box.innerHTML='<div style="font-size:11.5px;color:#6e7681;padding:9px 0">填入「可投资金融资产」总额后开始计算。</div>';
    con.innerHTML=''; return;
  }
  const after=hold+plan, pA=after/asset*100;
  const W=v=>v>=10000?(v/10000).toFixed(v>=100000?0:1)+' 万':Math.round(v)+' 元';
  const P=v=>(v/asset*100).toFixed(1)+'%';
  const Y=v=>save>0?(v/save).toFixed(1)+' 年储蓄':(v>=10000?(v/10000).toFixed(0)+' 万':v+' 元');
  const loss25=after*0.25, loss386=after*0.386;
  const cap15=asset*0.15, cap20=asset*0.20;

  const chips=[[5,'#26a69a'],[10,'#58a6ff'],[15,'#e8c35a'],[20,'#f0524d']].map(([p])=>{
    const on=(pA>=p-2.5&&pA<p+2.5), hi=(p===20&&pA>20);
    return `<span class="szchip ${on?'on':''} ${hi?'hi':''}">${p}% = ${W(asset*p/100)}</span>`;
  }).join('');

  box.innerHTML=`<table class="szt">
    <thead><tr><th>层级</th><th>金额</th><th>占可投资资产</th><th>说明</th></tr></thead>
    <tbody>
      <tr><td>家庭可投资金融资产</td><td>${W(asset)}</td><td>100%</td><td style="color:#5a6371">分母</td></tr>
      <tr><td>现有黄金（含积存金）</td><td>${W(hold)}</td><td>${P(hold)}</td><td style="color:#5a6371">已经在里面了</td></tr>
      <tr><td>本次三档计划投入</td><td>${W(plan)}</td><td>${P(plan)}</td><td style="color:#5a6371">分三次付</td></tr>
      <tr class="key"><td>执行后黄金合计</td><td>${W(after)}</td><td>${P(after)}</td><td>这是真正要回答的数</td></tr>
      <tr class="sub"><td>└ 若金价再跌 25%（历次中级调整中位）</td><td style="color:#26a69a">-${W(loss25)}</td><td style="color:#26a69a">-${P(loss25)}</td><td>≈ ${Y(loss25)}</td></tr>
      <tr class="sub"><td>└ 若跌 38.6%（1992 以来最深）</td><td style="color:#26a69a">-${W(loss386)}</td><td style="color:#26a69a">-${P(loss386)}</td><td>≈ ${Y(loss386)}</td></tr>
    </tbody></table>
    <div style="margin-top:8px">${chips}</div>`;

  let lv, col, msg;
  if(pA>20){
    lv='过重'; col='#f0524d';
    msg=`黄金占总资产 <b>${pA.toFixed(1)}%</b>，属于集中押注。把三档压到 15%（${W(cap15)}）需要减少 <b>${W(after-cap15)}</b>；
         压到 20%（${W(cap20)}）需要减少 ${W(after-cap20)}。再跌 25% 那一下，损失约等于 <b>${Y(loss25)}</b>。`;
  }else if(pA>=15){
    lv='偏重'; col='#e8c35a';
    msg=`黄金占总资产 <b>${pA.toFixed(1)}%</b>，偏重但不算失控。能接受的前提是：再跌 25% 亏 ${W(loss25)}（${Y(loss25)}）不会让你被迫卖掉别的资产。
         如果这个数让你犹豫，就把计划砍到 ${W(cap15)}。`;
  }else if(pA>=5){
    lv='在常见区间'; col='#26a69a';
    msg=`黄金占总资产 <b>${pA.toFixed(1)}%</b>，落在 5–15% 的常见区间内。这个仓位的特点是：涨了有感受，跌了不影响主线，
         属于「不需要每天盯着」的量。再跌 25% 的账户影响是 ${P(loss25)}（${W(loss25)}）。`;
  }else{
    lv='偏轻'; col='#8b949e';
    msg=`黄金占总资产 <b>${pA.toFixed(1)}%</b>，对组合的影响有限 —— 它的作用是分散，不是改变结果。若想让它有实际作用，
         15% 对应 ${W(cap15)}。`;
  }
  con.innerHTML=`<div class="szc" style="border-color:${col}"><b style="color:${col}">${lv}</b> —— ${msg}<br>
    <span style="color:#6e7681">这段是算术，不是建议：它只回答「这个数在你家账本上意味着什么」，不回答「金价会涨还是会跌」——后者这个系统做不到。</span></div>`;
}

function fillVerify(){
  const box=document.getElementById('verline'); if(!box) return;
  const V=DATA.validation||{};
  if(!V.status){ box.className='verline'; box.innerHTML='<span class="vd"></span><span>数据自检无记录（validation.json 未生成）</span>'; return; }
  const n=(V.checks||[]).length, bad=(V.fails||[]).length, wr=(V.warns||[]).length;
  const det=(V.checks||[]).map(c=>`<div class="${c.ok?'':'x'}">${c.ok?'✓':'✗'} ${c.n} · ${c.d}</div>`).join('');
  let head='';
  if(V.status==='fail'){
    head=`<b>数据自检未通过（${bad} 项）</b> · `+
         (V.rolledBack?`已回滚到 <b>${V.date||'上一份'}</b> 的收盘`:(V.dropped?`已丢弃可疑K线 <b>${V.dropped}</b>`:`无备份可回滚`))+
         ` — 本页与推送<b>用的不是今天的行情</b>，先看日志再动手。`;
  }else if(V.status==='warn'){
    head=`数据自检 ${wr} 项预警 · ${n} 项通过 · 截至 <b>${V.date||'-'}</b> 收 ${V.close||'-'}`;
  }else{
    head=`数据自检通过 · ${n} 项 · 截至 <b>${V.date||'-'}</b> 收 ${V.close||'-'}`;
  }
  box.className='verline '+(V.status==='fail'?'fail':(V.status==='warn'?'warn':'ok'));
  box.innerHTML=`<span class="vd"></span><span>${head}<span class="vmore" id="vmore">明细</span><div class="vdet">${det}</div></span>`;
  const m=document.getElementById('vmore');
  if(m) m.onclick=()=>{ box.classList.toggle('open'); m.textContent=box.classList.contains('open')?'收起':'明细'; };
}

function fillMA200(){
  const E=DATA.ma200env||{}; const v=document.getElementById('m2v'), s=document.getElementById('m2s');
  if(!v||!s) return;
  if(E.dev==null){ v.textContent='--'; s.textContent='数据不足'; return; }
  const d=E.dev;
  let col,lbl;
  if(d<=-15){ col='#f0524d'; lbl='极端低位 · 接近历史极限'; }
  else if(d<=-8){ col='#e8c35a'; lbl='深度低位 · 下方空间有限'; }
  else if(d<=8){ col='#8b949e'; lbl='正常区间'; }
  else { col='#f0524d'; lbl='偏高 · 追高风险'; }
  v.innerHTML = `<span style="color:${col}">${d>0?'+':''}${d.toFixed(1)}%</span>`;
  let extra='';
  if(E.slope!=null) extra += `<br>MA200 ${E.ma200} · ${E.slope>=0?'上行 +':'下行 '}${E.slope.toFixed(2)}%`;
  if(E.p15!=null) extra += `<br>到 -15% 偏离：${E.p15.toFixed(1)}%`;
  s.innerHTML = `<span style="color:${col}">${lbl}</span>` +
    (E.pct!=null?`<br>历史 ${E.pct}% 分位${E.min!=null?` · 极值 ${E.min}%`:''}`:'') + extra;
}

// ---------- 人民币视角（2026-10-30） ----------
const GRAM=31.1035;
function pcol(x){ return x>=0?'#f0524d':'#26a69a'; }   // 涨红跌绿，全页统一
function psign(x,d=2){ return (x>0?'+':'')+Number(x).toFixed(d); }

function fillFX(){
  const E=DATA.fxenv||{}, W=document.getElementById('fxwrap');
  const cv=document.getElementById('cnyv'), cs=document.getElementById('cnys');
  if(!W) return;
  if(E.cny==null){
    if(cv) cv.textContent='--';
    if(cs) cs.textContent='汇率数据未就绪';
    W.innerHTML='<div style="font-size:11.5px;color:#6e7681">汇率历史未加载，元/克换算不可用。检查 fx_hist.json。</div>';
    return;
  }
  // 主值走实时价，副值回落到收盘口径 —— 两个口径同时给出，避免"页面价变了卡片没变"
  const pxNow=(live&&live.price)?live.price:((DATA.trend||{}).close||0);
  const fxNow=(DATA.fx&&+DATA.fx)||E.fx;
  const cnyNow=pxNow?pxNow*fxNow/GRAM:E.cny;
  const isLive=!!(live&&live.price&&Math.abs(pxNow-((DATA.trend||{}).close||0))>0.01);
  if(cv) cv.innerHTML=`<span style="color:#e8c35a">${fmt(cnyNow,1)}</span>`;
  if(cs) cs.innerHTML=`元/克 · 汇率 ${fxNow}<br>${isLive?'实时':'收盘'} ${fmt(pxNow,1)} × ${fxNow} ÷ 31.1035`+
    `<br><span style="color:#6e7681">收盘口径 ${fmt(E.cny,1)} · 距历史最高 ${psign(E.cnyDD,1)}%</span>`;

  // 顶部四格
  const hist=(E.rows||[]).find(r=>r.k.indexOf('250')===0)||{};
  const drag250 = hist.drag!=null?hist.drag:null;
  const st=[
    {l:'人民币金价', v:fmt(cnyNow,1), u:'元/克', d:`${isLive?'实时':'收盘'} ${fmt(pxNow,1)} USD × ${fxNow} ÷ 31.1035<br>历史最高 ${E.cnyHi?fmt(E.cnyHi,1)+' 元/克':'-'} · 收盘口径 ${fmt(E.cny,1)}`},
    {l:'USD/CNY', v:fxNow, u:'', d:`汇改后 ${E.pct}% 分位（收盘口径）<br>区间 ${E.min} – ${E.max}`,
     c: (E.pct<=25?'#26a69a':(E.pct>=75?'#f0524d':'#8b949e'))},
    {l:'汇率敏感度', v:fmt(E.sens,1), u:'元/克', d:`人民币每升值 1%<br>你的持仓被动 -${fmt(E.sens,1)} 元/克`},
    {l:'近 250 日 汇率吃掉', v:(drag250!=null?fmt(Math.abs(drag250),1)+'pp':'-'), u:'',
     d:(hist.usd!=null?`美元 ${psign(hist.usd,1)}% → 人民币 ${psign(hist.cny,1)}%<br>这一年汇率是逆风`:'-'),
     c:'#26a69a'}
  ];
  let h='<div class="fxstat">'+st.map(x=>
    `<div class="fxs"><div class="l">${x.l}</div>`+
    `<div class="v"${x.c?` style="color:${x.c}"`:''}>${x.v}${x.u?`<span style="font-size:11px;font-weight:400;color:#7d8794;margin-left:3px">${x.u}</span>`:''}</div>`+
    `<div class="d">${x.d}</div></div>`).join('')+'</div>';

  // 区间分解
  h+='<div class="tblwrap"><table class="fxt"><thead><tr>'+
     '<th>区间</th><th>美元金价</th><th>USD/CNY</th><th>人民币金价</th><th>汇率贡献<br><span style="font-weight:400;font-size:10px;color:#5a6371">负 = 拖累</span></th></tr></thead><tbody>';
  (E.rows||[]).forEach(r=>{
    const isHi=r.k.indexOf('2026')===0;
    h+=`<tr${isHi?' class="sum"':''}><td>${r.k}</td>`+
       `<td style="color:${pcol(r.usd)}">${psign(r.usd)}%</td>`+
       `<td style="color:${pcol(r.fx)}">${psign(r.fx)}%</td>`+
       `<td style="color:${pcol(r.cny)}">${psign(r.cny)}%</td>`+
       `<td style="color:${pcol(r.drag)}">${psign(r.drag,1)}pp</td></tr>`;
  });
  h+='</tbody></table></div>';

  // 关键价位 → 元/克
  h+='<div style="font-size:11.5px;color:#8b949e;margin:11px 0 6px">同样的价位，换成你下单用的<b style="color:#c9d1d9">元/克</b>：</div>';
  h+='<div class="fxstat" style="margin-bottom:0">'+(E.levels||[]).map(l=>
    `<div class="fxs"><div class="l">${l.n} · ${fmt(l.usd,1)}</div>`+
    `<div class="v" style="font-size:15px">${fmt(l.cny,1)}<span style="font-size:10px;font-weight:400;color:#7d8794;margin-left:3px">元/克</span></div>`+
    `<div class="d" style="color:${pcol(l.gap)}">距现价 ${psign(l.gap,1)}%</div></div>`).join('')+'</div>';

  W.innerHTML=h;
}

// ---------- 三档全覆盖委托（2026-10-30） ----------
function renderTranche(){
  const E=DATA.fxenv||{}, M=DATA.ma||{}, T=DATA.trend||{};
  const box=document.getElementById('tranbox'); if(!box) return;
  const amt=parseFloat((document.getElementById('t-amt')||{}).value)||0;
  const fx=parseFloat((document.getElementById('t-fx')||{}).value)||E.fx||6.66;
  const px=((live&&live.price)?live.price:(T.close||0));
  let low=null, ma60=M.ma60;
  (E.levels||[]).forEach(l=>{ if(l.n==='参照低点') low=l.usd; });
  if(!px){
    box.innerHTML='<div style="font-size:11.5px;color:#6e7681">价位数据未就绪（行情未载入）</div>'; return;
  }
  const defs=[
    {n:'第 1 档 · 无条件', w:.40, usd:px, cls:'t1', cond:`就在今天，现价 ${fmt(px,0)} 直接买<br>不等任何确认`, note:'位置已在 -28%，越过历次中级调整中位'},
    {n:'第 2 档 · 破前低', w:.30, usd:low, cls:'t2', cond:`收盘跌破 ${fmt(low,2)}<br>次日开盘买`, note:'前低破位 = 恐慌价，只买这一次；参照线已锁死，不随窗口滑动'},
    {n:'第 3 档 · 收复趋势', w:.30, usd:ma60, cls:'t3', cond:`收盘站上 ${fmt(ma60,0)}<br>且 3 日不破再买`, note:'趋势确认，多付 6.7% 买确定性'}
  ];
  let g=0, cost=0;
  const cards=defs.map(d=>{
    if(!d.usd){
      return `<div class="trc ${d.cls}" style="opacity:.55"><div class="n">${d.n}</div>`+
        `<div class="a" style="font-size:15px">待数据</div>`+
        `<div class="p">均线/前低缺失，本次跳过</div>`+
        `<div class="c">${d.note}</div></div>`;
    }
    const money=amt*d.w, grams=money/(d.usd*fx/GRAM);
    g+=grams; cost+=money;
    return `<div class="trc ${d.cls}"><div class="n">${d.n}</div>`+
      `<div class="a">${amt?fmt(money/10000,0)+' 万':'--'}<span style="font-size:10px;font-weight:400;color:#7d8794;margin-left:3px">${Math.round(d.w*100)}%</span></div>`+
      `<div class="p">${fmt(d.usd*fx/GRAM,1)} 元/克 · ${amt?fmt(grams,1)+' 克':'-'}</div>`+
      `<div class="c">${d.cond}<br><span style="color:#5a6371">${d.note}</span></div></div>`;
  }).join('');
  box.innerHTML=cards;
  const sum=document.getElementById('t-sum');
  if(sum) sum.innerHTML = (amt&&g)?`合计 <b style="color:#e6edf3">${fmt(g,1)} 克</b> · 平均成本 <b style="color:#e8c35a">${fmt(cost/g,1)} 元/克</b>`:'';
}

function renderQuickRef(){
  const st=alertState(), V=DATA.volenv||{}, M=DATA.ma||{}, S=DATA.stop||{}, M2=DATA.ma200env||{}, F=DATA.fxenv||{}, MA=DATA.macroenv||{};
  const dsc=(st.m&&st.m.day&&st.m.day.score)||0;
  const lowV=V.grade==='low';
  const R=[
   ['磨底黄灯','低位（60 日位置 ≤20%）+ 动能衰竭 + 形态企稳；有量能时 3/4 亮，无量能时动能与形态必须同时成立','唯一正式买点：分批建仓，单笔不超过计划仓位的 1/3','1999–2026 共 69 次，T+20 均值 +1.78%、胜率 70%（随机 57%）', dsc>=3, dsc+'/4'],
   ['暴跌雷达','单日大跌 + 放量，急跌进行中','只做 T 的参考，不是买点','历史 5 次里 3 次是下跌中继，接刀要快', !!st.crash, st.crash?'触发':'—'],
   ['超买灯','超买 + 动量透支，不等于见顶','别追高、别加仓；卖出不看它','亮灯后 60 日跌 ≥8% 仅 9.0%，随机是 21.4%', (st.ts||0)>=3, (st.ts||0)+'/4'],
   ['8% 回撤线','距 250 日最高价回落 8%','最先触发、最可靠的卖出线：先减一半，不等均线确认','5 个大顶 5/5 触发，平均让出 9.7%', !!M.dd8, M.dd8?('破 '+(M.dd8_days||0)+' 日'):'未破'],
   ['MA20 破位','高位（120 日位置 ≥70%）跌破 20 日线','减仓一半；位置 &lt;70% 时静默，视为噪音','低位破位 6 次全部静默，事后都是假警报', !!M.high20break, M.high20break?'已破':'守住'],
   ['MA60 破位','跌破 60 日趋势线','牛·中位→减半；牛·深位 / 过渡·中位→清仓','5 个大顶 5/5 触发，比 8% 线平均多让 0.8 点', !!M.below60, M.below60?('破 '+(M.below60_days||0)+' 日'):'守住'],
   ['ATR 棘轮','从阶段高点回落 2.5 倍 ATR','追踪止盈，只是辅助；破 MA60 后本模块作废','非主力，单独用会卖太早', !!S.trigger, (S.fail?'已失效':(S.trigger?'触发':'未触发'))],
   ['偏离 MA200','收盘相对 200 日均线的偏离度 · 看「还有多少下跌空间」','不是买卖信号。极低位（≤-15%）时不再砍仓，等企稳','1992 以来 ≤-10% 共 18 次：T+60 中位 +3.3%（67% 涨），T+250 仅 50%', (M2.dev!=null&&M2.dev<=-8), (M2.dev!=null?((M2.dev>0?'+':'')+M2.dev.toFixed(1)+'%'):'—')],
   ['人民币金价','美元金价 ÷ 31.1035 × USD/CNY —— 你买卖的是元/克，不是 USD/oz','所有美元价位都要再过一次汇率才是你的成交价；汇率变动直接进你的盈亏，不进任何一条买卖规则','近 250 日：美元 -2.3% → 人民币 -8.6%，汇率多让 6.3 个点', (F.pct!=null&&(F.pct<=25||F.pct>=75)), (F.fx!=null?F.fx+(F.pct!=null?' · '+F.pct+'%分位':''):'—')],
   ['实际利率','美国 10 年期 TIPS 实际利率 —— 持有黄金的机会成本，扣掉通胀后的无风险收益','<b style="color:#f0524d">不进任何买卖规则</b>：17 年实测与金价 60 日收益相关 −0.03，只用来量逆风有多强','当前 '+(MA.r!=null?MA.r+'%，2010 以来 '+MA.pct+'% 分位':'—'), (MA.pct!=null&&MA.pct>=90), (MA.r!=null?MA.r+'%':'—')],
   ['1H / 4H 蓝灯','短线回调的低吸位','只在 MA20&gt;MA60 时做 T；破 MA60 直接关闭','上涨趋势 5 次净胜率 100%，下跌趋势 29%', !!(st.s1>=2||st.s4>=2), st.s1+'/'+st.s4],
   ['趋势 / 通道','MA20 与 MA60 关系、距前 120 日高','只展示，不参与任何买卖判定','通道提示 105 次，20 日仍 +2.15%，减仓会亏', false, '仅参考'],
   ['量能待确认','沪金当日量能未更新（黄点）','等收盘后再判定，不算「不达标」','量能项 2026-10 起已降级为展示（p=1.000）', false, '—'],
   ['低波动环境','60 日均振幅 &lt;1.1%，阈值等价于 7 倍日波动','信号只当提示，别据此重仓','&lt;1.1% 胜率 47%；&gt;1.3% 胜率 82%', lowV, V.amp!=null?V.amp.toFixed(2)+'%':'—']
  ];
  const body=document.getElementById('qbody'); if(!body) return;
  body.innerHTML=R.map(r=>{
    const on=r[4], col=on?'#e8c35a':'#4a5563';
    return `<tr class="${on?'on':''}"><td class="qn">${r[0]}</td><td>${r[1]}</td><td class="qa">${r[2]}</td>`+
      `<td class="qh">${r[3]}</td><td class="qs" style="color:${col}">${on?'●':'○'} ${r[5]}</td></tr>`;
  }).join('');
}

function renderPeriods(){
  const st=alertState();
  const box=document.getElementById('periods');
  const gateOn = !!st.gateOk;
  const gateSub = st.gateTrend==='down' ? '做T已关闭 · 趋势向下'
    : (st.gateTrend==='range' ? '做T已关闭 · 趋势不明'
    : (st.gateTrend==='up' ? (st.s1>=2&&st.s4>=2?'牛市回调做T':'未达共振线') : '做T已关闭 · 数据不足'));
  const small=(name,sc,ok1,ok2,ok3)=>{
    const cls = !gateOn ? 'gray' : (sc>=2?'blue':(sc>=1?'yellow':'gray'));
    const dot=(ok,t)=>`<span style="color:${ok?(gateOn?'#8ab4ff':'#4a5563'):'#4a5563'}">${ok?'●':'○'}${t}</span>`;
    return `<div class="pcard ${cls}"${gateOn?'':' style="opacity:.6"'}><div class="pc-l">${name}</div><div class="pc-s">${sc}<span style="font-size:11px;color:#6e7681">/3</span></div>
      <div class="pc-d">${dot(ok1,'空间')} ${dot(ok2,'动能')} ${dot(ok3,'形态')}<br>${gateSub}</div></div>`;
  };
  const dScore = st.m ? st.m.day.score : 0;
  const _lowV = (DATA.volenv||{}).grade==='low';
  const dCls = st.crash ? 'red' : (dScore>=3 ? (_lowV?'gray':'yellow') : 'gray');
  const h1=st.h1?st.h1.detail:{}, h4=st.h4?st.h4.detail:{};
  box.innerHTML = small('1H', st.s1, st.h1&&st.h1.space, st.h1&&st.h1.momentum, st.h1&&st.h1.pattern)
    + small('4H', st.s4, st.h4&&st.h4.space, st.h4&&st.h4.momentum, st.h4&&st.h4.pattern)
    + `<div class="pcard ${dCls}"><div class="pc-l">日线底</div><div class="pc-s">${dScore}<span style="font-size:11px;color:#6e7681">/4</span></div>
        <div class="pc-d">${st.crash?'暴跌触发 + 确认':(dScore>=3?(_lowV?'预警 · 低波动打折':'磨底预警'):'未达标')}<br>${st.daily?'大周期允许':'大周期压制'}${_lowV?'<br><span style="font-size:9.5px;color:#e8c35a">振幅 '+((DATA.volenv||{}).amp||0).toFixed(2)+'% · 仅参考</span>':''}</div></div>`
    + (()=>{ const ts=st.ts, T=st.T||{}, d=T.detail||{};
        const muted = ((PHASE==='bull'||PHASE==='left') && ts>=3 && !st.topBreak);
        const cls = st.topBreak?'red':(ts>=3?(muted?'gray':'purple'):(ts>=1?'yellow':'gray'));
        const desc = muted ? '静音 · 仅作参考' : (ts>=3?(st.topBreak?'跌破MA20 · 破位':'超买衰竭'):'未触发');
        return `<div class="pcard ${cls}"${muted?' style="opacity:.62"':''}><div class="pc-l">超买</div><div class="pc-s">${ts}<span style="font-size:11px;color:#6e7681">/4</span></div>
          <div class="pc-d">${desc}<br>120日位置 ${d.pos120!=null?d.pos120+'%':'--'} · 偏离MA20 ${d.dev20!=null?d.dev20+'%':'--'}${muted?'<br><span style="font-size:9.5px;color:#5a6371">'+(PHASE==='bull'?'牛市 60 日内 77% 会卖飞':'左侧寻底 · 卖出类已静音')+'</span>':''}</div></div>`;
      })();
}

function paintAlert(){
  const st=alertState();
  const bar=document.getElementById('alertbar');
  const t=document.getElementById('abtext'), meta=document.getElementById('abmeta');
  bar.classList.remove('red','yellow','blue','purple','darkred','orange','idle');
  if(PHASE==='bull' && st.ma60break && !st.shallow60){
    bar.classList.add(st.ma60act==='减半'?'orange':(st.ma60act==='不动'?'idle':'darkred'));
    t.textContent = st.ma60act==='减半' ? '【跌破 MA60，减仓一半】'
      : (st.ma60act==='不动' ? '【牛市高位破位，视为洗盘 · 不动】' : '【深度跌破 MA60，趋势破坏 → 清仓】');
    meta.textContent=`收盘 ${fmt(st.M.close)} < MA60 ${fmt(st.M.ma60)} · ${st.M.gap60}% · 已 ${st.m60days} 天 · ${st.env||''}·${st.zone||''}位`;
  } else if(PHASE==='bull' && st.shallow60){
    bar.classList.add('orange');
    t.textContent='【浅破 MA60，观察 10 天】';
    meta.textContent=`收盘 ${fmt(st.M.close)} < MA60 ${fmt(st.M.ma60)} · 仅 ${st.M.gap60}% · 第 ${st.m60days}/10 天`;
  } else if(PHASE==='bull' && st.reclaim20){
    bar.classList.add('blue');
    t.textContent='【假摔收回，建议买回减掉的仓位】';
    meta.textContent=`重新站上 MA20 ${fmt(st.M.ma20)} · 前次跌破 ${st.M.reclaim20_date} · 现价 ${fmt(st.price)}`;
  } else if(PHASE==='bull' && st.ma20break){
    bar.classList.add('orange');
    t.textContent='【高位破 MA20，建议减仓一半】';
    meta.textContent=`收盘 ${fmt(st.M.close)} < MA20 ${fmt(st.M.ma20)} · ${st.M.gap20}% · 120日位置 ${st.pos120}%（≥70%）· 牛市模式`;
  } else if(PHASE==='right' && st.ma60break){
    bar.classList.add(st.ma60act==='减半'?'orange':'darkred');
    t.textContent = st.ma60act==='减半' ? '【跌破 MA60，减仓一半（熊市/中低位）】' : '【跌破 MA60 趋势破位，建议清仓离场】';
    meta.textContent=`收盘 ${fmt(st.M.close)} < MA60 ${fmt(st.M.ma60)} · ${st.M.gap60}% · ${st.env||''}·${st.zone||''}位`;
  } else if(PHASE==='right' && st.ultimate){
    bar.classList.add('darkred');
    t.textContent='【终极警告：超买信号后跌破 MA20】';
    meta.textContent=`超买 ${st.T.last_top3?(st.T.last_top3.date+' 触发'):''} · 收盘 ${fmt(st.M.close)} < MA20 ${fmt(st.M.ma20)}`;
  } else if(PHASE==='right' && st.topBreak){
    bar.classList.add('darkred');
    t.textContent='【趋势破位！清仓离场！】';
    meta.textContent=`超买 ${st.ts}/4 · 收盘跌破 MA20 · ${fmt(st.price)}`;
  } else if(PHASE==='right' && st.top3){
    bar.classList.add('purple');
    t.textContent='【警惕！进入超买衰竭区，建议开始左侧分批止盈】';
    meta.textContent=`超买 ${st.ts}/4 · 120日位置 ${st.T.detail.pos120}% · 偏离MA20 ${st.T.detail.dev20}%`;
  } else if(PHASE==='right' && st.ma20break){
    bar.classList.add('orange');
    t.textContent='【高位破 MA20，建议减仓一半】';
    meta.textContent=`收盘 ${fmt(st.M.close)} < MA20 ${fmt(st.M.ma20)} · ${st.M.gap20}% · 120日位置 ${st.pos120}%（≥70%）· 超买 ${st.ts}/4 · 同日 ATR 不叠加`;
  } else if(PHASE==='right' && st.trailHit && !st.ma20break){
    bar.classList.add('orange');
    t.textContent='【ATR 锁利润线触发（辅助）】';
    meta.textContent=`收盘 ${fmt(st.S.close)} < 追踪线 ${fmt(st.S.trail)} · ${st.S.gap_trail}% · ATR14 ${st.S.atr14}`;
  } else if(st.red3){
    bar.classList.add('red');
    t.textContent='【三维共振！重仓出击！】';
    meta.textContent=`1H ${st.s1}/3 · 4H ${st.s4}/3 · 日线达标 · ${fmt(st.price)}`;
  } else if(st.crash){
    bar.classList.add('red');
    t.textContent='【极速反弹机会出现】';
    meta.textContent=`暴跌 ${st.c.score}/4 · 右侧确认已出现 · ${fmt(st.price)}`;
  } else if(st.blue2){
    bar.classList.add('blue');
    t.textContent='【小周期共振，可轻仓做T】';
    meta.textContent=`1H ${st.s1}/3 · 4H ${st.s4}/3 · 日线未达标 · ${fmt(st.price)}`;
  } else if(st.mo){
    bar.classList.add('yellow');
    t.textContent='【进入震荡底部区，可开启分批网格建仓】';
    meta.textContent=`磨底 ${st.m.day.score}/${st.m.day.denom||4} · 60日位置 ${st.m.day.space.pos60.toFixed(0)}% · ${fmt(st.price)}`;
  } else if(st.blue1){
    bar.classList.add('blue');
    t.textContent='【短线超跌反弹预警】';
    meta.textContent=`${st.s1>=2?'1H '+st.s1+'/3':''}${st.s1>=2&&st.s4>=2?' · ':''}${st.s4>=2?'4H '+st.s4+'/3':''} · ${fmt(st.price)}`;
  } else {
    bar.classList.add('idle');
    t.textContent='监控中 · 暂无信号';
    const sp60 = (st.m && st.m.day.space) ? st.m.day.space.pos60 : null;
    let _d5 = 0;
    if(bars && bars.length>5){ _d5 = (bars[bars.length-1].c/bars[bars.length-6].c-1)*100; }
    const _why20 = _d5 <= -5 ? '急跌致位置快速下移' : '位置本就不高';
    meta.innerHTML=`${PHASE==='left'?'左侧寻底 · 卖出静音':'右侧持仓 · 卖出激活'} · 1H ${st.s1}/3 · 4H ${st.s4}/3 · 超买 ${st.ts}/4 · ${fmt(st.price)} · 60日位置(收盘) ${sp60!=null?sp60.toFixed(0)+'%':'--'} · 追踪线 ${st.S.trail?fmt(st.S.trail):'--'}${st.S.fail?'（已失效）':''}`
      + (st.low20break?` · <span style="color:#6e7681">MA20 已破但 120日位置 ${st.pos120}%（&lt;70%），${_why20}，按规则静默</span>`:'');
  }
  renderPeriods(); renderDefense(); fillVolEnv(); fillMA200(); fillFX(); renderMacro(); renderTranche(); renderSizing(); fillVerify(); renderQuickRef();
  return st;
}

function beep(freq, dur){
  try{
    const AC=window.AudioContext||window.webkitAudioContext; if(!AC) return;
    const ctx=beep.ctx||(beep.ctx=new AC());
    const o=ctx.createOscillator(), g=ctx.createGain();
    o.type='sine'; o.frequency.value=freq||880;
    g.gain.setValueAtTime(0.18, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime+(dur||0.35));
    o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime+(dur||0.35));
  }catch(e){}
}

function showAlert(type, preview){
  if(!preview && PHASE==='left' && SELL_TYPES.includes(type)) return;
  const st=alertState();
  const mask=document.getElementById('alertmask');
  const modal=document.getElementById('alertmodal');
  const t=document.getElementById('amtitle'), sub=document.getElementById('amsub'), det=document.getElementById('amdetail');
  modal.classList.remove('red','yellow','blue','purple','darkred','orange');
  const pv = preview?'<br><b style="color:#e8c35a">当前为样式预览，非真实信号。</b>':'';
  if(type==='bullshallow'){
    modal.classList.add('orange');
    t.style.color='#fbbf24'; t.textContent='浅破 MA60，观察 10 天';
    sub.innerHTML = preview
      ? `收盘 4,120.50 < MA60 4,150.00，幅度仅 <b>-0.71%</b><br>已持续 3 / 10 个交易日`
      : `收盘 ${fmt(st.M.close)} < MA60 ${fmt(st.M.ma60)}，幅度仅 <b>${st.M.gap60}%</b><br>已持续 ${st.m60days} / 10 个交易日`;
    det.innerHTML = `牛市模式下，MA60 被"蹭破"很常见：2015-2026 的 13 次牛市洗盘里，<b>9 次破位幅度 <1%</b>，且多在 10 日内收回。<br>
      规则：<b>10 天内收回 → 假摔，不动仓；第 11 天仍未收回，或幅度扩大到 1.5% → 自动升级清仓。</b>${pv}`;
    beep(600,.4); setTimeout(()=>beep(520,.45),180);
  } else if(type==='bullreclaim'){
    modal.classList.add('blue');
    t.style.color='#8ab4ff'; t.textContent='假摔收回，建议买回减掉的仓位';
    sub.innerHTML = preview
      ? `价格重新站上 MA20 <b>4,150.00</b><br>前次跌破 10-14 · 现价 4,013.48`
      : `价格重新站上 MA20 <b>${fmt(st.M.ma20)}</b><br>前次跌破 ${st.reclaim20_date||''} · 现价 ${fmt(st.price)}`;
    det.innerHTML = `牛市洗盘数据：13 次跌破 MA20/MA10 的案例，<b>13 次都在 20 日内收回</b>，平均 8.5 天。<br>
      按规则把减掉的那一半买回；若同时浅破 MA60，等 MA60 收回再补满。${pv}`;
    beep(880,.4); setTimeout(()=>beep(1046,.45),180);
  } else if(type==='trail'){
    modal.classList.add('orange');
    t.style.color='#fbbf24'; t.textContent='ATR 锁利润线触发（辅助）';
    sub.innerHTML = preview
      ? `动态止盈线 <b>4,241.20</b>（样例），收盘已跌破<br>现价 ${fmt(st.price)} · 建议减仓一半`
      : `动态止盈线 <b>${fmt(st.S.trail)}</b>，收盘 ${fmt(st.S.close)} 已跌破（${st.S.gap_trail}%）<br>建议减仓一半`;
    det.innerHTML = `追踪线 = 段内最高（近 20 日最高 − 3×ATR14），<b>只上移不下移</b>；当前 ATR14 ${st.S.atr14}，本轮起点 ${st.S.seg_start}（第 ${st.S.seg_days} 天）。<br>
      <b style="color:#fbbf24">【定位：锁利润辅助线，不是逃顶主力】</b>2011–2026 的 17 个阶段性大顶实测：它只触发 <b>9 次（53%）</b>，平均延迟 <b>8.7 天</b>、卖在顶下 <b>6.51%</b>，且有 <b>47%</b> 因先跌破 MA60 而直接失效。真正逃顶看 MA20（17/17 触发、4 天、-4.82%）。<br>
      触发条件：<b>日线收盘</b>跌破该线，且收盘失守 MA10（当前偏离 MA20 ${st.S.dev20}%，${st.S.paused?'处于震荡带 → 已暂停':'已脱离震荡带'}）。<br>
      动作：只减一半，不清仓；清仓仍等收盘跌破 MA60。${pv}`;
    beep(500,.45); setTimeout(()=>beep(430,.5),200);
  } else if(type==='ma60'){
    modal.classList.add('darkred');
    const _a = st.ma60act || '清仓';
    const _isHalf = _a==='减半', _isHold = _a==='不动';
    modal.classList.remove('darkred'); modal.classList.add(_isHalf?'orange':'darkred');
    t.style.color=_isHalf?'#fbbf24':'#ff4d4d';
    t.textContent = _isHalf ? '跌破 MA60：熊市/中低位，减仓一半'
      : (_isHold ? '牛市高位破位：视为洗盘，不动仓' : '跌破 MA60：过渡期反转确认，清仓离场');
    sub.innerHTML=`收盘 <b>${fmt(preview?3997.79:st.M.close)}</b> < MA60 <b>${fmt(preview?4299:(st.M.ma60||0))}</b>（${preview?'-7.01':st.M.gap60}%）<br>
      环境 <b>${st.env||'--'}</b> · 距 250 日高 <b>${st.pos250!=null?st.pos250+'%':'--'}</b>（${st.zone||'--'}位）`;
    det.innerHTML=`同一个破位，三种环境含义相反：<br>
      · 牛市+高位（&lt;10%）→ <b>洗盘不动</b>｜72 次，20 日 <b>+1.04%</b><br>
      · 过渡期（年线刚转向）→ <b>清仓</b>｜16 次，20 日 <b>-2.82%</b>，胜率 31%<br>
      · 其余（熊市/中低位）→ <b>减半</b>｜熊市低位常是最后一跌<br>
      <span style="color:#c9d1d9">本行判定：${st.env||'--'} · ${st.zone||'--'}位 → ${_a}</span>${pv}`;
    beep(360,.6); setTimeout(()=>beep(280,.7),260); setTimeout(()=>beep(220,.9),560);
  } else if(type==='ultimate'){
    modal.classList.add('darkred');
    t.style.color='#ff4d4d'; t.textContent='终极警告：超买信号后跌破 MA20';
    sub.innerHTML=`超买雷达曾在 <b>${st.T.last_top3?st.T.last_top3.date:'近期'}</b> 给出 ≥3 分，随后收盘跌破 MA20<br>现价 ${fmt(st.price)}`;
    det.innerHTML=`两项条件叠加：① 超买雷达 ≥3 分；② 随后跌破 MA20。说明顶部结构已确认破位。<br>按你的规则：直接清仓，不等反抽。${pv}`;
    beep(420,.55); setTimeout(()=>beep(320,.65),250); setTimeout(()=>beep(240,.85),520);
  } else if(type==='ma20'){
    modal.classList.add('orange');
    t.style.color='#fbbf24'; t.textContent='高位破 MA20，建议减仓一半';
    sub.innerHTML=`收盘 <b>${fmt(preview?3997.79:st.M.close)}</b> < MA20 <b>${fmt(preview?4135:(st.M.ma20||0))}</b>（${preview?'-3.33':st.M.gap20}%）<br>120 日位置 <b>${preview?88:(st.pos120!=null?st.pos120:'--')}%</b> · 高位过滤阈值 70%`;
    det.innerHTML=`MA20 是短期趋势线，也是本系统<b>逃顶第一顺位</b>。2011–2026 的 17 个阶段性大顶实测：MA20 <b>17/17 全部触发</b>，平均延迟 <b>4.0 天</b>、卖在顶下 <b>4.82%</b>、假摔率 12%，是三法里最快最省的。<br>
      <b>只有 120 日位置 ≥70% 时才报警</b>：低于 70% 的破位属于下跌途中的正常回踩，报警只会被震荡市反复打脸（无条件破 MA20 的历史假信号率 44%）。<br>
      动作：减仓一半，剩下的看 MA60 是否守住。${pv}`;
    beep(520,.45); setTimeout(()=>beep(440,.5),200);
  } else if(type==='topbreak'){
    modal.classList.add('darkred');
    t.style.color='#ff4d4d'; t.textContent='趋势破位！清仓离场！';
    sub.innerHTML=`超买雷达 <b>${preview?4:st.ts}/4</b> 分，且收盘价已跌破 MA20<br>现价 ${fmt(st.price)} · MA20 ${preview?'4,130':(st.T.detail?st.T.detail.ma20:'--')}`;
    det.innerHTML=`触发条件：超买衰竭 ≥3 分 + 收盘跌破 MA20。这是本系统最高级别的风险提示。<br>按你的规则：清仓离场，不抢反弹、不摊平。${pv}`;
    beep(420,.6); setTimeout(()=>beep(330,.7),260); setTimeout(()=>beep(260,.9),560);
  } else if(type==='top'){
    modal.classList.add('purple');
    t.style.color='#d8b4fe'; t.textContent='警惕！进入超买衰竭区';
    sub.innerHTML=`超买雷达 <b>${preview?3:st.ts}/4</b> 分<br>现价 ${fmt(st.price)} · 120日高位`;
    det.innerHTML=`触发条件：空间超买 + 动能衰竭 + 形态滞涨 + 放量滞涨，四项中满足三项以上。<br>按你的规则：开始左侧分批止盈，先减一部分，留仓看 MA20 是否失守。${pv}`;
    beep(560,.45); setTimeout(()=>beep(500,.5),200);
  } else if(type==='resonance3'){
    modal.classList.add('red');
    t.style.color='#ff5b55'; t.textContent='三维共振！重仓出击！';
    sub.innerHTML=`1H <b>${preview?2:st.s1}/3</b> · 4H <b>${preview?2:st.s4}/3</b> · 日线 <b>${preview?3:(st.m?st.m.day.score:0)}/4</b><br>现价 ${fmt(st.price)}`;
    det.innerHTML=`三个周期同时达标：1H 与 4H 均 ≥2 分，且日线雷达（磨底 ≥3 或 暴跌 ≥3+确认）成立。<br><b style="color:#5b8dee">趋势闸门已开（日线收盘 &gt; MA20 &gt; MA60），才允许出现这个提示。</b>2026-05~10 的 1023 根 60 分钟数据显示：蓝灯在上涨趋势里 5 次、扣点差净收益 +0.72%、净胜率 100%；在下跌趋势里 14 次、净收益 -0.52%、净胜率 29% —— 所以下跌趋势中这盏灯被直接封杀。<br>按你的规则这是最高级别信号；仓位与止损仍由你决定。${pv}`;
    beep(1046,.5); setTimeout(()=>beep(1318,.5),160); setTimeout(()=>beep(1568,.6),330);
  } else if(type==='resonance2'){
    modal.classList.add('blue');
    t.style.color='#8ab4ff'; t.textContent='牛市回调做T（1H+4H 共振）';
    sub.innerHTML=`1H <b>${preview?2:st.s1}/3</b> · 4H <b>${preview?2:st.s4}/3</b> · 日线多头（闸门已开）<br>现价 ${fmt(st.price)}`;
    det.innerHTML=`<b style="color:#8ab4ff">【牛市回调做T专用 · 日线未达标时不出现】</b><br>
      触发前提：日线 <b>收盘 &gt; MA20 &gt; MA60</b>，趋势闸门开放。日线收盘跌破 MA60 时这盏灯被<b>直接封杀</b>，不弹窗、不响铃，卡片转灰。<br>
      数据：2026-05~10 的 1023 根 60 分钟数据里，蓝灯在上涨趋势 5 次、扣点差净收益 <b>+0.72%</b>、净胜率 <b>100%</b>；在下跌趋势 14 次、净收益 <b>-0.52%</b>、净胜率 <b>29%</b>。<br>
      动作：只做短线 T，仓位 5% 以内，跌破信号 K 线最低价即走，不恋战、不加仓。${pv}`;
    beep(740,.45); setTimeout(()=>beep(880,.45),180);
  } else if(type==='crash'){
    modal.classList.add('red');
    t.style.color='#ff6b66'; t.textContent='极速反弹机会出现';
    sub.innerHTML = preview
      ? `暴跌雷达 <b>4/4</b> 分（样例），右侧确认：MACD 金叉（样例）。<br>2026-10-23 · 现价 ${fmt(st.price)}`
      : `暴跌雷达 <b>${st.c?st.c.score:0}/4</b> 分，且右侧确认已出现。<br>${st.c?st.c.date:''} · 现价 ${fmt(st.price)}`;
    det.innerHTML=`<b style="color:#ff6b66">【短线/抢反弹信号，请轻仓】</b><br>触发条件：空间极速下坠 + K线极度恐慌 + 天量承接（3/4 以上），并满足「MACD 金叉」或「站上 MA5 且 MA5 拐头」。<br>历史同类信号（n=5）：5/10 日胜率 100%，20 日 80%，但 15 年仅出现 5 次。${pv}`;
    beep(960,.5); setTimeout(()=>beep(1200,.45),180);
  } else {
    const ys = yseqState();
    const sq = ys ? ys.seq : null;
    const ban = sq >= 4;
    modal.classList.add(ban ? 'darkred' : 'yellow');
    t.style.color = ban ? '#ff4d4d' : (sq === 2 ? '#f7b955' : '#f0d27a');
    t.textContent = ys ? `黄灯第 ${sq} 次 · ${ys.short}` : '进入震荡底部区';
    sub.innerHTML = preview
      ? `磨底雷达 <b>3/4</b> 分（样例），价格处于近 60 日低位区。<br>2026-10-23 · 现价 ${fmt(st.price)}`
      : `磨底雷达 <b>${st.m?st.m.day.score:0}/4</b> 分，价格处于近 60 日低位区（位置 ${st.m?st.m.day.space.pos60.toFixed(0):'--'}%）。<br>${st.m?st.m.day.d:''} · 现价 ${fmt(st.price)}`;
    let body;
    if(ys){
      const key = sq >= 4 ? '4+' : String(sq);
      const g = (DATA.yseq.groups || {})[key] || {n:0,w5:0,w20:0,a20:0};
      body  = `<b style="color:${ban?'#ff4d4d':'#f0d27a'}">【仓位纪律】本轮第 ${sq} 次亮灯 → ${ys.nm}，建议仓位 ${ys.pos}</b><br>`;
      body += `历史同档 ${g.n} 次：+5 日胜率 ${g.w5}%、+20 日胜率 ${g.w20}%、20 日均值 ${g.a20>=0?'+':''}${g.a20}%。<br>`;
      if(sq === 1 && ys.cur.gap <= -4) body += `<b style="color:#ff6b66">【深水首灯】偏离 MA60 ${ys.cur.gap}%，历史上这一档 +10 日胜率 71%、但 20 日内曾出现 -9.2% 收盘回撤 → 仓位封顶 30%，ATR 硬止损，浮亏严禁补仓。深水只赚反弹，不赌反转。</b><br>`;
      if(ban) body += `<b style="color:#ff4d4d">【红色禁令】第 4 次及以后共 8 次样本，+5 日胜率仅 12.5%、+20 日胜率 37.5% —— 真正的半山腰在这里。禁止加仓，已有仓位只减不加。</b><br>`;
      body += `<span style="color:#6e7681">仓位是风险预算分配，不是胜率加权；系统只提示，不代下单。黄灯只看「60 日低位 + 分数」，不看具体点位。${pv}</span>`;
    } else {
      body = `建议动作（系统仅提示，不代下单）：可开启分批网格建仓，把计划资金分成 3~5 档，档距按百分比等比下移（越跌买越多），具体档位由你自己设定。<br>注意：磨底雷达 15 年触发 99 次，20 日胜率仅 55.6%，接近随机；务必配合右侧确认与止损。黄灯只看「60日低位 + 分数」，不看具体点位。${pv}`;
    }
    det.innerHTML = body;
    beep(620,.45); setTimeout(()=>beep(520,.5),200);
  }
  mask.classList.add('show');
}

function initCheat(){
  const m=document.getElementById('cheatmask'), b=document.getElementById('btncheat');
  if(!m||!b) return;
  const close=()=>{ m.style.display='none'; };
  b.onclick=()=>{ m.style.display='block'; };
  document.getElementById('cheatclose').onclick=close;
  m.onclick=(e)=>{ if(e.target===m) close(); };
  document.addEventListener('keydown',(e)=>{ if(e.key==='Escape') close(); });
}

function initAlerts(){
  document.getElementById('amclose').onclick=()=>document.getElementById('alertmask').classList.remove('show');
  document.getElementById('alertmask').onclick=(e)=>{ if(e.target.id==='alertmask') e.currentTarget.classList.remove('show'); };
  document.getElementById('abpreview').onclick=()=>{
    const seq=['crash','mo','resonance2','resonance3','top','topbreak','trail','bullshallow','bullreclaim','ma20','ma60','ultimate'];
    showAlert(seq[previewIdx++%seq.length], true);
  };
  document.getElementById('abnotify').onclick=async()=>{
    if(!('Notification' in window)){ alert('当前浏览器不支持桌面通知'); return; }
    const p=await Notification.requestPermission();
    if(p==='granted'){ new Notification('提醒已开启',{body:'雷达触发时会弹出桌面通知（页面需保持打开）'}); }
    else alert('未授权，通知无法弹出；可继续使用页面内红黄蓝闪烁提醒。');
  };
  const qp=new URLSearchParams(location.search).get('phase');
  if(qp==='left'||qp==='right'||qp==='bull') PHASE=qp;
  const setPhase=(p)=>{
    PHASE=p; localStorage.setItem('gold_phase',p);
    document.getElementById('ph-left').classList.toggle('on',p==='left');
    document.getElementById('ph-right').classList.toggle('on',p==='right');
    document.getElementById('ph-bull').classList.toggle('on',p==='bull');
    document.getElementById('ph-hint').textContent = p==='left'
      ? 'MA20 / ATR / 超买已静音；MA60 趋势线照常报警'
      : (p==='bull'
         ? '牛市主升浪：MA10 与超买紫灯静音、MA60 浅破宽恕 10 天、重回 MA20 提示回补'
         : 'MA20 / MA60 清仓报警已激活，破位立刻弹窗');
    if(p==='left') document.getElementById('alertmask').classList.remove('show');
    paintAlert(); renderDefense(); renderPeriods(); fillVolEnv(); fillMA200(); fillFX(); renderMacro(); renderTranche(); renderSizing(); fillVerify(); renderQuickRef();
  };
  const br=document.getElementById('btnrefresh'); if(br) br.onclick=()=>refresh();
  document.getElementById('ph-left').onclick=()=>setPhase('left');
  document.getElementById('ph-right').onclick=()=>setPhase('right');
  document.getElementById('ph-bull').onclick=()=>setPhase('bull');
  setPhase(PHASE);

  const st=paintAlert();
  const pv=new URLSearchParams(location.search).get('preview');
  if(['crash','mo','resonance2','resonance3','top','topbreak','trail','bullshallow','bullreclaim','ma20','ma60','ultimate'].includes(pv)){ showAlert(pv, true); return; }
  if(pv) return;
  const key='alert_shown_'+new Date().toISOString().slice(0,10);
  const fire=(k,type,title,body)=>{
    if(sessionStorage.getItem(key+'_'+k)) return;
    sessionStorage.setItem(key+'_'+k,'1');
    showAlert(type);
    if(window.Notification && Notification.permission==='granted') new Notification(title,{body});
  };
  if(PHASE==='bull' && st.ma60break && !st.shallow60) fire('bullbreak','bullshallow','深度跌破 MA60，清仓',`收盘 ${fmt(st.M.close)} < MA60 ${fmt(st.M.ma60)}（${st.M.gap60}%）`);
  else if(PHASE==='bull' && st.shallow60) fire('bullsh','bullshallow','浅破 MA60，观察 10 天',`${st.M.gap60}% · 第 ${st.m60days}/10 天`);
  else if(PHASE==='bull' && st.reclaim20) fire('bullre','bullreclaim','假摔收回，建议买回',`重回 MA20 ${fmt(st.M.ma20)}`);
  else if(PHASE==='bull' && st.ma20break) fire('bull20','ma20','高位破 MA20，减仓一半',`收盘 ${fmt(st.M.close)} < MA20 ${fmt(st.M.ma20)}`);
  else if(PHASE==='right' && st.ma60break) fire('ma60','ma60','跌破 MA60 趋势破位，建议清仓离场',`收盘 ${fmt(st.M.close)} < MA60 ${fmt(st.M.ma60)}`);
  else if(PHASE==='right' && st.ultimate) fire('ult','ultimate','终极警告：超买后跌破 MA20',`${st.T.last_top3?st.T.last_top3.date:''} 超买信号 + 跌破 MA20`);
  else if(PHASE==='right' && st.topBreak) fire('tb','topbreak','趋势破位！清仓离场！',`超买 ${st.ts}/4 · 跌破 MA20 · ${fmt(st.price)}`);
  else if(PHASE==='right' && st.top3) fire('top','top','警惕！进入超买衰竭区',`超买 ${st.ts}/4 · ${fmt(st.price)}`);
  else if(PHASE==='right' && st.ma20break) fire('ma20','ma20','高位破 MA20，建议减仓一半',`收盘 ${fmt(st.M.close)} < MA20 ${fmt(st.M.ma20)} · 120日位置 ${st.pos120}%`);
  else if(PHASE==='right' && st.trailHit && !st.ma20break) fire('trail','trail','ATR 锁利润线触发（辅助）',`收盘 ${fmt(st.S.close)} < 追踪线 ${fmt(st.S.trail)}（${st.S.gap_trail}%）`);
  else if(st.red3) fire('r3','resonance3','三维共振！重仓出击！',`1H ${st.s1}/3 · 4H ${st.s4}/3 · 日线达标 · ${fmt(st.price)}`);
  else if(st.crash) fire('crash','crash','极速反弹机会出现',`暴跌 ${st.c.score}/4 + 右侧确认 · ${fmt(st.price)}`);
  else if(st.blue2) fire('r2','resonance2','牛市回调做T · 1H+4H 共振',`1H ${st.s1}/3 · 4H ${st.s4}/3 · ${fmt(st.price)}`);
  else if(st.mo){
    const ys = yseqState();
    if(ys) fire('mo','mo', `黄灯第 ${ys.seq} 次 · ${ys.nm}`, `建议仓位 ${ys.pos} · 偏离 MA60 ${ys.cur.gap}% · 磨底 ${st.m.day.score}/${st.m.day.denom||4} · ${fmt(st.price)}`);
    else fire('mo','mo','进入震荡底部区',`磨底 ${st.m.day.score}/${st.m.day.denom||4} · 60日位置 ${st.m.day.space.pos60.toFixed(0)}% · ${fmt(st.price)}`);
  }
}

function renderTripleReview(){
  const R = DATA.tripleReview || []; if(!R.length) return;
  const modColor = m => (m.indexOf('超买')>=0 ? '#a855f7' : (m.indexOf('MA60')>=0 ? '#f0524d' : '#f59e0b'));
  document.getElementById('trptb').innerHTML = R.map(r=>{
    const t = r.top;
    const topCell = t
      ? `<span style="color:#a855f7">${t.score}/4</span><br><span style="color:#6e7681">${t.date.slice(5)} T+${t.days} · ${fmt(t.close)}</span>`
      : '<span style="color:#4a5563">未触发</span><br><span style="color:#6e7681">雷达盲区</span>';
    const th = r.trail_hit;
    const trailCell = th
      ? `<span style="color:#f59e0b">${th.date.slice(5)} T+${th.days}</span><br><span style="color:#6e7681">${fmt(th.close)} · MA10 ${th.dev10}%</span>`
      : '<span style="color:#4a5563">未触发</span>';
    const m = r.ma60;
    const maCell = m
      ? (m.before
          ? `<span style="color:#f0524d">顶点前 ${Math.abs(m.days)} 天已破</span><br><span style="color:#6e7681">${m.date.slice(0,7)} · ${fmt(m.close)}</span>`
          : `<span style="color:#f0524d">${m.date.slice(5)} T+${m.days}</span><br><span style="color:#6e7681">${fmt(m.close)}</span>`)
      : '<span style="color:#26a69a">未破</span>';
    const f = r.first || {};
    return `<tr>
      <td style="text-align:left">${r.date.slice(2)}<br><span style="color:#6e7681">高 ${fmt(r.high)} · 收 ${fmt(r.close)}</span></td>
      <td style="font-size:10.5px;color:#9aa4b2">${r.tag}</td>
      <td>${topCell}</td><td>${trailCell}</td><td>${maCell}</td>
      <td style="color:${modColor(f.module||'')};font-weight:600">${f.module||'-'}<br><span style="color:#6e7681;font-weight:400">${f.date?f.date.slice(5)+' · '+fmt(f.price):''}</span></td>
      <td>${fmt(r.low)}<br><span style="color:#6e7681">${r.low_day.slice(5)}</span></td>
      <td style="color:#26a69a">${r.drop}%</td>
      <td style="color:#26a69a;font-weight:600">${r.avoid!=null?'+'+r.avoid+'%':'-'}</td></tr>`;
  }).join('');

  document.getElementById('trpsum').innerHTML =
    `<b>1-29（绝对大顶）：三模块全中，超买紫灯当天就响。</b>3/4 分（空间 90%+ / 3日涨 7.37% / 量比 2.18 收阴），收 5,377 报警；次日止盈线再确认 4,860。后续跌到 4,099（<b>-23.77%</b>），信号价比最低点高 <b>31.18%</b>——完整避开。` +
    `<br><b>3-02（第一波诱多顶）：超买雷达没响，止盈线救了。</b>雷达 0/4（120 日位置不足、无天量），但止盈线仍是 1-29 那段锁定的 <b>5,174.02</b>，3-03 收盘 5,088 就跌破 MA10 → <b>T+1 报警</b>。后续跌 4,099（<b>-22.98%</b>），信号价高出最低 <b>24.13%</b>。` +
    `<br><b>5-12（破 MA60 后反弹）：根本不是"新顶"，MA60 早在 3-18 就报警了。</b>依赖 MA60 纪律，这个位置<b>本就不该有仓位</b>；止盈线 5-14 只是二次确认（4,652）。后续跌 3,943（-16.36%）。` +
    `<br><b>结论：两个诱多陷阱都躲过了，但贡献者不同——3-02 靠止盈线，5-12 靠 MA60。</b>超买雷达在这两个位置<b>连续未触发</b>，印证它只认"垂直赶顶 + 天量"，对缩量反弹顶天然失明。三者不是并列关系，而是接力：<b>紫灯提示赶顶（只停加仓、不下卖单）→ 止盈线管缓跌 → MA60 管趋势</b>。` +
    `<br><span style="color:#6e7681">注：3-02 的止盈线之所以有效，正是因为 2-24/3-02 都没创 60 日新高，线没有重置、仍沿用 1-29 的 5,174——"次高不重置"这条规则在这里直接兑现。</span>`;
}

function renderTrailReview(){
  const R = DATA.trailReview || []; if(!R.length) return;
  document.getElementById('trvtb').innerHTML = R.map(r=>{
    const neg = r.gap_peak < 0;
    const gapCol = neg ? '#f0524d' : '#8b949e';
    const gapTxt = `${r.gap_peak>=0?'+':''}${r.gap_peak}%` + (neg?'<br><span style="color:#f0524d;font-size:10px">已在线下</span>':'');
    const m60 = r.ma60_broken
      ? `<span style="color:#f0524d">已破 ${r.ma60_gap}%</span><br><span style="color:#f0524d;font-size:10px">模块失效</span>`
      : `<span style="color:#26a69a">未破 +${r.ma60_gap}%</span>`;
    let filt = '-';
    if(r.paused!=null){
      filt = r.paused
        ? `<span style="color:#f59e0b">暂停</span><br><span style="color:#6e7681">仍在 MA10 上方</span>`
        : `<span style="color:#26a69a">放行</span><br><span style="color:#6e7681">已破 MA10</span>`;
    }
    const first = r.first_break ? `${r.first_break.date.slice(5)} <span style="color:#6e7681">T+${r.first_break.days}</span>` : '-';
    const brk = r.break_date ? `${r.break_date.slice(5)}` : '-';
    const firstWho = r.who_first==='止盈线' ? '<span style="color:#f59e0b">止盈线</span>'
                    : (r.who_first==='MA60' ? '<span style="color:#f0524d">MA60</span>' : '-');
    return `<tr>
      <td style="text-align:left">${r.date.slice(2)}<br><span style="color:#6e7681">高 ${fmt(r.high)}</span></td>
      <td>${r.seg_start.slice(2)}<br><span style="color:#6e7681">${r.seg_days}天 · ${r.is_new_high?'新高':'次高'}</span></td>
      <td style="color:#e8c35a">${fmt(r.trail)}</td>
      <td style="color:${gapCol}">${gapTxt}</td>
      <td>${first}</td>
      <td>${r.break_days!=null?'T+'+r.break_days:'-'}</td>
      <td>${brk}</td>
      <td>${r.dev10!=null?(r.dev10>=0?'+':'')+r.dev10+'%':'-'}</td>
      <td>${filt}</td>
      <td>${m60}</td>
      <td>${firstWho}</td></tr>`;
  }).join('');

  document.getElementById('trvsum').innerHTML =
    `<b>MA10 过滤一次解决两件事：既不误伤，也不再拖。</b>5 个高点全部在 <b>T+1~T+5</b> 触发，<b>0 次被暂停</b>（原 ±3% 口径是 4 次暂停、平均 5.2 天）。` +
    `<br><b>8-25 的“慢刀子”从 T+12 提前到 T+5</b>：9-01 收盘 4,328.08 已跌破 MA10（-4.63%），当天就报警，不再等 MA20 慢吞吞跟上来。` +
    `<br><b>10-20 也从 T+7 提前到 T+5</b>：10-27 收盘 3,981.10、MA10 下方 4.58%，直接放行。` +
    `<br><b>唯一“变慢”的是 4-17（T+1 → T+2）</b>：4-20 那天收盘 4,820.63 仍勉强站在 MA10 上方，被暂停一天；但当天 MA60 已破 -3.87%，清仓线已经在响，晚这 1 天不影响结果。` +
    `<br><span style="color:#6e7681">平均触发延迟：原 ±3% 口径（含豁免）5.2 天 → <b style="color:#26a69a">MA10 口径 3.6 天</b>；最早 T+1、最晚 T+5。</span>`;
}

function round1(v){ return Math.round(v*10)/10; }

function renderTopReview(){
  const R = DATA.topReview || []; if(!R.length) return;
  const yn = b => b ? '<span style="color:#a855f7">✓</span>' : '<span style="color:#4a5563">✗</span>';
  document.getElementById('trtb').innerHTML = R.map(o=>{
    const d=o.day, fa=o.first_alert, br=o.break_ma20;
    const alert = d.score>=3 ? '<span style="color:#c084fc">当日紫警</span>' : '<span style="color:#6e7681">未发出</span>';
    const faTxt = fa ? `${fa[0].slice(5)} <span style="color:#6e7681">(T+${fa[1]})</span>` : '<span style="color:#6e7681">未出现</span>';
    const brTxt = br ? `T+${br[1]} <span style="color:#6e7681">${br[0].slice(5)}</span>` : '--';
    const clr = br && br[2]>=3 ? '<span style="color:#ef4444">是</span>' : '<span style="color:#6e7681">否</span>';
    return `<tr><td style="text-align:left">${o.date}</td><td>${fmt(o.peak)}</td>
      <td style="color:${d.score>=3?'#c084fc':'#8b949e'};font-weight:600">${d.score}/4</td>
      <td>${yn(d.space)}</td><td>${yn(d.momentum)}</td><td>${yn(d.pattern)}</td><td>${yn(d.volume)}</td>
      <td>${alert}</td><td>${faTxt}</td><td>${brTxt}</td><td>${br?br[2]+'/4':'--'}</td><td>${clr}</td>
      <td style="color:#26a69a">${o.dd60.toFixed(1)}%</td></tr>`;
  }).join('');

  const hit = R.filter(o=>o.day.score>=3).length;
  const clr = R.filter(o=>o.break_ma20 && o.break_ma20[2]>=3).length;
  document.getElementById('trsum').innerHTML =
    `<b>成绩：当日预警 ${hit}/4，清仓信号 ${clr}/4。</b>` +
    `只有 <b>2026-01-29</b> 在最高点当天拿到 3 分（空间 90.4% + 形态 3 日涨 7.37% + 量比 2.18 收阴），紫色预警准时；` +
    `其余三个高点（02-24、04-17、08-25）当日 <b>0 分</b>，之后 10 个交易日内也从未达到 3 分。` +
    `<br><b>为什么漏：</b>它们的 120 日位置只有 77.4% / 54.7% / 55.2%，不满足 ≥80%；上影线 11.4% / 45.4% / 41.6%，均未过 50%；量比 0.26 / 0.72 / 1.55，没有天量。` +
    `本质是<b>下跌趋势里的反弹次高点</b>，不是“加速赶顶”，这套雷达按定义就不认。` +
    `<br><b>清仓为什么也没给：</b>四次跌破 MA20 分别在 T+2 / T+7 / T+4 / T+5，破位当天得分只有 1 / 2 / 2 / 1，` +
    `达不到 ≥3 的门槛，所以深红弹窗一次都没亮。` +
    `<br><span style="color:#6e7681">结论：这套超买雷达只擅长“垂直赶顶 + 天量长上影”，对“缓涨/反弹次高点的阴跌顶”几乎无感；如果想靠它逃顶，必须再加一条「跌破 MA20 即减仓」的机械规则，而不是等 3 分。</span>`;
}

function calcGrid(){
  const budget=parseFloat(document.getElementById('g-budget').value)||0;
  const price=parseFloat(document.getElementById('g-price').value)||live.price;
  const invested=parseFloat(document.getElementById('g-invested').value)||0;
  const held=parseFloat(document.getElementById('g-held').value)||0;
  const remain=Math.max(0,budget-invested);
  const fx=parseFloat(document.getElementById('g-fx').value)||6.69;
  const au=(DATA.intra&&DATA.intra.h1&&DATA.intra.h1.detail)?DATA.intra.h1.detail.close:null;
  const lv0=parseFloat(document.getElementById('g-lv0').value)||price;
  const step=parseFloat(document.getElementById('g-step').value)||1.5;
  const levels=[0,1,2,3].map(k=>+(lv0*(1-step*(k+1)/100)).toFixed(1));
  const weights=[1,2,3,4], tot=10;
  const rows=levels.map((lv,k)=>{
    const amt=remain*weights[k]/tot;
    const cny=lv*fx/31.1035;
    const g=amt/cny;
    const hit=price<=lv;
    const gap=(price/lv-1)*100;
    return `<tr class="${hit?'hit':''}"><td>${lv} ${hit?'<span style="color:#f0524d">已触发</span>':''}</td>
      <td>${weights[k]}/10</td><td>${amt.toLocaleString('zh-CN',{maximumFractionDigits:0})}</td>
      <td>${cny.toFixed(2)}</td><td>${g.toFixed(2)}</td>
      <td style="color:${gap<=0?'#f0524d':'#8b949e'}">${gap>=0?'+':''}${gap.toFixed(2)}%</td></tr>`;
  }).join('');
  let bought=0; levels.forEach((lv,k)=>{ const cny=lv*fx/31.1035; bought += (remain*weights[k]/tot)/cny; });
  const avgOld = held>0 ? invested/held : null;
  const avgNew = (held+bought)>0 ? (invested+remain)/(held+bought) : null;
  const sum = `<div style="font-size:11px;color:#9aa4b2;margin-top:8px;line-height:1.8">
    计划总预算 ${budget.toLocaleString('zh-CN')} · 已投入 ${invested.toLocaleString('zh-CN')} · 剩余可投 <b style="color:#e6edf3">${remain.toLocaleString('zh-CN')}</b> 元
    ${held>0?` · 已持有 ${held} 克（旧均价 ${avgOld.toFixed(2)} 元/克）`:''}
    <br>若四档全部成交：新增约 <b style="color:#e6edf3">${bought.toFixed(2)}</b> 克，合计 ${(held+bought).toFixed(2)} 克，摊薄均价约 <b style="color:#e8c35a">${avgNew.toFixed(2)} 元/克</b>
  </div>`;
  const implied = au ? au*31.1035/fx : null;
  const note=document.getElementById('gridnote');
  if(au){
    note.innerHTML = `沪金 AU0 最新 <b style="color:#e6edf3">${au.toFixed(2)} 元/克</b> · 折伦敦金约 ${implied.toFixed(0)} USD/oz · 银行价通常在沪金上下几元内，点差属正常，不作建模。<br>
      克价 = 美元点位 × 汇率 ÷ 31.1035；档位 = 首档价逐档下移 ${step}%，比例 1:2:3:4。`;
  }
  document.getElementById('gridout').innerHTML = sum + `<table class="gtable"><thead><tr><th>档位</th><th>比例</th><th>金额(元)</th><th>克价(元/克)</th><th>克数</th><th>距触发</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderStop(){
  const S=DATA.stop||{}; const box=document.getElementById('stopout'), note=document.getElementById('stopnote');
  if(!S.date){ box.innerHTML='<div style="color:#6e7681;font-size:12px">暂无数据</div>'; return; }

  let cls='good', state='持有', desc='收盘未跌破 → 继续持有', head='动态止盈线（HH20 − 3×ATR14，只上移）';
  if(S.fail){ cls='fail'; state='失效'; head='动态止盈线（已失效）'; desc='<span style="color:#f0524d">MA60 已破 → 请看清仓线</span>'; }
  else if(PHASE==='bull' && S.trigger){ cls='muted'; state='静音'; desc='<span style="color:#8b949e">牛市主升浪 · MA10 已静音，不减仓</span>'; }
  else if(S.trigger){ cls='warn'; state='触发'; desc='<span style="color:#f59e0b">跌破止盈线且失守 MA10 → 建议减仓一半</span>'; }
  else if(S.below_trail){ cls='muted'; state='暂停'; desc='<span style="color:#8b949e">跌破止盈线但守住 MA10 → 震荡暂停</span>'; }

  box.innerHTML = `<div class="stopcard ${cls}">
      <div><div class="sl">${head}</div><div class="sv">${fmt(S.trail)}</div></div>
      <div class="sd">收盘 ${fmt(S.close)} · 距线 ${S.gap_trail>=0?'+':''}${S.gap_trail}%<br>${desc}</div>
    </div>
    <div class="stopcard ${S.fail?'fail':(S.paused?'muted':'good')}">
      <div><div class="sl">MA60 / MA10 过滤</div><div class="sv">${S.fail?'已破 MA60':(S.paused?'暂停':'已破 MA10')}</div></div>
      <div class="sd">${S.fail?`收盘低于 MA60 ${Math.abs(((S.close/S.ma60-1)*100)).toFixed(2)}% · <span style="color:#f0524d">本模块失效</span>`
                        :`收盘 vs MA10 ${S.dev10>=0?'+':''}${S.dev10}%${S.paused?'（在上方 → 暂停）':'（在下方 → 放行）'}<br>MA10 ${fmt(S.ma10)} · MA20 ${fmt(S.ma20)}`}</div>
    </div>`;

  const segLine = `起点 <b>${S.seg_start}</b>（最近一次 60 日新高，第 ${S.seg_days} 个交易日），段内最高锁定 <b>${fmt(S.trail)}</b>，只上移不下移。`;
  const ruleLine = `规则：① 只用<b>日线收盘价</b>；② 跌破止盈线 <b>且收盘失守 MA10</b> → 立即触发；仍在 MA10 上方 → 视为震荡带暂停；③ 触发只减半仓；④ <b>MA60 一破，本模块立即失效</b>，清仓交给 MA60。`;
  note.innerHTML = (S.fail
      ? `<b style="color:#f0524d">当前 MA60 已破（收盘 ${fmt(S.close)} &lt; MA60 ${fmt(S.ma60)}），动态止盈线不再提供保护，请直接看顶部深红清仓提示。</b><br>`
      : '') +
    `ATR14 <b>${S.atr14}</b> · 近 20 日最高 <b>${fmt(S.hh20)}</b> · 未棘轮值 ${fmt(S.chandelier_raw)}<br>` +
    segLine + `<br>` + ruleLine;
}

const LOG_KEY='goldTradeLog_v1';
function loadLog(){ try{ return JSON.parse(localStorage.getItem(LOG_KEY)||'[]'); }catch(e){ return []; } }
function saveLog(a){ localStorage.setItem(LOG_KEY, JSON.stringify(a)); }
function renderLog(){
  const a=loadLog(); const box=document.getElementById('loglist');
  document.getElementById('l-count').textContent = `共 ${a.length} 条（存在本机浏览器）`;
  if(!a.length){ box.innerHTML='<div style="font-size:11.5px;color:#5b6472;margin-top:8px">还没有记录。第一笔写下来，之后就不好意思乱来了。</div>'; return; }
  box.innerHTML = a.slice().reverse().map((x,idx)=>`<div class="logitem">
    <div class="lh"><span class="lt">${x.date} · ${x.act}</span>
      <span>${x.price?fmt(+x.price):'--'}</span><span>${x.size?x.size+'%':''}</span>
      <span class="lx" data-i="${a.length-1-idx}">删除</span></div>
    ${x.mood?`<div class="lm">${x.mood.replace(/</g,'&lt;')}</div>`:''}
  </div>`).join('');
  box.querySelectorAll('.lx').forEach(el=>el.onclick=()=>{
    const arr=loadLog(); arr.splice(+el.dataset.i,1); saveLog(arr); renderLog();
  });
}

function initTools(){
  const gp=document.getElementById('g-price');
  gp.value = live.price ? live.price.toFixed(1) : '';
  const gfx=document.getElementById('g-fx');
  if(DATA.fx) gfx.value=(+DATA.fx).toFixed(4);
  const lv0el=document.getElementById('g-lv0');
  if(lv0el && !lv0el.value) lv0el.value = live.price ? Math.floor(live.price/10)*10 : '';
  ['g-budget','g-price','g-fx','g-invested','g-held','g-lv0','g-step'].forEach(id=>document.getElementById(id).addEventListener('input',calcGrid));
  calcGrid(); renderStop();

  // 三档全覆盖委托：汇率默认取实时，改金额即时重算
  const tfx=document.getElementById('t-fx');
  if(tfx){ const _f=(DATA.fx&&+DATA.fx)||(DATA.fxenv||{}).fx; if(_f) tfx.value=(+_f).toFixed(4); }
  ['t-amt','t-fx'].forEach(id=>{ const el=document.getElementById(id); if(el) el.addEventListener('input',()=>{renderTranche();renderSizing();}); });
  (function(){
    let sv={}; try{ sv=JSON.parse(localStorage.getItem('gm_size')||'{}'); }catch(e){}
    ['s-asset','s-hold','s-save'].forEach(k=>{ const el=document.getElementById(k);
      if(el&&sv[k]!=null) el.value=sv[k];
      if(el) el.addEventListener('input',()=>{ const o={};
        ['s-asset','s-hold','s-save'].forEach(kk=>{ const e2=document.getElementById(kk); if(e2) o[kk]=e2.value; });
        try{ localStorage.setItem('gm_size',JSON.stringify(o)); }catch(e){}
        renderSizing(); });
    });
  })();
  renderTranche();

  document.getElementById('l-date').value = new Date().toISOString().slice(0,10);
  document.getElementById('l-price').value = live.price ? live.price.toFixed(1) : '';
  document.getElementById('l-add').onclick=()=>{
    const x={date:document.getElementById('l-date').value, act:document.getElementById('l-act').value,
             price:document.getElementById('l-price').value, size:document.getElementById('l-size').value,
             mood:document.getElementById('l-mood').value.trim()};
    if(!x.date){ alert('请选择日期'); return; }
    const a=loadLog(); a.push(x); saveLog(a); renderLog();
    document.getElementById('l-mood').value=''; document.getElementById('l-size').value='';
  };
  document.getElementById('l-export').onclick=()=>{
    const blob=new Blob([JSON.stringify(loadLog(),null,1)],{type:'application/json'});
    const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
    a.download='gold-trade-log-'+new Date().toISOString().slice(0,10)+'.json'; a.click();
  };
  document.getElementById('l-clear').onclick=()=>{
    if(confirm('确定清空全部交易记录？建议先导出备份。')){ saveLog([]); renderLog(); }
  };
  renderLog();
}

function paintTable(){
  const start = Math.max(0, bars.length-10);
  const rows = bars.slice(start);
  document.getElementById('tb').innerHTML = rows.map((b,i)=>{
    const idx = start+i;
    const prev = bars[idx-1] ? bars[idx-1].c : b.o;
    const d = b.c-prev, dp = d/prev*100, amp = (b.h-b.l)/prev*100;
    const col = d>=0 ? '#f0524d' : '#26a69a';
    return `<tr><td>${b.d}</td><td>${fmt(b.o)}</td><td>${fmt(b.h)}</td><td>${fmt(b.l)}</td>
      <td style="color:${col}">${fmt(b.c)}</td>
      <td style="color:${col}">${(dp>=0?'+':'')}${dp.toFixed(2)}%</td><td>${amp.toFixed(2)}%</td></tr>`;
  }).reverse().join('');
}

document.querySelectorAll('.btns button').forEach(btn=>{
  btn.onclick=()=>{
    document.querySelectorAll('.btns button').forEach(b=>b.classList.remove('on'));
    btn.classList.add('on'); N=+btn.dataset.n; drawK(); drawMACD(); drawVol();
  };
});

async function refresh(){
  try{
    const r = await fetch('https://api.gold-api.com/price/XAU',{cache:'no-store'});
    const j = await r.json();
    if(j && j.price){
      live.price = j.price;
      if(j.price>live.high) live.high=j.price;
      if(j.price<live.low) live.low=j.price;
      const now=new Date();
      live.date = now.toISOString().slice(0,10);
      live.time = now.toTimeString().slice(0,8);
      document.getElementById('liveflag').innerHTML='<span style="color:#26a69a">● 实时（60s）</span>';
      paintHeader(); paintAlert();
      const gp=document.getElementById('g-price');
      if(gp && document.activeElement!==gp) gp.value=live.price.toFixed(1);
      if(typeof calcGrid==='function') calcGrid();
    }
  }catch(e){
    document.getElementById('liveflag').innerHTML='<span style="color:#e8c35a">● 实时源不可达（显示构建快照）</span>';
  }
}

const _dl=document.getElementById('dline'); if(_dl && bars.length) _dl.textContent=bars[bars.length-1].d;
paintHeader(); renderTrend(); renderSignals(); renderMatrix(); renderRadar(); renderYseq(); renderCrash(); renderBacktest(); renderUpgrade(); renderTopReview(); renderTrailReview(); renderTripleReview(); paintTable(); initAlerts(); initCheat(); initTools(); drawK(); drawMACD(); drawVol(); drawRadar();
window.addEventListener('resize', ()=>{drawK();drawMACD();drawVol();drawRadar();});
setInterval(refresh, 60000);
</script>
</body>
</html>
"""

html = html.replace("__PAYLOAD__", payload)
path = "index.html"
open(path, "w", encoding="utf-8").write(html)
print("written", path, len(html))
