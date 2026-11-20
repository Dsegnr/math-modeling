"""
问题三：航点集的联合优化
目标 J(S) = tour(S) + n_src * mean_x(到最近航点的距离)
约束：L2 全域最少可测点数 >= 2；L3 可见点方位最小覆盖弧 >= GAMMA
做法：多环候选池 -> 贪心删点（在可行前提下最小化 J）-> 全域核验
"""
import os
import math
import json
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
TABDIR = os.path.join(BASE, "output", "tables")
SCRATCH = os.path.join(BASE, "_scratch")
os.makedirs(TABDIR, exist_ok=True)

ARENA, RMIN, GAMMA, NSRC = 1800.0, 1000.0, 40.0, 13
RINGS = [(0, 1), (450, 6), (750, 8), (950, 12), (1150, 14), (1350, 16), (1550, 18), (1750, 20)]


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def pool():
    P = []
    for r, n in RINGS:
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
    maxgap = np.maximum(inner, 360.0 - (last - first))
    span = 360.0 - maxgap
    return bool(np.all(span >= GAMMA)), int(cnt.min()), float(span.min())


def tour_len(P, S):
    pts = [P[i] for i in S]
    rem = list(pts)
    cur = (0.0, 0.0)
    seq = []
    while rem:
        j = min(rem, key=lambda q: math.hypot(q[0] - cur[0], q[1] - cur[1]))
        seq.append(j)
        cur = j
        rem.remove(j)

    def L(sq):
        t = (0.0, 0.0)
        d = 0.0
        for q in sq:
            d += math.hypot(q[0] - t[0], q[1] - t[1])
            t = q
        return d
    best = L(seq)
    improved = True
    while improved:
        improved = False
        for i in range(len(seq) - 1):
            for j in range(i + 1, len(seq)):
                cand = seq[:i] + seq[i:j + 1][::-1] + seq[j + 1:]
                d = L(cand)
                if d < best - 1e-9:
                    seq, best, improved = cand, d, True
    return best


def main():
    print("问题三：航点集联合优化（巡回 + 覆盖半径）", flush=True)
    X, Y = grid(20.0)
    print("  网格 %d 点；候选池 %d 点" % (len(X), len(pool())), flush=True)
    P = pool()
    D, A = matrices(P, X, Y)
    S = list(range(len(P)))
    ok, mc, ms = feasible(D, A, S)
    mn = D[:, S].min(axis=1).mean()
    J = tour_len(P, S) + NSRC * mn
    print("  全集：航点 %d，巡回 %.0f m，平均最近距离 %.0f m，J=%.0f m" % (len(S), tour_len(P, S), mn, J), flush=True)
    rnd = 0
    while True:
        rnd += 1
        best = None
        for j in list(S):
            cand = [s for s in S if s != j]
            if len(cand) < 2:
                continue
            okc, mcc, msc = feasible(D, A, cand)
            if not okc:
                continue
            mnc = D[:, cand].min(axis=1).mean()
            Jc = tour_len(P, cand) + NSRC * mnc
            if best is None or Jc < best[0]:
                best = (Jc, j, mnc, msc)
        if best is None or best[0] >= J - 1e-6:
            break
        J, j, mn, ms = best[0], best[1], best[2], best[3]
        S.remove(j)
        print("  第 %d 轮：删 1 点 -> %d 点，J=%.0f m（平均最近距离 %.0f m，最小跨角 %.1f度）"
              % (rnd, len(S), J, mn, ms), flush=True)
        if rnd > 40:
            break
    ok, mc, ms = feasible(D, A, S)
    t = tour_len(P, S)
    mn = D[:, S].min(axis=1).mean()
    print("\n最终：%d 个航点" % len(S), flush=True)
    print("  巡回 %.0f m；平均最近航点距离 %.0f m；最大覆盖半径 %.1f m" % (t, mn, D[:, S].min(axis=1).max()), flush=True)
    print("  J = %.0f m（联合代价）" % (t + NSRC * mn), flush=True)
    print("  20 m 网格：可行=%s，最少可测 %d，最小覆盖弧 %.1f度" % (ok, mc, ms), flush=True)
    X2, Y2 = grid(15.0)
    D2, A2 = matrices(P, X2, Y2)
    ok2, mc2, ms2 = feasible(D2, A2, S)
    print("  15 m 网格复核：可行=%s，最少可测 %d，最小覆盖弧 %.1f度" % (ok2, mc2, ms2 if ms2 else -1), flush=True)
    pts = [P[i] for i in S]
    json.dump({"n": len(S), "tour_m": t, "mean_nearest_m": mn, "max_cover_r_m": float(D[:, S].min(axis=1).max()),
               "min_visible": mc, "min_span_deg": ms, "feasible_20m": ok, "feasible_15m": ok2,
               "waypoints": [[round(q[0], 1), round(q[1], 1)] for q in pts]},
              open(os.path.join(SCRATCH, "certset2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n  航点坐标：", [(round(q[0]), round(q[1])) for q in pts], flush=True)
    print("  [out] _scratch/certset2.json", flush=True)


if __name__ == "__main__":
    main()