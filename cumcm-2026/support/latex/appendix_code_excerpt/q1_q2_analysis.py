# 问题一、二数值实验 q1_q2_analysis.py（核心函数摘录）
# hull()：单调链求凸包
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

# diameter_calipers()：旋转卡壳求直径
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

# _welzl()：最小外接圆递归基
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

# mec()：最小外接圆入口
def mec(P, rng=None):
    lst = [(float(p[0]), float(p[1])) for p in P]
    (rng or random).shuffle(lst)
    return _welzl(lst, [], len(lst))

# wilson()：Wilson 得分区间
def wilson(k, n, z=1.96):
    p = k / n
    ctr = (p + z * z / (2 * n)) / (1 + z * z / n)
    hw = z / (1 + z * z / n) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ctr - hw, ctr + hw

# ratio_of_region()：区域直径与最小外接圆直径之比
def ratio_of_region(poly):
    H = hull(poly)
    if len(H) < 3:
        return None
    D, _ = diameter_bruteforce(H)
    if D < 1e-9:
        return None
    ctr, rho = mec_bruteforce(H)
    return D, rho, rho / (D / 2.0), H, ctr

# ...（其余辅助函数与完整可运行版本见支撑材料）