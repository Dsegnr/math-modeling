"""
Q4 证书布局选型（按"总时间代理"排序）：
  - 位掩码用 bitorder='little' 打包，彻底避免字节补位被误判为"未覆盖"；
  - 结构族 {原点?} U 内环(R1,n1)? U 外环(R2,n2)；
  - 目标不是点数最少，而是 时间代理 J = 巡回里程/5 + n_点 x (未现频道数 x 6 s)
    -- 因为每访问一个证书点都要把所有"尚未出现的频道"各测一次。
用法：python q4_layout5.py [未现频道数]
"""
import os
import math
import sys
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
    def __init__(self, step, ostep, rmin, half):
        self.X, self.Y = grid(step)
        self.TH = np.arange(0.0, 360.0, ostep)
        self.rmin, self.half = rmin, half
        self.n = len(self.X) * len(self.TH)
        self.full = (1 << self.n) - 1
        self.cache = {}

    def bits(self, p):
        if p in self.cache:
            return self.cache[p]
        dx, dy = p[0] - self.X, p[1] - self.Y
        vis = dx * dx + dy * dy <= self.rmin * self.rmin
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - self.TH[None, :] + 180.0) % 360.0 - 180.0)
        cov = (vis[:, None] & (diff <= self.half)).ravel()
        b = int.from_bytes(np.packbits(cov, bitorder="little").tobytes(), "little")
        self.cache[p] = b
        return b

    def ok(self, pts):
        acc = 0
        for p in pts:
            acc |= self.bits(p)
        return (self.full & ~acc) == 0


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


def main():
    n_absent = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    M = Masker(20.0, 2.0, 990.0, 89.0)
    print("20 mx2度 (990,89)：%d 位/点；按未现频道数 %d（每点 %.0f s）排序"
          % (M.n, n_absent, n_absent * 6.0), flush=True)
    out = []
    for use0 in (True, False):
        for R1 in (0, 900, 950, 1000, 1050, 1100, 1200, 1400):
            for n1 in ((0,) if R1 == 0 else (3, 4, 5, 6, 8, 9, 10, 12, 15)):
                for R2 in (1810, 1850, 1900, 1950, 2000):
                    for n2 in (10, 12, 14, 15, 16, 18, 20, 24):
                        pts = ([(0.0, 0.0)] if use0 else []) \
                            + (ring(R1, n1) if R1 else []) + ring(R2, n2)
                        if not M.ok(pts):
                            continue
                        W = nn_tour([tuple(map(float, p)) for p in pts])
                        L = tour_len(W)
                        J = L / 5.0 + len(W) * n_absent * 6.0
                        out.append((J, L, len(W), use0, R1, n1, R2, n2, W))
    out.sort()
    print("可行结构 %d 个；按时间代理 J 升序前 15：" % len(out), flush=True)
    print(" %9s %8s %5s %5s %6s %5s %6s %5s" %
          ("J/s", "里程/m", "点数", "原点", "内环R", "n1", "外环R", "n2"))
    for J, L, n, u0, R1, n1, R2, n2, W in out[:15]:
        print(" %9.0f %8.0f %5d %5s %6d %5d %6d %5d" %
              (J, L, n, "是" if u0 else "否", R1, n1, R2, n2))
    if out:
        J, L, n, u0, R1, n1, R2, n2, W = out[0]
        print("\n最优结构：%d 点、巡回 %.0f m、J=%.0f s" % (n, L, J))
        print("  原点=%s 内环 R=%d n=%d 外环 R=%d n=%d" % (u0, R1, n1, R2, n2))
        for p in W:
            print("   (%8.1f, %8.1f)  r=%.0f" % (p[0], p[1], math.hypot(*p)))


if __name__ == "__main__":
    main()