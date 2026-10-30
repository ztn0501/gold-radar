#!/usr/bin/env python3
"""数据异常校验：抓回来的数先过一遍合理性检查，再允许进入计算链

为什么需要：trim.py 只判断「最后一根是否收盘」，不判断数值是否合理。
东财/新浪若返回 402.1 而不是 4021，全链会照常跑完，所有雷达、推送、页面
全部按 402.1 计算 —— 价格跌破一切均线，磨底雷达满分，系统会大声喊买。
这类错误不会被任何现有环节拦住。

校验分三档：
  ok   —— 全部通过，更新「上一份有效数据」备份
  warn —— 有可疑项但不足以判定为坏数据，放行并记录（页面/推送会标出）
  fail —— 判定为坏数据，回滚到上一份有效数据，本链用旧数据跑完，推送告警

设计原则：宁可疑不放行。回滚的代价是「页面少更新一天」，
误用的代价是「基于错误价格给出买卖动作」。
"""
import json
import os
import shutil
import statistics

os.chdir(os.path.dirname(os.path.abspath(__file__)))

CUR = "data_full.json"
LAST = "data_full.last.json"      # 上一份通过校验的数据
OUT = "validation.json"

# ── 阈值 ────────────────────────────────────────────────────────────
PRICE_MIN, PRICE_MAX = 100.0, 20000.0   # 美元/盎司，1992 以来区间 250–5600
DAY_MOVE_FAIL = 15.0                    # 单日涨跌幅超过即判坏数据
DAY_MOVE_WARN = 8.0                     # 超过即标记可疑（历史极端值约 8–10%）
AMP_FAIL = 30.0                         # 单根振幅（高-低）/收
PEER_MEDIAN_FAIL = 1.0                  # 与旧数据重叠日收盘差中位数（%）
PEER_MAX_FAIL = 3.0                     # 与旧数据重叠日收盘差最大值（%）
SHRINK_FAIL = 20.0                      # 样本数比上份减少超过该比例
LIVE_DEV_WARN = 8.0                     # 实时价偏离最后收盘
LIVE_DEV_FAIL = 20.0                    # 偏离超过即丢弃实时价


def pct(a, b):
    return (a / b - 1) * 100 if b else 0.0


