#!/usr/bin/env python3
"""信号台账：每个交易日把「环境 / 位置 / 动作 / 雷达」写进 ledger.csv。
用途：一年后不用重新推数据，直接拿这份台账做样本外复检。
用法：
    python ledger.py                # 增量更新（补今天 + 回填 T+20/40/60）
    python ledger.py --from 2026-01-01   # 从指定日期补录
"""
import json, csv, os, io, sys, contextlib, importlib.util

os.chdir(os.path.dirname(os.path.abspath(__file__)))
CSV = "ledger.csv"
FIELDS = ["date", "close", "ma20", "ma60", "ma200", "slope200", "hi250", "pos250",
          "zone", "env", "action60", "score", "s_space", "s_mom", "s_pat", "s_vol",
          "pos60", "below_lower", "yellow", "seq", "r20", "r40", "r60", "note"]

D = json.load(open("data_full.json", encoding="utf-8"))
bars = D["kline"]
C = [b["c"] for b in bars]
H = [b["h"] for b in bars]
DT = [b["d"] for b in bars]
N = len(bars)

with contextlib.redirect_stdout(io.StringIO()):
    spec = importlib.util.spec_from_file_location("rr", "radar.py")
    rr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rr)


def ma(i, n):
    return sum(C[i - n + 1:i + 1]) / n if i >= n - 1 else None


def judge(i):
    """返回当日的全部判定字段"""
    c = C[i]
    m20, m60, m200 = ma(i, 20), ma(i, 60), ma(i, 200)
    slope200 = (m200 / ma(i - 20, 200) - 1) * 100 if (m200 and i - 20 >= 199 and ma(i - 20, 200)) else None
    hi250 = max(H[max(0, i - 249):i + 1])
    pos250 = (c / hi250 - 1) * 100 if hi250 else None

    # 环境
    if slope200 is None:
        env = "过渡"
    elif c > m200 and slope200 > 0:
        env = "牛"
    elif c < m200 and slope200 < 0:
        env = "熊"
    else:
        env = "过渡"

    # 位置
    if pos250 is None:
        zone = "--"
    elif pos250 > -10:
        zone = "高"
    elif pos250 > -25:
        zone = "中"
    else:
        zone = "低"

    # MA60 破位动作
    if not (m60 and c < m60):
        act = "守住"
    elif env == "牛" and zone == "高":
        act = "不动"
    elif env == "过渡":
        act = "清仓"
    else:
        act = "减半"

    # 磨底雷达
    r = rr.radar(i)
    space = r["space"]
    return {
        "date": DT[i], "close": round(c, 2),
        "ma20": round(m20, 2) if m20 else None,
        "ma60": round(m60, 2) if m60 else None,
        "ma200": round(m200, 2) if m200 else None,
        "slope200": round(slope200, 2) if slope200 is not None else None,
        "hi250": round(hi250, 2), "pos250": round(pos250, 1) if pos250 is not None else None,
        "zone": zone, "env": env, "action60": act,
        "score": r["score"],
        "s_space": int(space["ok"]), "s_mom": int(r["momentum"]["ok"]),
        "s_pat": int(r["pattern"]["ok"]), "s_vol": int(r["volume"]["ok"]),
        "pos60": round(space["pos60"], 1), "below_lower": int(space["below_lower"]),
    }


def load():
    if not os.path.exists(CSV):
        return {}
    with open(CSV, encoding="utf-8-sig") as f:
        return {row["date"]: row for row in csv.DictReader(f)}


def main():
    rows = load()
    if "--from" in sys.argv:
        start = sys.argv[sys.argv.index("--from") + 1]
    elif rows:
        start = max(rows)          # 增量：从最后一天接着写
    else:
        start = "2026-01-01"       # 首次：默认补 2026 年至今
    i0 = next((k for k, d in enumerate(DT) if d >= start), N)
    added = 0
    for i in range(max(i0, 60), N):
        j = judge(i)
        if j["date"] not in rows:
            rows[j["date"]] = j
            added += 1
        else:
            rows[j["date"]].update({k: v for k, v in j.items() if k not in ("r20", "r40", "r60")})

    # 黄灯轮次 + 回填未来收益
    seq = 0
    last = -999
    idx = {d: k for k, d in enumerate(DT)}
    for d in sorted(rows):
        row = rows[d]
        k = idx.get(d)
        if k is None:
            continue
        is_y = int(int(row["score"]) >= 3 and float(row["pos60"] or 0) <= 20)
        if is_y and k - last >= 10:
            seq += 1
            last = k
            row["yellow"] = 1
            row["seq"] = seq
        else:
            row["yellow"] = 0
            row["seq"] = seq if seq else ""
        for n, key in ((20, "r20"), (40, "r40"), (60, "r60")):
            row[key] = round((C[k + n] / C[k] - 1) * 100, 2) if k + n < N else ""

    tmp = CSV + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for d in sorted(rows):
            w.writerow(rows[d])
    os.replace(tmp, CSV)
    print(f"台账已更新：{CSV}｜共 {len(rows)} 行｜本次新增 {added} 行｜最新 {max(rows)}")


if __name__ == "__main__":
    main()
