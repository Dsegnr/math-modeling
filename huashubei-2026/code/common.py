# -*- coding: utf-8 -*-
"""
A 题公共库：几何常量、距离计算、连通判定、C1 随机采样、Wilson 区间、绘图样式。
所有函数向量化/分块化，支持大规模蒙特卡洛。
"""
import math
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---------------- 几何与物理常量 ----------------
SIDE = 10000.0            # 微构体边长 nm
HALF = SIDE / 2.0
R_A = 30.0                # 介质 A 半径 nm
H_A = 5000.0              # 介质 A 高 nm
R_B = 200.0               # 介质 B 半径 nm
DELTA = 1.8               # 导通表面间距阈值 nm
V_A = math.pi * R_A**2 * H_A
V_B = 4.0 / 3.0 * math.pi * R_B**3
V_CUBE = 1e12             # nm^3

# 导通阈值（轴线/球心距离，nm）
TH_AA = 2 * R_A + DELTA            # 61.8  A-A
TH_AB = R_A + R_B + DELTA          # 231.8 A-B
TH_BB = 2 * R_B + DELTA            # 401.8 B-B
TH_AF = R_A + DELTA                # 31.8  A-面
TH_BF = R_B + DELTA                # 201.8 B-面


# ---------------- 中文与绘图样式 ----------------
def setup_font():
    """注册并启用中文字体（解决白框），西文 Times New Roman。"""
    import viz_common
    return viz_common.setup_chinese_font()


def save_fig(fig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=300)
    plt.close(fig)
    print("[fig]", path)


def style_clean(ax, grid=False, bg="#F7F8FB"):
    """APMCM 风格：浅灰蓝底、去上右边框、无网格或极淡网格。"""
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.set_facecolor(bg)
    if grid:
        ax.grid(True, ls="--", alpha=0.25)
    else:
        ax.grid(False)
    ax.tick_params(labelsize=9)
    return ax


def add_cylinder_tubes(ax, P1, P2, colors, radius=90.0, alpha=0.92, n=16):
    """把线段画成三维圆柱管（Poly3DCollection），比线条更有体积感。
    P1/P2: (N,3)；colors: (N,) 颜色（可含 alpha 的 RGBA/hex）。
    radius 为视觉半径（数据单位），可按需放大以增强可读性。
    """
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    vecs = P2 - P1
    norms = np.linalg.norm(vecs, axis=1)
    u = vecs / norms[:, None]
    # 构造正交基 (v, w)
    helper = np.where(np.abs(u[:, 2:]) > 0.9, [1.0, 0.0, 0.0], [0.0, 0.0, 1.0])
    v = np.cross(u, helper)
    v = v / np.linalg.norm(v, axis=1)[:, None]
    w = np.cross(u, v)
    theta = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    ct = np.cos(theta)
    st = np.sin(theta)
    faces = []
    facecolors = []
    for i in range(len(P1)):
        rv = radius * (ct[:, None] * v[i] + st[:, None] * w[i])
        circ1 = P1[i] + rv
        circ2 = P2[i] + rv
        for k in range(n):
            k2 = (k + 1) % n
            faces.append([circ1[k], circ1[k2], circ2[k2], circ2[k]])
            facecolors.append(colors[i])
    pc = Poly3DCollection(faces, facecolors=facecolors, alpha=alpha,
                          edgecolors="none", zorder=10)
    ax.add_collection3d(pc)
    return pc


def add_cluster_hull(ax, pts, color, alpha=0.10):
    """给一组端点画半透明凸包，让连通簇呈现“材料团块”的体积感。"""
    from scipy.spatial import ConvexHull
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    if len(pts) < 4:
        return
    try:
        hull = ConvexHull(pts)
    except Exception:
        return
    pc = Poly3DCollection(pts[hull.simplices], alpha=alpha,
                          facecolor=color, edgecolor="none", zorder=5)
    ax.add_collection3d(pc)


def add_midpoint_dots(ax, pts, color, s=8.0, alpha=0.25):
    """把背景段画成淡色小点（中点），避免满屏线条。"""
    ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=s, c=color,
               alpha=alpha, depthshade=False, zorder=2)


# ---------------- 距离计算 ----------------
def seg_seg_dist_batch(pA, uA, LA, pB, vB, LB):
    """批量线段-线段最短距离（精确，含内部最近点与边界钳制）。"""
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


