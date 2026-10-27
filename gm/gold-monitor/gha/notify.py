#!/usr/bin/env python3
"""信号推送：磨底黄灯（买）/ MA60 破位（卖）/ 逃顶雷达（卖）/ 数据滞后

两条通道，可单开也可同时开：
  微信  SERVERCHAN_KEY = Server酱 Turbo 的 SendKey（SCT 开头）
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
    data = urllib.parse.urlencode({"title": title, "desp": desp}).encode()
    req = urllib.request.Request(
        "https://sctapi.ftqq.com/%s.send" % key, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        r = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        print("[notify] 微信已发送 ->", r[:160])
        return True
    except Exception as e:
        print("[notify] 微信发送失败：", e)
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
    # 以最新行情日期为准（服务器是 UTC，直接取本地日期会差 8 小时）
    today = last_bar or date.today().isoformat()
    price = kl[-1]["c"] if kl else 0
    ma60 = ma.get("ma60") or 0
    gap60 = ma.get("gap60") or 0
    action = ma.get("ma60_action") or "清仓"
    env = ma.get("env") or "—"
    zone = ma.get("zone") or "—"
    pos250 = ma.get("pos250")

    msgs = []

    # 1) 磨底黄灯（买点）
    cur = yseq.get("cur") or {}
    if cur.get("lit") and cur.get("date") == today:
        msgs.append((
            "yellow",
            "【磨底黄灯】%s 第%s次 %.0f" % (today, cur.get("curSeq", "?"), price),
            "\n\n".join([
                "**收盘** %.2f　MA60 %.2f（%+.2f%%）" % (price, ma60, gap60),
                "**雷达** %s/4 分｜空间%s" % (cur.get("score", "?"), "达标" if cur.get("space") else "未达标"),
                "这一轮第 **%s** 次，上一次 %s（%s）" % (
                    cur.get("curSeq", "?"), cur.get("lastSeq", "-"), cur.get("lastDate", "-")),
                "**动作**：第 1 次 30%%，第 2 次 30%%，第 3 次起不加仓。\n试仓止损 %s。" % (cur.get("stopLow") or "—"),
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ])
        ))

    # 2) MA60 破位（卖点）
    if ma.get("below60") and ma.get("below60_days") == 1:
        msgs.append((
            "break60",
            "【跌破 MA60】%s · %s" % (today, action),
            "\n\n".join([
                "**收盘** %.2f　<　MA60 %.2f（%+.2f%%）" % (price, ma60, gap60),
                "**环境** %s　**位置** %s（距一年高 %s%%）" % (env, zone, pos250),
                "**判定**：%s" % action,
                "牛+高位→不动｜过渡期→清仓｜其余→减半。\n买回：站上 MA60 连续 2 日。",
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ])
        ))

    # 3) 逃顶雷达（卖点）
    try:
        tscore = int(top.get("score") or 0)
    except Exception:
        tscore = 0
    if tscore >= 3 and (top.get("date") or "") == today:
        msgs.append((
            "top",
            "【逃顶雷达】%s · %d/4" % (today, tscore),
            "\n\n".join([
                "**收盘** %.2f" % price,
                "空间%s 动能%s 形态%s 量能%s" % (
                    "✓" if top.get("space") else "✗",
                    "✓" if top.get("momentum") else "✗",
                    "✓" if top.get("pattern") else "✗",
                    "✓" if top.get("volume") else "✗"),
                "高位 3 项以上成立，注意减仓。",
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ])
        ))

    # 4) 数据滞后（超过 3 天）
    if last_bar:
        try:
            lag = (datetime.fromisoformat(today) - datetime.fromisoformat(last_bar)).days
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

    key = (os.environ.get("SERVERCHAN_KEY") or "").strip()
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
                "**环境** %s　**位置** %s（距一年高 %s%%）　**动作** %s" % (env, zone, pos250, action),
                "**磨底雷达** %s/4｜上次黄灯 %s（第 %s 次）" % (
                    (yseq.get("cur") or {}).get("score", "-"),
                    (yseq.get("cur") or {}).get("lastDate", "-"),
                    (yseq.get("cur") or {}).get("lastSeq", "-")),
                "通道测试成功，以后的真实信号会按同样格式推送。",
                "[打开盯盘台](https://ztn0501.github.io/gold-radar/)",
            ])
        ))

    if not todo:
        print("[notify] 今日无新信号")
        return

    if not key and not (mu and mp):
        for k, title, desp in todo:
            print("[dry-run] %s" % title)
            print("         " + desp.replace("\n\n", " / ").replace("\n", " ")[:200])
        print("[skip] 未配置推送通道（SERVERCHAN_KEY 或 MAIL_USER/MAIL_PASS），未实际发送")
        return

    for k, title, desp in todo:
        ok = False
        if key:
            ok = send(key, title, desp) or ok
        if mu and mp:
            ok = send_mail(title, desp, mu, mp, mt, host=mh) or ok
        if ok:
            st[k] = today
            save_state(st)


if __name__ == "__main__":
    main()
