#!/usr/bin/env python3
"""每日跑一次波浪结构 + 中枢，写入 wave_log.csv（只记录，不判定）

设计要点：
  · update.py 每 30 分钟跑一次，这里做“当天只记一次”的去重
  · 任何异常都吞掉并返回 0 —— 研究模块不能拖垮主流程
"""
import json, os, sys, csv

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
os.chdir(ROOT)
sys.path.insert(0, BASE)

LOG = os.path.join(BASE, "wave_log.csv")


def last_logged_date():
    try:
        with open(LOG, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        return rows[-1][0] if len(rows) > 1 else ""
    except Exception:
        return ""


def add_zhongshu():
    """把最近一个日线中枢写进 wave_candidates.json，供页面展示"""
    import chan as CH
    DT, C, H, L = CH.load()
    mh, ml, mi = CH.merge_inclusion(H, L, DT)
    fr = CH.fractals(mh, ml)
    bi = CH.build_bi(fr, mh, ml)
    zs = CH.zhongshu(bi)
    if not zs:
        return

    def ri(m, k):
        seg = mi[m]
        return max(seg, key=lambda i: H[i]) if k == "H" else min(seg, key=lambda i: L[i])

    z = zs[-1]
    s, e = ri(z["start"], "L"), ri(z["end"], "H")
    pos = "内部"
    if C[-1] > z["zg"]:
        pos = "上沿之上"
    elif C[-1] < z["zd"]:
        pos = "下沿之下"
    p = os.path.join(BASE, "wave_candidates.json")
    d = json.load(open(p, encoding="utf-8"))
    d["chan"] = dict(zd=round(z["zd"]), zg=round(z["zg"]),
                     start=DT[s], end=DT[e], pos=pos, n_bi=z.get("n"))
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[wave] 中枢 %.0f–%.0f（%s 起，现价%s）" % (z["zd"], z["zg"], DT[s], pos))


def main():
    import wave_model
    d = json.load(open("data_full.json", encoding="utf-8"))["kline"]
    today = d[-1]["d"]
    if last_logged_date() == today:
        print("[wave] %s 已记录，跳过" % today)
        return
    wave_model.main()
    add_zhongshu()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[wave] 跳过（不影响主流程）：%s" % e)
    sys.exit(0)
