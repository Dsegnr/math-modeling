"""
Q4 证书布局两级选型：粗网格（40 m x 5度）筛结构 -> 细网格（20 mx2度、10 mx1度）复核。
结构族：{原点?} U 内环(R1,n1)? U 外环(R2,n2)
"""
import math
import numpy as np

from q4_layout2 import grid, ring, cover_bits, nn_tour, tour_len, feasible


def main():
    # -- 第一级：粗网格 --
    Xc, Yc = grid(40.0)
    THc = np.arange(0.0, 360.0, 5.0)
    refc = [(0.0, 0.0)] + ring(1200, 72) + ring(1900, 72)
    fullc = cover_bits(refc, Xc, Yc, THc, 975.0, 87.5)
    print("第一级 40 mx5度：%d 位置 x %d 朝向" % (len(Xc), len(THc)), flush=True)
    cands = []
    for use0 in (True, False):
        for R1 in (0, 900, 1000, 1100, 1200, 1300, 1400):
            for n1 in ((0,) if R1 == 0 else (5, 6, 8, 9, 12, 15)):
                for R2 in (1850, 1900, 2000, 2100):
                    for n2 in (9, 12, 15, 18, 24):
                        pts = ([(0.0, 0.0)] if use0 else []) \
                            + (ring(R1, n1) if R1 else []) + ring(R2, n2)
                        if not feasible(pts, Xc, Yc, THc, 975.0, 87.5, fullc):
                            continue
                        W = nn_tour([tuple(map(float, p)) for p in pts])
                        cands.append((tour_len(W), len(pts), use0, R1, n1, R2, n2, W))
    cands.sort()
    print("粗筛可行 %d 个；前 12 个：" % len(cands), flush=True)
    print(" %8s %5s %5s %6s %5s %6s %5s" % ("里程/m", "点数", "原点", "内环R", "n1", "外环R", "n2"))
    for L, n, u0, R1, n1, R2, n2, W in cands[:12]:
        print(" %8.0f %5d %5s %6d %5d %6d %5d" % (L, n, "是" if u0 else "否", R1, n1, R2, n2))
    # -- 第二级：细网格复核前 20 个 --
    Xf, Yf = grid(20.0)
    THf = np.arange(0.0, 360.0, 2.0)
    reff = [(0.0, 0.0)] + ring(1200, 72) + ring(1900, 72)
    fullf = cover_bits(reff, Xf, Yf, THf, 975.0, 87.5)
    print("\n第二级 20 mx2度 复核：", flush=True)
    keep = []
    for L, n, u0, R1, n1, R2, n2, W in cands[:20]:
        ok = feasible(W, Xf, Yf, THf, 975.0, 87.5, fullf)
        print(" %8.0f m  %5d 点  原点=%s 内环%4dx%2d 外环%4dx%2d  -> %s"
              % (L, n, "是" if u0 else "否", R1, n1, R2, n2, "OK" if ok else "否"), flush=True)
        if ok:
            keep.append((L, n, u0, R1, n1, R2, n2, W))
    if not keep:
        print(" 无通过第二级的结构", flush=True)
        return
    L, n, u0, R1, n1, R2, n2, W = keep[0]
    X10, Y10 = grid(10.0)
    TH1 = np.arange(0.0, 360.0, 1.0)
    ref10 = [(0.0, 0.0)] + ring(1200, 72) + ring(1900, 72)
    full10 = cover_bits(ref10, X10, Y10, TH1, 990.0, 89.0)
    ok10 = feasible(W, X10, Y10, TH1, 990.0, 89.0, full10)
    print("\n最优结构（%d 点，%.0f m）：10 mx1度 交付口径复核 = %s" % (n, L, "通过" if ok10 else "未通过"))
    print("  原点=%s 内环 R=%d n=%d 外环 R=%d n=%d" % (u0, R1, n1, R2, n2))
    for p in W:
        print("   (%8.1f, %8.1f)  r=%.0f" % (p[0], p[1], math.hypot(*p)))


if __name__ == "__main__":
    main()