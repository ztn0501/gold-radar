#!/usr/bin/env python3
"""GitHub Actions 用：判断提醒条件并通过 Server酱 推送微信
环境变量：SERVERCHAN_KEY
"""
import json, os, urllib.request, urllib.parse, datetime, re

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

ZONE = (3850, 3959)
COOLDOWN_H = 6

def load(name, default=None):
    try:
        return json.load(open(name, encoding="utf-8"))
    except Exception:
        return default

def live_price():
    try:
        req = urllib.request.Request("https://hq.sinajs.cn/list=hf_XAU",
                                     headers={"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"})
        s = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        f = re.search(r'"(.*)"', s).group(1).split(",")
        return float(f[0]), f[12] + " " + f[6]
    except Exception:
        return None, None

def send(key, title, desp):
    data = urllib.parse.urlencode({"title": title, "desp": desp}).encode()
    url = f"https://sctapi.ftqq.com/{key}.send"
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    r = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    print("[notify]", r[:200])

def main():
    bt = load("backtest.json", {}) or {}
    radar = load("radar.json", []) or []
    c = bt.get("latest_crash") or {}
    m = radar[-1]["day"] if radar else {}
    price, ts = live_price()

    crash = bool(c.get("score", 0) >= 3 and c.get("confirm"))
    mo = bool(m.get("score", 0) >= 3 and price and ZONE[0] <= price <= ZONE[1])

    state = load("alert_state.json", {}) or {}
    now = datetime.datetime.utcnow()

    def can_send(k):
        last = state.get(k)
        if not last:
            return True
        try:
            return (now - datetime.datetime.fromisoformat(last)).total_seconds() > COOLDOWN_H * 3600
        except Exception:
            return True

    key = os.environ.get("SERVERCHAN_KEY", "").strip()
    if not key:
        print("[skip] 未配置 SERVERCHAN_KEY")
        return

    if crash and can_send("crash"):
        send(key, "【黄金】极速反弹机会出现",
             f"暴跌雷达 {c.get('score')}/4 + 右侧确认成立\n日期：{c.get('date')}\n现价：{price}（{ts}）\n\n"
             f"空间 {float(c.get('ret3') or 0):.2f}%/3日 · 下影 {float(c.get('ls') or 0):.1f}% · 量比 {float(c.get('ratio') or 0):.2f}x\n"
             "系统提示，不构成投资建议。")
        state["crash"] = now.isoformat()

    if mo and can_send("mo"):
        send(key, "【黄金】进入震荡底部区",
             f"磨底雷达 {m.get('score')}/4，价格 {price} 位于 3850–3959\n日期：{m.get('d')}\n\n"
             "可考虑分批网格建仓（系统仅提示，不代下单）。\n"
             "注意：磨底雷达 20 日胜率约 55.6%，接近随机，务必配合确认与止损。")
        state["mo"] = now.isoformat()

    json.dump(state, open("alert_state.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[done] crash={crash} mo={mo} price={price}")

if __name__ == "__main__":
    main()
