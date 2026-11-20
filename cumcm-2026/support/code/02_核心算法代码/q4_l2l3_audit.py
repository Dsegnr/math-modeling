"""问题四 L2/L3 可定位性全域审计。
对每个 (x, theta) 统计证书段可检出航点数与最佳交会角，判定 L2（可见数 >= 2）与 L3（交会角 >= gamma，默认 30 度）缺口。
用法：python q4_l2l3_audit.py [gamma度]"""
import os
import sys
import json
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ARENA, RMIN = 1800.0, 1000.0


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


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
            okj, aj = angs[j]
            both = oki & okj
            if not np.any(both):
                continue
            diff = np.abs(((ang_i - ang_j) + 180.0) % 360.0 - 180.0)   # 源处两方向的夹角
            angij = np.where(diff > 90.0, 180.0 - diff, diff)[:, None]
            upd = both & (angij > best)
            best = np.where(upd, angij.astype(np.float32), best)
    return cnt, best


def report(tag, cnt, best, gamma):
    n = cnt.size
    l1 = np.count_nonzero(cnt >= 1) / n * 100
    l2 = np.count_nonzero(cnt >= 2) / n * 100
    l3 = np.count_nonzero((cnt >= 2) & (best >= gamma)) / n * 100
    print("  %-26s 可见点数 min=%d 中位=%.0f | L1 %.2f%% | L2 %.2f%% | L3(>=%.0f度) %.2f%%"
          % (tag, cnt.min(), np.median(cnt), l1, l2, gamma, l3), flush=True)
    return l2, l3


def main():
    gamma = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    d = json.load(open(os.path.join(BASE, "waypoints_p4.json"), encoding="utf-8"))
    allpts = [tuple(map(float, p)) for p in d["waypoints"]]
    ncert = int(d["n_cert"])
    cert, supply = allpts[:ncert], allpts[ncert:]
    X, Y = grid(40.0)
    TH = np.arange(0.0, 360.0, 15.0)
    print("网格 %d 位置 x %d 朝向 = %.2f M 对（证书段 %d 点，补给点 %d 点）"
          % (len(X), len(TH), len(X) * len(TH) / 1e6, len(cert), len(supply)), flush=True)
    c1, b1 = audit_pairs(cert, None, X, Y, TH)
    report("证书段（31 点）", c1, b1, gamma)
    c2, b2 = audit_pairs(cert + supply, None, X, Y, TH)
    report("证书段+50 补给点", c2, b2, gamma)
    # 打印 L2/L3 缺口样例
    bad = np.argwhere((c1 < 2) | ((c1 >= 2) & (b1 < gamma)))
    print("\n证书段下 L2/L3 未达标的 (x,theta) 对数：%d" % len(bad), flush=True)
    for k, (i, j) in enumerate(bad[:10]):
        print("   样例%d: x=(%.0f,%.0f) theta=%.0f度  可见点=%d 最佳交会角=%.1f度"
              % (k + 1, X[i], Y[i], TH[j], c1[i, j], b1[i, j]))


if __name__ == "__main__":
    main()
