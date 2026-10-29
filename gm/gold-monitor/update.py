#!/usr/bin/env python3
"""一键更新：抓数 → 历史信号 → 磨底雷达 → 双雷达回测 → 升级回测 → 重建页面"""
import os, sys, subprocess, time

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

STEPS = [
    ("抓取行情", "fetch_full.py"),
    ("裁掉未收盘K线", "trim.py"),
    ("抓取小时线", "fetch_intraday.py"),
    ("GLD 持仓", "fetch_gld.py"),
    ("COMEX 基差", "fetch_comex.py"),
    ("1H/4H 雷达", "radar_intra.py"),
    ("计算历史节点", "analyze.py"),
    ("两种背离口径", "divergence2.py"),
    ("合并背离结果", "merge_signals.py"),
    ("磨底雷达", "radar.py"),
    ("逃顶雷达", "radar_top.py"),
    ("高点复盘", "top_review.py"),
    ("均线防守线", "radar_ma.py"),
    ("追踪止损", "radar_stop.py"),
    ("回撤复盘", "trail_review.py"),
    ("三模块复盘", "triple_review.py"),
    ("黄灯轮次统计", "yellow_seq.py"),
    ("双雷达回测", "backtest.py"),
    ("升级版回测", "upgrade_backtest.py"),
    ("波浪结构（仅记录）", "wave/run_daily.py"),
    ("生成页面", "build_page.py"),
    ("信号台账", "ledger.py"),
]

for name, script in STEPS:
    print(f"\n=== {name} ({script}) ===", flush=True)
    t = time.time()
    r = subprocess.run([sys.executable, os.path.join(BASE, script)], cwd=BASE)
    if r.returncode != 0:
        print(f"[失败] {script} 退出码 {r.returncode}")
        sys.exit(r.returncode)
    print(f"[完成] {name} 用时 {time.time()-t:.1f}s")

print("\n全部完成：index.html 已更新。双击打开即可。")
