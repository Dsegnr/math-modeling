# 问题四 L2/L3 审计 q4_l2l3_audit.py（核心函数摘录）
# audit()：单点 L2/L3 审计
def audit(pts, X, Y, TH, rmin=RMIN):
    """返回 (可见点数数组, 最佳交会角数组)，形状 (npos, ntheta)"""
    cnt = np.zeros((len(X), len(TH)), dtype=np.int16)
    best = np.zeros((len(X), len(TH)), dtype=np.float32)
    for (wx, wy) in pts:
        dx, dy = wx - X, wy - Y           # 源 -> 航点
        d = np.sqrt(dx * dx + dy * dy)
        vis = d <= rmin
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - TH[None, :] + 180.0) % 360.0 - 180.0)
        ok = vis[:, None] & (diff <= 90.0)
        cnt += ok.astype(np.int16)
        # 更新该航点与"此前可见航点"的交会角：两可见点方位差 |Delta| 的补角
        if np.any(ok):
            prev_ang = ang  # 单个航点的方位
            # 与已记录的最近可见方位比较（近似：用已存的最大交会角，下轮再更新）
        # 为精确起见，改为两两比较（航点数不多）
    return cnt, best

# audit_pairs()：点对交会角审计
def audit_pairs(cert, supply, X, Y, TH, rmin=RMIN):
    """逐位置精确计算：可见点数、最大交会角（源处两可见点夹角，取 <=90度 的等价锐角）"""
    npos = len(X)
    cnt = np.zeros((npos, len(TH)), dtype=np.int16)
    best = np.zeros((npos, len(TH)), dtype=np.float32)
    angs = []
    for (wx, wy) in cert:
        dx, dy = wx - X, wy - Y
        d = np.sqrt(dx * dx + dy * dy)
        vis = d <= rmin
        ang = np.degrees(np.arctan2(dy, dx))           # (npos,)
        ok = vis[:, None] & (np.abs((ang[:, None] - TH[None, :] + 180.0) % 360.0 - 180.0) <= 90.0)
        cnt += ok.astype(np.int16)
        angs.append((ok, ang))
    # 两两交会角（对每一对可见航点取源处夹角）
    m = len(angs)
    for i in range(m):
        oki, ang_i = angs[i]
        for j in range(i + 1, m):
            okj, ang_j = angs[j]
            both = oki & okj
            if not np.any(both):
                continue
            diff = np.abs(((ang_i - ang_j) + 180.0) % 360.0 - 180.0)   # 源处两方向的夹角
            angij = np.where(diff > 90.0, 180.0 - diff, diff)[:, None]
            upd = both & (angij > best)
            best = np.where(upd, angij.astype(np.float32), best)
    return cnt, best

# report()：结果汇总输出
def report(tag, cnt, best, gamma):
    n = cnt.size
    l1 = np.count_nonzero(cnt >= 1) / n * 100
    l2 = np.count_nonzero(cnt >= 2) / n * 100
    l3 = np.count_nonzero((cnt >= 2) & (best >= gamma)) / n * 100
    print("  %-26s 可见点数 min=%d 中位=%.0f | L1 %.2f%% | L2 %.2f%% | L3(>=%.0f度) %.2f%%"
          % (tag, cnt.min(), np.median(cnt), l1, l2, gamma, l3), flush=True)
    return l2, l3

# ...（其余辅助函数与完整可运行版本见支撑材料）
