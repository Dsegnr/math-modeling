# -*- coding: utf-8 -*-
"""
模型口径辨析（关键验证）：
  A1 周期卷回+同一导体+周期距离（原方案）          -> 预期 P 恒≈1
  B1 周期卷回+分段各自成导体+直接距离（无跨边界相邻）
  C1 完全悬浮于内部（拒绝采样）+直接距离
同时给出问题一在 B1 口径下的三组导通性。
"""
import math
import time
import multiprocessing as mp
import numpy as np

SIDE = 10000.0
HALF = SIDE / 2
FACE_D = 31.8
SEG_D = 61.8
V_A = math.pi * 30.0**2 * 5000.0


def seg_seg_dist_single(p1, p2, q1, q2):
    """直接距离（不周期化）的线段最短距离。"""
    u = p2 - p1
    v = q2 - q1
    w = p1 - q1
    a = np.dot(u, u)
    b = np.dot(u, v)
    c = np.dot(v, v)
    d = np.dot(u, w)
    e = np.dot(v, w)
    den = a * c - b * b
    if abs(den) > 1e-12:
        s = (b * e - c * d) / den
        t = (a * e - b * d) / den
    else:
        s = 0.0
        t = e / c if c > 0 else 0.0
    best = np.inf
    for ss in (0.0, 1.0):
        tt = max(0.0, min(1.0, (b * ss + e) / c if c > 0 else 0.0))
        vv = w + ss * u - tt * v
        best = min(best, np.linalg.norm(vv))
    for tt in (0.0, 1.0):
        ss = max(0.0, min(1.0, (b * tt - d) / a if a > 0 else 0.0))
        vv = w + ss * u - tt * v
        best = min(best, np.linalg.norm(vv))
    return best


def pieces_of_segment(p1, p2):
    """把线段按周期卷回切成 Ω 内的 1~3 段（B1 口径用，段之间不视为相连）。"""
    d = p2 - p1
    ts = [0.0, 1.0]
    for axis in range(3):
        if abs(d[axis]) < 1e-12:
            continue
        for face in (-HALF, HALF):
            t = (face - p1[axis]) / d[axis]
            if 1e-9 < t < 1 - 1e-9:
                ts.append(t)
    ts = sorted(set(round(t, 12) for t in ts))
    pieces = []
    for i in range(len(ts) - 1):
        t0, t1 = ts[i], ts[i + 1]
        if t1 - t0 < 1e-9:
            continue
        mid = 0.5 * (t0 + t1)
        pm = p1 + mid * d
        if all(-HALF - 1e-9 <= pm[k] <= HALF + 1e-9 for k in range(3)):
            a = p1 + t0 * d
            b = p1 + t1 * d
            # 把越界端点卷回
            for k in range(3):
                while a[k] > HALF:
                    a[k] -= SIDE
                while a[k] < -HALF:
                    a[k] += SIDE
                while b[k] > HALF:
                    b[k] -= SIDE
                while b[k] < -HALF:
                    b[k] += SIDE
            pieces.append((a, b))
    return pieces


def conduct_direct(segs, seed=0):
    """直接距离口径：segs = list of (p1,p2)，每个元素一个节点。"""
    N = len(segs)
    parent = list(range(N + 2))
    LEFT = N
    RIGHT = N + 1

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i, (p1, p2) in enumerate(segs):
        dl = min(np.linalg.norm(p1 - np.array([-HALF, p1[1], p1[2]])),
                 np.linalg.norm(p2 - np.array([-HALF, p2[1], p2[2]])))
        # 到面的最短距离：到 x=-5000 / x=5000 平面的距离
        dL = min(abs(p1[0] + HALF), abs(p2[0] + HALF))
        dR = min(abs(p1[0] - HALF), abs(p2[0] - HALF))
        if dL <= FACE_D:
            union(i, LEFT)
        if dR <= FACE_D:
            union(i, RIGHT)
    for i in range(N):
        for j in range(i + 1, N):
            if seg_seg_dist_single(segs[i][0], segs[i][1], segs[j][0], segs[j][1]) <= SEG_D:
                union(i, j)
    return 1 if find(LEFT) == find(RIGHT) else 0


