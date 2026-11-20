"""Q3 联合路径（剩余航点 U 待清源，最近邻 + 2-opt）与现行「固定环序 + 最优绕道点」离线对照"""
import sys
import numpy as np

import q3_offline_eval as Q
from q3_tune import ring


def rep(rows, label):
    tt = np.array([r["t"] for r in rows])
    ok = 100 * np.mean([r["cleared"] == r["n_src"] for r in rows])
    per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
    print(" %-30s %7.1f%% %8.0f %8.0f %8.0f %8.0f %7.0f %7.0f" %
          (label, ok, tt.mean(), per, np.mean([r["mv"] for r in rows]),
           np.mean([r["me"] for r in rows]), np.mean([r["sw"] for r in rows]),
           np.mean([r["n_meas"] for r in rows])))


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    W = Q.nn_tour([tuple(map(float, p)) for p in ring(990, 15)])
    masks = Q.build_masks(W)
    rng = np.random.default_rng(4321)
    cases = [Q.gen_case(rng) for _ in range(nrun)]
    print(" %-30s %8s %8s %8s %8s %8s %7s" %
          ("配置（%d 局）" % nrun, "清除率", "总时间", "s/源", "移动", "检测", "measure"))
    rep([Q.run_policy(W, c, ncert=len(W), masks=masks) for c in cases], "固定环序+最优绕道点（现行）")
    for sd in (0.0, 0.05):
        rep([Q.run_policy_joint(W, c, masks=masks, bear_sigma=sd, seed=i) for i, c in enumerate(cases)],
            "联合路径 2-opt（sigma=%.2f）" % sd)
        rep([Q.run_policy_joint(W, c, masks=masks, bear_sigma=sd, seed=i, wc_gamma=30.0)
             for i, c in enumerate(cases)], "联合路径 2-opt + 良态门槛（sigma=%.2f）" % sd)


if __name__ == "__main__":
    main()