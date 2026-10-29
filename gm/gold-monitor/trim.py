#!/usr/bin/env python3
"""裁掉尚未收盘的最后一根 K 线：所有判定只用已完成的日线

伦敦金日线在纽约 17:00 收盘，对应 UTC 21:00（夏令时）/ 22:00（冬令时）。
这里保守统一按 UTC 22:30 判定：夏令时多等 1.5 小时，冬令时正好留 30 分钟缓冲，
一年四季都不用改。
"""
import json
import os
import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

CLOSE_UTC = datetime.time(22, 30)


def bar_closed(ds):
    try:
        d = datetime.date.fromisoformat(ds)
    except Exception:
        return True
    return datetime.datetime.utcnow() >= datetime.datetime.combine(d, CLOSE_UTC)


def main():
    D = json.load(open("data_full.json", encoding="utf-8"))
    kl = D.get("kline") or []
    if not kl:
        print("[trim] 无 K 线，跳过")
        return

    drop = 0
    while kl and not bar_closed(kl[-1]["d"]) and drop < 3:
        print("[trim] 丢弃未收盘 %s  O%.2f H%.2f L%.2f C%.2f" % (
            kl[-1]["d"], kl[-1]["o"], kl[-1]["h"], kl[-1]["l"], kl[-1]["c"]))
        kl.pop()
        drop += 1

    if not drop:
        print("[trim] 最后一根已收盘 %s" % kl[-1]["d"])
        return

    if not kl:
        print("[trim] 全部被裁掉，保留原文件不动")
        return

    D["kline"] = kl
    json.dump(D, open("data_full.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("[trim] 已裁掉 %d 根，最新完整日 %s 收盘 %.2f" % (drop, kl[-1]["d"], kl[-1]["c"]))


if __name__ == "__main__":
    main()
