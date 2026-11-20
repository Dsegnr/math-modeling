# 问题四全域证书 q4_detect_cover.py（核心函数摘录）
# cover_bits()：各朝向可见性位图
def cover_bits(wx, wy, X, Y, TH, rmin=None, half=None):
    rmin = SEARCH_RMIN if rmin is None else rmin
    half = SEARCH_HALF if half is None else half
    dx = wx - X
    dy = wy - Y
    vis = dx * dx + dy * dy <= rmin * rmin
    ang = np.degrees(np.arctan2(dy, dx))[:, None]
    diff = (ang - TH[None, :] + 180.0) % 360.0 - 180.0
    cov = vis[:, None] & (np.abs(diff) <= half)
    return int.from_bytes(np.packbits(cov.ravel()).tobytes(), "little")

# greedy_cover()：贪心建覆盖集
def greedy_cover(bits, full):
    chosen, cur, n = [], 0, len(bits)
    while cur != full:
        best, bj = -1, -1
        for j in range(n):
            if j in chosen:
                continue
            g = (bits[j] & ~cur).bit_count()
            if g > best:
                best, bj = g, j
        if best <= 0:
            return None
        chosen.append(bj)
        cur |= bits[bj]
    improved = True
    while improved:
        improved = False
        for j in list(chosen):
            acc = 0
            for k in chosen:
                if k != j:
                    acc |= bits[k]
            if acc == full:
                chosen.remove(j)
                improved = True
    return chosen

# nn_order()：最近邻初始巡回
def nn_order(pts, start=(0.0, 0.0)):
    rem, cur, out = list(pts), start, []
    while rem:
        j = min(rem, key=lambda q: math.hypot(q[0] - cur[0], q[1] - cur[1]))
        out.append(j)
        cur = j
        rem.remove(j)
    return out

# tour_len()：巡回里程
def tour_len(pts):
    s, cur = 0.0, (0.0, 0.0)
    for p in pts:
        s += math.hypot(p[0] - cur[0], p[1] - cur[1])
        cur = p
    return s

# two_opt()：2-opt 改进
def two_opt(pts, iters=200):
    """以原点为起点、开放路径的 2-opt 改进"""
    seq = list(pts)

    def L(s):
        return tour_len(s)

    best = L(seq)
    improved = True
    rounds = 0
    while improved and rounds < iters:
        improved = False
        rounds += 1
        n = len(seq)
        for i in range(n - 1):
            for j in range(i + 1, n):
                cand = seq[:i] + seq[i:j + 1][::-1] + seq[j + 1:]
                v = L(cand)
                if v < best - 1e-9:
                    seq, best, improved = cand, v, True
    return seq, best

# validate()：逐点复核覆盖
def validate(Cpts, step, ostep, tag, rmin, half, X=None, Y=None, TH=None):
    if X is None:
        X, Y = grid(step)
    if TH is None:
        TH = theta_grid(ostep)
    acc = 0
    for w in Cpts:
        acc |= cover_bits(w[0], w[1], X, Y, TH, rmin, half)
    f2 = (1 << (len(X) * len(TH))) - 1
    miss = (f2 ^ (acc & f2)).bit_count()
    print("  复核 %-14s：格点 %6d x 朝向 %3d | 未覆盖 (x,theta) 对 = %d %s"
          % (tag, len(X), len(TH), miss, "OK" if miss == 0 else "FAIL"), flush=True)
    return miss, X, Y, TH

# ...（其余辅助函数与完整可运行版本见支撑材料）