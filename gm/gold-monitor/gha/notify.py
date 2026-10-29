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
    # 数据缺失时不要落到"清仓"这种吓人的默认值，避免抓数失败误报
    if not kl or price <= 0 or not ma60:
        action = "数据缺失（抓数未成功）"
    else:
        action = ma.get("ma60_action") or "清仓"
    env = ma.get("env") or "—"
    zone = ma.get("zone") or "—"
    pos250 = ma.get("pos250")

    msgs = []

    # 1) 磨底黄灯（买点）
    cur = yseq.get("cur") or {}
    if cur.get("lit") and cur.get("date") == today:
        # 上一轮最后一次：取今天之前的最后一个事件（否则会显示成今天自己）
        _prev = [e for e in (yseq.get("events") or []) if (e.get("date") or "") < today]
        _pe = _prev[-1] if _prev else {}
        msgs.append((
            "yellow",
            "【磨底黄灯】%s 本轮第%s次 %.0f" % (today, cur.get("curSeq", "?"), price),
            "\n\n".join([
                "**收盘** %.2f　MA60 %.2f（%+.2f%%）" % (price, ma60, gap60),
                "**雷达** %s/%s 分%s｜空间%s" % (
                    cur.get("score", "?"), cur.get("denom", 4),
                    "（量能待确认）" if cur.get("volMeasured") is False else "",
                    "达标" if cur.get("space") else "未达标"),
                "这一轮第 **%s** 次｜上一轮最后一次 %s（第 %s 次）" % (
                    cur.get("curSeq", "?"), _pe.get("date", "-"), _pe.get("seq", "-")),
                "**动作**：第 1 次 30%%，第 2 次 30%%，第 3 次起不加仓。\n试仓止损 %s。" % (cur.get("stopLow") or "—"),
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ])
        ))

    # 2) MA60 破位（卖点）—— 破位第 1 天推一次，之后每 5 个交易日补一次
    # 只推第 1 天的话，那天没看手机就永久沉默（2026-10 实际连续 23 天未再提醒）
    d60 = ma.get("below60_days") or 0
    try:
        last_d60 = int(st.get("break60_d60") or 0)
    except Exception:
        last_d60 = 0
    if ma.get("below60") and d60 >= 1 and (d60 == 1 or (d60 - last_d60) >= 5):
        msgs.append((
            "break60",
            "【跌破 MA60】%s · %s（第%d日）" % (today, action, d60),
            "\n\n".join([
                "**收盘** %.2f　<　MA60 %.2f（%+.2f%%）" % (price, ma60, gap60),
                "**环境** %s　**位置** %s（距一年高 %s）" % (env, zone, ("%s%%" % pos250) if pos250 is not None else "--"),
                "**判定**：%s" % action,
                "牛+高位→不动｜过渡期→清仓｜其余→减半。\n买回：站上 MA60 连续 2 日。",
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ])
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
            "\n\n".join([
                "**收盘** %.2f　MA60 %.2f（%+.2f%%）" % (price, ma60, gap60),
                "**环境** %s　**位置** %s（距一年高 %s）　**动作** %s" % (env, zone, ("%s%%" % pos250) if pos250 is not None else "--", action),
                "**磨底雷达** %s/%s｜上次黄灯 %s（第 %s 次）" % (
                    (yseq.get("cur") or {}).get("score", "-"),
                    (yseq.get("cur") or {}).get("denom", 4),
                    (yseq.get("cur") or {}).get("lastDate", "-"),
                    (yseq.get("cur") or {}).get("lastSeq", "-")),
                "通道测试成功，以后的真实信号会按同样格式推送。",
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ])
        ))

    if not todo:
        print("[notify] 今日无新信号")
        return

    if not keys and not (mu and mp):
        for k, title, desp in todo:
            print("[dry-run] %s" % title)
            print("         " + desp.replace("\n\n", " / ").replace("\n", " ")[:200])
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
