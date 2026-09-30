# -*- coding: utf-8 -*-
"""
华数杯 A 题 问题二：蒙特卡洛导通概率（初版）
运行：python q2_mc_quick.py
"""
import math
import time
import multiprocessing as mp
import numpy as np

SIDE = 10000.0
FACE_D = 30.0 + 1.8          # 圆柱轴线到带电面阈值
SEG_D = 60.0 + 1.8           # 圆柱轴线间阈值
V_A = math.pi * 30.0**2 * 5000.0
SHIFTS = np.array(
    [[tx, ty, tz] for tx in (-SIDE, 0, SIDE)
     for ty in (-SIDE, 0, SIDE)
     for tz in (-SIDE, 0, SIDE)], dtype=float)


def interval_dist_to_zero(a, b):
    lo = np.minimum(a, b)
    hi = np.maximum(a, b)
    return np.where(hi < 0, -hi, np.where(lo > 0, lo, 0.0))


def seg_seg_dist_batch(pA, uA, LA, pB, vB, LB):
    w = pA - pB
    a = np.einsum('ij,ij->i', uA, uA)
    b = np.einsum('ij,ij->i', uA, vB)
    c = np.einsum('ij,ij->i', vB, vB)
    d = np.einsum('ij,ij->i', uA, w)
    e = np.einsum('ij,ij->i', vB, w)
    den = a * c - b * b
    with np.errstate(divide='ignore', invalid='ignore'):
        s = np.where(np.abs(den) > 1e-12, (b * e - c * d) / den, 0.0)
        t = np.where(np.abs(den) > 1e-12, (a * e - b * d) / den,
                     e / np.where(c > 0, c, 1.0))
    s = np.clip(s, 0.0, LA)
    t = np.clip(t, 0.0, LB)
    t2 = np.clip((e + b * s) / np.where(c > 0, c, 1.0), 0.0, LB)
    s2 = np.clip((b * t - d) / np.where(a > 0, a, 1.0), 0.0, LA)
    z = np.zeros_like(LA)
    la = LA.copy()
    lb = LB.copy()
    cand = []
    for ss, tt in [(s, t2), (s2, t), (z, t2), (la, t2), (s2, z), (s2, lb)]:
        v = w + ss[:, None] * uA - tt[:, None] * vB
        cand.append(np.einsum('ij,ij->i', v, v))
    return np.sqrt(np.minimum.reduce(cand))


def one_sample(N, seed):
    rng = np.random.default_rng(seed)
    c = rng.uniform(-SIDE / 2, SIDE / 2, size=(N, 3))
    v = rng.normal(size=(N, 3))
    u = v / np.linalg.norm(v, axis=1)[:, None]
    P1 = c - 2500.0 * u
    P2 = c + 2500.0 * u

    bestL = np.full(N, np.inf)
    bestR = np.full(N, np.inf)
    for k in (-1, 0, 1):
        a = P1[:, 0] + SIDE * k + SIDE / 2
        b = P2[:, 0] + SIDE * k + SIDE / 2
        bestL = np.minimum(bestL, interval_dist_to_zero(a, b))
        a = P1[:, 0] + SIDE * k - SIDE / 2
        b = P2[:, 0] + SIDE * k - SIDE / 2
        bestR = np.minimum(bestR, interval_dist_to_zero(a, b))
    touchL = bestL <= FACE_D
    touchR = bestR <= FACE_D

    idx = np.arange(N)
    i_idx, j_idx = np.meshgrid(idx, idx, indexing='ij')
    i_idx = i_idx.ravel()
    j_idx = j_idx.ravel()
    pA = P1[i_idx]
    uA = u[i_idx]
    lA = np.full(N * N, 5000.0)
    dist = np.full(N * N, np.inf)
    for s in range(27):
        pB = P1[j_idx] + SHIFTS[s]
        d = seg_seg_dist_batch(pA, uA, lA, pB, u[j_idx], lA)
        dist = np.minimum(dist, d)
    adj = (dist <= SEG_D).reshape(N, N)
    np.fill_diagonal(adj, False)

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

    for i in range(N):
        if touchL[i]:
            union(i, LEFT)
        if touchR[i]:
            union(i, RIGHT)
    for i in range(N):
        for j in range(i + 1, N):
            if adj[i, j]:
                union(i, j)
    return 1 if find(LEFT) == find(RIGHT) else 0


def worker(args):
    phi, N, base_seed, M = args
    hits = [one_sample(N, base_seed * 100000 + m) for m in range(M)]
    return phi, hits


def wilson(k, M, z=1.96):
    p = k / M
    den = 1 + z * z / M
    center = (p + z * z / (2 * M)) / den
    half = z * math.sqrt(p * (1 - p) / M + z * z / (4 * M * M)) / den
    return p, max(0.0, center - half), min(1.0, center + half)


if __name__ == "__main__":
    t0 = time.time()
    phis = [0.005, 0.006, 0.007, 0.010]
    M_TOTAL = 300
    CHUNK = 50
    tasks = []
    for phi in phis:
        N = round(phi * 1e12 / V_A)
        for c in range(M_TOTAL // CHUNK):
            tasks.append((phi, N, 42 + c, CHUNK))
    n_workers = min(8, mp.cpu_count())
    print(f"workers={n_workers}, tasks={len(tasks)}", flush=True)

    results = {phi: [] for phi in phis}
    with mp.Pool(n_workers) as pool:
        for phi, hits in pool.imap_unordered(worker, tasks):
            results[phi].extend(hits)

    for phi in phis:
        k = sum(results[phi])
        M = len(results[phi])
        p, lo, hi = wilson(k, M)
        N = round(phi * 1e12 / V_A)
        print(f"phi={phi*100:.2f}%  N={N}  M={M}  导通={k}  "
              f"p̂={p:.4f}  95%CI=[{lo:.4f},{hi:.4f}]", flush=True)
    print(f"总耗时 {time.time()-t0:.1f}s", flush=True)
