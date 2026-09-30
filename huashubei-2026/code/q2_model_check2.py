# -*- coding: utf-8 -*-
"""
正确（向量化）口径下问题二概率曲线：
  B1: 周期卷回 + 分段各自成节点 + 直接距离
  C1: 完全悬浮于内部（拒绝采样）+ 整根圆柱一个节点 + 直接距离
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


def conduct_segs(P1, P2):
    """直接距离口径：每行一条线段为一个节点。返回是否导通。"""
    N = len(P1)
    if N == 0:
        return 0
    U = P2 - P1
    L = np.linalg.norm(U, axis=1)
    U = U / L[:, None]
    dL = np.minimum(np.abs(P1[:, 0] + HALF), np.abs(P2[:, 0] + HALF))
    dR = np.minimum(np.abs(P1[:, 0] - HALF), np.abs(P2[:, 0] - HALF))
    touchL = dL <= FACE_D
    touchR = dR <= FACE_D

    ii, jj = np.triu_indices(N, 1)
    edges = []
    CH = 20000
    for st in range(0, len(ii), CH):
        sl = slice(st, st + CH)
        d = seg_seg_dist_batch(P1[ii[sl]], U[ii[sl]], L[ii[sl]],
                               P1[jj[sl]], U[jj[sl]], L[jj[sl]])
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


def sample_B1(N, seed):
    rng = np.random.default_rng(seed)
    c = rng.uniform(-HALF, HALF, size=(N, 3))
    v = rng.normal(size=(N, 3))
    u = v / np.linalg.norm(v, axis=1)[:, None]
    ps = []
    for i in range(N):
        ps.extend(pieces_of_segment(c[i] - 2500.0 * u[i], c[i] + 2500.0 * u[i]))
    if not ps:
        return 0
    P1 = np.array([s[0] for s in ps])
    P2 = np.array([s[1] for s in ps])
    return conduct_segs(P1, P2)


def sample_C1(N, seed):
    rng = np.random.default_rng(seed)
    P1 = []
    P2 = []
    while len(P1) < N:
        c = rng.uniform(-HALF, HALF, size=(1, 3))
        v = rng.normal(size=(1, 3))
        u = v / np.linalg.norm(v)
        a = c - 2500.0 * u
        b = c + 2500.0 * u
        if all(-HALF <= a[0, k] <= HALF and -HALF <= b[0, k] <= HALF for k in range(3)):
            P1.append(a[0])
            P2.append(b[0])
    return conduct_segs(np.array(P1), np.array(P2))


def worker(args):
    model, phi, N, base_seed, M = args
    fn = sample_B1 if model == "B1" else sample_C1
    hits = [fn(N, base_seed * 100000 + m) for m in range(M)]
    return model, phi, hits


def wilson(k, M, z=1.96):
    p = k / M
    den = 1 + z * z / M
    center = (p + z * z / (2 * M)) / den
    half = z * math.sqrt(p * (1 - p) / M + z * z / (4 * M * M)) / den
    return p, max(0.0, center - half), min(1.0, center + half)


if __name__ == "__main__":
    t0 = time.time()
    configs = [
        ("B1", [0.005, 0.006, 0.007, 0.010]),
        ("C1", [0.005, 0.007, 0.010, 0.015, 0.020, 0.030]),
    ]
    M_TOTAL = 200
    CHUNK = 40
    tasks = []
    for model, phis in configs:
        for phi in phis:
            N = round(phi * 1e12 / V_A)
            for c in range(M_TOTAL // CHUNK):
                tasks.append((model, phi, N, 11 + c, CHUNK))
    n_workers = min(4, mp.cpu_count())
    print(f"workers={n_workers} tasks={len(tasks)}", flush=True)
    results = {m: {} for m, _ in configs}
    for m, phis in configs:
        results[m] = {phi: [] for phi in phis}
    with mp.Pool(n_workers) as pool:
        for model, phi, hits in pool.imap_unordered(worker, tasks):
            results[model][phi].extend(hits)
    for model, phis in configs:
        for phi in phis:
            k = sum(results[model][phi])
            M = len(results[model][phi])
            p, lo, hi = wilson(k, M)
            print(f"{model} phi={phi*100:.2f}% N={round(phi*1e12/V_A)} M={M} 导通={k} "
                  f"p̂={p:.4f} 95%CI=[{lo:.4f},{hi:.4f}]", flush=True)
    print(f"总耗时 {time.time()-t0:.1f}s", flush=True)
