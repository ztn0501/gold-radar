#!/usr/bin/env python3
"""信号推送：磨底黄灯（买）/ MA60 破位（卖）/ 超买雷达（已停推）/ 数据滞后

两条通道，可单开也可同时开：
  微信  SERVERCHAN_KEY = Server酱 Turbo 的 SendKey（SCT 开头）
        多个微信：用英文逗号分隔，如 SCTaaa,SCTbbb（各发一份）
  邮件  MAIL_USER / MAIL_PASS / MAIL_TO——QQ 邮箱用授权码，smtp.qq.com:465

状态文件：alert_state.json（同一天同一类只推一次）
"""
import json, os, re, smtplib, ssl, urllib.parse, urllib.request
from datetime import date, datetime
from email.message import EmailMessage

BASE = os.path.dirname(os.path.abspath(__file__))
# 脚本若在 gha/ 子目录里，数据在上一级
if not os.path.exists(os.path.join(BASE, "data.json")):
    _up = os.path.dirname(BASE)
    if os.path.exists(os.path.join(_up, "data.json")):
        BASE = _up
os.chdir(BASE)

STATE_FILE = "alert_state.json"


def load(name, default=None):
    try:
        return json.load(open(name, encoding="utf-8"))
    except Exception:
        return default


def save_state(st):
    json.dump(st, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def send(key, title, desp):
    tag = key[-6:] if len(key) > 6 else key
    data = urllib.parse.urlencode({"title": title, "desp": desp}).encode()
    req = urllib.request.Request(
        "https://sctapi.ftqq.com/%s.send" % key, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        r = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        code = None
        try:
            code = json.loads(r).get("code")
        except Exception:
            pass
        if code not in (0, None):
            print("[notify] 微信(%s)被服务端拒绝：%s" % (tag, r[:160]))
            return False
        print("[notify] 微信(%s)已发送 -> %s" % (tag, r[:120]))
        return True
    except Exception as e:
        print("[notify] 微信(%s)发送失败：%s" % (tag, e))
        return False


def to_html(desp):
    s = desp.replace("&", "&amp;").replace("<", "&lt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[(.+?)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    return s.replace("\n", "<br>")


def send_mail(title, desp, user, pwd, to, host="smtp.qq.com", port=465):
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = user
    msg["To"] = to
    msg.set_content(re.sub(r"\*\*|\[(.+?)\]\((.+?)\)", r"\1\2", desp))
    msg.add_alternative(
        '<div style="font-family:-apple-system,Segoe UI,sans-serif;font-size:14px;line-height:1.8">'
        "<h3 style='margin:0 0 12px'>%s</h3>%s</div>" % (title, to_html(desp)),
        subtype="html")
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, pwd)
            s.send_message(msg)
        print("[notify] 邮件已发送 ->", to)
        return True
    except Exception as e:
        print("[notify] 邮件发送失败：", e)
        return False


def main():
    st = load(STATE_FILE, {}) or {}

    yseq = load("yellow_seq.json", {}) or {}
    ma = load("radar_ma.json", {}) or {}
    top = load("radar_top.json", {}) or {}
    ve = load("volenv.json", {}) or {}
    data = load("data.json", {}) or {}

    kl = data.get("kline") or []
    last_bar = kl[-1]["d"] if kl else ""
    # 判定日以磨底台账为准（trim.py 已裁掉未收盘那根），行情只用来取价
    today = (yseq.get("cur") or {}).get("date") or last_bar or date.today().isoformat()
    price = kl[-1]["c"] if kl else 0
    if kl and kl[-1]["d"] != today:
        # 行情比判定日新（最后一根还没收盘），价格退回台账里的收盘价，避免"今天价格配昨天均线"
        price = (yseq.get("cur") or {}).get("close") or price
    ma60 = ma.get("ma60") or 0
    gap60 = ma.get("gap60") or 0
    ma20 = ma.get("ma20") or 0
    # 数据缺失时不要落到"清仓"这种吓人的默认值，避免抓数失败误报
    if not kl or price <= 0 or not ma60:
        action = "数据缺失（抓数未成功）"
    else:
        action = ma.get("ma60_action") or "清仓"
    env = ma.get("env") or "—"
    zone = ma.get("zone") or "—"
    pos250 = ma.get("pos250")

    # 波动率环境（2026-10-30）：磨底雷达的阈值是绝对百分比，低波动时等价于 7 倍日波动，信号多为噪音
    # 分箱实测：60日均振幅 <1.1% 胜率 47%，1.1-1.3% 67%，1.3-1.6% 82%，>1.6% 68%
    _amp = ve.get("amp"); _pct = ve.get("pct"); _gr = ve.get("grade") or ""
    _pt = ("（历史 %s%% 分位）" % _pct) if _pct is not None else ""
    if _amp is None:
        vol_line = "**波动环境** 数据不足（60 日均振幅未算出）"
    elif _gr == "low":
        vol_line = "**波动环境** %.2f%%%s → **低波动，阈值失配，这个黄灯只当提示**" % (_amp, _pt)
    elif _gr == "mid":
        vol_line = "**波动环境** %.2f%%%s → 中性，信号中等" % (_amp, _pt)
    else:
        vol_line = "**波动环境** %.2f%%%s → 高波动，信号可信" % (_amp, _pt)

    # 人民币视角（2026-10-30）：用户持人民币积存金，美元金价的涨跌不是他实际的盈亏
    fe = load("fxenv.json", {}) or {}
    fx_line = ""
    if fe.get("cny"):
        _hi = None
        for _r in (fe.get("rows") or []):
            if str(_r.get("k", "")).startswith("2026"):
                _hi = _r
        if _hi:
            fx_line = "**人民币金价** %.1f 元/克（汇率 %.4f）｜自高点 美元 %+.1f%% → 人民币 %+.1f%%（差额 %.1f 个点来自汇率）" % (
                fe["cny"], fe["fx"], _hi["usd"], _hi["cny"], abs(_hi["drag"]))
        else:
            fx_line = "**人民币金价** %.1f 元/克（汇率 %.4f）" % (fe["cny"], fe["fx"])

    # 宏观环境（2026-10-30）：实际利率是黄金的机会成本，只描述逆风强度，不产生信号
    me = load("macroenv.json", {}) or {}
    ma_line = ""
    if me.get("r") is not None:
        _d = me.get("d60")
        _trend = "逆风加强" if (_d or 0) > 10 else ("逆风减弱" if (_d or 0) < -10 else "逆风持平")
        ma_line = "**宏观** 10Y 实际利率 %.2f%%（2010 以来 %.0f%% 分位）｜60日 %+dbp · %s" % (
            me["r"], me.get("pct") or 0, _d or 0, _trend)
        if me.get("sincePeakBp") is not None:
            ma_line += "｜金价见顶以来 %+dbp" % me["sincePeakBp"]

    # 风险温度（2026-10-30）：只描述恐慌强度与归属，不做信号
    re_ = load("riskenv.json", {}) or {}
    risk_line = ""
    if re_.get("gvz") is not None:
        _tag = ("黄金专属" if (re_.get("ratio") or 0) > 1.3
                and (re_.get("gvzPct") or 0) >= 70 else
                ("全市场" if (re_.get("vixPct") or 0) >= 70 else "常态"))
        risk_line = "**风险** VIX %.1f（%d%% 分位）｜GVZ %.1f（%d%% 分位）｜%s" % (
            re_["vix"], re_.get("vixPct") or 0, re_["gvz"], re_.get("gvzPct") or 0, _tag)

    msgs = []

    # 参照低点（2026-10-30）：第 2 档的触发线。
    # 不能直接用 250 日窗口最低价 —— 窗口每天滑动，触发价会跟着下跌往下爬，破了也显示「还没破」。
    rl = load("ref_low.json", {}) or {}
    rl_usd = rl.get("usd") or 0
    rl_line = ""
    if rl_usd and price:
        _rg = (price / rl_usd - 1) * 100
        rl_line = "**参照低点** %.2f（%s）｜距 %+.1f%%%s" % (
            rl_usd, rl.get("d", "--"), _rg,
            "　已破，第 2 档条件成立" if _rg <= 0 else ("　逼近，第 2 档待命" if _rg <= 3 else ""))

    # 0) 跌破参照低点 → 第 2 档触发（用收盘价，不用盘中价，避免假破位）
    if rl_usd and price and price < rl_usd and st.get("reflow") != today:
        msgs.append((
            "reflow",
            "【跌破参照低点】%s · 收 %.0f < %.2f" % (today, price, rl_usd),
            "\n\n".join([x for x in [
                "**收盘** %.2f　<　参照低点 %.2f（%+.2f%%）" % (price, rl_usd, (price / rl_usd - 1) * 100),
                "该价位是 %s 的 250 日最低点，已锁定为第 2 档触发线，不随窗口滑动。" % rl.get("d", "--"),
                fx_line or None,
                "**动作**：第 2 档（30%）条件成立 —— 但**第 1 档没执行完，这笔钱不许动**。",
                "再跌破 3500（自高点 -37.5%）→ 三档全部作废，停止加仓，重新评估。",
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ] if x])
        ))

    # 1) 磨底黄灯（买点）
    cur = yseq.get("cur") or {}
    # 第 3 档 B 路径：雷达 ≥3/4 且收盘站上 MA20（A 路径仍是站上 MA60 且 3 日不破，两条先到先算）
    t3_line = None
    if ma20 and price > 0:
        _g20 = (price / ma20 - 1) * 100
        _sc = cur.get("score") or 0
        if _sc >= 3 and price > ma20:
            t3_line = "**第 3 档 B 路径成立**：雷达 %s/4 ≥3 ＋ 收盘站上 MA20 %.0f（%+.2f%%）" % (_sc, ma20, _g20)
        else:
            _bits = []
            if _sc < 3:
                _bits.append("雷达还需 %d 项（现 %s/4）" % (3 - _sc, _sc))
            if price <= ma20:
                _bits.append("收盘站上 MA20 %.0f（现 %+.2f%%）" % (ma20, _g20))
            t3_line = "**第 3 档 B 路径**：" + " ＋ ".join(_bits)
    if cur.get("lit") and cur.get("date") == today:
        # 上一轮最后一次：取今天之前的最后一个事件（否则会显示成今天自己）
        _prev = [e for e in (yseq.get("events") or []) if (e.get("date") or "") < today]
        _pe = _prev[-1] if _prev else {}
        msgs.append((
            "yellow",
            "【磨底黄灯】%s 本轮第%s次 %.0f" % (today, cur.get("curSeq", "?"), price),
            "\n\n".join([x for x in [
                "**收盘** %.2f　MA60 %.2f（%+.2f%%）" % (price, ma60, gap60),
                "**雷达** %s/%s 分%s｜空间%s" % (
                    cur.get("score", "?"), cur.get("denom", 4),
                    "（量能待确认）" if cur.get("volMeasured") is False else "",
                    "达标" if cur.get("space") else "未达标"),
                "这一轮第 **%s** 次｜上一轮最后一次 %s（第 %s 次）" % (
                    cur.get("curSeq", "?"), _pe.get("date", "-"), _pe.get("seq", "-")),
                vol_line,
                t3_line or None,
                fx_line or None,
                rl_line or None,
                ma_line or None,
                risk_line or None,
                "**动作**：第 1 次 30%%，第 2 次 30%%，第 3 次起不加仓。\n试仓止损 %s。" % (cur.get("stopLow") or "—"),
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ] if x])
        ))

    # 2) MA60 破位（卖点）—— 破位第 1 天推一次，之后每 5 个交易日补一次
    # 只推第 1 天的话，那天没看手机就永久沉默（2026-10 实际连续 23 天未再提醒）
    d60 = ma.get("below60_days") or 0
    try:
        last_d60 = int(st.get("break60_d60") or 0)
    except Exception:
        last_d60 = 0
    if ma.get("below60") and d60 >= 1 and (d60 == 1 or (d60 - last_d60) >= 5):
        # 偏离 MA200：破位推送里给一行「还有多少下跌空间」（2026-10-30）
        _m2 = {}
        try:
            _m2 = load("ma200env.json", {}) or {}
        except Exception:
            _m2 = {}
        m2_line = ""
        if _m2.get("dev") is not None:
            m2_line = "**偏离 MA200** %+.1f%%（历史 %s%% 分位，极值 %s%%）" % (
                _m2["dev"], _m2.get("pct", "--"), _m2.get("min", "--"))
        msgs.append((
            "break60",
            "【跌破 MA60】%s · %s（第%d日）" % (today, action, d60),
            "\n\n".join([x for x in [
                "**收盘** %.2f　<　MA60 %.2f（%+.2f%%）" % (price, ma60, gap60),
                "**环境** %s　**位置** %s（距一年高 %s）" % (env, zone, ("%s%%" % pos250) if pos250 is not None else "--"),
                m2_line or None,
                fx_line or None,
                rl_line or None,
                ma_line or None,
                risk_line or None,
                "**判定**：%s" % action,
                "牛+高位→不动｜过渡期→清仓｜其余→减半。\n买回：站上 MA60 连续 2 日。",
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ] if x])
        ))

    # 3) 超买雷达 —— 2026-10 起停止推送（它是超买提示，不是卖点）
    # 依据：2006-2026 共触发 69 次，只有 19 次在真顶 ±20 日内（28%），
    # T+60 有 74% 上涨；2024-2025 的 17 次 T+60 全部上涨。
    # 它只在页面展示，不再进微信/邮件。

    # 4) 数据滞后（超过 3 天）
    if last_bar:
        try:
            lag = (date.today() - datetime.fromisoformat(last_bar).date()).days
        except Exception:
            lag = 0
        if lag >= 3 and st.get("stale") != today:
            msgs.append((
                "stale",
                "【数据滞后】页面停在 %s" % last_bar,
                "\n\n".join([
                    "今天 %s，最新行情只到 **%s**。" % (today, last_bar),
                    "可能是接口故障或被限流，去 Actions 看日志。",
                ])
            ))

    # 4) 数据自检未通过（2026-10-30）—— 优先级最高的告警
    # 场景：接口返回 402.1 而非 4021，若不放行拦截，全链会按 402.1 计算并推送"全线破位"
    va = load("validation.json", {}) or {}
    if va.get("status") == "fail":
        _fl = va.get("fails") or []
        _tag = "%s|%d" % (va.get("time") or "", len(_fl))
        if st.get("validation") != _tag:
            msgs.append((
                "validation",
                "【数据自检未通过】已拦截，本日不更新",
                "\n\n".join([
                    "**拦截了 %d 项异常**（共 %d 项检查）" % (len(_fl), len(va.get("checks") or [])),
                    "\n".join(["· **%s**：%s" % (f["n"], f["d"]) for f in _fl]),
                    ("**已回滚**到上一份有效数据，页面与信号仍基于旧行情。" if va.get("rolledBack")
                     else ("**已丢弃最新一根** %s。" % va["dropped"]) if va.get("dropped")
                     else "**无备份可回滚**，请人工检查 data_full.json。"),
                    "**不要按今天的信号操作**。先去 Actions 看 fetch_full.py 的日志，确认是接口异常还是真行情。",
                    "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
                ])
            ))
            st["validation"] = _tag

    todo = [(k, t, d) for k, t, d in msgs if st.get(k) != today]
    for k, _, _ in msgs:
        if st.get(k) == today:
            print("[skip] %s 今天已推送过" % k)

    # 支持多个微信号：SERVERCHAN_KEY 用英文逗号分隔多把 SendKey
    keys = [x.strip() for x in (os.environ.get("SERVERCHAN_KEY") or "").split(",") if x.strip()]
    mu = (os.environ.get("MAIL_USER") or "").strip()
    mp = (os.environ.get("MAIL_PASS") or "").strip()
    mt = (os.environ.get("MAIL_TO") or mu).strip()
    mh = (os.environ.get("MAIL_HOST") or "smtp.qq.com").strip()
    manual = (os.environ.get("MANUAL") or "") == "workflow_dispatch"

    # 手动运行 → 额外发一条当前状态，用来验证通道是否通
    if manual and st.get("manual") != today:
        todo.append((
            "manual",
            "【状态播报】%s · 收 %.0f · %s/%s" % (today, price, env, zone),
            "\n\n".join([x for x in [
                "**收盘** %.2f　MA60 %.2f（%+.2f%%）" % (price, ma60, gap60),
                "**环境** %s　**位置** %s（距一年高 %s）　**动作** %s" % (env, zone, ("%s%%" % pos250) if pos250 is not None else "--", action),
                fx_line or "**人民币金价** 数据未就绪",
                rl_line or "**参照低点** 未锁定（ref_low.json 缺失）",
                ma_line or "**宏观** 实际利率数据未就绪",
                risk_line or "**风险** VIX/GVZ 数据未就绪",
                "**磨底雷达** %s/%s｜上次黄灯 %s（第 %s 次）" % (
                    (yseq.get("cur") or {}).get("score", "-"),
                    (yseq.get("cur") or {}).get("denom", 4),
                    (yseq.get("cur") or {}).get("lastDate", "-"),
                    (yseq.get("cur") or {}).get("lastSeq", "-")),
                t3_line,
                "通道测试成功，以后的真实信号会按同样格式推送。",
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ] if x])
        ))

    if not todo:
        print("[notify] 今日无新信号")
        return

    if not keys and not (mu and mp):
        for k, title, desp in todo:
            print("[dry-run] %s" % title)
            print("         " + desp.replace("\n\n", " / ").replace("\n", " ")[:420])
        print("[skip] 未配置推送通道（SERVERCHAN_KEY 或 MAIL_USER/MAIL_PASS），未实际发送")
        return

    for k, title, desp in todo:
        ok = False
        for kk in keys:
            ok = send(kk, title, desp) or ok
        if mu and mp:
            ok = send_mail(title, desp, mu, mp, mt, host=mh) or ok
        if ok:
            st[k] = today
            if k == "break60":
                st["break60_d60"] = d60
            save_state(st)


if __name__ == "__main__":
    main()
