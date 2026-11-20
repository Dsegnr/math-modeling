"""问题一、问题二的数值实验与绘图脚本。
产出 figures/fig_q1_*.png|pdf、figures/fig_q2_*.png|pdf 与 output/tables/tab_q*.csv。
用法：python q1_q2_analysis.py"""
import os
import json
import math
import csv
import random
import itertools
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(BASE, "figures")
TABDIR = os.path.join(BASE, "output", "tables")
SCRATCH = os.path.join(BASE, "_scratch")
for _d in (FIGDIR, TABDIR, SCRATCH):
    os.makedirs(_d, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(SCRATCH, "mplconfig"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle as MplCircle
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.lines import Line2D

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["figure.dpi"] = 110
plt.rcParams["font.size"] = 10
plt.rcParams["axes.titlesize"] = 11.5
plt.rcParams["axes.labelsize"] = 10.5
plt.rcParams["legend.fontsize"] = 9

EPS = 1.0
ARENA = 1800.0
RMAX = 1500.0
RMIN = 1000.0
JUNG = 2.0 / math.sqrt(3.0)

C_A = "#1f4e79"
C_B = "#c0504d"
C_C = "#4f81bd"
C_D = "#9bbb59"
C_E = "#f79646"
RES = {}


def save_fig(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIGDIR, "%s.%s" % (name, ext)), bbox_inches="tight")
    plt.close(fig)
    print("  [fig] %s.png / .pdf" % name, flush=True)


def clip_hp(poly, n, c):
    out = []
    m = len(poly)
    for i in range(m):
        A = poly[i]
        B = poly[(i + 1) % m]
        da = n[0] * A[0] + n[1] * A[1] - c
        db = n[0] * B[0] + n[1] * B[1] - c
        if da <= 1e-12:
            out.append(A)
        if (da < -1e-12 < db) or (db < -1e-12 < da):
            t = da / (da - db)
            out.append((A[0] + t * (B[0] - A[0]), A[1] + t * (B[1] - A[1])))
    if not out:
        return []
    res = [out[0]]
    for p in out[1:]:
        if abs(p[0] - res[-1][0]) > 1e-9 or abs(p[1] - res[-1][1]) > 1e-9:
            res.append(p)
    if len(res) > 1 and abs(res[0][0] - res[-1][0]) < 1e-9 and abs(res[0][1] - res[-1][1]) < 1e-9:
        res.pop()
    return res


def disk_hps(R, nc=180):
    return [((math.cos(2 * math.pi * k / nc), math.sin(2 * math.pi * k / nc)), R) for k in range(nc)]


def wedge_hps(S, th, eps=EPS):
    t = math.radians(th)
    u1 = (math.cos(t - math.radians(eps)), math.sin(t - math.radians(eps)))
    u2 = (math.cos(t + math.radians(eps)), math.sin(t + math.radians(eps)))
    nA = (u1[1], -u1[0])
    nB = (-u2[1], u2[0])
    return [(nA, nA[0] * S[0] + nA[1] * S[1]), (nB, nB[0] * S[0] + nB[1] * S[1])]


_DISK_CACHE = {}


def disk_cache(R, nc):
    key = (R, nc)
    if key not in _DISK_CACHE:
        _DISK_CACHE[key] = disk_hps(R, nc)
    return _DISK_CACHE[key]


def region(obs, nc=180, cap=True, arena=True):
    """楔形优先裁剪（4 顶点起步），再依次加 d<=RMAX 圆盘、目标圆域"""
    poly = [(-30000.0, -30000.0), (30000.0, -30000.0), (30000.0, 30000.0), (-30000.0, 30000.0)]
    for (S, th) in obs:
        for (n, c) in wedge_hps(S, th):
            poly = clip_hp(poly, n, c)
            if not poly:
                return None
    if cap:
        for (n, c) in disk_cache(RMAX, nc):
            poly = clip_hp(poly, n, c)
            if not poly:
                return None
    if arena:
        for (n, c) in disk_cache(ARENA, nc):
            poly = clip_hp(poly, n, c)
            if not poly:
                return None
    return poly if len(poly) >= 3 else None


def hull(P):
    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    pts = sorted(set((round(p[0], 9), round(p[1], 9)) for p in P))
    if len(pts) < 3:
        return [tuple(p) for p in pts]
    lo = []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return [tuple(p) for p in (lo[:-1] + up[:-1])]


def diameter_bruteforce(P):
    P = np.asarray(P, float)
    best = 0.0
    pair = (0, 0)
    for i in range(len(P)):
        d = np.hypot(P[i, 0] - P[:, 0], P[i, 1] - P[:, 1])
        j = int(d.argmax())
        if d[j] > best:
            best = float(d[j])
            pair = (i, j)
    return best, pair


def diameter_calipers(H):
    n = len(H)
    if n < 2:
        return 0.0
    k = 1
    best = 0.0
    for i in range(n):
        j = (i + 1) % n
        while True:
            nk = (k + 1) % n
            ex, ey = H[j][0] - H[i][0], H[j][1] - H[i][1]
            ax, ay = H[k][0] - H[i][0], H[k][1] - H[i][1]
            bx, by = H[nk][0] - H[i][0], H[nk][1] - H[i][1]
            if abs(ex * by - ey * bx) > abs(ex * ay - ey * ax):
                k = nk
            else:
                break
        best = max(best, math.hypot(H[i][0] - H[k][0], H[i][1] - H[k][1]))
        best = max(best, math.hypot(H[j][0] - H[k][0], H[j][1] - H[k][1]))
    return best


def _c2(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0), math.hypot(a[0] - b[0], a[1] - b[1]) / 2.0


def _c3(a, b, c):
    ax, ay = a
    bx, by = b
    cx, cy = c
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-14:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy), math.hypot(ux - ax, uy - ay)


def _welzl(P, R, n):
    if n == 0 or len(R) == 3:
        if len(R) == 0:
            return ((0.0, 0.0), 0.0)
        if len(R) == 1:
            return (R[0], 0.0)
        if len(R) == 2:
            return _c2(R[0], R[1])
        cc = _c3(R[0], R[1], R[2])
        return cc if cc else _c2(R[0], R[1])
    p = P[n - 1]
    cc = _welzl(P, R, n - 1)
    if math.hypot(p[0] - cc[0][0], p[1] - cc[0][1]) <= cc[1] + 1e-9:
        return cc
    return _welzl(P, R + [p], n - 1)


def mec(P, rng=None):
    lst = [(float(p[0]), float(p[1])) for p in P]
    (rng or random).shuffle(lst)
    return _welzl(lst, [], len(lst))


def mec_bruteforce(P):
    P = [(float(p[0]), float(p[1])) for p in P]
    n = len(P)
    best = None
    cands = []
    for i in range(n):
        for j in range(i + 1, n):
            cands.append(_c2(P[i], P[j]))
    for i, j, k in itertools.combinations(range(n), 3):
        cc = _c3(P[i], P[j], P[k])
        if cc:
            cands.append(cc)
    for (ctr, r) in cands:
        if all(math.hypot(p[0] - ctr[0], p[1] - ctr[1]) <= r + 1e-9 for p in P):
            if best is None or r < best[1]:
                best = (ctr, r)
    return best if best else ((0.0, 0.0), 0.0)


def bearing(A, B):
    return math.degrees(math.atan2(B[1] - A[1], B[0] - A[0])) % 360.0


def wilson(k, n, z=1.96):
    p = k / n
    ctr = (p + z * z / (2 * n)) / (1 + z * z / n)
    hw = z / (1 + z * z / n) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ctr - hw, ctr + hw


def ratio_of_region(poly):
    H = hull(poly)
    if len(H) < 3:
        return None
    D, _ = diameter_bruteforce(H)
    if D < 1e-9:
        return None
    ctr, rho = mec_bruteforce(H)
    return D, rho, rho / (D / 2.0), H, ctr


