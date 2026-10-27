#!/usr/bin/env python3
"""GLD 持仓（SPDR 官方 Excel）—— 只做展示，不参与任何交易判定。
数据源：api.spdrgoldshares.com 历史档案（xlsx），失败时静默跳过。
输出：gld_holdings.json
"""
import json, os, re, urllib.request, zipfile, io, datetime as dt
from xml.etree import ElementTree as ET

URL = "https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def parse(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(NS + "si"):
            ss.append("".join(t.text or "" for t in si.iter(NS + "t")))
    # sheet2 = "US GLD Historical Archive"
    name = "xl/worksheets/sheet2.xml"
    if name not in z.namelist():
        cands = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")]
        name = sorted(cands)[-1]
    root = ET.fromstring(z.read(name))
    hist = []
    for row in root.iter(NS + "row"):
        cells = {}
        for c in row.findall(NS + "c"):
            m = re.match(r"([A-Z]+)", c.get("r") or "")
            if not m:
                continue
            v = c.find(NS + "v")
            if v is None:
                continue
            val = v.text or ""
            if c.get("t") == "s":
                try:
                    val = ss[int(val)]
                except Exception:
                    pass
            cells[m.group(1)] = val
        d, j = cells.get("A"), cells.get("J")
        if not d or not j:
            continue
        try:
            day = dt.datetime.strptime(d.strip(), "%d-%b-%Y").date().isoformat()
            tonnes = float(j)
        except Exception:
            continue
        hist.append([day, round(tonnes, 2)])
    hist.sort()
    return hist


def main():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=90).read()
        hist = parse(raw)
        if not hist:
            raise ValueError("无有效数据")
        tail = hist[-260:]
        cur = tail[-1][1]
        out = {
            "date": tail[-1][0],
            "tonnes": cur,
            "chg20": round(cur - tail[-21][1], 2) if len(tail) > 21 else None,
            "pct20": round((cur / tail[-21][1] - 1) * 100, 2) if len(tail) > 21 else None,
            "chg60": round(cur - tail[-61][1], 2) if len(tail) > 61 else None,
            "pct60": round((cur / tail[-61][1] - 1) * 100, 2) if len(tail) > 61 else None,
            "chg250": round(cur - tail[-251][1], 2) if len(tail) > 251 else None,
            "pct250": round((cur / tail[-251][1] - 1) * 100, 2) if len(tail) > 251 else None,
            "hi250": max(x[1] for x in tail),
            "lo250": min(x[1] for x in tail),
            "hist": tail,
        }
        json.dump(out, open("gld_holdings.json", "w", encoding="utf-8"), ensure_ascii=False)
        print(f"[gld] {out['date']} 持仓 {cur} 吨｜20日 {out['pct20']}%｜60日 {out['pct60']}%")
    except Exception as e:
        print("[gld] 跳过（不影响主流程）：", e)


if __name__ == "__main__":
    main()