def main():
    issues, checks = [], []          # issues: fail/warn 项；checks: 全部明细

    def rec(name, ok, detail, level="fail"):
        checks.append({"n": name, "ok": bool(ok), "d": detail, "lv": level})
        if not ok:
            issues.append({"n": name, "d": detail, "lv": level})
        return ok

    try:
        D = json.load(open(CUR, encoding="utf-8"))
        kl = D.get("kline") or []
    except Exception as e:
        rec("文件可读", False, "data_full.json 无法解析：%s" % e)
        kl = []

    if not kl:
        rec("K 线非空", False, "K 线为空")

    ok_all = True

    if kl:
        last = kl[-1]
        prev = kl[-2] if len(kl) > 1 else last

        # 1. 价格绝对区间
        ok_all &= rec("价格区间", PRICE_MIN <= last["c"] <= PRICE_MAX,
                      "最新收盘 %.2f，合理区间 %.0f–%.0f" % (last["c"], PRICE_MIN, PRICE_MAX))

        # 2. 单日变动
        mv = pct(last["c"], prev["c"])
        if abs(mv) > DAY_MOVE_FAIL:
            ok_all &= rec("单日变动", False, "%s 收 %.2f，前日 %.2f，变动 %+.2f%% > %.0f%%"
                          % (last["d"], last["c"], prev["c"], mv, DAY_MOVE_FAIL))
        else:
            rec("单日变动", True, "%+.2f%%" % mv)
            if abs(mv) > DAY_MOVE_WARN:
                rec("单日变动偏大", False, "%+.2f%% 超过 %.0f%% 预警线" % (mv, DAY_MOVE_WARN), "warn")

        # 3. OHLC 逻辑
        bad_ohlc = [b["d"] for b in kl[-60:]
                    if not (b["l"] <= b["o"] <= b["h"] and b["l"] <= b["c"] <= b["h"] and b["l"] > 0)]
        ok_all &= rec("OHLC 逻辑", not bad_ohlc,
                      "近 60 根正常" if not bad_ohlc else "异常：%s" % ",".join(bad_ohlc[:5]))

        # 4. 日期单调、无重复
        ds = [b["d"] for b in kl]
        dup = len(ds) - len(set(ds))
        mono = all(ds[i] < ds[i + 1] for i in range(len(ds) - 1))
        ok_all &= rec("日期序列", dup == 0 and mono,
                      "%d 根，重复 %d，单调 %s" % (len(ds), dup, "是" if mono else "否"))

        # 5. 振幅
        amp = (last["h"] - last["l"]) / last["c"] * 100 if last["c"] else 0
        ok_all &= rec("最新振幅", amp <= AMP_FAIL, "%.2f%%" % amp)

        # 6. 与上一份有效数据对比（重叠日收盘是否稳定）
        if os.path.exists(LAST):
            try:
                P = json.load(open(LAST, encoding="utf-8"))
                pm = {b["d"]: b["c"] for b in (P.get("kline") or [])}
                diffs = [abs(pct(b["c"], pm[b["d"]])) for b in kl if b["d"] in pm]
                if diffs:
                    med, mx = statistics.median(diffs), max(diffs)
                    ok_all &= rec("与旧数据一致", med <= PEER_MEDIAN_FAIL and mx <= PEER_MAX_FAIL,
                                  "%d 个重叠日，差中位 %.3f%% 最大 %.3f%%" % (len(diffs), med, mx))
                # 7. 日期不得倒退
                # 允许倒退 3 天内：末根未收盘被 trim 掉属正常现象。
                # 超过 3 天才说明数据源出了问题（返回了旧快照）。
                # 这一条若判 fail 会回滚到「比新数据更新」的备份，形成死循环，所以必须宽容。
                plast = (P.get("kline") or [{}])[-1].get("d", "")
                if not last["d"] >= plast:
                    _gap = 0
                    try:
                        _gap = (__import__("datetime").date.fromisoformat(plast)
                                - __import__("datetime").date.fromisoformat(last["d"])).days
                    except Exception:
                        _gap = 99
                    if _gap <= 3:
                        rec("日期未倒退", True, "本次 %s / 上份 %s（落后 %d 天，末根未收盘被裁，正常）"
                            % (last["d"], plast, _gap))
                    else:
                        rec("日期未倒退", False, "本次 %s / 上份 %s（落后 %d 天）"
                            % (last["d"], plast, _gap))
                else:
                    rec("日期未倒退", True, "本次 %s / 上份 %s" % (last["d"], plast))
                # 8. 样本数不得骤降
                shrink = pct(len(kl), len(P.get("kline") or [1]))
                ok_all &= rec("样本数稳定", shrink > -SHRINK_FAIL,
                              "%d 根（上份 %d，变化 %+.1f%%）" % (len(kl), len(P.get("kline") or []), shrink))
            except Exception as e:
                rec("与旧数据一致", False, "备份不可用：%s" % e, "warn")
        else:
            print("[validate] 首次运行，建立基线备份")

    fails = [i for i in issues if i["lv"] == "fail"]
    warns = [i for i in issues if i["lv"] == "warn"]

    dropped = None
    if fails:
        status = "fail"
        # 回滚：坏数据绝不进入计算链
        if os.path.exists(LAST):
            shutil.copy(LAST, CUR)
            print("[validate] 已回滚至上一份有效数据 %s" % LAST)
        else:
            # 首次运行没有备份：退一步，砍掉最新的可疑 K 线
            try:
                D2 = json.load(open(CUR, encoding="utf-8"))
                k2 = D2.get("kline") or []
                if len(k2) > 2:
                    dropped = k2[-1]["d"]
                    D2["kline"] = k2[:-1]
                    json.dump(D2, open(CUR, "w", encoding="utf-8"),
                              ensure_ascii=False, separators=(",", ":"))
                    print("[validate] 无备份可回滚，已丢弃最新一根 %s" % dropped)
            except Exception as e:
                print("[validate] 降级处理失败：%s（下游可能基于坏数据）" % e)
    elif warns:
        status = "warn"
    else:
        status = "ok"

    # 通过（含仅 warn）时更新基线备份
    if status != "fail":
        try:
            shutil.copy(CUR, LAST)
        except Exception:
            pass

    # 9. 实时价与收盘价的偏离 —— 放在回滚之后，用可信的收盘价作基准
    live_fixed = False
    fixed_src = None
    try:
        if fails:
            kl = json.load(open(CUR, encoding="utf-8")).get("kline") or []
        J = json.load(open("data.json", encoding="utf-8"))
        lv = J.get("live") or {}
        if lv.get("price") and kl:
            dv = pct(lv["price"], kl[-1]["c"])
            if abs(dv) > LIVE_DEV_FAIL:
                rec("实时价可信", False, "实时 %.2f 偏离收盘 %.2f 达 %+.2f%%，本次已丢弃实时价、回用收盘"
                    % (lv["price"], kl[-1]["c"], dv), "warn")
                fixed_src = lv["price"]
                J["live"] = {"price": kl[-1]["c"], "prevClose": kl[-1]["c"], "open": kl[-1]["o"],
                             "high": kl[-1]["h"], "low": kl[-1]["l"], "time": "",
                             "date": kl[-1]["d"], "_fallback": True}
                json.dump(J, open("data.json", "w", encoding="utf-8"),
                          ensure_ascii=False, separators=(",", ":"))
                live_fixed = True
            else:
                rec("实时价可信", True, "%.2f 对收盘 %.2f（%+.2f%%）" % (lv["price"], kl[-1]["c"], dv))
                if abs(dv) > LIVE_DEV_WARN:
                    rec("实时价偏离", False, "%+.2f%%，无成交时属正常" % dv, "warn")
    except Exception:
        pass
    warns = [i for i in issues if i["lv"] == "warn"]

    payload = {
        "status": status,
        "time": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "date": (kl[-1]["d"] if kl else ""),
        "close": (round(kl[-1]["c"], 2) if kl else None),
        "n": len(kl),
        "fails": fails,
        "warns": warns,
        "checks": checks,
        "rolledBack": bool(fails) and os.path.exists(LAST),
        "dropped": dropped,
        "liveFixed": bool(live_fixed),
        "liveRejected": fixed_src,
    }
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("[validate] %s —— %d 项检查，%d 失败 %d 预警"
          % (status.upper(), len(checks), len(fails), len(warns)))
    for f in fails:
        print("   ✗ %s：%s" % (f["n"], f["d"]))
    for w in warns:
        print("   ! %s：%s" % (w["n"], w["d"]))


if __name__ == "__main__":
    main()