def q1():
    print("\n问题一", flush=True)
    rng = random.Random(20260911)
    maxdev = 0.0
    for _ in range(400):
        G = (rng.uniform(-1200, 1200), rng.uniform(-1200, 1200))
        obs = []
        for _k in range(rng.randint(2, 4)):
            a = rng.uniform(0, 360)
            d = rng.uniform(200, 1500)
            S = (G[0] + d * math.cos(math.radians(a)), G[1] + d * math.sin(math.radians(a)))
            obs.append((S, bearing(S, G)))
        poly = region(obs, cap=False, arena=False)
        if not poly:
            continue
        H = hull(poly)
        Db, _ = diameter_bruteforce(H)
        Dc = diameter_calipers(H)
        maxdev = max(maxdev, abs(Db - Dc))
    print("  [算法校验] 旋转卡壳 vs 暴力枚举 最大偏差 = %.3e m" % maxdev, flush=True)
    RES["q1_calipers_max_dev"] = maxdev
    RES["q1_disk_dev_N180"] = RMAX * (1 - math.cos(math.pi / 180))
    RES["q1_disk_dev_N720"] = RMAX * (1 - math.cos(math.pi / 720))
    print("  [精度] 圆盘 N 边形径向偏差：N=180 -> %.4f m, N=720 -> %.4f m"
          % (RES["q1_disk_dev_N180"], RES["q1_disk_dev_N720"]), flush=True)

    ratios, diams = [], []
    ntries = 0
    while len(ratios) < 2000 and ntries < 80000:
        ntries += 1
        G = (rng.uniform(-1400, 1400), rng.uniform(-1400, 1400))
        if math.hypot(*G) > 1700:
            continue
        a1 = rng.uniform(0, 360)
        d1 = rng.uniform(400, 1500)
        S1 = (G[0] + d1 * math.cos(math.radians(a1)), G[1] + d1 * math.sin(math.radians(a1)))
        a2 = a1 + rng.uniform(20, 160)
        d2 = rng.uniform(250, 800)
        S2 = (G[0] + d2 * math.cos(math.radians(a2)), G[1] + d2 * math.sin(math.radians(a2)))
        poly = region([(S1, bearing(S1, G)), (S2, bearing(S2, G))], cap=False, arena=False)
        if not poly:
            continue
        out = ratio_of_region(poly)
        if not out:
            continue
        ratios.append(out[2])
        diams.append(out[0])
    R = np.array(ratios)
    Darr = np.array(diams)
    strict = R > 1.0 + 1e-9
    k = int(strict.sum())
    lo, hi = wilson(k, len(R))
    print("  [采样 n=%d] D 中位数 %.2f m | ratio 中位 %.6f 最大 %.6f"
          % (len(R), np.median(Darr), np.median(R), R.max()), flush=True)
    print("  [采样 n=%d] P(rho>D/2) = %.2f%%  Wilson 95%% CI [%.2f%%, %.2f%%]"
          % (len(R), 100 * k / len(R), 100 * lo, 100 * hi), flush=True)
    RES["q1_mc_n"] = len(R)
    RES["q1_mc_D_median"] = float(np.median(Darr))
    RES["q1_mc_ratio_max"] = float(R.max())
    RES["q1_mc_frac_gt"] = k / len(R)
    RES["q1_mc_wilson"] = [lo, hi]

    sweep = {}
    for m, ntry in ((2, 200000), (3, 60000), (4, 60000), (5, 60000), (6, 60000)):
        best = 0.0
        for _ in range(ntry):
            G = (rng.uniform(-1200, 1200), rng.uniform(-1200, 1200))
            obs = []
            for _k in range(m):
                a = rng.uniform(0, 360)
                d = rng.uniform(60, 1500)
                S = (G[0] + d * math.cos(math.radians(a)), G[1] + d * math.sin(math.radians(a)))
                obs.append((S, bearing(S, G)))
            poly = region(obs, cap=False, arena=False)
            if not poly:
                continue
            H = hull(poly)
            if len(H) < 3:
                continue
            D, _ = diameter_bruteforce(H)
            if D < 1e-9:
                continue
            _, rho = mec(H, rng)
            best = max(best, rho / (D / 2.0))
        sweep[m] = best
        print("  [极值搜索] m=%d 点（%d 例）: max ratio = %.6f" % (m, ntry, best), flush=True)
    RES["q1_sweep"] = sweep

    best_combo = None
    best_val = 0.0
    for combo in itertools.product((-1.0, 1.0), repeat=3):
        obs = []
        for kk in range(3):
            a = math.radians(120.0 * kk)
            S = (1000.0 * math.cos(a), 1000.0 * math.sin(a))
            th = (math.degrees(math.atan2(-S[1], -S[0])) + combo[kk] * 0.95) % 360.0
            obs.append((S, th))
        pl = region(obs, cap=False)
        out = ratio_of_region(pl) if pl else None
        if out and out[2] > best_val:
            best_val = out[2]
            best_combo = combo
    print("  [反例族] 最坏符号组合 %s -> ratio = %.6f (2/sqrt3=%.6f)"
          % (str(best_combo), best_val, JUNG), flush=True)
    fam = []
    for delta in np.arange(0.0, 0.9501, 0.05):
        obs = []
        for kk in range(3):
            a = math.radians(120.0 * kk)
            S = (1000.0 * math.cos(a), 1000.0 * math.sin(a))
            th = (math.degrees(math.atan2(-S[1], -S[0])) + best_combo[kk] * delta) % 360.0
            obs.append((S, th))
        pl = region(obs, cap=False)
        out = ratio_of_region(pl) if pl else None
        if out is None:
            print("    [warn] delta=%.2f 区域为空，跳过" % delta, flush=True)
        fam.append((float(delta), float(out[2]) if out else float("nan")))
    RES["q1_family"] = fam
    RES["q1_family_max"] = best_val
    RES["q1_best_combo"] = list(best_combo)
    return R, Darr, k, lo, hi, sweep, best_val, best_combo, fam


