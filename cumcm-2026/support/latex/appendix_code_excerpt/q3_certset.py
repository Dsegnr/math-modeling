# 问题三建证集 q3_certset.py（核心函数摘录）
# matrices()：距离矩阵与方位角矩阵
def matrices(P, X, Y):
    W = np.array(P)
    D = np.sqrt((X[:, None] - W[None, :, 0]) ** 2 + (Y[:, None] - W[None, :, 1]) ** 2)
    A = np.degrees(np.arctan2(Y[:, None] - W[None, :, 1], X[:, None] - W[None, :, 0])) % 360.0
    return D, A

# feasible()：可见数与跨角判据
def feasible(D, A, S):
    vis = D[:, S] <= RMIN
    cnt = vis.sum(axis=1)
    if np.any(cnt < 2):
        return False, int(cnt.min()), None
    ang = np.where(vis, A[:, S], np.nan)
    ang.sort(axis=1)
    idx = np.arange(len(cnt))
    first = ang[:, 0]
    last = ang[idx, np.maximum(cnt - 1, 0)]
    d = np.diff(ang, axis=1)
    inner = np.where(np.isnan(d), -1.0, d).max(axis=1)
    wrap = 360.0 - (last - first)
    maxgap = np.maximum(inner, wrap)
    span = 360.0 - maxgap
    return bool(np.all(span >= GAMMA)), int(cnt.min()), float(span.min())

# ...（其余辅助函数与完整可运行版本见支撑材料）