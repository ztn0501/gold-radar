#!/usr/bin/env python3
"""把两种背离口径并入 signals.json"""
import json, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sig=json.load(open("signals.json",encoding="utf-8"))
dv=json.load(open("divergence2.json",encoding="utf-8"))
m={x["date"]:x for x in dv}
for s in sig:
    x=m.get(s["date"])
    if not x: continue
    s["div_area"]=x.get("area"); s["div_swing"]=x.get("swing"); s["confirmed"]=x.get("confirmed")
json.dump(sig,open("signals.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("[merge] ok", len(sig))
