"""
Q3 布局系统扫描：内环半径 x 外环半径 x 外环点数 x 相位
  约束：L1 盲区 <= 1000 m 且 L2 全域 >=2 可测（否则终止时会漏源）
  目标：300 局随机案例的平均总虚拟时间
用法：python q3_sweep.py [每配置局数]
"""
import sys
import numpy as np

import q3_offline_eval as Q
from q3_tune import grid, ring, cert


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    X, Y = grid()
    rng = np.random.default_rng(20260911)
    cases = [Q.gen_case(rng) for _ in range(nrun)]
    print("布局扫描：%d 局/配置" % nrun)
    print(" %-30s %6s %7s %6s %6s %8s %9s %9s" %
          ("布局", "点数", "盲区/m", "L1", "L2", "清除率", "总时间/s", "s/源"))
    out = []
    for r_in in (0, 1):
        for r_out in (700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600):
            for n_out in (10, 12, 15, 18, 21, 24):
                for off in (0.0,):
                    # r_in=1 表示把原点（机器狗起飞点，零移动测量）作为第一个航点
                    pts = ([(0.0, 0.0)] if r_in else []) + ring(r_out, n_out, off)
                    l1, l2, worst, blind = cert(pts, X, Y)
                    if not (l1 and l2):
                        continue
                    W = Q.nn_tour([tuple(map(float, p)) for p in pts])
                    masks = Q.build_masks(W)
                    rows = [Q.run_policy(W, c, ncert=len(W), masks=masks) for c in cases]
                    tt = np.array([r["t"] for r in rows])
                    ok = np.mean([r["cleared"] == r["n_src"] for r in rows])
                    per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
                    out.append((tt.mean(), per, ok, len(pts), blind, r_in, r_out, n_out, off))
    out.sort()
    for t, per, ok, n, blind, ri, ro, no, off in out:
        print(" 内环%4d+外环%4dx%2d off%4.0f      %6d %7.1f %6s %6s %7.1f%% %9.0f %9.0f" %
              (ri, ro, no, off, n, blind, "OK", "OK", 100 * ok, t, per))


if __name__ == "__main__":
    main()