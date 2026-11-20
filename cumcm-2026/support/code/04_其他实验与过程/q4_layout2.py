"""
Q4 证书布局的结构化重选型：把「原点/内环 + 外环」当作结构族，
在满足「位置 x 朝向」保证检出证书的前提下，最小化巡回里程。

结构：{原点} U 内环(R1,n1) U 外环(R2,n2)
  - 外环半径必须 > 1800（边界源朝外时，捕获点必须位于其外侧），故 R2 in {1850,1900,2000}
  - 内环负责中半径源朝外波束与圆心附近的可测性
用法：python q4_layout2.py
"""
import os
import math
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ARENA = 1800.0
R_SEARCH, HALF_SEARCH = 975.0, 87.5     # 搜索留余量
R_VALID, HALF_VALID = 990.0, 89.0       # 交付口径


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def ring(r, n, off=0.0):
    return [(r * math.cos(math.radians(360.0 * k / n + off)),
             r * math.sin(math.radians(360.0 * k / n + off))) for k in range(n)]


def cover_bits(pts, X, Y, TH, rmin, half):
    acc = 0
    for (wx, wy) in pts:
        dx, dy = wx - X, wy - Y
        vis = dx * dx + dy * dy <= rmin * rmin
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - TH[None, :] + 180.0) % 360.0 - 180.0)
        cov = vis[:, None] & (diff <= half)
        acc |= int.from_bytes(np.packbits(cov.ravel()).tobytes(), "little")
    return acc


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


def feasible(pts, X, Y, TH, rmin, half, full):
    acc = cover_bits(pts, X, Y, TH, rmin, half)
    return (full & ~acc).bit_count() == 0


def main():
    X, Y = grid(20.0)
    TH = np.arange(0.0, 360.0, 2.0)
    N = len(X) * len(TH)
    # 全域参考掩码：用「原点 + 超密环」构造可达全集
    ref = [(0.0, 0.0)] + ring(1200, 72) + ring(1900, 72)
    full = cover_bits(ref, X, Y, TH, R_SEARCH, HALF_SEARCH)
    print("搜索网格 %d 位置 x %d 朝向 = %.2f M 对" % (len(X), len(TH), N / 1e6))
    cands = []
    for use0 in (True, False):
        for R1 in (0, 900, 1000, 1100, 1200, 1300):
            for n1 in ((0,) if R1 == 0 else (6, 9, 12, 15)):
                for R2 in (1850, 1900, 2000):
                    for n2 in (9, 12, 15, 18, 24):
                        pts = ([(0.0, 0.0)] if use0 else []) \
                            + (ring(R1, n1) if R1 else []) + ring(R2, n2)
                        ok = feasible(pts, X, Y, TH, R_SEARCH, HALF_SEARCH, full)
                        if ok:
                            W = nn_tour([tuple(map(float, p)) for p in pts])
                            cands.append((tour_len(W), len(pts), use0, R1, n1, R2, n2, W))
    cands.sort()
    print("\n可行结构（按巡回里程升序，前 15）：")
    print(" %8s %5s %5s %6s %5s %6s %5s" % ("里程/m", "点数", "原点", "内环R", "n1", "外环R", "n2"))
    for L, n, u0, R1, n1, R2, n2, W in cands[:15]:
        print(" %8.0f %5d %5s %6d %5d %6d %5d" % (L, n, "是" if u0 else "否", R1, n1, R2, n2))
    if cands:
        L, n, u0, R1, n1, R2, n2, W = cands[0]
        X2, Y2 = grid(10.0)
        TH2 = np.arange(0.0, 360.0, 1.0)
        ref2 = [(0.0, 0.0)] + ring(1200, 72) + ring(1900, 72)
        full2 = cover_bits(ref2, X2, Y2, TH2, R_VALID, HALF_VALID)
        ok2 = feasible(W, X2, Y2, TH2, R_VALID, HALF_VALID, full2)
        print("\n最优结构复核（10 m x 1度）：%s" % ("通过" if ok2 else "未通过"))
        print("最优结构巡回（%d 点，%.0f m）：" % (n, L))
        for p in W:
            print("   (%8.1f, %8.1f)" % p)


if __name__ == "__main__":
    main()