def q1_figs(R, Darr, k, lo, hi, sweep, best_val, best_combo, fam):
    t = np.linspace(0, 2 * math.pi, 400)
    Gc = (0.0, 0.0)
    angs = [95.0, 215.0, 335.0]
    dists = [900.0, 1000.0, 1100.0]
    obs = []
    for a, d in zip(angs, dists):
        S = (Gc[0] + d * math.cos(math.radians(a)), Gc[1] + d * math.sin(math.radians(a)))
        obs.append((S, bearing(S, Gc)))
    D, rho, rt, H, ctr = ratio_of_region(region(obs, cap=False))
    Hn = np.array(H)
    pair = None
    for i in range(len(H)):
        for j in range(i + 1, len(H)):
            dd = math.hypot(H[i][0] - H[j][0], H[i][1] - H[j][1])
            if pair is None or dd > pair[0]:
                pair = (dd, i, j)
    pa, pb = H[pair[1]], H[pair[2]]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0))
    ax = axes[0]
    for (S, th) in obs:
        for sgn in (-1, 1):
            a = math.radians(th + sgn * EPS)
            ax.plot([S[0], S[0] + 2600 * math.cos(a)], [S[1], S[1] + 2600 * math.sin(a)],
                    "--", color="0.6", lw=0.9, zorder=1)
        a = math.radians(th)
        ax.plot([S[0], S[0] + 2600 * math.cos(a)], [S[1], S[1] + 2600 * math.sin(a)],
                "-", color=C_A, lw=1.5, zorder=2)
        ax.plot([S[0]], [S[1]], "s", color=C_B, ms=6, zorder=4)
    ax.add_patch(MplPolygon(H, closed=True, facecolor=C_C, edgecolor=C_A, alpha=0.45, lw=1.4, zorder=3))
    ax.add_patch(MplCircle(ctr, rho, facecolor="none", edgecolor=C_E, lw=1.8, ls="-.", zorder=5))
    ax.plot([pa[0], pb[0]], [pa[1], pb[1]], "-", color=C_B, lw=2.0, zorder=6)
    ax.add_patch(MplCircle((0.0, 0.0), ARENA, fill=False, ec="0.45", ls=":", lw=1.2, zorder=0))
    ax.text(-ARENA * 0.92, ARENA * 0.60, "目标圆域 $R=1800$ m", fontsize=9, color="0.35",
            bbox=dict(fc="white", ec="0.75", alpha=0.92, pad=2.0))
    ax.set_xlim(-1950, 1950)
    ax.set_ylim(-1950, 1950)
    ax.set_aspect("equal")
    ax.set_title("(a) 三点交会：区域 $\\Omega$、直径 $D$、最小外接圆 $\\rho_{\\min}$")
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.grid(alpha=0.25)
    ax = axes[1]
    ax.add_patch(MplPolygon(H, closed=True, facecolor=C_C, edgecolor=C_A, alpha=0.45, lw=1.4))
    ax.plot((pa[0] + pb[0]) / 2 + (D / 2) * np.cos(t), (pa[1] + pb[1]) / 2 + (D / 2) * np.sin(t),
            "-", color=C_B, lw=3.2, alpha=0.85, label="以 $D$ 为直径的圆")
    ax.plot(ctr[0] + rho * np.cos(t), ctr[1] + rho * np.sin(t), "-.", color=C_E, lw=1.6,
            label="最小外接圆 $\\rho_{\\min}$")
    ax.plot([pa[0], pb[0]], [pa[1], pb[1]], "-", color="k", lw=1.6)
    ax.plot([pa[0], pb[0]], [pa[1], pb[1]], "o", color="k", ms=5)
    for p in H:
        v1 = (p[0] - pa[0], p[1] - pa[1])
        v2 = (p[0] - pb[0], p[1] - pb[1])
        if v1[0] * v2[0] + v1[1] * v2[1] <= 0:
            ax.plot([p[0]], [p[1]], "o", color=C_D, ms=7, zorder=7)
    cx, cy = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
    half = (D / 2) * 1.55
    ax.set_xlim(cx - half, cx + half)
    ax.set_ylim(cy - half, cy + half)
    ax.set_aspect("equal")
    ax.set_title("(b) Thales 判据：全部顶点满足 $(X-A)\\cdot(X-B)\\leq 0$")
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.legend(loc="upper right", framealpha=0.92)
    ax.grid(alpha=0.25)
    fig.suptitle("图 1  问题一：交会定位区域的直径与直径圆覆盖判据", y=1.02, fontsize=12.5)
    save_fig(fig, "fig_q1_geometry")

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.2))
    S1 = (-900.0, -200.0)
    S2 = (900.0, -150.0)
    cases = [("(a) 可覆盖：$\\rho_{\\min}=D/2$，比值 $=1$",
              [(S1, bearing(S1, Gc)), (S2, bearing(S2, Gc))])]
    obs3 = []
    for kk in range(3):
        a = math.radians(120.0 * kk)
        S = (1000.0 * math.cos(a), 1000.0 * math.sin(a))
        th = (math.degrees(math.atan2(-S[1], -S[0])) + best_combo[kk] * 0.95) % 360.0
        obs3.append((S, th))
    cases.append(("(b) 不可覆盖：比值 $=%.4f>1$" % best_val, obs3))
    for ax, (title, o) in zip(axes, cases):
        D, rho, rt, H, ctr = ratio_of_region(region(o, cap=False))
        for (S, th) in o:
            for sgn in (-1, 1):
                a = math.radians(th + sgn * EPS)
                ax.plot([S[0], S[0] + 3000 * math.cos(a)], [S[1], S[1] + 3000 * math.sin(a)],
                        "--", color="0.62", lw=0.8)
            ax.plot([S[0]], [S[1]], "s", color=C_B, ms=6)
        ax.add_patch(MplPolygon(H, closed=True, facecolor=C_C, edgecolor=C_A, alpha=0.5, lw=1.3))
        p2 = None
        for i in range(len(H)):
            for j in range(i + 1, len(H)):
                dd = math.hypot(H[i][0] - H[j][0], H[i][1] - H[j][1])
                if p2 is None or dd > p2[0]:
                    p2 = (dd, i, j)
        pa, pb = H[p2[1]], H[p2[2]]
        ax.plot((pa[0] + pb[0]) / 2 + (D / 2) * np.cos(t), (pa[1] + pb[1]) / 2 + (D / 2) * np.sin(t),
                "-", color=C_B, lw=3.2, alpha=0.85, label="以 $D$ 为直径的圆")
        ax.plot(ctr[0] + rho * np.cos(t), ctr[1] + rho * np.sin(t), "-.", color=C_E, lw=1.6,
                label="最小外接圆 $\\rho_{\\min}$")
        if rt > 1 + 1e-9:
            out = [p for p in H if math.hypot(p[0] - (pa[0] + pb[0]) / 2, p[1] - (pa[1] + pb[1]) / 2) > D / 2 + 1e-6]
            if out:
                ax.plot([out[0][0]], [out[0][1]], "*", color="red", ms=11, zorder=8, label="漏出直径圆的顶点")
        cx, cy = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        half = (D / 2) * 1.5
        ax.set_xlim(cx - half, cx + half)
        ax.set_ylim(cy - half, cy + half)
        ax.set_aspect("equal")
        ax.set_title(title)
        ax.set_xlabel("$x$ / m")
        ax.set_ylabel("$y$ / m")
        ax.legend(loc="upper right", framealpha=0.92)
        ax.grid(alpha=0.25)
        if rt <= 1 + 1e-9:
            ax.text(0.03, 0.05, "两圆完全重合：$\\rho_{\\min}=D/2$", transform=ax.transAxes,
                    fontsize=9.5, bbox=dict(fc="white", ec="0.7", alpha=0.92))
    fig.suptitle("图 2  问题一：以定位区域直径为直径的圆能否覆盖该区域", y=1.02, fontsize=12.5)
    save_fig(fig, "fig_q1_cover_compare")

    k_loose = int((R > 1.0).sum())
    RES["q1_mc_frac_gt_loose"] = k_loose / len(R)
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.6))
    ax = axes[0]
    labels = ["严格判据\n$\\rho>D/2+10^{-9}$", "含浮点平局\n$\\rho>D/2$"]
    vals = [100.0 * k / len(R), 100.0 * k_loose / len(R)]
    bars = ax.bar(labels, vals, color=[C_B, C_C], width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.6, "%.2f%%" % v, ha="center", fontsize=10)
    ax.set_ylabel("不满足覆盖的比例 / %")
    ax.set_ylim(0, max(vals) * 1.35)
    ax.set_title("(a) 判据口径敏感性：浮点平局会虚增比例")
    ax.grid(alpha=0.25, axis="y")
    ax = axes[1]
    ts = np.linspace(1.0, 1.16, 800)
    ccdf = np.array([100.0 * float((R > t).mean()) for t in ts])
    ax.semilogy(ts, np.maximum(ccdf, 0.03), "-", color=C_A, lw=2.0,
                label="经验互补分布 $P(\\rho_{\\min}/(D/2)>t)$")
    ax.axvline(1.0, color=C_B, lw=1.4, ls="--", label="$\\rho_{\\min}=D/2$")
    ax.axvline(JUNG, color=C_E, lw=1.5, ls="-.", label="Jung 上界 $2/\\sqrt{3}=%.4f$" % JUNG)
    ax.plot([1.0], [100.0 * k / len(R)], "o", color=C_B, ms=8, zorder=6,
            label="不满足覆盖 $%.2f$%%" % (100.0 * k / len(R)))
    ax.set_xlabel("$t=\\rho_{\\min}/(D/2)$")
    ax.set_ylabel("$P(\\rho_{\\min}/(D/2)>t)$ / %")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: "%g" % v))
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_title("(b) 尾部互补分布（对数纵轴）")
    ax.legend(loc="upper right", framealpha=0.92)
    ax.grid(alpha=0.25, which="both")
    fig.suptitle("图 3  问题一：直径圆覆盖判据的经验证据（两点交会，$n=%d$）" % len(R), y=1.02, fontsize=12.5)
    save_fig(fig, "fig_q1_ratio_hist")

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.plot([f[0] for f in fam], [f[1] for f in fam], "-o", color=C_A, lw=1.8, ms=4,
            label="三点近正三角形，示向度偏移 $\\delta$")
    ax.axhline(JUNG, color=C_E, lw=1.5, ls="-.", label="Jung 上界 $2/\\sqrt{3}$")
    ax.axhline(1.0, color=C_B, lw=1.3, ls="--", label="$\\rho_{\\min}=D/2$")
    ax.set_xlabel("示向度向楔形边界偏移量 $\\delta$ / (度)")
    ax.set_ylabel("$\\rho_{\\min}/(D/2)$")
    ax.set_title("图 4  问题一：反例族--比值随偏移逼近 Jung 上界")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.25)
    save_fig(fig, "fig_q1_counterexample")

    with open(os.path.join(TABDIR, "tab_q1_cover_stats.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["指标", "数值", "说明"])
        w.writerow(["采样例数", len(R), "两点交会，源位|G|<=1700均匀"])
        w.writerow(["D 中位数 /m", "%.2f" % np.median(Darr), "定位区域直径"])
        w.writerow(["rho/(D/2) 中位数", "%.6f" % np.median(R), ""])
        w.writerow(["rho/(D/2) 最大值", "%.6f" % R.max(), "实测"])
        w.writerow(["不满足覆盖比例", "%.2f%%" % (100 * k / len(R)), "阈值 1+1e-9"])
        w.writerow(["不满足覆盖比例(含浮点平局)", "%.2f%%" % (100 * k_loose / len(R)), "阈值 1，口径敏感性对照"])
        w.writerow(["Wilson 95% CI", "[%.2f%%, %.2f%%]" % (100 * lo, 100 * hi), ""])
        for m in sorted(sweep):
            w.writerow(["极值搜索 m=%d 点" % m, "%.6f" % sweep[m], "随机极值上界"])
        w.writerow(["最坏构型（三点偏移）", "%.6f" % best_val, "反例族"])
        w.writerow(["Jung 上界 2/sqrt3", "%.6f" % JUNG, ""])
        w.writerow(["旋转卡壳 vs 暴力 最大偏差 /m", "%.3e" % RES["q1_calipers_max_dev"], ""])
    print("  [tab] tab_q1_cover_stats.csv", flush=True)


def q2():
    print("\n问题二", flush=True)
    rng = random.Random(20260912)
    G = (0.0, 1200.0)
    S1 = (0.0, 0.0)
    th1 = bearing(S1, G)
    d1 = math.hypot(G[0] - S1[0], G[1] - S1[1])

    def exact_D(S2, nc=360):
        d2 = math.hypot(S2[0] - G[0], S2[1] - G[1])
        if d2 <= 5.0:
            return None
        poly = region([(S1, th1), (S2, bearing(S2, G))], nc=nc, cap=True)
        if not poly:
            return None
        H = hull(poly)
        if len(H) < 3:
            return None
        return diameter_bruteforce(H)[0]

    def analytic_D(S2):
        d2 = math.hypot(S2[0] - G[0], S2[1] - G[1])
        v1 = (S1[0] - G[0], S1[1] - G[1])
        v2 = (S2[0] - G[0], S2[1] - G[1])
        cc = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
        s = abs(math.sin(math.acos(max(-1.0, min(1.0, cc)))))
        if s < 1e-6:
            return float("inf")
        return 2 * math.tan(math.radians(EPS)) * math.sqrt(d1 * d1 + d2 * d2) / s

    poly1 = region([(S1, th1)], nc=360, cap=True)
    D1 = diameter_bruteforce(hull(poly1))[0]
    cand = []
    for l in np.arange(25, 1801, 5.0):
        for b in np.arange(-180, 180, 1.0):
            S2 = (l * math.cos(math.radians(b)), l * math.sin(math.radians(b)))
            if math.hypot(*S2) > ARENA:
                continue
            if math.hypot(S2[0] - G[0], S2[1] - G[1]) <= 5.0:
                continue
            cand.append((analytic_D(S2), l, b, S2))
    cand.sort(key=lambda r: r[0])
    rows = []
    for (av, l, b, S2) in cand[:400]:
        D = exact_D(S2, nc=180)
        if D is None:
            continue
        d2 = math.hypot(S2[0] - G[0], S2[1] - G[1])
        v1 = (S1[0] - G[0], S1[1] - G[1])
        v2 = (S2[0] - G[0], S2[1] - G[1])
        cc = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
        psi = math.degrees(math.acos(max(-1.0, min(1.0, cc))))
        rows.append((D, l, b, d2, psi, S2))
    rows.sort(key=lambda r: r[0])
    l0, b0 = rows[0][1], rows[0][2]
    for b in np.arange(b0 - 6.0, b0 + 6.01, 0.5):
        for l in np.arange(max(25.0, l0 - 60.0), l0 + 60.01, 2.0):
            S2 = (l * math.cos(math.radians(b)), l * math.sin(math.radians(b)))
            if math.hypot(*S2) > ARENA:
                continue
            if math.hypot(S2[0] - G[0], S2[1] - G[1]) <= 5.0:
                continue
            D = exact_D(S2, nc=720)
            if D is None:
                continue
            d2 = math.hypot(S2[0] - G[0], S2[1] - G[1])
            v1 = (S1[0] - G[0], S1[1] - G[1])
            v2 = (S2[0] - G[0], S2[1] - G[1])
            cc = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
            psi = math.degrees(math.acos(max(-1.0, min(1.0, cc))))
            rows.append((D, l, b, d2, psi, S2))
    rows.sort(key=lambda r: r[0])
    Dbest, lb, bb, d2b, psib, S2b = rows[0]
    ana = 2 * d1 * math.tan(math.radians(EPS))
    print("  [基准] d1=%.0f m | 单点 D1=%.2f m | 候选点 %d" % (d1, D1, len(rows)), flush=True)
    print("  [基准] 最优 S2=(%.1f,%.1f) d2=%.0f m psi=%.1f deg D_min=%.2f m 增益=%.1fx"
          % (S2b[0], S2b[1], d2b, psib, Dbest, D1 / Dbest), flush=True)
    print("  [基准] 解析式 2*d1*tan(1deg) = %.2f m" % ana, flush=True)
    RES["q2_baseline"] = dict(D1=D1, D_best=Dbest, gain=D1 / Dbest, d2=d2b, psi=psib,
                              S2=list(S2b), analytic=ana)
    knee = d1 * math.tan(math.radians(EPS))
    perp = []
    for a in list(np.arange(5.5, 60.1, 1.0)) + list(np.arange(65.0, 501.0, 5.0)):
        S2 = (float(a), G[1])
        dv = exact_D(S2, nc=720)
        if dv is None:
            continue
        perp.append((float(a), float(dv), float(math.hypot(S2[0] - S1[0], S2[1] - S1[1]))))
    RES["q2_perp"] = perp
    RES["q2_knee"] = float(knee)
    _best_a = min(perp, key=lambda r: r[1])
    _near_knee = min(perp, key=lambda r: abs(r[0] - knee))
    _far = min(perp, key=lambda r: abs(r[0] - 200.0))
    print("  [垂线偏移] 拐点 a* = d1*tan1deg = %.2f m" % knee, flush=True)
    print("  [垂线偏移] a=%.1f -> D=%.2f m ; a=a* -> D=%.2f m ; a=200 -> D=%.2f m"
          % (_best_a[0], _best_a[1], _near_knee[1], _far[1]), flush=True)
    RES["q2_perp_best"] = [_best_a[0], _best_a[1]]
    RES["q2_perp_knee"] = [_near_knee[0], _near_knee[1]]
    RES["q2_perp_far"] = [_far[0], _far[1]]
    uvec = (math.cos(math.radians(th1)), math.sin(math.radians(th1)))
    nvec0 = (-uvec[1], uvec[0])
    grec = []
    for l in np.arange(20.0, RMAX + 1e-9, 20.0):
        if max(l, RMAX - l) > RMIN:
            continue
        gmax = math.sqrt(max(0.0, RMIN ** 2 - max(l, RMAX - l) ** 2))
        for g in np.arange(-gmax, gmax + 1e-9, 20.0):
            S2 = (l * uvec[0] + g * nvec0[0], l * uvec[1] + g * nvec0[1])
            if math.hypot(*S2) > ARENA:
                continue
            if math.hypot(S2[0] - G[0], S2[1] - G[1]) <= 5.0:
                continue
            dv = exact_D(S2, nc=180)
            if dv is None:
                continue
            v1 = (S1[0] - G[0], S1[1] - G[1])
            v2 = (S2[0] - G[0], S2[1] - G[1])
            cc = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
            grec.append((float(dv), float(l), float(g),
                         float(math.hypot(S2[0] - G[0], S2[1] - G[1])),
                         float(math.degrees(math.acos(max(-1.0, min(1.0, cc))))),
                         float(S2[0]), float(S2[1])))
    grec.sort(key=lambda r: r[0])
    RES["q2_recv_candidates"] = len(grec)
    RES["q2_recv_best"] = list(grec[0]) if grec else None
    print("  [保证可收] 源距离上界 R_max=%.0f m，r_min=%.0f m => 可行区为示向线上 %.0f m 处、半径 %.2f m 的圆盘"
          % (RMAX, RMIN, RMAX / 2.0, math.sqrt(RMIN ** 2 - (RMAX / 2.0) ** 2)), flush=True)
    if grec:
        b = grec[0]
        print("  [保证可收] 最优 D=%.2f m (l=%.0f, g=%.0f, d2=%.0f, psi=%.1f deg, S2=(%.0f,%.0f))，候选 %d 个"
              % (b[0], b[1], b[2], b[3], b[4], b[5], b[6], len(grec)), flush=True)

    ls = np.arange(200, 1601, 100.0)
    bs = np.arange(-180, 180, 3.0)
    A2 = np.full((len(bs), len(ls)), np.nan)
    E2 = np.full((len(bs), len(ls)), np.nan)
    D2 = np.full((len(bs), len(ls)), np.nan)
    for i, b in enumerate(bs):
        for j, l in enumerate(ls):
            S2 = (l * math.cos(math.radians(b)), l * math.sin(math.radians(b)))
            if math.hypot(*S2) > ARENA:
                continue
            dv = exact_D(S2, nc=180)
            if dv is None:
                continue
            E2[i, j] = dv
            A2[i, j] = analytic_D(S2)
            D2[i, j] = math.hypot(S2[0] - G[0], S2[1] - G[1])
    msk = np.isfinite(A2) & np.isfinite(E2)
    corr = float(np.corrcoef(A2[msk], E2[msk])[0, 1])
    msk_far = msk & (D2 >= 200.0)
    corr_far = float(np.corrcoef(A2[msk_far], E2[msk_far])[0, 1])
    RES["q2_corr_far"] = corr_far
    print("  [解析vs精确] r(全网格)=%.5f  r(d2>=200m)=%.5f" % (corr, corr_far), flush=True)
    amin = np.unravel_index(np.nanargmin(A2), A2.shape)
    emin = np.unravel_index(np.nanargmin(E2), E2.shape)
    devm = abs(ls[amin[1]] - ls[emin[1]])
    devd = min(abs(bs[amin[0]] - bs[emin[0]]), 360 - abs(bs[amin[0]] - bs[emin[0]]))
    print("  [解析vs精确] r=%.5f | 最优点偏差 %.1f m / %.1f deg" % (corr, devm, devd), flush=True)
    RES["q2_corr"] = corr
    RES["q2_opt_dev_m"] = float(devm)
    RES["q2_opt_dev_deg"] = float(devd)

    flat = []
    for l in np.arange(25, 1201, 12.5):
        S2 = (l * math.cos(math.radians(bb)), l * math.sin(math.radians(bb)))
        if math.hypot(*S2) > ARENA:
            continue
        dv = exact_D(S2, nc=360)
        if dv is None:
            continue
        flat.append((float(l), float(dv), float(math.hypot(S2[0] - G[0], S2[1] - G[1]))))
    RES["q2_flat"] = flat
    print("  [平坦性] %d 个采样点，d2 范围 %.0f~%.0f m" % (len(flat), flat[0][2], flat[-1][2]), flush=True)

    robust = []
    while len(robust) < 24:
        Gg = (rng.uniform(-1400, 1400), rng.uniform(-1400, 1400))
        if math.hypot(*Gg) > 1650:
            continue
        d1g = rng.choice([200.0, 400.0, 600.0, 800.0, 1000.0, 1200.0, 1400.0, 1500.0])
        a1g = rng.uniform(0, 360)
        S1g = (Gg[0] + d1g * math.cos(math.radians(a1g)), Gg[1] + d1g * math.sin(math.radians(a1g)))
        th1g = bearing(S1g, Gg)
        cand = []
        for l in np.arange(25, 1801, 25.0):
            for b in np.arange(-180, 180, 2.0):
                S2 = (l * math.cos(math.radians(b)), l * math.sin(math.radians(b)))
                if math.hypot(*S2) > ARENA:
                    continue
                d2 = math.hypot(S2[0] - Gg[0], S2[1] - Gg[1])
                if d2 <= 5.0:
                    continue
                v1 = (S1g[0] - Gg[0], S1g[1] - Gg[1])
                v2 = (S2[0] - Gg[0], S2[1] - Gg[1])
                cc = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
                s = abs(math.sin(math.acos(max(-1.0, min(1.0, cc)))))
                if s < 1e-4:
                    continue
                cand.append((2 * math.tan(math.radians(EPS)) * math.sqrt(d1g ** 2 + d2 ** 2) / s, l, b, d2, S2))
        cand.sort(key=lambda r: r[0])
        got = None
        for c in cand[:120]:
            poly = region([(S1g, th1g), (c[4], bearing(c[4], Gg))], nc=180, cap=True)
            if not poly:
                continue
            H = hull(poly)
            if len(H) < 3:
                continue
            D = diameter_bruteforce(H)[0]
            if got is None or D < got[0]:
                v1 = (S1g[0] - Gg[0], S1g[1] - Gg[1])
                v2 = (c[4][0] - Gg[0], c[4][1] - Gg[1])
                cc = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
                got = (D, d1g, c[3], math.degrees(math.acos(max(-1.0, min(1.0, cc)))))
        if got:
            robust.append(got)
    rb = np.array(robust)
    print("  [多场景 n=%d] 最优 d2 中位 %.0f m (%.0f~%.0f) | psi 中位 %.1f deg (%.1f~%.1f)"
          % (len(rb), np.median(rb[:, 2]), rb[:, 2].min(), rb[:, 2].max(),
             np.median(rb[:, 3]), rb[:, 3].min(), rb[:, 3].max()), flush=True)
    RES["q2_robust"] = [[float(v) for v in row] for row in rb]
    return (G, S1, th1, d1, D1, Dbest, bb, d2b, psib, S2b, poly1, A2, E2, ls, bs,
            amin, emin, corr, flat, rb, perp, knee)


def q2_infogain(D, n_prior=120, step=40.0):
    """带接收约束的主动观测点设计：
        max_{S2} E_{x~prior}[ ln( rho_min(T1) / rho_min(T2(x;S2)) ) ]
        s.t. S2 在保证可收圆盘内
    """
    print("\n问题二：效用最优的第二测点（主动观测设计）", flush=True)
    G, S1, th1, d1 = D[0], D[1], D[2], D[3]
    u = (math.cos(math.radians(th1)), math.sin(math.radians(th1)))
    nv = (-u[1], u[0])
    poly1 = region([(S1, th1)], nc=360, cap=True)
    H1 = hull(poly1)
    _, rho1 = mec_bruteforce(H1)
    RES["q2_ig_rho1"] = rho1

    rng = random.Random(7)
    prior = []
    while len(prior) < n_prior:
        d = RMAX * math.sqrt(rng.random())
        if d <= 5.0:
            continue
        a = math.radians(th1) + math.radians(rng.uniform(-EPS, EPS))
        prior.append((S1[0] + d * math.cos(a), S1[1] + d * math.sin(a)))

    EPS_RHO = 1e-6

    def upd_rho(S2, x):
        """返回第二次观测后的残余不确定度；near 分支按“可直接清除”处理"""
        if math.hypot(S2[0] - x[0], S2[1] - x[1]) <= 5.0:
            return 20.0
        poly = list(poly1)
        for (nn, cc) in wedge_hps(S2, bearing(S2, x)):
            poly = clip_hp(poly, nn, cc)
            if not poly:
                return None
        H = hull(poly)
        if len(H) < 3:
            return None
        return mec_bruteforce(H)[1]

    def gain_of(S2):
        gs, rs = [], []
        for x in prior:
            r = upd_rho(S2, x)
            if r is None:
                continue
            r = max(r, EPS_RHO)          # 钳制而非丢弃样本，避免选择偏差
            gs.append(math.log(rho1 / r))
            rs.append(r)
        if not gs:
            return None
        return (float(np.mean(gs)), float(np.min(gs)), float(np.percentile(rs, 90)),
                float(np.mean([1.0 if r <= 20.0 else 0.0 for r in rs])), len(gs))

    grid = []
    for l in np.arange(120.0, RMAX + 1e-9, step):
        if max(l, RMAX - l) > RMIN:
            continue
        gmax = math.sqrt(max(0.0, RMIN ** 2 - max(l, RMAX - l) ** 2))
        for g in np.arange(-gmax, gmax + 1e-9, step):
            S2 = (l * u[0] + g * nv[0], l * u[1] + g * nv[1])
            if math.hypot(*S2) > ARENA:
                continue
            out = gain_of(S2)
            if out is None:
                continue
            grid.append((out[0], out[1], out[2], out[3], float(l), float(g), S2[0], S2[1]))
    grid.sort(key=lambda r: -r[0])
    RES["q2_ig_grid"] = [[r[0], r[4], r[5], r[2], r[3]] for r in grid]
    best = grid[0]
    RES["q2_ig_best"] = [best[0], best[1], best[2], best[3], best[4], best[5], best[6], best[7]]
    refs = {}
    for lab, (l, g) in (("ideal", (d1, 10.0)), ("straight", (RMAX / 2.0, 0.0))):
        S2 = (l * u[0] + g * nv[0], l * u[1] + g * nv[1])
        out = gain_of(S2)
        refs[lab] = [out[0], out[1], out[2], out[3], l, g] if out else None
    RES["q2_ig_refs"] = refs
    print("  [增益最优] l=%.0f g=%.0f psi=%.1f  E[gain]=%.3f  min=%.3f  rho90=%.1f  P(rho<=20)=%.3f"
          % (best[4], best[5], math.degrees(math.acos(max(-1, min(1, (
              (S1[0] - G[0]) * (best[6] - G[0]) + (S1[1] - G[1]) * (best[7] - G[1])) /
              (d1 * math.hypot(best[6] - G[0], best[7] - G[1]) + 1e-12))))),
             best[0], best[1], best[2], best[3]), flush=True)
    for lab, r in refs.items():
        if r:
            print("  [对照-%s] E[gain]=%.3f  rho90=%.1f  P(rho<=20)=%.3f" % (lab, r[0], r[2], r[3]), flush=True)
    print("  [对比] 增益最优相对理想解收益提升 %.1f 倍" % (best[0] / refs["ideal"][0]), flush=True)

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.0))
    ax = axes[0]
    gg = np.array(RES["q2_ig_grid"])
    sc = ax.scatter(gg[:, 1], gg[:, 2], c=gg[:, 0], s=42, cmap="viridis", marker="s")
    th_c = np.linspace(0, 2 * math.pi, 400)
    ax.plot(RMAX / 2.0 + (RMIN) * 0 + 0, 0, "s", color="k", ms=7)
    _rad = math.sqrt(RMIN ** 2 - (RMAX / 2.0) ** 2)
    ax.plot(RMAX / 2.0 + _rad * np.cos(th_c), _rad * np.sin(th_c), "-", color=C_B, lw=1.8,
            label="接收可行边界 $R_{\\mathrm{recv}}$")
    ax.plot([best[4]], [best[5]], "*", color="red", ms=18, mec="k", label="效用最优")
    ax.plot([refs["ideal"][4]], [refs["ideal"][5]], "o", color=C_E, ms=9, mec="k", label="原“理想解”（贴近源）")
    ax.plot([refs["straight"][4]], [refs["straight"][5]], "^", color="0.4", ms=9, mec="k", label="沿示向线直冲")
    ax.set_xlabel("沿示向线前进量 $\\ell$ / m")
    ax.set_ylabel("侧向偏移 $g$ / m")
    ax.set_aspect("equal")
    ax.set_title("(a) 后验几何收缩效用场（示向线坐标系）")
    ax.legend(loc="best", fontsize=8.5, framealpha=1.0)
    ax.grid(alpha=0.25)
    fig.colorbar(sc, ax=ax, label="$\\mathbb{E}[\\ln(\\rho_1/\\rho_2)]$")
    ax = axes[1]
    labs = ["效用最优", "原“理想解”", "沿示向线直冲"]
    v_exp = [best[0], refs["ideal"][0], refs["straight"][0]]
    v_p20 = [100 * best[3], 100 * refs["ideal"][3], 100 * refs["straight"][3]]
    xb = np.arange(3)
    b1 = ax.bar(xb - 0.19, v_exp, 0.36, color=C_A, label="后验几何收缩效用 $\\mathbb{E}[\\ln(\\rho_1/\\rho_2)]$")
    ax2 = ax.twinx()
    b2 = ax2.bar(xb + 0.19, v_p20, 0.36, color=C_E, label="二次测量后 $P(\\rho_{\\min}\\leq20$ m$)$ / %")
    for b, v in zip(b1, v_exp):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.06, "%.2f" % v, ha="center", fontsize=9.5)
    for b, v in zip(b2, v_p20):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.6, "%.1f%%" % v, ha="center", fontsize=9.5)
    ax.set_xticks(xb)
    ax.set_xticklabels(labs, fontsize=9.5)
    ax.set_ylabel("后验几何收缩效用 / nat")
    ax2.set_ylabel("$P(\\rho_{\\min}\\leq20$ m$)$ / %")
    ax.set_title("(b) 三种选点的效用收益对比")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=8.5)
    ax.grid(alpha=0.25, axis="y")
    fig.suptitle("图 9  问题二：带接收约束的主动观测点设计--以后验几何收缩效用为目标", y=1.02, fontsize=12.5)
    save_fig(fig, "fig_q2_infogain")

    with open(os.path.join(TABDIR, "tab_q2_infogain.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["选点方案", "沿示向线 l /m", "侧向偏移 g /m", "后验几何收缩效用 /nat",
                    "最差增益 /nat", "rho_90 /m", "P(rho_min<=20m)"])
        w.writerow(["效用最优", "%.0f" % best[4], "%.0f" % best[5], "%.3f" % best[0],
                    "%.3f" % best[1], "%.1f" % best[2], "%.3f" % best[3]])
        for lab, nm in (("ideal", "原“理想解”（贴近源）"), ("straight", "沿示向线直冲")):
            r = refs[lab]
            w.writerow([nm, "%.0f" % r[4], "%.0f" % r[5], "%.3f" % r[0], "%.3f" % r[1],
                        "%.1f" % r[2], "%.3f" % r[3]])
        w.writerow([])
        w.writerow(["先验可行集直径 D1 /m", "%.2f" % D[4], ""])
        w.writerow(["先验可行集 rho_min /m", "%.2f" % rho1, "第二次测量前"])
    print("  [tab] tab_q2_infogain.csv", flush=True)