def gen_rods(N, rng):
    c = rng.uniform(-HALF, HALF, size=(N, 3))
    v = rng.normal(size=(N, 3))
    u = v / np.linalg.norm(v, axis=1)[:, None]
    return c - 2500.0 * u, c + 2500.0 * u


def sample_B1(N, seed):
    rng = np.random.default_rng(seed)
    p1, p2 = gen_rods(N, rng)
    segs = []
    for i in range(N):
        segs.extend(pieces_of_segment(p1[i], p2[i]))
    return conduct_direct(segs)


def sample_C1(N, seed):
    rng = np.random.default_rng(seed)
    segs = []
    while len(segs) < N:
        c = rng.uniform(-HALF, HALF, size=(1, 3))
        v = rng.normal(size=(1, 3))
        u = v / np.linalg.norm(v)
        a = c - 2500.0 * u
        b = c + 2500.0 * u
        if all(-HALF <= a[0, k] <= HALF and -HALF <= b[0, k] <= HALF for k in range(3)):
            segs.append((a[0].copy(), b[0].copy()))
    return conduct_direct(segs)


def worker(args):
    model, phi, N, base_seed, M = args
    hits = []
    fn = sample_B1 if model == "B1" else sample_C1
    for m in range(M):
        hits.append(fn(N, base_seed * 100000 + m))
    return model, phi, hits


def wilson(k, M, z=1.96):
    p = k / M
    den = 1 + z * z / M
    center = (p + z * z / (2 * M)) / den
    half = z * math.sqrt(p * (1 - p) / M + z * z / (4 * M * M)) / den
    return p, max(0.0, center - half), min(1.0, center + half)


if __name__ == "__main__":
    # ---- 问题一 B1 口径（附件行直接作为独立节点，直接距离）----
    import openpyxl
    AFILE = (r"2026年第七届华数杯数学建模竞赛赛题/2026年第七届华数杯数学建模竞赛赛题/"
             r"A题 微构体中填充导电介质的仿真优化/附件.xlsx")
    print("===== 问题一：B1 口径（分段各自独立+直接距离）=====")
    wb = openpyxl.load_workbook(AFILE, read_only=True, data_only=True)
    for name in ["组1", "组2", "组3"]:
        ws = wb[name]
        segs = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i <= 1 or row[0] is None:
                continue
            try:
                r = [float(v) for v in row]
            except Exception:
                continue
            segs.append((np.array(r[:3]), np.array(r[3:])))
        res = conduct_direct(segs)
        print(f"{name}: 行数={len(segs)} -> {'导通' if res else '不导通'}")

    # ---- 问题二：B1 与 C1 口径 ----
    t0 = time.time()
    phis = [0.005, 0.006, 0.007, 0.010]
    M_TOTAL = 200
    CHUNK = 40
    tasks = []
    for model in ["B1", "C1"]:
        for phi in phis:
            N = round(phi * 1e12 / V_A)
            for c in range(M_TOTAL // CHUNK):
                tasks.append((model, phi, N, 7 + c, CHUNK))
    n_workers = min(8, mp.cpu_count())
    print(f"\n===== 问题二：B1/C1 口径 MC（workers={n_workers}, tasks={len(tasks)}）=====", flush=True)
    results = {m: {phi: [] for phi in phis} for m in ["B1", "C1"]}
    with mp.Pool(n_workers) as pool:
        for model, phi, hits in pool.imap_unordered(worker, tasks):
            results[model][phi].extend(hits)
    for model in ["B1", "C1"]:
        for phi in phis:
            k = sum(results[model][phi])
            M = len(results[model][phi])
            p, lo, hi = wilson(k, M)
            print(f"{model} phi={phi*100:.2f}% N={round(phi*1e12/V_A)} M={M} 导通={k} "
                  f"p̂={p:.4f} 95%CI=[{lo:.4f},{hi:.4f}]", flush=True)
    print(f"总耗时 {time.time()-t0:.1f}s", flush=True)
