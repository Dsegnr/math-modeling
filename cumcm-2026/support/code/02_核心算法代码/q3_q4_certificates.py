"""
Q3「频道 x 空间」覆盖证书 与 Q4 三级覆盖证书（L1/L2/L3）的精算

Q3：对任一频道，若其检测点集合的 r_min 圆盘覆盖全域，则该频道无未清除源。
    本脚本求覆盖全域所需的**最少航点数**（最小集合覆盖，精确求解）。
Q4：L1(x): Delta_max(x) <= 180度 <=> x in conv(P_x)，P_x = {p_j : ‖p_j-x‖ <= r_min}
    L2(x): |P_x| >= 2；L3(x): 存在可见点对使 |sin∠| >= gamma
输出：output/tables/tab_q3_cover_certificate.csv, tab_q4_L123_certificate.csv
"""
import os
import math
import csv
import itertools
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
TABDIR = os.path.join(BASE, "output", "tables")
os.makedirs(TABDIR, exist_ok=True)

ARENA = 1800.0
RMIN = 1000.0
STEP = 20.0


def layout_center6(r):
    return [(0.0, 0.0)] + [(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k)))
                          for k in range(6)]


def layout_p3():
    pts = [(0.0, 0.0)]
    pts += [(1000 * math.cos(math.radians(60 * k)), 1000 * math.sin(math.radians(60 * k))) for k in range(6)]
    pts += [(1700 * math.cos(math.radians(30 * k)), 1700 * math.sin(math.radians(30 * k))) for k in range(12)]
    return pts


def layout_p4():
    pts = list(layout_p3())
    pts += [(2100 * math.cos(math.radians(20 * k)), 2100 * math.sin(math.radians(20 * k))) for k in range(18)]
    pts += [(2400 * math.cos(math.radians(20 * k + 10)), 2400 * math.sin(math.radians(20 * k + 10))) for k in range(18)]
    uniq = []
    for p in pts:
        if not any(math.hypot(p[0] - q[0], p[1] - q[1]) < 1.0 for q in uniq):
            uniq.append(p)
    return uniq


def arena_grid(step=STEP):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def min_cover_subset(pts, X, Y, rmin=RMIN):
    n = len(pts)
    N = len(X)
    bits = []
    for (px, py) in pts:
        cov = (X - px) ** 2 + (Y - py) ** 2 <= rmin * rmin
        b = 0
        for i in np.nonzero(cov)[0]:
            b |= (1 << int(i))
        bits.append(b)
    full = (1 << N) - 1
    chosen = []
    cur = 0
    while cur != full:
        best, bi = -1, -1
        for j in range(n):
            if j in chosen:
                continue
            gain = bin(bits[j] & ~cur).count("1")
            if gain > best:
                best, bi = gain, j
        if best <= 0:
            return None, bits
        chosen.append(bi)
        cur |= bits[bi]
    greedy = list(chosen)
    for k in range(1, len(greedy)):
        for comb in itertools.combinations(range(n), k):
            acc = 0
            for j in comb:
                acc |= bits[j]
                if acc == full:
                    break
            if acc == full:
                return list(comb), bits
    return greedy, bits


def q3_certificate():
    print("\nQ3：「频道 x 空间」覆盖证书", flush=True)
    X, Y = arena_grid()
    print("  全域网格点数 = %d（步长 %.0f m）" % (len(X), STEP), flush=True)
    rows = []
    for name, pts in (("7点最小布局(中心+1200六边形)", layout_center6(1200.0)),
                      ("19点(Q3采用)", layout_p3()),
                      ("55点(Q4采用)", layout_p4())):
        W = np.array(pts)
        d = np.sqrt((X[:, None] - W[None, :, 0]) ** 2 + (Y[:, None] - W[None, :, 1]) ** 2)
        blind = float(d.min(axis=1).max())
        k2 = int((d <= RMIN).sum(axis=1).min())
        sel, _ = min_cover_subset(pts, X, Y)
        tag = ("%d个" % len(sel)) if sel else "无解"
        print("  %-28s 最大盲区=%6.1f m | 全域可覆盖=%s | 最少可测点数=%d | 覆盖全域最少航点=%s"
              % (name, blind, "是" if blind <= RMIN else "否", k2, tag), flush=True)
        if sel:
            print("     选中: %s" % [(round(pts[j][0]), round(pts[j][1])) for j in sel], flush=True)
        rows.append((name, len(pts), round(blind, 1), "是" if blind <= RMIN else "否", k2,
                     len(sel) if sel else -1,
                     str([(round(pts[j][0]), round(pts[j][1])) for j in sel]) if sel else ""))
    with open(os.path.join(TABDIR, "tab_q3_cover_certificate.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["布局", "航点数", "全域最大盲区/m", "满足全域半径覆盖", "全域最少可测点数",
                    "覆盖全域所需最少航点数", "选中的航点"])
        for r in rows:
            w.writerow(list(r))
    print("  [tab] tab_q3_cover_certificate.csv", flush=True)


