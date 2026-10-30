#!/usr/bin/env python3
"""基本面环境：美国 10 年期 TIPS 实际利率 + 历史分位 + 与金价的历史关系

为什么只做这一个指标：
  黄金没有现金流，它的定价锚是「持有黄金的机会成本」——即扣掉通胀后的实际利率。
  实际利率是所有宏观变量里与金价关系最稳定、最容易拿到、最不容易被解读分歧污染的一个。
  央行购金、地缘、ETF 流向都影响金价，但前两个拿不到可靠的高频数据，后一个已在页面里
  （GLD 持仓）。与其堆四个半可信的指标，不如把一个可信的做深。

数据源：美国财政部每日实际收益率曲线（TIPS），免费、无需 key、按年 CSV。
  https://home.treasury.gov/.../daily_treasury_real_yield_curve
  这是 FRED DFII10 的原始来源，比 FRED 更稳（FRED 在本环境多次超时）。

边界（必须写在页面上）：
  这只能回答「现在的宏观环境对黄金是顺风还是逆风、逆风有多大」，
  不能回答「什么时候转」。历史上实际利率与金价多次长时间背离（2022-2024 就是），
  所以它不产生任何买卖信号，只做环境描述。
"""
import json
import os
import statistics
import urllib.request

os.chdir(os.path.dirname(os.path.abspath(__file__)))

YEARS = list(range(2010, 2027))     # 2010 起：TIPS 市场深度足够，且跨过负利率周期
OUT = "macro_hist.json"
URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
       "daily-treasury-rates.csv/%d/all?type=daily_treasury_real_yield_curve"
       "&field_tdr_date_value=%d&page&_format=csv")


def get(u, t=40):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=t).read().decode("utf-8", "ignore")


def main():
    rows = {}
    ok_years, bad = 0, []
    for y in YEARS:
        try:
            txt = get(URL % (y, y))
        except Exception as e:
            bad.append(y)
            print("[macro] %d 抓取失败：%s" % (y, type(e).__name__))
            continue
        lines = [l for l in txt.strip().split("\n") if l.strip()]
        if len(lines) < 2:
            bad.append(y)
            continue
        head = [h.strip().strip('"') for h in lines[0].split(",")]
        try:
            i_date = head.index("Date")
            i_10 = [i for i, h in enumerate(head) if h.startswith("10 YR")][0]
        except Exception:
            bad.append(y)
            continue
        n = 0
        for l in lines[1:]:
            p = [x.strip().strip('"') for x in l.split(",")]
            if len(p) <= max(i_date, i_10):
                continue
            try:
                m, d, yy = p[i_date].split("/")
                v = float(p[i_10])
            except Exception:
                continue
            rows["%s-%02d-%02d" % (yy, int(m), int(d))] = round(v, 3)
            n += 1
        ok_years += 1
        print("[macro] %d：%d 个交易日" % (y, n))

    if len(rows) < 800:
        print("[macro] 样本过少（%d），放弃写入" % len(rows))
        return

    ds = sorted(rows)
    # 简单校验：实际利率不可能常年超过 6% 或低于 -3%
    bad_v = [d for d in ds if not (-3.0 < rows[d] < 6.0)]
    if bad_v:
        print("[macro] 剔除 %d 个异常值：%s" % (len(bad_v), bad_v[:5]))
        for d in bad_v:
            rows.pop(d)
        ds = sorted(rows)

    # 不允许日期倒退：若新年份抓失败，宁可用旧文件，也不要用一份「停在去年」的数据
    # 覆盖掉本来更新的（否则页面会悄悄显示过期的实际利率，看不出异常）
    try:
        old = json.load(open(OUT, encoding="utf-8"))
        if old.get("d") and old["d"][-1] > ds[-1]:
            print("[macro] 新数据 %s 早于旧文件 %s —— 保留旧文件不覆盖"
                  % (ds[-1], old["d"][-1]))
            return
    except Exception:
        pass

    json.dump({"d": ds, "v": [rows[d] for d in ds]},
              open(OUT, "w", encoding="utf-8"), separators=(",", ":"))
    print("[macro] 共 %d 个交易日，%s → %s，最新 %.2f%%"
          % (len(ds), ds[0], ds[-1], rows[ds[-1]]))
    if bad:
        print("[macro] 缺年份：%s" % bad)


if __name__ == "__main__":
    main()