def seg_point_dist_chunk(P1, P2, C, chunk=1_000_000):
    """批量线段-点最短距离（供 A-B 判定），分块控制内存。返回 (N_r*N_s,) 数组。"""
    N = len(P1)
    M = len(C)
    U = P2 - P1
    L = np.linalg.norm(U, axis=1)
    U = U / L[:, None]
    out = np.empty(N * M)
    ii, jj = np.meshgrid(np.arange(N), np.arange(M), indexing='ij')
    ii = ii.ravel()
    jj = jj.ravel()
    for st in range(0, N * M, chunk):
        sl = slice(st, st + chunk)
        w = C[jj[sl]] - P1[ii[sl]]
        t = np.einsum('ij,ij->i', w, U[ii[sl]])
        t = np.clip(t / L[ii[sl]], 0.0, 1.0)
        d = np.linalg.norm(w - t[:, None] * U[ii[sl]], axis=1)
        out[sl] = d
    return out.reshape(N, M)


def rod_face_dist(P1, P2):
    """圆柱轴线到左右带电面的最短距离（段完全在盒内，取端点最小）。"""
    dL = np.minimum(np.abs(P1[:, 0] + HALF), np.abs(P2[:, 0] + HALF))
    dR = np.minimum(np.abs(P1[:, 0] - HALF), np.abs(P2[:, 0] - HALF))
    return dL, dR


def sphere_face_dist(C):
    return np.abs(C[:, 0] + HALF), np.abs(C[:, 0] - HALF)


# ---------------- 连通判定 ----------------
class UnionFind:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb

    def sizes(self, n_real):
        from collections import Counter
        c = Counter(self.find(i) for i in range(n_real))
        return sorted(c.values(), reverse=True)


def _build_uf(rod_segs, sphere_centers, merge_groups=None):
    """构建并查集（含左右面节点），返回 (uf, n_real)。"""
    N = len(rod_segs)
    M = len(sphere_centers) if sphere_centers is not None else 0
    n_real = N + M
    uf = UnionFind(n_real + 2)
    LEFT = n_real
    RIGHT = n_real + 1

    if merge_groups is not None:
        group_map = {}
        for i, g in enumerate(merge_groups):
            group_map.setdefault(g, i)
            uf.union(i, group_map[g])

    # 面接触
    if N:
        P1 = rod_segs[:, 0]
        P2 = rod_segs[:, 1]
        dL, dR = rod_face_dist(P1, P2)
        for i in np.nonzero(dL <= TH_AF)[0]:
            uf.union(i, LEFT)
        for i in np.nonzero(dR <= TH_AF)[0]:
            uf.union(i, RIGHT)
    if M:
        dL, dR = sphere_face_dist(sphere_centers)
        for i in np.nonzero(dL <= TH_BF)[0]:
            uf.union(N + i, LEFT)
        for i in np.nonzero(dR <= TH_BF)[0]:
            uf.union(N + i, RIGHT)

    # A-A
    if N >= 2:
        ii, jj = np.triu_indices(N, 1)
        P1 = rod_segs[:, 0]
        P2 = rod_segs[:, 1]
        U = P2 - P1
        L = np.linalg.norm(U, axis=1)
        U = U / L[:, None]
        CH = 100_000
        for st in range(0, len(ii), CH):
            sl = slice(st, st + CH)
            d = seg_seg_dist_batch(P1[ii[sl]], U[ii[sl]], L[ii[sl]],
                                   P1[jj[sl]], U[jj[sl]], L[jj[sl]])
            for a, b in zip(ii[sl][d <= TH_AA], jj[sl][d <= TH_AA]):
                uf.union(int(a), int(b))

    # A-B
    if N and M:
        P1 = rod_segs[:, 0]
        P2 = rod_segs[:, 1]
        D = seg_point_dist_chunk(P1, P2, sphere_centers)
        idx = np.argwhere(D <= TH_AB)
        for a, b in idx:
            uf.union(int(a), N + int(b))

    # B-B
    if M >= 2:
        try:
            from scipy.spatial import cKDTree
            pairs = cKDTree(sphere_centers).query_pairs(TH_BB, output_type='ndarray')
            for a, b in pairs:
                uf.union(N + int(a), N + int(b))
        except Exception:
            ii, jj = np.triu_indices(M, 1)
            D = np.linalg.norm(sphere_centers[ii] - sphere_centers[jj], axis=1)
            for a, b in zip(ii[D <= TH_BB], jj[D <= TH_BB]):
                uf.union(N + int(a), N + int(b))
    return uf, n_real


def conduct_mixed(rod_segs, sphere_centers, merge_groups=None, need_clusters=False):
    """
    混合体系导通判定。
    rod_segs: (N,2,3) 圆柱段；sphere_centers: (M,3) 球心。
    merge_groups: 可选，长度 N 的组标签；同组节点先合并（口径敏感性用）。
    返回 (导通 0/1, 节点数, 连通簇大小列表[可选])。
    """
    uf, n_real = _build_uf(rod_segs, sphere_centers, merge_groups)
    LEFT = n_real
    RIGHT = n_real + 1

    conduct = 1 if uf.find(LEFT) == uf.find(RIGHT) else 0
    sizes = uf.sizes(n_real) if need_clusters else None
    return conduct, n_real, sizes


