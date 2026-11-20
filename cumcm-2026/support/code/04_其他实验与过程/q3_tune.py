"""
Q3 布局与策略离线寻优：
  (1) 对候选布局做 L1(可检出)/L2(两点可测)/L3(交会角) 证书检验（20 m 网格）；
  (2) 对通过证书的布局，用 q3_offline_eval 的策略复现器跑 N 局随机案例，比较总时间；
  (3) 扫描策略开关（顺路清除 / 通道覆盖剪枝 / 观测数剔除阈值）。
用法：python q3_tune.py [每配置局数]
"""
import os
import sys
import math
import numpy as np

import q3_offline_eval as Q

BASE = os.path.dirname(os.path.abspath(__file__))
ARENA, STEP = 1800.0, 20.0


def grid(step=STEP):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def ring(r, n, off=0.0):
    return [(r * math.cos(math.radians(360.0 * k / n + off)),
             r * math.sin(math.radians(360.0 * k / n + off))) for k in range(n)]


def cert(pts, X, Y, rmin=1000.0):
    W = np.array(pts)
    d = np.sqrt((X[:, None] - W[None, :, 0]) ** 2 + (Y[:, None] - W[None, :, 1]) ** 2)
    blind = float(d.min(axis=1).max())
    cnt = (d <= rmin).sum(axis=1)
    l1 = bool(blind <= rmin)
    l2 = bool(cnt.min() >= 2)
    worst = 1e9
    if l2:
        for i in np.nonzero(cnt >= 2)[0]:
            vis = np.nonzero(d[i] <= rmin)[0]
            best = 0.0
            for a in range(len(vis)):
                for b in range(a + 1, len(vis)):
                    u = (W[vis[a]][0] - X[i], W[vis[a]][1] - Y[i])
                    v = (W[vis[b]][0] - X[i], W[vis[b]][1] - Y[i])
                    c = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
                    ang = math.degrees(math.acos(max(-1.0, min(1.0, c))))
                    if ang > 90.0:
                        ang = 180.0 - ang
                    best = max(best, ang)
            worst = min(worst, best)
    return l1, l2, (0.0 if worst > 1e8 else worst), blind


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    X, Y = grid()
    S17 = [(779, -450), (1427, -464), (1237, -1237), (453, -1690), (0, -900), (-464, -1427),
           (-875, -1516), (-1214, -882), (-900, 0), (-1750, 0), (-1516, 875), (-875, 1516),
           (-450, 779), (0, 1750), (464, 1427), (849, 849), (1690, 453)]
    S19 = [(0, 0)] + ring(1000, 6) + ring(1700, 12)
    cands = {
        "S17(现行)": S17,
        "S19(旧)": S19,
        "中心+1200环6": [(0, 0)] + ring(1200, 6),
        "中心+1050环6": [(0, 0)] + ring(1050, 6),
        "中心+1000环6+1500环12": [(0, 0)] + ring(1000, 6) + ring(1500, 12, 30),
        "1300环12": ring(1300, 12),
    }
    print("(1) 覆盖证书检验（20 m 网格，%d 格点）" % len(X))
    print(" %-24s %6s %8s %6s %6s %10s" % ("布局", "点数", "盲区/m", "L1", "L2", "最坏交会角/度"))
    for name, pts in cands.items():
        l1, l2, worst, blind = cert(pts, X, Y)
        print(" %-24s %6d %8.1f %6s %6s %10.1f" %
              (name, len(pts), blind, "OK" if l1 else "NG", "OK" if l2 else "NG", worst))
    print("\n(2) 策略复现（%d 局/配置）" % nrun)
    rng = np.random.default_rng(20260911)
    cases = [Q.gen_case(rng) for _ in range(nrun)]
    print(" %-24s %8s %10s %10s %9s %9s %9s" %
          ("布局", "清除率", "总时间/s", "s/源", "移动/s", "检测/s", "measure"))
    for name, pts in cands.items():
        W = Q.nn_tour([tuple(map(float, p)) for p in pts])
        masks = Q.build_masks(W)
        rows = [Q.run_policy(W, c, ncert=len(W), masks=masks) for c in cases]
        tt = np.array([r["t"] for r in rows])
        ok = np.mean([r["cleared"] == r["n_src"] for r in rows])
        per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
        print(" %-24s %7.1f%% %10.0f %10.0f %9.0f %9.0f %9.0f" %
              (name, 100 * ok, tt.mean(), per,
               np.mean([r["mv"] for r in rows]), np.mean([r["me"] for r in rows]),
               np.mean([r["n_meas"] for r in rows])))


if __name__ == "__main__":
    main()