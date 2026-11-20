"""问题三建证集的最小性求解与网格复核。
判据：全域每个位置 x 处 L2 可见航点数不小于 2、L3 最大交会角不小于 gamma（默认 30 度）。
方法：贪心建集 + 反向删点 + 全域复核。
输出 output/tables/tab_q3_certset.csv 与 _scratch/certset.json"""
import os
import math
import json
import csv
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
TABDIR = os.path.join(BASE, "output", "tables")
SCRATCH = os.path.join(BASE, "_scratch")
os.makedirs(TABDIR, exist_ok=True)

ARENA, RMIN = 1800.0, 1000.0
GAMMA = 40.0                      # L3 交会角阈值（度）
RING = [(0, 1), (500, 8), (900, 12), (1200, 16), (1500, 20), (1750, 24)]


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def pool():
    P = []
    for r, n in RING:
        for k in range(n):
            a = 2 * math.pi * k / n
            P.append((r * math.cos(a), r * math.sin(a)))
    return P


def matrices(P, X, Y):
    W = np.array(P)
    D = np.sqrt((X[:, None] - W[None, :, 0]) ** 2 + (Y[:, None] - W[None, :, 1]) ** 2)
    A = np.degrees(np.arctan2(Y[:, None] - W[None, :, 1], X[:, None] - W[None, :, 0])) % 360.0
    return D, A


def feasible(D, A, S):
    vis = D[:, S] <= RMIN
    cnt = vis.sum(axis=1)
    if np.any(cnt < 2):
        return False, int(cnt.min()), None
    ang = np.where(vis, A[:, S], np.nan)
    ang.sort(axis=1)
    idx = np.arange(len(cnt))
    first = ang[:, 0]
    last = ang[idx, np.maximum(cnt - 1, 0)]
    d = np.diff(ang, axis=1)
    inner = np.where(np.isnan(d), -1.0, d).max(axis=1)
    wrap = 360.0 - (last - first)
    maxgap = np.maximum(inner, wrap)
    span = 360.0 - maxgap
    return bool(np.all(span >= GAMMA)), int(cnt.min()), float(span.min())


def main():
    print("问题三：极小交会友好航点集搜索", flush=True)
    X, Y = grid(20.0)
    print("  搜索网格：%d 点（步长 20 m）" % len(X), flush=True)
    P = pool()
    D, A = matrices(P, X, Y)
    print("  候选池：%d 个点（%s）" % (len(P), RING), flush=True)
    S = list(range(len(P)))
    ok, mc, ms = feasible(D, A, S)
    print("  初始全集可行=%s（最少可测 %d，最小跨角 %.1f度）" % (ok, mc, ms), flush=True)
    improved = True
    it = 0
    while improved:
        improved = False
        it += 1
        for j in list(S):
            cand = [s for s in S if s != j]
            if len(cand) < 2:
                continue
            ok, mc, ms = feasible(D, A, cand)
            if ok:
                S = cand
                improved = True
        print("  第 %d 轮删点后：%d 个点" % (it, len(S)), flush=True)
        if it > 6:
            break
    ok, mc, ms = feasible(D, A, S)
    print("\n  最终集合：%d 个点；20 m 网格核验 可行=%s，最少可测 %d，最小跨角 %s" %
          (len(S), ok, mc, ("%.1f度" % ms) if ms is not None else "-"), flush=True)
    # 15 m 独立核验（更密，用于暴露 20 m 网格未覆盖到的违例）
    X2, Y2 = grid(15.0)
    D2, A2 = matrices(P, X2, Y2)
    ok2, mc2, ms2 = feasible(D2, A2, S)
    print("  15 m 网格复核 可行=%s，最少可测 %d，最小跨角 %s（网格点 %d）" %
          (ok2, mc2, ("%.1f度" % ms2) if ms2 is not None else "-", len(X2)), flush=True)
    pts = [P[i] for i in S]
    print("\n  航点坐标（按极角排序输出）：")
    for q in sorted(pts, key=lambda p: (round(math.hypot(*p)), math.atan2(p[1], p[0]))):
        print("    (%.0f, %.0f)   r=%.0f" % (q[0], q[1], math.hypot(*q)), flush=True)
    json.dump({"n": len(S), "gamma_deg": GAMMA, "ring": RING,
               "min_visible_20m": mc2, "min_span_deg_20m": ms2,
               "waypoints": [[round(q[0], 1), round(q[1], 1)] for q in pts]},
              open(os.path.join(SCRATCH, "certset.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(TABDIR, "tab_q3_certset.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["项目", "值"])
        w.writerow(["航点数", len(S)])
        w.writerow(["交会角阈值 /度", GAMMA])
        w.writerow(["20 m 网格最少可测点数", mc])
        w.writerow(["15 m 网格最少可测点数", mc2])
        w.writerow(["15 m 网格最小覆盖弧 /度", round(ms2, 1) if ms2 is not None else "L2不合格"])
        w.writerow([])
        w.writerow(["航点坐标 x", "航点坐标 y"])
        for q in pts:
            w.writerow([round(q[0], 1), round(q[1], 1)])
    print("\n  [tab] tab_q3_certset.csv ；_scratch/certset.json", flush=True)


if __name__ == "__main__":
    main()
