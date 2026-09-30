# -*- coding: utf-8 -*-
"""
B1 口径（分段独立+直接距离）下问题二的概率曲线扫描：
φ = 0.8%, 0.9%, 1.2%, 1.5%，M=200，用于判断问题三的搜索区间。
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


def pieces_of_segment(p1, p2):
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
        pm = p1 + 0.5 * (t0 + t1) * d
        if all(-HALF - 1e-9 <= pm[k] <= HALF + 1e-9 for k in range(3)):
            a = p1 + t0 * d
            b = p1 + t1 * d
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


def conduct_b1(segs):
    N = len(segs)
    if N == 0:
        return 0
    P1 = np.array([s[0] for s in segs])
    P2 = np.array([s[1] for s in segs])
    U = P2 - P1
    L = np.linalg.norm(U, axis=1)
    U = U / L[:, None]
    dL = np.minimum(np.abs(P1[:, 0] + HALF), np.abs(P2[:, 0] + HALF))
    dR = np.minimum(np.abs(P1[:, 0] - HALF), np.abs(P2[:, 0] - HALF))
    touchL = dL <= FACE_D
    touchR = dR <= FACE_D

    # 只取上三角配对，分块计算，控制峰值内存
    ii, jj = np.triu_indices(N, 1)
    edges = []
    CH = 20000
    for st in range(0, len(ii), CH):
        sl = slice(st, st + CH)
        pA = P1[ii[sl]]
        uA = U[ii[sl]]
        lA = L[ii[sl]]
        pB = P1[jj[sl]]
        vB = U[jj[sl]]
        lB = L[jj[sl]]
        d = seg_seg_dist_batch(pA, uA, lA, pB, vB, lB)
        hit = np.nonzero(d <= SEG_D)[0]
        if len(hit):
            edges.append(np.stack([ii[sl][hit], jj[sl][hit]], axis=1))

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
    if edges:
        edges = np.concatenate(edges, axis=0)
        for a, b in edges:
            union(int(a), int(b))
    return 1 if find(LEFT) == find(RIGHT) else 0


def sample_B1(N, seed):
    rng = np.random.default_rng(seed)
    c = rng.uniform(-HALF, HALF, size=(N, 3))
    v = rng.normal(size=(N, 3))
    u = v / np.linalg.norm(v, axis=1)[:, None]
    segs = []
    for i in range(N):
        segs.extend(pieces_of_segment(c[i] - 2500.0 * u[i], c[i] + 2500.0 * u[i]))
    return conduct_b1(segs)


def worker(args):
    phi, N, base_seed, M = args
    hits = [sample_B1(N, base_seed * 100000 + m) for m in range(M)]
    return phi, hits


def wilson(k, M, z=1.96):
    p = k / M
    den = 1 + z * z / M
    center = (p + z * z / (2 * M)) / den
    half = z * math.sqrt(p * (1 - p) / M + z * z / (4 * M * M)) / den
    return p, max(0.0, center - half), min(1.0, center + half)


if __name__ == "__main__":
    t0 = time.time()
    phis = [0.008, 0.009, 0.012, 0.015]
    M_TOTAL = 200
    CHUNK = 40
    tasks = []
    for phi in phis:
        N = round(phi * 1e12 / V_A)
        for c in range(M_TOTAL // CHUNK):
            tasks.append((phi, N, 9 + c, CHUNK))
    n_workers = min(4, mp.cpu_count())
    print(f"B1 sweep workers={n_workers} tasks={len(tasks)}", flush=True)
    results = {phi: [] for phi in phis}
    with mp.Pool(n_workers) as pool:
        for phi, hits in pool.imap_unordered(worker, tasks):
            results[phi].extend(hits)
    for phi in phis:
        k = sum(results[phi])
        M = len(results[phi])
        p, lo, hi = wilson(k, M)
        print(f"B1 phi={phi*100:.2f}% N={round(phi*1e12/V_A)} M={M} 导通={k} "
              f"p̂={p:.4f} 95%CI=[{lo:.4f},{hi:.4f}]", flush=True)
    print(f"总耗时 {time.time()-t0:.1f}s", flush=True)