def cluster_labels(rod_segs, sphere_centers=None):
    """返回每个真实节点（圆柱段在前、球在后）的连通簇编号（0 起）。"""
    uf, n_real = _build_uf(rod_segs, sphere_centers)
    mapping = {}
    labels = np.empty(n_real, dtype=int)
    for i in range(n_real):
        r = uf.find(i)
        if r not in mapping:
            mapping[r] = len(mapping)
        labels[i] = mapping[r]
    return labels


def find_spanning_path(rod_segs):
    """返回连接左右带电面的圆柱段索引集合（存在导通路径时），否则 None。"""
    N = len(rod_segs)
    if N == 0:
        return None
    P1 = rod_segs[:, 0]
    P2 = rod_segs[:, 1]
    dL, dR = rod_face_dist(P1, P2)
    touchL = list(np.nonzero(dL <= TH_AF)[0])
    touchR = set(np.nonzero(dR <= TH_AF)[0].tolist())
    if not touchL or not touchR:
        return None
    U = P2 - P1
    L = np.linalg.norm(U, axis=1)
    U = U / L[:, None]
    adj = {i: [] for i in range(N)}
    ii, jj = np.triu_indices(N, 1)
    for st in range(0, len(ii), 100000):
        sl = slice(st, st + 100000)
        d = seg_seg_dist_batch(P1[ii[sl]], U[ii[sl]], L[ii[sl]],
                               P1[jj[sl]], U[jj[sl]], L[jj[sl]])
        for a, b in zip(ii[sl][d <= TH_AA], jj[sl][d <= TH_AA]):
            adj[int(a)].append(int(b))
            adj[int(b)].append(int(a))
    from collections import deque
    parent = {s: -1 for s in touchL}
    q = deque(touchL)
    reached = None
    while q:
        u = q.popleft()
        if u in touchR:
            reached = u
            break
        for v in adj.get(u, []):
            if v not in parent:
                parent[v] = u
                q.append(v)
    if reached is None:
        return None
    path = set()
    node = reached
    while node != -1:
        path.add(node)
        node = parent[node]
    return path


def contact_edges(rod_segs):
    """返回圆柱段之间的接触对 (N,2) 以及左右带电面接触掩码。"""
    N = len(rod_segs)
    if N == 0:
        return np.zeros((0, 2), dtype=int), np.zeros(0, bool), np.zeros(0, bool)
    P1 = rod_segs[:, 0]
    P2 = rod_segs[:, 1]
    dL, dR = rod_face_dist(P1, P2)
    U = P2 - P1
    L = np.linalg.norm(U, axis=1)
    U = U / L[:, None]
    ii, jj = np.triu_indices(N, 1)
    pairs = []
    CH = 100_000
    for st in range(0, len(ii), CH):
        sl = slice(st, st + CH)
        d = seg_seg_dist_batch(P1[ii[sl]], U[ii[sl]], L[ii[sl]],
                               P1[jj[sl]], U[jj[sl]], L[jj[sl]])
        hit = np.nonzero(d <= TH_AA)[0]
        if len(hit):
            pairs.append(np.stack([ii[sl][hit], jj[sl][hit]], axis=1))
    edges = np.concatenate(pairs, axis=0) if pairs else np.zeros((0, 2), dtype=int)
    return edges, dL <= TH_AF, dR <= TH_AF


# ---------------- C1 随机采样 ----------------
def sample_rods_c1(N, rng):
    """完全位于盒内的随机圆柱（拒绝越界）。返回 (N,2,3)。"""
    segs = []
    while len(segs) < N:
        c = rng.uniform(-HALF, HALF, size=(1, 3))
        v = rng.normal(size=(1, 3))
        u = v / np.linalg.norm(v)
        a = c - (H_A / 2) * u
        b = c + (H_A / 2) * u
        if np.all(np.abs(a) <= HALF) and np.all(np.abs(b) <= HALF):
            segs.append(np.stack([a[0], b[0]], axis=0))
    return np.array(segs)


def sample_spheres_c1(N, rng):
    """完全位于盒内的随机球心（球不越界）。返回 (N,3)。"""
    lo = -HALF + R_B
    hi = HALF - R_B
    return rng.uniform(lo, hi, size=(N, 3))


# ---------------- 统计 ----------------
def wilson(k, M, z=1.96):
    p = k / M
    den = 1 + z * z / M
    center = (p + z * z / (2 * M)) / den
    half = z * math.sqrt(p * (1 - p) / M + z * z / (4 * M * M)) / den
    return p, max(0.0, center - half), min(1.0, center + half)


def n_rods(phi):
    return round(phi * V_CUBE / V_A)


def n_spheres(phi):
    return round(phi * V_CUBE / V_B)