def in_convex_hull(x, pts):
    P = [(p[0] - x[0], p[1] - x[1]) for p in pts]
    P.sort(key=lambda v: math.atan2(v[1], v[0]))
    bad = 0
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        if a[0] * b[1] - a[1] * b[0] < -1e-9:
            bad += 1
    return bad == 0


def q4_certificate():
    print("\nQ4：L1/L2/L3 全域证书", flush=True)
    X, Y = arena_grid()
    rows = []
    for name, pts in (("7点(中心+1200六边形)", layout_center6(1200.0)),
                      ("19点", layout_p3()),
                      ("55点(Q4采用)", layout_p4())):
        W = np.array(pts)
        d = np.sqrt((X[:, None] - W[None, :, 0]) ** 2 + (Y[:, None] - W[None, :, 1]) ** 2)
        kmin = int((d <= RMIN).sum(axis=1).min())
        worst_gap = 0.0
        worst_xy = None
        n1 = n2 = 0
        worst_sin = 1.0
        worst_sin_xy = None
        mismatch = 0
        for i in range(len(X)):
            x = (float(X[i]), float(Y[i]))
            vis = [j for j in range(len(W)) if d[i, j] <= RMIN]
            if len(vis) < 2:
                n2 += 1
                continue
            rel = [(W[j][0] - x[0], W[j][1] - x[1]) for j in vis]
            ang = sorted(math.atan2(v[1], v[0]) for v in rel)
            gaps = [ang[t + 1] - ang[t] for t in range(len(ang) - 1)] + [2 * math.pi - (ang[-1] - ang[0])]
            gmax = math.degrees(max(gaps))
            if gmax > worst_gap:
                worst_gap, worst_xy = gmax, x
            if gmax > 180.0 + 1e-9:
                n1 += 1
            best = 0.0
            for a in range(len(vis)):
                for b in range(a + 1, len(vis)):
                    u, v = rel[a], rel[b]
                    cc = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
                    best = max(best, abs(math.sin(math.acos(max(-1.0, min(1.0, cc))))))
            if best < worst_sin:
                worst_sin, worst_sin_xy = best, x
            if in_convex_hull(x, [W[j] for j in vis]) != (gmax <= 180.0 + 1e-9):
                mismatch += 1
        print("  %-22s 最少可测=%d | 最坏角隙=%6.1f度@%s | L1失败=%d | L2失败=%d | 最坏可测对交会角=%.1f度@%s | 凸包判据不一致=%d"
              % (name, kmin, worst_gap, (round(worst_xy[0]), round(worst_xy[1])) if worst_xy else "-",
                 n1, n2, math.degrees(math.asin(min(1.0, worst_sin))),
                 (round(worst_sin_xy[0]), round(worst_sin_xy[1])) if worst_sin_xy else "-", mismatch),
              flush=True)
        rows.append((name, len(pts), kmin, round(worst_gap, 1), n1, n2,
                     round(math.degrees(math.asin(min(1.0, worst_sin))), 1), mismatch))
    with open(os.path.join(TABDIR, "tab_q4_L123_certificate.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["布局", "航点数", "全域最少可测点数(L2)", "全域最坏角隙/度(L1)",
                    "L1失败网格点", "L2失败网格点", "全网最坏可测对交会角/度(L3)", "L1与凸包判据不一致点"])
        for r in rows:
            w.writerow(list(r))
    print("  [tab] tab_q4_L123_certificate.csv", flush=True)
    print("  说明：L1 等价重述为 x in conv(P_x)；不一致点数=0 表示两种判据在网格上完全一致。", flush=True)


if __name__ == "__main__":
    q3_certificate()
    q4_certificate()
    print("\n[done]", flush=True)