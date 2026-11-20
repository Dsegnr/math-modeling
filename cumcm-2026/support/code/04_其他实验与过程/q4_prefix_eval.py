"""
评估 Q4 新巡回（证书前缀 + 补给点）在不同前缀长度下的
  L1 保证检出率 与 L2/L3 可定位率

对 20 m x 10度 的 (位置, 朝向) 网格，统计：
  c1 = 前缀中能检出该 (x,theta) 的航点数
  L1：c1 >= 1（保证检出）
  L2：c1 >= 2（两点可交会）
  L3：存在可见点对，交会角 >= 30度
"""
import os
import math
import json
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ARENA, RMIN, HALF = 1800.0, 990.0, 89.0


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def det_matrix(pts, X, Y, TH):
    """返回 (Npos, Ntheta, Nw) 的 bool 张量会太大，改为逐点累加"""
    cnt = np.zeros((len(X), len(TH)), dtype=np.int16)
    for (wx, wy) in pts:
        dx = wx - X
        dy = wy - Y
        vis = dx * dx + dy * dy <= RMIN * RMIN
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - TH[None, :] + 180.0) % 360.0 - 180.0)
        cnt += (vis[:, None] & (diff <= HALF)).astype(np.int16)
    return cnt


def best_pair_angle(pts, X, Y, TH, targets, tmax=4000):
    """对给定 (x,theta) 子集，求最佳可见点对的交会角（度）"""
    out = []
    for n, (xi, ti) in enumerate(targets[:tmax]):
        x, y, th = X[xi], Y[xi], TH[ti]
        vis = []
        for (wx, wy) in pts:
            dx, dy = wx - x, wy - y
            if dx * dx + dy * dy > RMIN * RMIN:
                continue
            a = math.degrees(math.atan2(dy, dx))
            if abs((a - th + 180.0) % 360.0 - 180.0) <= HALF:
                vis.append((dx, dy))
        best = 0.0
        for i in range(len(vis)):
            for j in range(i + 1, len(vis)):
                u, v = vis[i], vis[j]
                c = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
                ang = math.degrees(math.acos(max(-1.0, min(1.0, c))))
                if ang > 90.0:
                    ang = 180.0 - ang
                best = max(best, ang)
        out.append(best)
    return np.array(out)


def main():
    d = json.load(open(os.path.join(BASE, "_scratch", "certset_p4_cover.json"), encoding="utf-8"))
    tour = [tuple(p) for p in d["tour"]]
    ncert = d["n_cert"]
    X, Y = grid(20.0)
    TH = np.arange(0.0, 360.0, 10.0)
    print("Q4 新巡回前缀能力评估")
    print("巡回总点数 %d，证书前缀 %d 点" % (len(tour), ncert))
    print("评估网格：%d 位置 x %d 朝向 = %.2f M 对\n" % (len(X), len(TH), len(X) * len(TH) / 1e6))
    print(" %-10s %8s %8s %8s %8s" % ("前缀长度", "L1%", "L2%", "最少可见", "中位可见"))
    for K in (13, 19, 23, 31, len(tour)):
        if K > len(tour):
            continue
        cnt = det_matrix(tour[:K], X, Y, TH)
        tot = cnt.size
        l1 = 100.0 * np.count_nonzero(cnt >= 1) / tot
        l2 = 100.0 * np.count_nonzero(cnt >= 2) / tot
        print(" %-10d %7.2f %7.2f %8d %8.1f" % (K, l1, l2, cnt.min(), np.median(cnt)))
    # L3：对证书前缀内 L2 达标的子集抽样评估最佳交会角
    cnt = det_matrix(tour[:ncert], X, Y, TH)
    idx = np.argwhere(cnt >= 2)
    if len(idx) > 0:
        rng = np.random.default_rng(0)
        sel = idx[rng.choice(len(idx), size=min(3000, len(idx)), replace=False)]
        targets = [(int(a), int(b)) for a, b in sel]
        ang = best_pair_angle(tour[:ncert], X, Y, TH, targets, tmax=3000)
        print("\n证书前缀内（%d 个 L2 达标对抽样）最佳交会角：" % len(targets))
        print("  中位 %.1f度 | 5%%分位 %.1f度 | 最小 %.1f度 | <30度 占比 %.2f%%"
              % (np.median(ang), np.percentile(ang, 5), ang.min(), 100.0 * (ang < 30).mean()))

    # 对照：现用 55 点序（按原顺序）
    old = [tuple(map(float, p)) for p in
           json.load(open(os.path.join(BASE, "waypoints_p4.json"), encoding="utf-8"))["waypoints"]]
    print("\n对照：现用 55 点序（原顺序）")
    print(" %-10s %8s %8s %8s %8s" % ("前缀长度", "L1%", "L2%", "最少可见", "中位可见"))
    for K in (19, 23, 28, len(old)):
        cnt = det_matrix(old[:K], X, Y, TH)
        tot = cnt.size
        print(" %-10d %7.2f %7.2f %8d %8.1f"
              % (K, 100.0 * np.count_nonzero(cnt >= 1) / tot,
                 100.0 * np.count_nonzero(cnt >= 2) / tot, cnt.min(), np.median(cnt)))


if __name__ == "__main__":
    main()