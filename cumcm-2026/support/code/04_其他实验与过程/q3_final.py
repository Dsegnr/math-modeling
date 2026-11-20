"""
Q3 终选：现用 17 点建证集 vs 新 15 点环（半径 990 m）的详细对照 + 策略开关扫描。
用法：python q3_final.py [局数]
"""
import sys
import numpy as np

import q3_offline_eval as Q
from q3_tune import grid, ring, cert


def stats(rows, label):
    tt = np.array([r["t"] for r in rows])
    ok = 100 * np.mean([r["cleared"] == r["n_src"] for r in rows])
    per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
    mv = np.mean([r["mv"] for r in rows])
    me = np.mean([r["me"] for r in rows])
    sw = np.mean([r["sw"] for r in rows])
    cl = np.mean([r["cl"] for r in rows])
    nm = np.mean([r["n_meas"] for r in rows])
    print(" %-30s %7.1f%% %8.0f %8.0f %8.0f %8.0f %7.0f %7.0f %7.0f" %
          (label, ok, tt.mean(), per, mv, me, sw, cl, nm))


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    X, Y = grid()
    S17 = [(779, -450), (1427, -464), (1237, -1237), (453, -1690), (0, -900), (-464, -1427),
           (-875, -1516), (-1214, -882), (-900, 0), (-1750, 0), (-1516, 875), (-875, 1516),
           (-450, 779), (0, 1750), (464, 1427), (849, 849), (1690, 453)]
    R15 = ring(990, 15)
    for name, pts in (("S17 现用", S17), ("R15 单环990x15", R15)):
        l1, l2, worst, blind = cert(pts, X, Y)
        print(" %s：%d 点，盲区 %.1f m，L1 %s，L2 %s" %
              (name, len(pts), blind, "OK" if l1 else "NG", "OK" if l2 else "NG"))
    rng = np.random.default_rng(777)
    cases = [Q.gen_case(rng) for _ in range(nrun)]
    print("\n布局 x 策略对照（%d 局）" % nrun)
    print(" %-30s %8s %8s %8s %8s %8s %7s %7s %7s" %
          ("配置", "清除率", "总时间", "s/源", "移动", "检测", "切频", "清除", "measure"))
    for name, pts in (("S17 现用", S17), ("R15 单环990x15", R15)):
        W = Q.nn_tour([tuple(map(float, p)) for p in pts])
        masks = Q.build_masks(W)
        for flags in (dict(side_clear=True, prune=True, cull_obs=3),
                      dict(side_clear=True, prune=False, cull_obs=3),
                      dict(side_clear=True, prune=True, cull_obs=99),
                      dict(side_clear=False, prune=True, cull_obs=3)):
            rows = [Q.run_policy(W, c, ncert=len(W), masks=masks, **flags) for c in cases]
            tag = "%s | 顺路%s 剪枝%s cull%d" % (
                name, "ON" if flags["side_clear"] else "OFF",
                "ON" if flags["prune"] else "OFF", flags["cull_obs"])
            stats(rows, tag)


if __name__ == "__main__":
    main()