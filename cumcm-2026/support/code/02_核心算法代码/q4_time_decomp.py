"""把日志虚拟时间分解为移动、检测、切频、清除四项，并与日志自带的 virtual_time_s 逐局校验。
口径：移动 = 相邻合法动作位置差 / 5 m/s；measure 5 s；切频 1 s；clear 成功 5 s、失败 3 s。"""
import os
import sys
import json
import math

BASE = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(BASE, "_scratch", "archive")
V = 5.0


def decompose(path):
    d = json.load(open(path, encoding="utf-8"))
    log = [e for e in d["log"] if isinstance(e.get("resp"), dict) and e["resp"].get("accepted")]
    pos = (0.0, 0.0)
    last_ch = None
    mv = me = sw = cl = 0.0
    n_meas = n_clear_ok = n_clear_miss = 0
    cleared = set()
    for e in log:
        p = e.get("payload", {})
        q = p.get("position")
        if q:
            mv += math.hypot(q["x"] - pos[0], q["y"] - pos[1]) / V
            pos = (q["x"], q["y"])
        if e["path"] == "/measure":
            me += 5.0
            n_meas += 1
            ch = p.get("channel")
            if last_ch is not None and ch != last_ch:
                sw += 1.0
            last_ch = ch
        elif e["path"] == "/clear":
            if e["resp"].get("clear_result") == "success":
                cl += 5.0
                n_clear_ok += 1
                cleared.add(p.get("channel"))
            else:
                cl += 3.0
                n_clear_miss += 1
    tot = mv + me + sw + cl
    vt = d["virtual_time_s"]
    return {"case": d.get("case"), "file": os.path.basename(path), "n_src": len(cleared),
            "vt": vt, "approx": tot, "mv": mv, "me": me, "sw": sw, "cl": cl,
            "n_meas": n_meas, "n_ok": n_clear_ok, "n_miss": n_clear_miss,
            "n_req": len(log)}


def report(rows):
    print(" %-42s %5s %10s %10s %9s %9s %8s %8s %8s" %
          ("日志", "源数", "虚拟时间", "近似合计", "移动", "检测", "切频", "清除", "请求"))
    for r in rows:
        print(" %-42s %5d %10.1f %10.1f %9.1f %9.1f %8.1f %8.1f %8d" %
              (r["file"][:42], r["n_src"], r["vt"], r["approx"], r["mv"], r["me"],
               r["sw"], r["cl"], r["n_req"]))
    print("\n 占比：")
    print(" %-42s %8s %8s %8s %8s %8s" % ("日志", "移动%", "检测%", "切频%", "清除%", "误差%"))
    for r in rows:
        t = max(r["approx"], 1e-9)
        print(" %-42s %8.1f %8.1f %8.1f %8.1f %8.2f" %
              (r["file"][:42], 100 * r["mv"] / t, 100 * r["me"] / t, 100 * r["sw"] / t,
               100 * r["cl"] / t, 100 * (r["approx"] - r["vt"]) / max(r["vt"], 1e-9)))
    if rows:
        print("\n 平均：移动 %.0f s/局、检测 %.0f s/局、切频 %.0f s/局、清除 %.0f s/局"
              % (sum(r["mv"] for r in rows) / len(rows), sum(r["me"] for r in rows) / len(rows),
                 sum(r["sw"] for r in rows) / len(rows), sum(r["cl"] for r in rows) / len(rows)))


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "p4"
    if arg in ("p3", "p4"):
        files = sorted([os.path.join(ARCH, f) for f in os.listdir(ARCH)
                        if f.endswith("_%s.json" % arg)
                        and (f.startswith("practice_") or f.startswith("baseline_"))])
    else:
        files = [arg]
    rows = [decompose(f) for f in files]
    report(rows)


if __name__ == "__main__":
    main()
