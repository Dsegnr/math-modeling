"""
Q4 布局选型（带"点级位掩码缓存"的快速版）：结构族 {原点?} U 内环(R1,n1)? U 外环(R2,n2)。
思路：单个航点在 (位置x朝向) 网格上的覆盖只与它自己有关，故按点缓存掩码，
      枚举结构时只需按位或 -- 把 1480 个结构 x 39 点的重复计算压成"每个点算一次"。
"""
import os
import math
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ARENA = 1800.0


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def ring(r, n, off=0.0):
    return [(round(r * math.cos(math.radians(360.0 * k / n + off)), 3),
             round(r * math.sin(math.radians(360.0 * k / n + off)), 3)) for k in range(n)]


class Masker:
    def __init__(self, step, ostep, rmin, half, ref):
        self.X, self.Y = grid(step)
        g = np.arange(0.0, 360.0, ostep)
        self.TH = g
        self.rmin, self.half = rmin, half
        self.cache = {}
        self.npos = len(self.X)
        # 航点可布于任意位置（只需 |坐标| 不超过平台上限），故对任一 (x,theta) 总能在源的正前方
        # 放一个航点；因此「可达全集」= 全部 (位置x朝向) 对。
        self.full = (1 << (len(self.X) * len(self.TH))) - 1

    def bits(self, p):
        k = p
        if k in self.cache:
            return self.cache[k]
        dx, dy = p[0] - self.X, p[1] - self.Y
        vis = dx * dx + dy * dy <= self.rmin * self.rmin
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - self.TH[None, :] + 180.0) % 360.0 - 180.0)
        cov = vis[:, None] & (diff <= self.half)
        b = int.from_bytes(np.packbits(cov.ravel()).tobytes(), "little")
        self.cache[k] = b
        return b

    def ok(self, pts):
        acc = 0
        for p in pts:
            acc |= self.bits(p)
        return (self.full & ~acc).bit_count() == 0


def nn_tour(pts, start=(0.0, 0.0)):
    rem, cur, out = list(pts), start, []
    while rem:
        j = min(rem, key=lambda q: math.hypot(q[0] - cur[0], q[1] - cur[1]))
        out.append(j)
        cur = j
        rem.remove(j)
    return out


def tour_len(pts):
    s, cur = 0.0, (0.0, 0.0)
    for p in pts:
        s += math.hypot(p[0] - cur[0], p[1] - cur[1])
        cur = p
    return s


def two_opt(seq, iters=60):
    best = tour_len(seq)
    improved = True
    r = 0
    while improved and r < iters:
        improved = False
        r += 1
        n = len(seq)
        for i in range(n - 1):
            for j in range(i + 1, n):
                cand = seq[:i] + seq[i:j + 1][::-1] + seq[j + 1:]
                v = tour_len(cand)
                if v < best - 1e-9:
                    seq, best, improved = cand, v, True
    return seq, best


def main():
    ref = [(0.0, 0.0), (2000.0, 0.0), (-2000.0, 0.0), (0.0, 2000.0), (0.0, -2000.0),
           (1414.0, 1414.0), (-1414.0, 1414.0), (1414.0, -1414.0), (-1414.0, -1414.0)]
    M = Masker(40.0, 5.0, 975.0, 87.5, ref)
    print("粗筛 40 mx5度：%d 位置 x %d 朝向，缓存 %d 点"
          % (len(M.X), len(M.TH), 0), flush=True)
    cands = []
    for use0 in (True, False):
        for R1 in (0, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500):
            for n1 in ((0,) if R1 == 0 else (4, 5, 6, 8, 9, 10, 12, 15)):
                for R2 in (1850, 1900, 2000, 2100, 2200):
                    for n2 in (8, 9, 10, 12, 15, 18, 24, 30):
                        pts = ([(0.0, 0.0)] if use0 else []) \
                            + (ring(R1, n1) if R1 else []) + ring(R2, n2)
                        if not M.ok(pts):
                            continue
                        W = nn_tour([tuple(map(float, p)) for p in pts])
                        L = tour_len(W)
                        cands.append((L, len(pts), use0, R1, n1, R2, n2, W))
    cands.sort()
    print("粗筛可行 %d 个（缓存 %d 点）；前 12：" % (len(cands), len(M.cache)), flush=True)
    print(" %8s %5s %5s %6s %5s %6s %5s" % ("里程/m", "点数", "原点", "内环R", "n1", "外环R", "n2"))
    for L, n, u0, R1, n1, R2, n2, W in cands[:12]:
        print(" %8.0f %5d %5s %6d %5d %6d %5d" % (L, n, "是" if u0 else "否", R1, n1, R2, n2))
    # 细网格复核前 20
    M2 = Masker(20.0, 2.0, 975.0, 87.5, ref)
    keep = []
    print("\n20 mx2度 复核：", flush=True)
    for L, n, u0, R1, n1, R2, n2, W in cands[:20]:
        pts = [(round(p[0], 3), round(p[1], 3)) for p in W]
        ok = M2.ok(pts)
        print(" %8.0f m %5d 点 原点=%s 内环%4dx%-2d 外环%4dx%-2d -> %s"
              % (L, n, "是" if u0 else "否", R1, n1, R2, n2, "OK" if ok else "否"), flush=True)
        if ok:
            keep.append((L, n, u0, R1, n1, R2, n2, pts))
    if not keep:
        print(" 无结构通过第二级", flush=True)
        return
    L, n, u0, R1, n1, R2, n2, W = keep[0]
    M3 = Masker(10.0, 1.0, 990.0, 89.0, ref)
    ok10 = M3.ok(W)
    print("\n最优：%d 点，巡回 %.0f m；10 mx1度 交付口径复核 = %s" % (n, L, "通过" if ok10 else "未通过"))
    Wt, L2 = two_opt(W)
    print("2-opt 后巡回 %.0f m" % L2)
    for p in Wt:
        print("   (%8.1f, %8.1f)  r=%.0f" % (p[0], p[1], math.hypot(*p)))


if __name__ == "__main__":
    main()