def q2_figs(D):
    (G, S1, th1, d1, D1, Dbest, bb, d2b, psib, S2b, poly1, A2, E2, ls, bs,
     amin, emin, corr, flat, rb, perp, knee) = D
    t = np.linspace(0, 2 * math.pi, 400)
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.2))
    ax = axes[0]
    P1 = np.array(poly1)
    ax.add_patch(MplPolygon(P1, closed=True, facecolor=C_B, alpha=0.16, edgecolor=C_B, lw=0.9,
                            label="单次观测区域（长条，$D_1$）"))
    polyb = region([(S1, th1), (S2b, bearing(S2b, G))], nc=360, cap=True)
    ax.add_patch(MplPolygon(np.array(hull(polyb)), closed=True, facecolor=C_D, alpha=0.85,
                            edgecolor="k", lw=1.0, label="双点交会区域（$D_{\\min}$）"))
    a = math.radians(th1)
    for sgn in (-1, 1):
        aa = math.radians(th1 + sgn * EPS)
        ax.plot([S1[0], S1[0] + 1900 * math.cos(aa)], [S1[1], S1[1] + 1900 * math.sin(aa)],
                "--", color="0.62", lw=0.9)
    ax.plot([S1[0], S1[0] + 1900 * math.cos(a)], [S1[1], S1[1] + 1900 * math.sin(a)],
            "-", color=C_A, lw=1.5, label="$\\theta_1$ 示向线")
    ax.plot([G[0], S2b[0]], [G[1], S2b[1]], "-", color=C_D, lw=1.8)
    for p, lab in ((S1, "$S_1$"), (G, "$G$")):
        ax.plot([p[0], S2b[0]], [p[1], S2b[1]], "-", color=C_E, lw=1.0, alpha=0.85)
    ax.plot([S1[0]], [S1[1]], "s", color=C_B, ms=7, label="$S_1$（第一检测点）")
    ax.plot([G[0]], [G[1]], "*", color=C_A, ms=16, label="$G$（干扰源）")
    ax.plot([S2b[0]], [S2b[1]], "o", color=C_D, ms=8, mec="k", label="$S_2^{*}$（垂足 $\\pm2\\hat d\\tan1^\\circ$）")
    ax.annotate("", xy=(S2b[0], S2b[1]), xytext=(G[0], G[1]),
                arrowprops=dict(arrowstyle="<->", color="k", lw=1.0))
    ax.set_aspect("equal")
    ax.set_xlim(-1500, 800)
    ax.set_ylim(-200, 1650)
    ax.set_title("(a) 最优第二测点几何：垂足 + 角误差宽度偏置")
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.legend(loc="upper left", framealpha=0.95)
    ax.grid(alpha=0.25)
    axins = ax.inset_axes([0.60, 0.05, 0.38, 0.40])
    axins.add_patch(MplPolygon(P1, closed=True, facecolor=C_B, alpha=0.20, edgecolor=C_B, lw=0.7))
    axins.add_patch(MplPolygon(np.array(hull(polyb)), closed=True, facecolor=C_D, alpha=0.9,
                               edgecolor="k", lw=0.8))
    axins.plot([G[0]], [G[1]], "*", color=C_A, ms=11)
    axins.plot([S2b[0]], [S2b[1]], "o", color=C_D, ms=5, mec="k")
    axins.set_xlim(-30, 20)
    axins.set_ylim(G[1] - 1.2, G[1] + 1.2)
    axins.set_xticks([])
    axins.set_yticks([])
    axins.set_title("源附近局部放大（纵向放大 40 倍）", fontsize=8,
                    bbox=dict(fc="white", ec="0.8", lw=0.6, alpha=1.0, pad=1.6))
    axins.set_zorder(6)
    axins.patch.set_alpha(1.0)
    axins.grid(alpha=0.25)
    ax.indicate_inset_zoom(axins, edgecolor="0.45", alpha=0.7)
    ax = axes[1]
    ax.plot([f[0] for f in perp], [f[1] for f in perp], "-o", color=C_A, ms=3, lw=1.7,
            label="精确交会区域直径 $D$")
    ax.axvline(knee, color=C_E, ls="-.", lw=1.3, label="拐点 $a^{*}=d_1\\tan1^\\circ=%.1f$ m" % knee)
    ax.axhline(2 * knee, color=C_B, ls="--", lw=1.2, label="平台 $2d_1\\tan1^\\circ=%.1f$ m" % (2 * knee))
    ax.axvspan(0, 5.5, color="0.75", alpha=0.45)
    ax.text(7.5, 0.05, "强信号盲区 $d_2\\leq5$ m", transform=ax.get_xaxis_transform(),
            fontsize=8.5, ha="left", va="bottom", color="0.3")
    ax.set_xlabel("垂线偏移量 $a$（第二测点到源的垂距）/ m")
    ax.set_ylabel("交会定位区域直径 $D$ / m")
    ax.set_title("(b) 目标函数对 $d_2$ 的平坦性")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.25)
    fig.suptitle("图 5  问题二：第二检测点的最优几何与目标函数平坦性", y=1.02, fontsize=12.5)
    save_fig(fig, "fig_q2_geometry")

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.9), sharey=True)
    im = None
    for ax, M, ttl in ((axes[0], A2, "(a) 解析误差尺度 $D_{\\mathrm{scale}}$"),
                       (axes[1], E2, "(b) 精确交会区域直径 $D$")):
        _cm = plt.get_cmap("viridis").copy()
        _cm.set_bad("0.88")
        _keep = np.isfinite(M).all(axis=1)          # 剔除 beta=+-90度 的退化行（无定义），避免伪影横线
        im = ax.pcolormesh(ls, bs[_keep], M[_keep], shading="auto", cmap=_cm)
        ax.text(0.02, 0.03, "beta=+-90度 为退化方向（无定义），已剔除", transform=ax.transAxes,
                fontsize=8, color="0.35",
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.2))
        ax.plot([ls[emin[1]]], [bs[emin[0]]], "r*", ms=16, label="数值最优")
        if ttl.startswith("(b)"):
            ax.plot([ls[amin[1]]], [bs[amin[0]]], "wo", ms=7, mfc="none", mew=1.8, label="解析最优")
        ax.set_xlabel("$|S_2|$ / m")
        ax.set_title(ttl)
        ax.legend(loc="upper right")
    axes[0].set_ylabel("极角 $\\beta$ / (度)")
    fig.colorbar(im, ax=axes, label="直径 $D$ / m", fraction=0.03)
    fig.suptitle("图 6  问题二：解析误差尺度场与精确直径场的一致性（$r=%.5f$）" % corr, y=1.03, fontsize=12.5)
    save_fig(fig, "fig_q2_scale_vs_exact")

    step = 12.0
    gx = np.arange(-ARENA, ARENA + step, step)
    gy = np.arange(-ARENA, ARENA + step, step)
    XX, YY = np.meshgrid(gx, gy)
    inside = XX ** 2 + YY ** 2 <= ARENA ** 2
    P1 = np.array(poly1)
    uvec = (math.cos(math.radians(th1)), math.sin(math.radians(th1)))
    c_half = RMAX / 2.0
    g_rad = math.sqrt(RMIN ** 2 - c_half ** 2)
    cx_recv = S1[0] + c_half * uvec[0]
    cy_recv = S1[1] + c_half * uvec[1]
    # 精确保证可收集： domega1 的极点各自 1000 m 圆盘的交集（一般不是圆盘）
    ext1 = hull(poly1)
    recv = np.ones(XX.shape, dtype=bool)
    for (vx, vy) in ext1[:8]:
        recv &= (XX - vx) ** 2 + (YY - vy) ** 2 <= RMIN ** 2
    outer = (XX - cx_recv) ** 2 + (YY - cy_recv) ** 2 <= g_rad ** 2
    dx = XX - G[0]
    dy = YY - G[1]
    dd2 = np.hypot(dx, dy)
    cospsi = ((S1[0] - G[0]) * dx + (S1[1] - G[1]) * dy) / (d1 * np.maximum(dd2, 1e-9))
    psi = np.degrees(np.arccos(np.clip(cospsi, -1, 1)))
    good = (psi >= 30) & (psi <= 150) & (np.hypot(XX - S1[0], YY - S1[1]) >= 52)
    cand = inside & recv & good
    fig, ax = plt.subplots(figsize=(7.4, 6.8))
    ax.contourf(XX, YY, recv.astype(float), levels=[0.5, 1.5], colors=[C_C], alpha=0.25)
    ax.contour(XX, YY, outer.astype(float), levels=[0.5], colors="0.45", linewidths=1.2, linestyles=":")
    ax.contour(XX, YY, good.astype(float), levels=[0.5], colors=[C_D], linewidths=1.6, linestyles="--")
    ax.contour(XX, YY, cand.astype(float), levels=[0.5], colors=[C_B], linewidths=1.8)
    ax.add_patch(MplCircle((0, 0), ARENA, fill=False, ec="0.35", lw=1.2))
    ax.add_patch(MplPolygon(P1, closed=True, facecolor=C_A, alpha=0.30, edgecolor=C_A, lw=1.0))
    ax.plot([S1[0]], [S1[1]], "s", color="k", ms=7)
    ax.plot([G[0]], [G[1]], "*", color="r", ms=16)
    ax.plot([S2b[0]], [S2b[1]], "o", color=C_D, ms=8, mec="k")
    ax.annotate("理想解 $S_2^{*}$", (S2b[0], S2b[1]), textcoords="offset points", xytext=(9, 6),
                fontsize=10, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.4))
    _rb = RES.get("q2_recv_best")
    if _rb:
        ax.plot([_rb[5]], [_rb[6]], "^", color=C_E, ms=10, mec="k",
                label="可执行解（保证可收，$D=%.1f$ m）" % _rb[0])
        ax.annotate("可执行解", (_rb[5], _rb[6]), textcoords="offset points", xytext=(9, -14),
                    fontsize=10, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.4))
    ax.set_aspect("equal")
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("图 7  问题二：候选区域 $S_2=R_{\\mathrm{geo}}\\cap R_{\\mathrm{recv}}\\cap R_{\\mathrm{good}}$"
                 "（理想解 vs 可执行解）")
    handles = [
        Line2D([], [], color="0.35", lw=1.2, label="$R_{\\mathrm{geo}}$：目标圆域（1800 m）"),
        Line2D([], [], color=C_C, lw=6, alpha=0.5,
               label="$R_{\\mathrm{recv}}$：保证可收集 $\\bigcap_{x\\in\\Omega_1}\\bar B(x,1000)$"),
        Line2D([], [], color="0.45", lw=1.2, ls=":",
               label="圆盘外近似（示向线 750 m 处、半径 %.0f m，仅作对照）" % g_rad),
        Line2D([], [], color=C_D, lw=1.6, ls="--", label="$R_{\\mathrm{good}}$：交会角与病态排除"),
        Line2D([], [], color=C_B, lw=1.8, label="$S_2$：候选区域"),
        Line2D([], [], marker="*", color="r", ls="", ms=13, label="干扰源 $G$"),
        Line2D([], [], marker="o", color=C_D, ls="", ms=7, mec="k", label="理想解（假定源位置已知）"),
    ]
    if _rb:
        handles.append(Line2D([], [], marker="^", color=C_E, ls="", ms=9, mec="k",
                              label="可执行解（源位置未知、保证可收）"))
    ax.legend(handles=handles, loc="lower right", framealpha=0.95)
    ax.grid(alpha=0.2)
    save_fig(fig, "fig_q2_candidate_region")

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot([f[0] for f in perp], [f[1] for f in perp], "-o", color=C_A, ms=3.5, lw=1.9,
            label="精确交会区域直径 $D(a)$")
    ax.axvline(knee, color=C_E, ls="-.", lw=1.4,
               label="拐点 $a^{*}=d_1\\tan1^\\circ=%.1f$ m" % knee)
    ax.axhline(2 * knee, color=C_B, ls="--", lw=1.3,
               label="平台值 $2d_1\\tan1^\\circ=%.1f$ m" % (2 * knee))
    ax.axvspan(0, 5.5, color="0.75", alpha=0.45)
    ax.text(7.5, 0.05, "强信号盲区 $d_2\\leq5$ m", transform=ax.get_xaxis_transform(),
            fontsize=8.5, ha="left", va="bottom", color="0.3")
    _ds = [f[1] for f in perp]
    ax.set_ylim(min(_ds) * 0.90, max(_ds) * 1.06)
    ax.set_xlabel("垂线偏移量 $a$（第二测点到源的垂距）/ m")
    ax.set_ylabel("交会定位区域直径 $D$ / m")
    ax.set_title("图 8  问题二：$D(a)$ 的双段规律--线性段 $d_1\\tan1^\\circ+a$ 与平台段 $2d_1\\tan1^\\circ$")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.25)
    save_fig(fig, "fig_q2_flatness")

    with open(os.path.join(TABDIR, "tab_q2_best.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["量", "数值", "说明"])
        w.writerow(["基准 d1 /m", "%.0f" % d1, "S1=(0,0), G=(0,1200)"])
        w.writerow(["单点观测 D1 /m", "%.2f" % D1, "仅含径向不确定度"])
        w.writerow(["最优 S2", "(%.1f, %.1f)" % (S2b[0], S2b[1]), ""])
        w.writerow(["最优 d2 /m", "%.0f" % d2b, ""])
        w.writerow(["最优交会角 psi /deg", "%.1f" % psib, ""])
        w.writerow(["D_min /m", "%.2f" % Dbest, "精确几何"])
        w.writerow(["解析平台值 /m", "%.2f" % (2 * d1 * math.tan(math.radians(EPS))), "2*d1*tan(1deg)，非最优值"])
        w.writerow(["增益", "%.1fx" % (D1 / Dbest), "D1 / D_min"])
        w.writerow(["解析 vs 精确 相关系数(全网格)", "%.5f" % corr, "含近退化几何"])
        w.writerow(["解析 vs 精确 相关系数(d2>=200m)", "%.5f" % RES["q2_corr_far"], "缩放律适用区"])
        w.writerow(["解析/数值最优点偏差", "%.1f m / %.1f deg" % (RES["q2_opt_dev_m"], RES["q2_opt_dev_deg"]), ""])
        w.writerow([])
        w.writerow(["垂线偏移拐点 a* /m", "%.2f" % knee, "a* = d1*tan(1deg)"])
        w.writerow(["a=5.5 m 时 D /m", "%.2f" % perp[0][1], "受 5 m 盲区约束的下界"])
        w.writerow(["a=a* 时 D /m", "%.2f" % RES["q2_perp_knee"][1], "拐点"])
        w.writerow(["a=200 m 时 D /m", "%.2f" % RES["q2_perp_far"][1], "平台段"])
        w.writerow(["稳健推荐偏移", "%.1f m" % (2 * knee), "2*d1*tan(1deg)，落在平台起点，对估计误差不敏感"])
        _rb = RES.get("q2_recv_best")
        if _rb:
            w.writerow([])
            w.writerow(["R_recv 定义", "Omega1 全部极点 <-> 各 1000 m 圆盘之交",
                        "精确保证可收集；一般不是圆盘"])
            w.writerow(["圆盘外近似 圆心/半径 /m",
                        "(%.0f, %.0f) / %.2f" % (S1[0] + (RMAX / 2.0) * math.cos(math.radians(th1)),
                                                 S1[1] + (RMAX / 2.0) * math.sin(math.radians(th1)),
                                                 math.sqrt(RMIN ** 2 - (RMAX / 2.0) ** 2)),
                        "仅作对照（外近似，用于保证型优化不安全）"])
            w.writerow(["可执行最优 D /m", "%.2f" % _rb[0], "源位置未知、要求第二点保证可收"])
            w.writerow(["可执行最优 l /m", "%.0f" % _rb[1], "沿示向线前进量"])
            w.writerow(["可执行最优 g /m", "%.0f" % _rb[2], "侧向偏移"])
            w.writerow(["可执行最优 psi /deg", "%.1f" % _rb[4], ""])
            w.writerow(["可执行最优 增益", "%.1fx" % (D1 / _rb[0]), "D1 / D"])
    print("  [tab] tab_q2_best.csv", flush=True)
    with open(os.path.join(TABDIR, "tab_q2_robust.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["场景", "d1 /m", "最优 D /m", "最优 d2 /m", "最优 psi /deg"])
        for i, row in enumerate(rb, 1):
            w.writerow([i, "%.0f" % row[1], "%.2f" % row[0], "%.0f" % row[2], "%.1f" % row[3]])
        w.writerow([])
        w.writerow(["中位数", "",
                    "%.2f" % np.median(rb[:, 0]), "%.0f" % np.median(rb[:, 2]),
                    "%.1f" % np.median(rb[:, 3])])
    print("  [tab] tab_q2_robust.csv", flush=True)


if __name__ == "__main__":
    res1 = q1()
    q1_figs(*res1)
    res2 = q2()
    q2_figs(res2)
    q2_infogain(res2)
    with open(os.path.join(SCRATCH, "summary_q1q2.json"), "w", encoding="utf-8") as f:
        json.dump(RES, f, ensure_ascii=False, indent=1, default=float)
    print("\n[done] 汇总写入 _scratch/summary_q1q2.json", flush=True)
