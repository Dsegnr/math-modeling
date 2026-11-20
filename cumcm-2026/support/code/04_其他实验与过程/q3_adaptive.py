"""
Q3 算法升级验证：覆盖子集前置 + 动态终止（覆盖完备即止）+ 频道缺失证明（停测无源频道）
对照：现行版（全巡回 + 静态终止）
用法：python q3_adaptive.py [局数]
"""
import sys
import math
import numpy as np

import q3_offline_eval as Q
from q3_tune import grid, ring, cert


def report(rows, label):
    tt = np.array([r["t"] for r in rows])
    ok = 100 * np.mean([r["cleared"] == r["n_src"] for r in rows])
    per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
    print(" %-34s %7.1f%% %8.0f %8.0f %8.0f %8.0f %7.0f %7.0f" %
          (label, ok, tt.mean(), per, np.mean([r["mv"] for r in rows]),
           np.mean([r["me"] for r in rows]), np.mean([r["sw"] for r in rows]),
           np.mean([r["n_meas"] for r in rows])))


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    X, Y = grid()
    S17 = [(779, -450), (1427, -464), (1237, -1237), (453, -1690), (0, -900), (-464, -1427),
           (-875, -1516), (-1214, -882), (-900, 0), (-1750, 0), (-1516, 875), (-875, 1516),
           (-450, 779), (0, 1750), (464, 1427), (849, 849), (1690, 453)]
    layouts = {"S17(原)": S17, "R15(单环990x15)": ring(990, 15)}
    rng = np.random.default_rng(2468)
    cases = [Q.gen_case(rng) for _ in range(nrun)]
    print(" %-34s %8s %8s %8s %8s %8s %7s %7s" %
          ("配置（%d 局）" % nrun, "清除率", "总时间", "s/源", "移动", "检测", "切频", "measure"))
    for name, pts in layouts.items():
        W0 = Q.nn_tour([tuple(map(float, p)) for p in pts])
        m0 = Q.build_masks(W0)
        Wc, ncore = Q.cover_first_order(W0, m0[0], m0[1])
        mc = Q.build_masks(Wc)
        l1, l2, worst, blind = cert(pts, X, Y)
        print("   [%s] 点数=%d 盲区=%.0f m 覆盖子集=%d 点 | 巡回 %.0f m -> 覆盖前置 %.0f m"
              % (name, len(pts), blind, ncore,
                 sum(math.hypot(W0[i][0] - (W0[i - 1] if i else (0, 0))[0],
                                W0[i][1] - (W0[i - 1] if i else (0, 0))[1]) for i in range(len(W0))),
                 sum(math.hypot(Wc[i][0] - (Wc[i - 1] if i else (0, 0))[0],
                                Wc[i][1] - (Wc[i - 1] if i else (0, 0))[1]) for i in range(len(Wc)))))
        report([Q.run_policy(W0, c, ncert=len(W0), masks=m0) for c in cases], name + " 现行")
        report([Q.run_policy(W0, c, ncert=len(W0), masks=m0, dyn_stop=True) for c in cases],
               name + " +动态终止")
        report([Q.run_policy(Wc, c, ncert=len(Wc), masks=mc, dyn_stop=True) for c in cases],
               name + " +覆盖前置+动态终止")
        report([Q.run_policy(Wc, c, ncert=len(Wc), masks=mc, dyn_stop=True, prune=True) for c in cases],
               name + " +前置+动态+缺失证明")


if __name__ == "__main__":
    main()
