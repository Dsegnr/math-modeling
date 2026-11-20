"""审计示向度的真实误差：每条观测射线到"清除成功点"（~=真源位置，误差 <=20 m）的垂距。"""
import os
import sys
import json
import math

BASE = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(BASE, "_scratch", "archive")


def audit(path):
    d = json.load(open(path, encoding="utf-8"))
    log = [e for e in d["log"] if e.get("resp", {}).get("accepted")]
    obs, clr = {}, {}
    for e in log:
        p = e["payload"]
        ch = p.get("channel")
        r = e["resp"]
        if e["path"] == "/measure" and r.get("measure_result") == "direction":
            obs.setdefault(ch, []).append(((p["position"]["x"], p["position"]["y"]), r["svd_deg"]))
        if e["path"] == "/clear" and r.get("clear_result") == "success":
            clr[ch] = (p["position"]["x"], p["position"]["y"])
    print("== %s ==" % os.path.basename(path))
    allv = []
    for ch in sorted(clr):
        s = clr[ch]
        ds = []
        for (p, a) in obs.get(ch, []):
            nx, ny = -math.sin(math.radians(a)), math.cos(math.radians(a))
            ds.append(abs((s[0] - p[0]) * nx + (s[1] - p[1]) * ny))
        allv += ds
        print("  ch%-2d 观测%2d 次 | 各观测到清除点的垂距/m: %s"
              % (ch, len(obs.get(ch, [])), ", ".join("%.1f" % v for v in ds)))
    if allv:
        print("  -- 垂距统计：中位 %.2f m，90%% 分位 %.2f m，最大 %.2f m，观测 %d 条"
              % (sorted(allv)[len(allv) // 2], sorted(allv)[int(0.9 * len(allv))], max(allv), len(allv)))


if __name__ == "__main__":
    names = sys.argv[1:] or ["practice_0911_run15_v9_run6_p3.json",
                             "practice_0911_run14_ring15_run6_p3.json",
                             "practice_0911_run13_ring15_run6_p3.json",
                             "practice_0911_run12_ring15_run6_p3.json"]
    for n in names:
        p = n if os.path.isabs(n) else os.path.join(ARCH, n)
        if os.path.exists(p):
            audit(p)