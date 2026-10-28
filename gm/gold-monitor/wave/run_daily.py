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
STATE = "alert_state.json"      # 这个文件会被 workflow 拷回仓库，是唯一能持久化的地方
HIST_KEY = "wave_history"
HIST_MAX = 500


def _load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def _save_state(st):
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def history():
    return _load_state().get(HIST_KEY, [])


def last_logged_date():
    h = history()
    if h:
        return h[-1].get("d", "")
    try:
        with open(LOG, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        return rows[-1][0] if len(rows) > 1 else ""
    except Exception:
        return ""


def push_history(row):
    """把当天记录写进 alert_state.json（会被 commit 回仓库）"""
    st = _load_state()
    h = st.get(HIST_KEY, [])
    if h and h[-1].get("d") == row["d"]:
        h[-1] = row
    else:
        h.append(row)
    st[HIST_KEY] = h[-HIST_MAX:]
    _save_state(st)
    print("[wave] 历史记录 %d 条" % len(st[HIST_KEY]))


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
    # 从 csv 读回当天那行，同步进 alert_state.json
    try:
        with open(LOG, encoding="utf-8-sig") as f:
            row = list(csv.DictReader(f))[-1]
        if float(row["wA"] or 0) + float(row["wB"] or 0) <= 0:
            print("[wave] 无合法标注（数据太短？），本次不记录")
            return
        push_history({
            "d": row["date"], "c": float(row["close"]),
            "wA": float(row["wA"]), "wB": float(row["wB"]),
            "A_dead": float(row["A_dead"] or 0), "B_dead": float(row["B_dead"] or 0),
            "c100": float(row["C_tgt_100"] or 0), "w5": float(row["w5_target"] or 0),
        })
    except Exception as e:
        print("[wave] 历史记录写入失败：%s" % e)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[wave] 跳过（不影响主流程）：%s" % e)
    sys.exit(0)
